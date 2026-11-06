"""Reusable helpers for the IBL probe-annotation workflow."""

from __future__ import annotations

import contextlib
import csv
import dataclasses
import datetime
import functools
import hashlib
import io
import json
import re
import time
from collections.abc import Iterable, Mapping
from typing import Any

import aind_session
import aind_session.utils.codeocean_utils
import npc_session
import upath
from codeocean.data_asset import DataAsset, DataAssetState

import npc_lims.metadata.codeocean_utils as codeocean_utils

ANNOTATIONS_ROOT = upath.UPath("s3://aind-scratch-data/dynamic-routing/annotated_neuroglancer_jsons")
IBL_CONVERSION_ROOT = upath.UPath("s3://aind-scratch-data/dynamic-routing/ibl_conv")
MANIFEST_ROOT = IBL_CONVERSION_ROOT / "manifests"

IBL_CONVERSION_CAPSULE_ID = "09e00815-6730-479c-8b50-355bffb0b2b9"

MANIFEST_COLUMNS = (
    "mouseid",
    "sorted_recording",
    "surface_finding",
    "probe_file",
    "probe_name",
    "probe_shank",
    "probe_id",
    "annotation_format",
)




def normalize_etag(value: object) -> str | None:
    """Normalize the ETag formats returned by different file systems.

    Examples
    --------
    >>> normalize_etag('"abc123"')
    'abc123'
    >>> normalize_etag(None) is None
    True
    """
    if value is None:
        return None
    result = str(value).strip().strip('"').strip("'")
    return result or None


def get_file_version(path: str | upath.UPath) -> str:
    """Return a stable version string for a local or cloud file.

    S3 ETags avoid downloading a potentially large object.  Other file systems
    fall back to SHA-256, which also makes local development deterministic.

    Examples
    --------
    >>> import tempfile
    >>> path = upath.UPath(tempfile.gettempdir()) / "npc-lims-version.txt"
    >>> _ = path.write_text("hello")
    >>> get_file_version(path)[:7]
    'sha256:'
    """
    path = upath.UPath(path)
    info = path.stat()
    etag = normalize_etag(info.get("ETag") or info.get("etag") if isinstance(info, Mapping) else None)
    if etag:
        return f"etag:{etag}"
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def get_annotated_ng_jsons(
    root: str | upath.UPath = ANNOTATIONS_ROOT,
) -> tuple[upath.UPath, ...]:
    """List annotated neuroglancer JSONs that match a standard naming pattern."""
    return tuple(
        sorted(
            (
                path
                for path in upath.UPath(root).glob("*_annotated.json")
                if re.fullmatch(r"\d+_annotated\.json", path.name)
            ),
            key=lambda path: path.name,
        )
    )


def get_manifest_path(subject_id: str | int) -> upath.UPath:
    """Return the canonical success marker for a subject's latest run."""
    return MANIFEST_ROOT / f"{subject_id}_manifest.csv"


def get_manifest_metadata_path(subject_id: str | int) -> upath.UPath:
    """Return the sidecar recording which annotation version was processed."""
    return MANIFEST_ROOT / f"{subject_id}_manifest.json"


def _mtime(path: upath.UPath) -> float:
    info = path.stat()
    value = info.get("mtime") or info.get("LastModified") if isinstance(info, Mapping) else info.st_mtime
    if isinstance(value, datetime.datetime):
        return value.timestamp()
    return float(value or 0)


def annotation_needs_processing(
    annotation_path: str | upath.UPath,
    manifest_path: str | upath.UPath,
    metadata_path: str | upath.UPath | None = None,
) -> bool:
    """Return whether an annotation lacks a current successful manifest.

    New runs write a JSON sidecar containing ``annotation_version``.  For old
    manifests without a sidecar, modification times provide a compatible
    fallback: replacing the annotation after the manifest retriggers the run.
    """
    annotation_path = upath.UPath(annotation_path)
    manifest_path = upath.UPath(manifest_path)
    if not manifest_path.exists():
        return True
    if metadata_path is not None and upath.UPath(metadata_path).exists():
        metadata = json.loads(upath.UPath(metadata_path).read_text())
        return metadata.get("annotation_version") != get_file_version(annotation_path)
    return _mtime(annotation_path) > _mtime(manifest_path)


