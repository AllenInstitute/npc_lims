from __future__ import annotations

import functools
import json
import logging
import os
import re
import time
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal, NamedTuple, Union

import npc_session
import requests
import upath
from codeocean import CodeOcean
from codeocean.components import (
    EveryoneRole,
)
from codeocean.computation import (
    Computation,
    ComputationEndStatus,
    ComputationState,
    DataAssetsRunParam,
    RunParams,
)
from codeocean.data_asset import (
    ComputationSource,
    DataAsset,
    DataAssetOrigin,
    DataAssetParams,
    DataAssetSearchParams,
    DataAssetType,
    Permissions,
    Source,
)
from typing_extensions import TypeAlias

import npc_lims.exceptions as exceptions
import npc_lims.paths.s3 as s3

logger = logging.getLogger(__name__)

RunCapsuleResponseAPI: TypeAlias = dict[
    Literal["created", "has_results", "id", "name", "run_time", "state"], Any
]


class CapsulePipelineInfo(NamedTuple):
    id: str
    process_name: str
    is_pipeline: bool


ResultItemAPI: TypeAlias = dict[Literal["name", "path", "size", "type"], Any]
"""Result from CodeOceanAPI when querying for results from a computation"""

MODEL_CAPSULE_PIPELINE_MAPPING: dict[str, str] = {
    "dlc_eye": "4cf0be83-2245-4bb1-a55c-a78201b14bfe",
    "dlc_side": "facff99f-d3aa-4ecd-8ef8-a343c38197aa",
    "dlc_face": "a561aa4c-2066-4ff2-a916-0db86b918cdf",
    "facemap": "670de0b3-f73d-4d22-afe6-6449c45fada4",
    "sorting_pipeline": "1f8f159a-7670-47a9-baf1-078905fc9c2e",
}

EXAMPLE_JOB_STATUS = Computation(
    created=1710962969,
    has_results=True,
    id="1c900aa5-dde4-475d-bf50-cc96aff9db39",
    name="Run With Parameters 962969",
    run_time=84184,
    state=ComputationState.Completed,
    end_status=ComputationEndStatus.Succeeded,
)

EXAMPLE_JOB_STATUS_INIT = Computation(
    created=1710962969,
    has_results=True,
    id="1c900aa5-dde4-475d-bf50-cc96aff9db39",
    name="Run With Parameters 962969",
    run_time=84184,
    state=ComputationState.Initializing,
    end_status=ComputationEndStatus.Succeeded,
)

EXAMPLE_JOB_STATUS_RUNNING = Computation(
    created=1710962969,
    has_results=True,
    id="1c900aa5-dde4-475d-bf50-cc96aff9db39",
    name="Run With Parameters 962969",
    run_time=84184,
    state=ComputationState.Running,
    end_status=ComputationEndStatus.Succeeded,
)

EXAMPLE_JOB_STATUS_FAIL = Computation(
    created=1710962969,
    has_results=True,
    id="1c900aa5-dde4-475d-bf50-cc96aff9db39",
    name="Run With Parameters 962969",
    run_time=84184,
    state=ComputationState.Completed,
    end_status=ComputationEndStatus.Failed,
)

EXAMPLE_JOB_STATUS_NO_RESULTS = Computation(
    created=1710962969,
    has_results=False,
    id="1c900aa5-dde4-475d-bf50-cc96aff9db39",
    name="Run With Parameters 962969",
    run_time=84184,
    state=ComputationState.Completed,
    end_status=ComputationEndStatus.Succeeded,
)

EXAMPLE_JOB_STATUS_BAD_RESULT = Computation(
    created=1710962969,
    has_results=False,
    id="d5444fc9-9c0f-4c91-90c0-8d17969971b8",
    name="Run With Parameters 962969",
    run_time=84184,
    state=ComputationState.Completed,
    end_status=ComputationEndStatus.Succeeded,
)


class SessionIndexError(IndexError):
    pass


class ModelCapsuleMappingError(KeyError):
    pass


def _get_ttl_hash(seconds=2 * 60) -> int:
    """Return the same value within `seconds` time period

    From https://stackoverflow.com/a/55900800
    """
    return round(time.time() / seconds)


