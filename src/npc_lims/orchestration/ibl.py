# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "aind-session>=0.3.25",
#   "codeocean>=0.3.1",
#   "dagster==1.5.14",
#   "dagster-webserver==1.5.14",
#   "npc-session>=0.1.36",
#   "universal-pathlib>=0.1.4",
# ]
# ///
import dataclasses
import datetime
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import npc_session
import upath
from dagster import (
    AssetObservation,
    DefaultSensorStatus,
    Definitions,
    OpExecutionContext,
    RunConfig,
    RunRequest,
    SensorEvaluationContext,
    SkipReason,
    job,
    op,
    sensor,
)

from npc_lims.ibl import (
    ANNOTATIONS_ROOT,
    get_annotated_ng_jsons,
    normalize_etag,
)

SENSOR_MINIMUM_INTERVAL_SECONDS = 10


@dataclasses.dataclass(frozen=True)
class S3ObjectMetadata:
    """Metadata used to identify one externally stored object."""

    uri: str
    etag: str
    size: int
    last_modified: str


@dataclasses.dataclass(frozen=True)
class NgJsonConfig:
    """Configuration for observing one annotated Neuroglancer JSON."""

    subject_id: int
    uri: str
    etag: str
    size: int
    last_modified: str


def _metadata_value(info: Mapping[str, object], *names: str) -> object | None:
    """Get metadata while tolerating common fsspec/S3 spellings."""
    for name in names:
        if (value := info.get(name)) is not None:
            return value
    return None


def get_s3_object_metadata(path: upath.UPath) -> S3ObjectMetadata | None:
    """Return object metadata without reading the annotation's contents.

    ``None`` means the object has no ETag and cannot be safely deduplicated.
    """
    info = path.stat()
    if not isinstance(info, Mapping):
        return None
    etag = normalize_etag(_metadata_value(info, "ETag", "etag"))
    if etag is None:
        return None

    size = _metadata_value(info, "size", "Size", "ContentLength")
    last_modified = _metadata_value(info, "LastModified", "last_modified", "mtime", "updated")
    if isinstance(last_modified, datetime.datetime):
        last_modified = last_modified.isoformat()
    elif last_modified is None:
        last_modified = "unknown"
    else:
        last_modified = str(last_modified)

    return S3ObjectMetadata(
        uri=path.as_posix(),
        etag=etag,
        size=int(str(size)) if size is not None else 0,
        last_modified=last_modified,
    )


@op(
    config_schema={
        "subject_id": int,
        "uri": str,
        "etag": str,
        "size": int,
        "last_modified": str,
    }
)
def observe_annotated_ng_json(context: OpExecutionContext) -> None:
    """Annotated Neuroglancer JSON for one subject"""
    config = NgJsonConfig(**context.op_config)
    metadata = dataclasses.asdict(config)
    context.log_event(
        AssetObservation(
            asset_key=["annotated_ng_json", str(config.subject_id)],
            description="Neuroglancer annotation observed in S3",
            metadata=metadata,
        )
    )
    context.log.info(
        "Observed annotated Neuroglancer JSON for subject %s at %s (ETag %s)",
        config.subject_id,
        config.uri,
        config.etag,
    )


@job(description=("Create data conversion asset for a subject to use with the IBL GUI in Code Ocean"))
def ibl_conversion_job() -> None:
    observe_annotated_ng_json()


@sensor(
    job=ibl_conversion_job,
    minimum_interval_seconds=SENSOR_MINIMUM_INTERVAL_SECONDS,
    default_status=DefaultSensorStatus.STOPPED,
    description="Detect new or overwritten annotated Neuroglancer JSONs in S3.",
)
def ng_json_sensor(
    context: SensorEvaluationContext,
) -> list[RunRequest] | SkipReason:
    """Return one RunRequest per subject/ETag pair, which can be used by Dagster to launch processing jobs or register asset-observations."""
    requests: list[RunRequest] = []
    for annotation_path in get_annotated_ng_jsons():
        subject_id = npc_session.extract_subject(str(annotation_path))
        if subject_id is None:
            context.log.warning(
                "Skipping JSON with no subject ID: %s",
                annotation_path,
            )
            continue
        metadata = get_s3_object_metadata(annotation_path)
        if metadata is None:
            context.log.warning(
                "Skipping annotated Neuroglancer JSON without an ETag: %s",
                annotation_path,
            )
            continue

        config = NgJsonConfig(
            subject_id=subject_id,
            uri=str(annotation_path),
            etag=metadata.etag,
            size=metadata.size,
            last_modified=metadata.last_modified,
        )
        requests.append(
            RunRequest(
                run_key=f"ibl-conversion:{subject_id}:{metadata.etag}",
                run_config=RunConfig(
                    ops={
                        "observe_annotated_ng_json": {
                            "config": dataclasses.asdict(config),
                        }
                    }
                ),
                tags={"subject_id": str(subject_id)},
            )
        )
    if not requests:
        return SkipReason(f"No annotated Neuroglancer JSONs were found in {ANNOTATIONS_ROOT}")
    return requests


defs = Definitions(
    jobs=[ibl_conversion_job],
    sensors=[ng_json_sensor],
)


if __name__ == "__main__":
    Path(".dagster").mkdir(exist_ok=True)
    raise SystemExit(
        subprocess.call(
            [
                sys.executable,
                "-m",
                "dagster",
                "dev",
                "-m",
                "npc_lims.orchestration.ibl",
            ]
        )
    )