def parse_probe_and_date(annotation_name: str) -> tuple[str, str]:
    """Extract an Open Ephys probe and MM-DD date from a layer name.

    The current annotation convention is ``<probe>_<MMDD>``.

    Examples
    --------
    >>> parse_probe_and_date("E_0822")
    ('ProbeE', '08-22')
    >>> parse_probe_and_date("A-1201_target")
    ('ProbeA', '12-01')
    """
    match = re.match(
        r"^(?P<probe>[A-F])[_ -](?P<month>\d{2})(?P<day>\d{2})(?:\D|$)",
        annotation_name,
        flags=re.IGNORECASE,
    )
    if match is None:
        raise ValueError(f"Cannot map annotation layer {annotation_name!r}; expected e.g. E_0822")
    return (
        f"Probe{match.group('probe').upper()}",
        f"{match.group('month')}-{match.group('day')}",
    )


def get_sorted_probes(asset: DataAsset) -> frozenset[str]:
    """Probes (e.g. ``ProbeA``) with curated output in a sorted data asset.

    Partially-errored sorting runs (e.g. a CUDA error on one probe) are still
    usable for the remaining probes.
    """
    curated = aind_session.utils.codeocean_utils.get_data_asset_source_dir(asset.id) / "curated"
    return frozenset(
        match.group(0)
        for path in curated.iterdir()
        if (match := re.search(r"Probe[A-F]", path.name))
    )


def _annotation_point_counts(annotation_path: upath.UPath) -> dict[str, int]:
    state = json.loads(annotation_path.read_text())
    return {
        layer["name"]: len(layer.get("annotations") or ())
        for layer in state.get("layers", ())
        if layer.get("type") == "annotation"
    }


@dataclasses.dataclass
class ManifestBuild:
    records: tuple[dict[str, Any], ...]
    sorted_assets: dict[str, DataAsset]
    """Main (non-surface) session name -> sorted asset used"""
    skipped: tuple[str, ...]
    """Human-readable reasons for annotation layers left out of the manifest"""