@functools.cache
def get_codeocean_client() -> CodeOcean:
    token = os.getenv(
        key="CODE_OCEAN_API_TOKEN",
        default=next(
            (v for v in os.environ.values() if v.lower().startswith("cop_")), None
        ),
    )
    if token is None:
        raise exceptions.MissingCredentials(
            "`CODE_OCEAN_API_TOKEN` not found in environment variables"
        )
    return CodeOcean(
        domain=os.getenv(
            key="CODE_OCEAN_DOMAIN",
            default="https://codeocean.allenneuraldynamics.org",
        ),
        token=token,
    )


@functools.cache
def get_subject_data_assets(
    subject: str | int,
    page_size: int = 10,
    max_pages: int = 1000,
    offset: int = 0,
    ttl_hash: int | None = None,
) -> tuple[DataAsset, ...]:
    """
    All assets associated with a subject ID.

    Examples:
        >>> assets = get_subject_data_assets(668759)
        >>> assert len(assets) > 0
    """
    del ttl_hash  # only used for functools.cache
    results = []
    while offset < max_pages:
        search_results = get_codeocean_client().data_assets.search_data_assets(
            DataAssetSearchParams(
                query=f"subject id: {npc_session.SubjectRecord(subject)}",
                limit=page_size,  # intentionally high, TODO: add pagination
                offset=offset * page_size,
                archived=False,
                favorite=False,
            )
        )
        results.extend(search_results.results)
        if not search_results.has_more:
            break
        offset += 1
    else:
        logger.warning(f"Max pages reached for {subject=}.")

    return tuple(results)


def get_session_data_assets(
    session: str | npc_session.SessionRecord,
) -> tuple[DataAsset, ...]:
    session = npc_session.SessionRecord(session)
    results = get_subject_data_assets(session.subject, ttl_hash=_get_ttl_hash())
    try:
        pattern = get_codoecean_session_id(session)
    except ValueError:  # no raw data uploaded
        pattern = f"ecephys_{session.subject}_{session.date}_{npc_session.PARSE_TIME}"
    return tuple(
        result
        for result in results
        if re.match(
            f"{pattern}(_[a-z]*_[a-z]*)*",
            result.name,
        )
    )


def get_session_result_data_assets(
    session: str | npc_session.SessionRecord,
) -> tuple[DataAsset, ...]:
    """
    Examples:
        >>> result_data_assets = get_session_result_data_assets('668759_20230711')
        >>> assert len(result_data_assets) > 0
    """
    session_data_assets = get_session_data_assets(session)
    result_data_assets = tuple(
        data_asset
        for data_asset in session_data_assets
        if data_asset.type == DataAssetType.Result
    )

    return result_data_assets


def get_latest_data_asset(
    data_assets: Sequence[DataAsset],
) -> DataAsset:
    return sorted(data_assets, key=lambda asset: asset.created)[-1]


def get_session_sorted_data_asset(
    session: str | npc_session.SessionRecord,
) -> DataAsset:
    """
    Examples:
        >>> asset = get_session_sorted_data_asset('ecephys_703333_2024-04-09_1')
        >>> asset = get_session_sorted_data_asset('668759_20230711')
        >>> assert isinstance(asset, DataAsset)
    """
    session_result_data_assets = get_session_data_assets(session)
    sorted_data_assets = tuple(
        data_asset
        for data_asset in session_result_data_assets
        if is_sorted_data_asset(data_asset) and (data_asset.files or -1) > 2
    )

    if not sorted_data_assets:
        raise ValueError(f"Session {session} has no sorted data assets")

    return get_latest_data_asset(sorted_data_assets)


@functools.cache
def get_sessions_with_data_assets(
    subject: str | int,
) -> tuple[npc_session.SessionRecord, ...]:
    """
    Examples:
        >>> sessions = get_sessions_with_data_assets(668759)
        >>> assert len(sessions) > 0
    """
    results = get_subject_data_assets(subject, ttl_hash=_get_ttl_hash())
    sessions = set()
    for asset in results:
        try:
            session = npc_session.SessionRecord(asset.name)
        except ValueError:
            continue
        sessions.add(session)
    return tuple(sessions)


def get_data_asset(asset: str | uuid.UUID | DataAsset) -> DataAsset:
    """Converts an asset uuid to dict of info from CodeOcean API."""
    if not isinstance(asset, DataAsset):
        return get_codeocean_client().data_assets.get_data_asset(str(asset))
    return asset


def is_raw_data_asset(asset: str | DataAsset) -> bool:
    """
    Examples:
        >>> is_raw_data_asset('83636983-f80d-42d6-a075-09b60c6abd5e')
        True
        >>> is_raw_data_asset('173e2fdc-0ca3-4a4e-9886-b74207a91a9a')
        False
    """
    asset = get_data_asset(asset)
    if is_sorted_data_asset(asset):
        return False
    return (asset.custom_metadata or {}).get("data level") == "raw data" or "raw" in (
        asset.tags or []
    )


def is_sorted_data_asset(asset: str | DataAsset) -> bool:
    """
    Examples:
        >>> is_sorted_data_asset('173e2fdc-0ca3-4a4e-9886-b74207a91a9a')
        True
        >>> is_sorted_data_asset('83636983-f80d-42d6-a075-09b60c6abd5e')
        False
    """
    asset = get_data_asset(asset)
    if "ecephys" not in asset.name:
        return False
    return "sorted" in asset.name


def get_session_raw_data_asset(
    session: str | npc_session.SessionRecord,
) -> DataAsset:
    """
    Examples:
        >>> get_session_raw_data_asset('668759_20230711').id
        '83636983-f80d-42d6-a075-09b60c6abd5e'
    """
    session = npc_session.SessionRecord(session)
    raw_assets = tuple(
        asset for asset in get_session_data_assets(session) if is_raw_data_asset(asset)
    )

    if not raw_assets:
        raise ValueError(f"Session {session} has no raw data assets")

    platforms = tuple(asset.name.split("_")[0] for asset in raw_assets)
    if len(set(platforms)) > 1:
        logger.debug(f"Raw data assets for multiple platforms found for {session}")
        # if a session has both an ecephys platform raw asset and a behavior platform
        # asset (which necessarily contains a subset of the ecephys data), we'll take the ecephys asset
        for platform in ("ecephys", "behavior"):
            if any(platform in asset.name for asset in raw_assets):
                raw_assets = tuple(
                    asset for asset in raw_assets if platform in asset.name
                )
                break
        else:
            raise NotImplementedError(
                f"Raw data assets from multiple platforms found for {session}, which we don't know how to handle: {platforms}"
            )
    return get_latest_data_asset(raw_assets)


def get_surface_channel_root(session: str | npc_session.SessionRecord) -> upath.UPath:
    """Reconstruct path to surface channel data in bucket (e.g. on s3) using data-asset
    info from Code Ocean.

    Examples:
        >>> get_surface_channel_root('660023_20230808')
        S3Path('s3://aind-ephys-data/ecephys_660023_2023-08-08_15-11-14')
        >>> assert get_surface_channel_root('660023_20230808') != get_raw_data_root('660023_20230808')
        >>> get_surface_channel_root('649943_20230216')
        Traceback (most recent call last):
        ...
        FileNotFoundError: 649943_20230216 has no surface channel data assets
    """
    raw_asset = get_surface_channel_raw_data_asset(session)
    return get_path_from_data_asset(raw_asset)


def get_surface_channel_raw_data_asset(
    session: str | npc_session.SessionRecord,
) -> DataAsset:
    """For a main ephys session (implict idx=0), find a raw asset corresponding to
    the second session on the same day (idx=1).
    """
    session = npc_session.SessionRecord(session).with_idx(1)
    try:
        raw_assets = tuple(
            asset
            for asset in get_session_data_assets(session)
            if is_raw_data_asset(asset)
        )
    except SessionIndexError:
        raise FileNotFoundError(
            f"{session} has no surface channel data assets"
        ) from None
    if not raw_assets:
        raise FileNotFoundError(f"{session} has no surface channel data assets")
    return get_latest_data_asset(raw_assets)