def build_manifest(
    annotation_path: str | upath.UPath,
    skip_missing_sessions: bool = False,
) -> ManifestBuild:
    """Build manifest rows with aind-session's IBL/Neuroglancer plugins.

    ``aind-session`` currently understands ordinal layer names such as ``A_1``.
    Dynamic Routing annotations use acquisition dates such as ``A_0825``, so
    this adapter uses the plugin's state parser and asset discovery while doing
    that small date-to-recording join here.

    Sorted assets are chosen with `npc_lims.get_session_sorted_data_asset`
    (latest non-errored KS2.5 asset, falling back to the latest errored one).
    Layers are skipped (and reported in ``skipped``) if they are empty, have
    names that don't follow the ``<probe>_<MMDD>`` convention, or refer to a
    probe without curated output in the sorted asset.

    With ``skip_missing_sessions=True`` ("force"), layers whose session has no
    raw/sorted asset yet are skipped (and reported) instead of raising.
    """
    # Importing this optional aind-session extension registers the
    # ``subject.neuroglancer`` and ``subject.ibl_data_converter`` namespaces.
    from aind_session.extensions.smartspim_neuropixels import NeuroglancerState

    annotation_path = upath.UPath(annotation_path)
    subject_id = npc_session.extract_subject(str(annotation_path))
    state = NeuroglancerState(annotation_path)
    try:
        state_subject_id = state.session.subject.id
    except ValueError:
        # newer stitched assets are named `<subject>_<date>_stitched_...`
        # (no `SmartSPIM_` prefix), which aind-session can't parse yet
        state_subject_id = subject_id
    if str(state_subject_id) != str(subject_id):
        raise ValueError(
            f"Filename subject {subject_id} does not match Neuroglancer subject {state_subject_id}"
        )

    converter = aind_session.Subject(subject_id).ibl_data_converter
    surface_recordings = converter.surface_recording_names
    # surface-channel recordings are separate sessions: exclude them so they
    # don't collide with the main recording on the same day
    main_sessions = sorted(
        session.id
        for session in converter.ecephys_sessions
        if session.id not in surface_recordings.values()
    )
    sorted_assets: dict[str, DataAsset] = {}
    for session_name in main_sessions:
        try:
            sorted_assets[session_name] = codeocean_utils.get_session_sorted_data_asset(
                session_name
            )
        except ValueError:
            continue
    sorted_probes = {name: get_sorted_probes(asset) for name, asset in sorted_assets.items()}
    point_counts = _annotation_point_counts(annotation_path)

    records: list[dict[str, Any]] = []
    skipped: list[str] = []
    for annotation_name in state.annotation_names:
        if point_counts.get(annotation_name, 0) == 0:
            skipped.append(f"{annotation_name!r}: empty layer")
            continue
        try:
            probe_name, month_day = parse_probe_and_date(annotation_name)
        except ValueError:
            skipped.append(f"{annotation_name!r}: name doesn't match <probe>_<MMDD>")
            continue
        matches = [
            session_name
            for session_name in main_sessions
            if f"-{month_day}_" in f"{session_name}_"
        ]
        if not matches and skip_missing_sessions:
            skipped.append(f"{annotation_name!r}: no recording found for {month_day}")
            continue
        if len(matches) != 1:
            raise ValueError(
                f"Expected one recording for {annotation_name!r} "
                f"({month_day}), found {matches}"
            )
        session_name = matches[0]
        if session_name not in sorted_assets:
            if skip_missing_sessions:
                skipped.append(f"{annotation_name!r}: no sorted asset for {session_name}")
                continue
            raise ValueError(f"No sorted data asset for {session_name} ({annotation_name!r})")
        sorted_asset = sorted_assets[session_name]
        if probe_name not in sorted_probes[session_name]:
            skipped.append(f"{annotation_name!r}: {probe_name} not in sorted output of {sorted_asset.name}")
            continue
        record = converter.ManifestRecord(
            mouseid=subject_id,
            sorted_recording=sorted_asset.name,
            surface_finding=surface_recordings.get(session_name),
            probe_file=annotation_path.stem,
            probe_name=probe_name,
            probe_id=annotation_name,
        )
        records.append(dataclasses.asdict(record))
    if not records:
        raise ValueError(f"No annotation layers found in {annotation_path}")
    return ManifestBuild(
        records=tuple(records), sorted_assets=sorted_assets, skipped=tuple(skipped)
    )


def build_manifest_records(
    annotation_path: str | upath.UPath,
) -> tuple[dict[str, Any], ...]:
    """Manifest rows only - see `build_manifest`."""
    return build_manifest(annotation_path).records


def manifest_csv(records: Iterable[Mapping[str, Any]]) -> str:
    """Serialize manifest records in the converter capsule's column order.

    Examples
    --------
    >>> record = {"mouseid": "123", "sorted_recording": "sorted",
    ...           "probe_file": "annotation", "probe_name": "ProbeA",
    ...           "probe_id": "A_0101"}
    >>> text = manifest_csv([record])
    >>> text.splitlines()[0]
    'mouseid,sorted_recording,surface_finding,probe_file,probe_name,probe_shank,probe_id,annotation_format'
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=MANIFEST_COLUMNS)
    writer.writeheader()
    for record in records:
        row = {column: record.get(column) for column in MANIFEST_COLUMNS}
        row["annotation_format"] = row["annotation_format"] or "json"
        writer.writerow(row)
    return output.getvalue()


def find_processed_asset(
    subject_id: str | int,
    probe_annotations_asset_id: str,
    created_after: int,
    conversion_capsule_id: str = IBL_CONVERSION_CAPSULE_ID,
) -> DataAsset | None:
    """Find the ready converter output derived from one annotation asset."""
    candidates = []
    for asset in codeocean_utils.get_subject_data_assets(subject_id, ttl_hash=round(time.time())):
        provenance = asset.provenance
        if (
            asset.created >= created_after
            and asset.state == DataAssetState.Ready
            and provenance is not None
            and provenance.capsule == conversion_capsule_id
            and probe_annotations_asset_id in (provenance.data_assets or ())
        ):
            candidates.append(asset)
    return max(candidates, key=lambda asset: asset.created, default=None)


# status helpers ----------------------------------------------------------- #
# Used by `npc_lims.scripts.update_session_status` to report per-session
# progress through the IBL workflow (see `ibl-orchestration/ibl.md`).

MANIFEST_ASSET_PREFIX = "ibl_manifest_"


def get_annotation_json_path(subject_id: str | int) -> upath.UPath:
    """Canonical location of a subject's annotated neuroglancer JSON (step A)."""
    return ANNOTATIONS_ROOT / f"{subject_id}_annotated.json"