@functools.cache
def get_codoecean_session_id(
    session: str | npc_session.SessionRecord,
) -> str:
    """Get the Code Ocean session ID for a given session, which includes session
    start time.

    Examples:
        >>> get_codoecean_session_id('703333_2024-04-09')
        'ecephys_703333_2024-04-09_13-06-44'
        >>> get_codoecean_session_id('703333_2024-04-09_1')
        'ecephys_703333_2024-04-09_15-14-46'
    """
    session = npc_session.SessionRecord(session)
    data_assets = [
        asset
        for asset in get_subject_data_assets(session.subject, ttl_hash=_get_ttl_hash())
        if asset.name.startswith(f"ecephys_{session.subject}_{session.date}")
        or asset.name.startswith(f"behavior_{session.subject}_{session.date}")
    ]

    asset_names = tuple(asset.name for asset in data_assets)
    session_times = sorted(
        {
            time
            for time in map(npc_session.extract_isoformat_time, asset_names)
            if time is not None
        }
    )
    session_times_to_assets = {
        session_time: tuple(
            asset
            for asset in data_assets
            if npc_session.extract_isoformat_time(asset.name) == session_time
        )
        for session_time in session_times
    }
    if not session_times_to_assets:
        raise ValueError(
            f"No assets found on codeocean for {session=} - cannot deduce session ID"
        )
    if len(session_times) < session.idx + 1:  # 0-indexed
        raise SessionIndexError(
            f"Number of assets is less than expected: cannot extract asset for session idx = {session.idx} from {asset_names = }"
        )
    session_assets = session_times_to_assets[session_times[session.idx]]
    session_id = npc_session.extract_aind_session_id(session_assets[0].name)
    assert all(
        npc_session.extract_aind_session_id(asset.name) == session_id
        for asset in session_assets
    )
    return session_id


@functools.cache
def get_raw_data_root(session: str | npc_session.SessionRecord) -> upath.UPath:
    """Reconstruct path to raw data in bucket (e.g. on s3) using data-asset
    info from Code Ocean.

        >>> get_raw_data_root('668759_20230711')
        S3Path('s3://aind-ephys-data/ecephys_668759_2023-07-11_13-07-32')
    """
    raw_asset = get_session_raw_data_asset(session)

    return get_path_from_data_asset(raw_asset)


def get_path_from_data_asset(asset: DataAsset) -> upath.UPath:
    """Reconstruct path to raw data in bucket (e.g. on s3) using data asset
    uuid or dict of info from Code Ocean API."""
    if not asset.source_bucket:
        raise ValueError(
            f"Asset {asset.id} has no `source_bucket` info - not sure how to create UPath:\n{asset!r}"
        )
    bucket_info = asset.source_bucket
    roots = {DataAssetOrigin.AWS: "s3", DataAssetOrigin.GCP: "gs"}
    if bucket_info.origin not in roots:
        raise RuntimeError(
            f"Unknown bucket origin - not sure how to create UPath: {bucket_info = }"
        )
    return upath.UPath(
        f"{roots[bucket_info.origin]}://{bucket_info.bucket}/{bucket_info.prefix}"
    )


def run_capsule_or_pipeline(
    data_assets: list[DataAssetsRunParam], id: str, is_pipeline: bool = False
) -> Computation:
    if is_pipeline:
        run_capsule_request = RunParams(
            pipeline_id=id,
            data_assets=data_assets,
        )
    else:
        run_capsule_request = RunParams(
            capsule_id=id,
            data_assets=data_assets,
        )

    return get_codeocean_client().computations.run_capsule(run_capsule_request)


def get_session_capsule_pipeline_data_asset(
    session: str | npc_session.SessionRecord, process_name: str
) -> DataAsset:
    """
    Returns the data asset for a given model
    >>> asset = get_session_capsule_pipeline_data_asset('676909_2023-12-13', 'dlc_eye')
    >>> asset = get_session_capsule_pipeline_data_asset('676909_2023-12-13', 'sorted')
    >>> asset.name
    'ecephys_676909_2023-12-13_13-43-40_sorted_2024-03-01_16-02-45'
    """
    session = npc_session.SessionRecord(session)

    session_data_assets = get_session_data_assets(session)
    session_model_asset = tuple(
        asset for asset in session_data_assets if process_name in asset.name
    )
    if not session_model_asset:
        raise FileNotFoundError(f"{session} has no {process_name} results")

    return get_latest_data_asset(session_model_asset)


def create_session_data_asset(
    session: str | npc_session.SessionRecord, computation_id: str, data_asset_name: str
) -> DataAsset:
    session = npc_session.SessionRecord(session)

    if is_computation_errored(computation_id) or not is_computation_finished(
        computation_id
    ):
        return None

    source = Source(computation=ComputationSource(id=computation_id))
    tags = [str(session.subject), "derived", "ephys", "results"]
    custom_metadata = {
        "data level": "derived data",
        "experiment type": "ecephys",
        "modality": "Extracellular electrophysiology",
        "subject id": str(session.subject),
    }

    return get_codeocean_client().data_assets.create_data_asset(
        DataAssetParams(
            name=data_asset_name,
            mount=data_asset_name,
            tags=tags,
            source=source,
            custom_metadata=custom_metadata,
        )
    )


def set_asset_viewable_for_everyone(asset_id: str) -> None:
    get_codeocean_client().data_assets.update_permissions(
        data_asset_id=asset_id,
        permissions=Permissions(
            everyone=EveryoneRole.Viewer,
            share_assets=True,
        ),
    )
    logger.debug(f"Asset {asset_id} made viewable for everyone")


def get_job_status(job_id: str, check_files: bool = False) -> Computation:
    """Current status from CodeOcean API, but with an additional check for no
    output files, which is a common error in the spike-sorting pipeline.

    Notes
    -----
    - TODO: rename this to `get_computation`?
    """
    computation = get_codeocean_client().computations.get_computation(job_id)
    if check_files and is_computation_errored(computation):
        logger.info(f"Job {computation.id} errored.")
    return computation


def _parse_job_id_and_response(
    job_id_or_response: str | Computation,
) -> Computation:
    if isinstance(job_id_or_response, str):
        return get_job_status(job_id_or_response)
    return job_id_or_response


def is_computation_finished(job_id_or_response: str | Computation) -> bool:
    """
    >>> is_computation_finished(EXAMPLE_JOB_STATUS)
    True
    >>> is_computation_finished(EXAMPLE_JOB_STATUS_INIT)
    False
    >>> is_computation_finished(EXAMPLE_JOB_STATUS_RUNNING)
    False
    """
    job_status = _parse_job_id_and_response(job_id_or_response)
    return job_status.state in (ComputationState.Completed,)


def get_result_names(job_id: str) -> list[str]:
    """File and folder names in the output directory of a job's result

    >>> results = get_result_names('1c900aa5-dde4-475d-bf50-cc96aff9db39')
    >>> assert 'output' in results
    """
    available_results = get_codeocean_client().computations.list_computation_results(
        job_id
    )
    result_item_names = sorted(item.name for item in available_results.items)
    return result_item_names


def is_computation_errored(job_id_or_response: str | Computation) -> bool:
    """Job status may say `completed` but the pipeline still errored: check the
    output folder for indications of error.

    - no files (or only `nextflow` and `output` files for pipeline runs)
    - `end_status` == `failed`
    - `has_results` == False
    - `output` file contains `Out of memory.`

    >>> is_computation_errored(EXAMPLE_JOB_STATUS)
    False
    >>> is_computation_errored(EXAMPLE_JOB_STATUS_FAIL)
    True
    >>> is_computation_errored(EXAMPLE_JOB_STATUS_NO_RESULTS)
    True
    >>> is_computation_errored(EXAMPLE_JOB_STATUS_BAD_RESULT)
    True
    """
    job_status = _parse_job_id_and_response(job_id_or_response)
    if not is_computation_finished(job_status):
        return False
    job_id = job_status.id
    if job_status.state in (ComputationState.Failed,):
        return True
    if job_status.end_status in (ComputationEndStatus.Failed,):
        return True
    if job_status.has_results is False:
        logger.debug(f"Job {job_id} suspected error based on no results")
        return True

    if job_status.state in (ComputationState.Completed,):
        # check if errored based on files in result
        result_item_names = get_result_names(job_id)
        is_no_files = len(result_item_names) == 0
        is_pipeline_error = len(result_item_names) == 2 and result_item_names == [
            "nextflow",
            "output",
        ]
        is_capsule_error = len(result_item_names) == 1 and result_item_names == [
            "output"
        ]
        if is_no_files or is_pipeline_error or is_capsule_error:
            logger.debug(
                f"Job {job_id} suspected error based on number of files available in result"
            )
            return True
        if "output" in result_item_names:
            output = requests.get(
                get_codeocean_client()
                .computations.get_result_file_download_url(job_id, "output")
                .url
            ).text
            if "Out of memory." in output:
                logger.debug(
                    f"Job {job_id} output file includes 'Out of memory.' in text"
                )
                return True
            if "Traceback (most recent call last)" in output:
                logger.debug(
                    f"Job {job_id} suspected error based on python traceback in output"
                )
                return True
            if "Command error:" in output:
                logger.debug(
                    f"Job {job_id} suspected error based on pipeline error message"
                )
                return True
            if "The CUDA error was:" in output:
                logger.warning(
                    f"Job {job_id} suspected failure based on CUDA error message"
                )
                # return True - currently (Apr 2024) this results from single
                # probes not sorting (due to artefacts or other issues), but other
                # probes still usable
            if all(
                text in output.lower()
                for text in ("sorting", "kilosort", "N E X T F L O W".lower())
            ):
                if "nwb" not in result_item_names:
                    logger.debug(
                        f"Job {job_id} suspected error based on missing NWB file"
                    )
                    return True
    return False