@functools.cache
def get_annotation_json_info(subject_id: str | int) -> dict[str, Any] | None:
    """`etag16` (as used for staging folders), `modified` timestamp and the
    `MM-DD` dates with non-empty, correctly-named annotation layers.

    Returns None if the subject has no annotation JSON.
    """
    path = get_annotation_json_path(subject_id)
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    raw_info = getattr(info, "info", info)
    etag = normalize_etag(raw_info.get("ETag")) if isinstance(raw_info, Mapping) else None
    dates: set[str] = set()
    with contextlib.suppress(ValueError):  # malformed JSON: no usable layers
        for name, count in _annotation_point_counts(path).items():
            if not count:
                continue
            with contextlib.suppress(ValueError):
                dates.add(parse_probe_and_date(name.strip())[1])
    return {
        "etag16": etag[:16] if etag else None,
        "modified": float(info.st_mtime),
        "dates": frozenset(dates),
    }


def get_current_manifest_asset(
    subject_id: str | int,
    subject_assets: Iterable[DataAsset],
) -> DataAsset | None:
    """Latest ready `ibl_manifest_<subject_id>_<date>` asset built from the
    current version of the subject's annotation JSON (step B4).

    Staging folders are keyed by the first 16 chars of the JSON's ETag, so an
    asset built from an older version of the JSON is ignored.
    """
    annotation = get_annotation_json_info(subject_id)
    if annotation is None:
        return None
    candidates = []
    for asset in subject_assets:
        if not asset.name.startswith(f"{MANIFEST_ASSET_PREFIX}{subject_id}_"):
            continue
        if asset.state != DataAssetState.Ready:
            continue
        prefix = getattr(asset.source_bucket, "prefix", None) or ""
        if annotation["etag16"] and f"/{subject_id}/" in f"/{prefix}":
            if f"/{annotation['etag16']}/" not in f"/{prefix}/":
                continue
        elif asset.created < annotation["modified"]:
            continue
        candidates.append(asset)
    return max(candidates, key=lambda asset: asset.created, default=None)


@functools.cache
def get_manifest_sorted_recordings(manifest_asset_id: str) -> frozenset[str]:
    """`sorted_recording` values listed in a probe-annotations asset's manifest."""
    source_dir = aind_session.utils.codeocean_utils.get_data_asset_source_dir(
        manifest_asset_id
    )
    recordings: set[str] = set()
    for path in source_dir.glob("*manifest*.csv"):
        for row in csv.DictReader(io.StringIO(path.read_text())):
            if row.get("sorted_recording"):
                recordings.add(row["sorted_recording"].strip())
    return frozenset(recordings)


def get_current_converted_asset(
    manifest_asset: DataAsset,
    subject_assets: Iterable[DataAsset],
    conversion_capsule_id: str = IBL_CONVERSION_CAPSULE_ID,
) -> DataAsset | None:
    """Latest ready conversion-capsule output derived from `manifest_asset`
    (step B6)."""
    candidates = [
        asset
        for asset in subject_assets
        if asset.state == DataAssetState.Ready
        and asset.created >= manifest_asset.created
        and (provenance := asset.provenance) is not None
        and provenance.capsule == conversion_capsule_id
        and manifest_asset.id in (provenance.data_assets or ())
    ]
    return max(candidates, key=lambda asset: asset.created, default=None)


@functools.cache
def get_converted_session_ids(
    converted_asset_id: str, subject_id: str | int
) -> frozenset[str]:
    """Session folders (e.g. `ecephys_795555_2025-08-21_12-00-17`) in a
    conversion-capsule output asset."""
    subject_dir = (
        aind_session.utils.codeocean_utils.get_data_asset_source_dir(
            converted_asset_id
        )
        / str(subject_id)
    )
    try:
        return frozenset(
            path.name
            for path in subject_dir.iterdir()
            if path.name.startswith("ecephys_")
        )
    except (FileNotFoundError, NotADirectoryError):
        return frozenset()