def get_skipped_probes(session_id: str | npc_session.SessionRecord) -> str:
    """Only works with new pipeline output

    Examples:
        >>> get_skipped_probes('702136_2024-03-05')
        'E'
        >>> get_skipped_probes('666986_2023-08-14')
        'B'
        >>> get_skipped_probes('668755_2023-08-28')
        ''
    """
    output = get_sorting_output_text(session_id)
    skipped_probes = ""
    if "skip" not in output.lower():
        return skipped_probes
    for text in output.split("Skipping further processing for this recording")[:-1]:
        preprocessing = text.split("Preprocessing".upper())[-1]
        skipped_probes += npc_session.ProbeRecord(preprocessing)
    return skipped_probes


def get_sorting_output_text(session_id: str | npc_session.SessionRecord) -> str:
    """Contents of the sorting pipeline `output` file (log)"""
    session = npc_session.SessionRecord(session_id)
    output_path = next(
        (p for p in s3.get_sorted_data_paths_from_s3(session) if p.name == "output"),
        None,
    )
    if output_path is None:
        raise FileNotFoundError(f"No output file found for {session}")
    return output_path.read_text()


def read_computation_queue(source: Path) -> dict[str, Computation | None]:
    return {
        session_id: (
            Computation.from_dict(computation_dict)
            if computation_dict is not None
            else None
        )
        for (session_id, computation_dict) in json.loads(source.read_text()).items()
    }


def serialize_computation(
    computation: Computation | None,
) -> dict[str, str | int] | None:
    if computation is None:
        return None
    elif isinstance(computation, Computation):
        return computation.to_dict()
    else:
        raise ValueError(f"Invalid computation type: {type(computation)}")


SessionID = Union[str, npc_session.SessionRecord]


def add_to_computation_queue(
    source: Path,
    session_id: SessionID,
    computation: Computation | None,
) -> None:
    if not source.exists():
        current = {}
    else:
        current = read_computation_queue(source)

    is_new = session_id not in current
    for session_queue_id in current:
        if not is_new and session_queue_id == session_id:
            current[session_queue_id] = serialize_computation(computation)
        else:
            current[session_queue_id] = serialize_computation(current[session_queue_id])

    if is_new:
        current.update({session_id: serialize_computation(computation)})

    source.write_text(json.dumps(current, indent=4))
    logger.info(
        f"{'Added' if is_new else 'Updated'} {session_id} {'to' if is_new else 'in'} json"
    )


def get_current_queue_computation(
    source: Path,
    job_or_session_id: str,
) -> Computation | None:
    try:
        session_id = npc_session.SessionRecord(job_or_session_id).id
    except ValueError:
        current_job_status = None
    else:
        current_job_status = read_computation_queue(source)[session_id]

    if current_job_status is not None:
        # if current_job_status is None:
        return get_job_status(current_job_status.id, check_files=True)
    else:
        return current_job_status


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
