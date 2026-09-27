#!/usr/bin/env python

# /// script
# requires-python = ">=3.9,<3.12"
# dependencies = [
#     "npc-lims[polars]",
# ]
#
# [tool.uv.sources]
# npc_lims = { git = "https://github.com/AllenInstitute/npc_lims" }
# ///

from __future__ import annotations

import argparse
import time
from collections.abc import Mapping, Sequence
from typing import Any

try:
    import polars as pl
except ImportError:
    raise ImportError(
        "polars is required: run `pip install npc_lims[polars]`"
    ) from None

from codeocean.computation import (
    Computation,
    ComputationEndStatus,
    ComputationState,
    NamedRunParam,
    RunParams,
)

import npc_lims

VIDEO_PROCESSING_CAPSULE_ID = "e8eb341f-96e6-4036-84c2-d4ad5558d96a"
STATUS_CSV_URL = (
    "https://raw.githubusercontent.com/AllenInstitute/npc_lims/main/tables/status.csv"
)

PROCESS_STATUS_COLUMNS = {
    "GammaEncoding": "is_gamma_encoding",
    "LPFaceParts": "is_LPFaceParts",
    "dlc_eye": "is_dlc_eye",
    "facemap": "is_facemap",
}
PROCESS_TYPES = tuple(PROCESS_STATUS_COLUMNS)
MAX_CONCURRENT_JOBS = 3
LAUNCH_PAUSE_SECONDS = 10.0
POLL_INTERVAL = 60.0


def get_missing_processes(
    row: Mapping[str, Any], process_types: Sequence[str] | None = None
) -> list[str]:
    """Return video processes whose status is false or unavailable."""
    process_types = PROCESS_TYPES if process_types is None else process_types
    return [
        process_name
        for process_name in process_types
        if row.get(PROCESS_STATUS_COLUMNS[process_name]) is not True
    ]


def get_run_params(
    raw_data_asset_id: str, process_types: Sequence[str] | None = None
) -> RunParams:
    """Create the argparse-style parameters expected by the dispatcher capsule."""
    parameters = {
        "raw_data_asset_id": raw_data_asset_id,
        "dry_run": "0",
        "skip_existing": "1",
    }
    if process_types is not None:
        parameters["processes"] = ",".join(process_types)

    return RunParams(
        capsule_id=VIDEO_PROCESSING_CAPSULE_ID,
        named_parameters=[
            NamedRunParam(param_name=k, value=v) for k, v in parameters.items()
        ],
    )


def trigger_video_processing(
    raw_data_asset_id: str, process_types: Sequence[str] | None = None
) -> Computation:
    """Trigger a dispatcher computation without waiting for it to finish."""
    return npc_lims.get_codeocean_client().computations.run_capsule(
        get_run_params(raw_data_asset_id, process_types)
    )


def _get_process_label(process_types: Sequence[str] | None) -> str:
    return (
        "all video processing"
        if process_types is None
        else ", ".join(process_types)
    )


def launch_video_session(
    raw_data_asset_id: str, process_types: Sequence[str] | None = None
) -> Computation:
    """Launch processing synchronously so API errors surface immediately."""
    process_label = _get_process_label(process_types)
    print(f"Requesting {process_label} for {raw_data_asset_id}...", flush=True)
    try:
        computation = trigger_video_processing(raw_data_asset_id, process_types)
    except Exception as exc:
        raise RuntimeError(
            f"Could not launch {process_label} for {raw_data_asset_id}"
        ) from exc

    print(
        f"Launched {process_label} for {raw_data_asset_id} "
        f"(computation {computation.id})",
        flush=True,
    )
    return computation


def is_computation_complete(computation: Computation) -> bool:
    """Poll once and return whether the job is complete.

    A failed computation is still terminal.  Report it and let the caller
    continue processing any other sessions rather than aborting the run.
    """
    status = npc_lims.get_codeocean_client().computations.get_computation(
        computation.id
    )
    if status.state == ComputationState.Failed or getattr(
        status, "end_status", None
    ) in (ComputationEndStatus.Failed, ComputationEndStatus.Stopped):
        print(
            f"Video processing failed for computation {computation.id}; continuing.",
            flush=True,
        )
        return True
    if status.state == ComputationState.Completed:
        if npc_lims.is_computation_errored(status):
            print(
                "Video processing failed for computation "
                f"{computation.id}; continuing.",
                flush=True,
            )
        return True
    return False


def wait_for_computation(computation: Computation) -> None:
    """Poll one dispatcher computation until it succeeds or fails."""
    while not is_computation_complete(computation):
        time.sleep(POLL_INTERVAL)


def process_video_session(
    raw_data_asset_id: str, process_types: Sequence[str] | None = None
) -> None:
    """Run and poll the full video-processing pipeline for one session."""
    computation = launch_video_session(raw_data_asset_id, process_types)
    wait_for_computation(computation)


def _wait_for_next_launch(last_launch_at: float | None) -> None:
    if last_launch_at is None:
        return
    elapsed = time.monotonic() - last_launch_at
    if elapsed < LAUNCH_PAUSE_SECONDS:
        remaining = LAUNCH_PAUSE_SECONDS - elapsed
        print(f"Waiting {remaining:.1f}s before next launch...", flush=True)
        time.sleep(remaining)


def process_video_sessions(
    raw_data_asset_ids: list[str],
    max_concurrent_jobs: int = MAX_CONCURRENT_JOBS,
    process_types: Sequence[str] | None = None,
) -> None:
    """Launch and poll video processing with bounded remote concurrency."""
    if max_concurrent_jobs < 1:
        raise ValueError("max_concurrent_jobs must be at least 1")

    active_computations: dict[str, tuple[Computation, str]] = {}
    next_session_index = 0
    last_launch_at: float | None = None

    while active_computations or next_session_index < len(raw_data_asset_ids):
        while (
            next_session_index < len(raw_data_asset_ids)
            and len(active_computations) < max_concurrent_jobs
        ):
            _wait_for_next_launch(last_launch_at)
            raw_data_asset_id = raw_data_asset_ids[next_session_index]
            computation = launch_video_session(
                raw_data_asset_id, process_types
            )
            active_computations[computation.id] = (
                computation,
                raw_data_asset_id,
            )
            next_session_index += 1
            last_launch_at = time.monotonic()

        completed_ids: list[str] = []
        for computation_id, (
            computation,
            raw_data_asset_id,
        ) in active_computations.items():
            is_complete = is_computation_complete(computation)
            if is_complete:
                print(
                    f"Finished video processing for {raw_data_asset_id} "
                    f"(computation {computation_id})",
                    flush=True,
                )
                completed_ids.append(computation_id)

        for computation_id in completed_ids:
            del active_computations[computation_id]

        if active_computations and not completed_ids:
            time.sleep(POLL_INTERVAL)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run video processing for incomplete sessions."
    )
    parser.add_argument(
        "--process-type",
        "--process",
        "--processes",
        dest="process_types",
        choices=PROCESS_TYPES,
        action="append",
        help="Process type to run; repeat to target multiple types (default: all).",
    )
    parser.add_argument(
        "--max-concurrent-jobs",
        type=int,
        default=MAX_CONCURRENT_JOBS,
        help=(
            "Maximum number of jobs to process concurrently "
            f"(default: {MAX_CONCURRENT_JOBS})."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    status = pl.read_csv(STATUS_CSV_URL, null_values=[""])
    video_sessions = status.filter(
        pl.col("is_video") & pl.col("raw_asset_id").is_not_null()
    )

    raw_data_asset_ids = []
    for row in video_sessions.iter_rows(named=True):
        raw_data_asset_id = str(row["raw_asset_id"])
        missing_processes = get_missing_processes(row, args.process_types)
        if not missing_processes:
            continue
        raw_data_asset_ids.append(raw_data_asset_id)

    process_label = (
        "all video processing"
        if args.process_types is None
        else ", ".join(args.process_types)
    )
    print(
        f"Found {len(raw_data_asset_ids)} sessions needing {process_label}",
        flush=True,
    )

    process_video_sessions(
        raw_data_asset_ids,
        max_concurrent_jobs=args.max_concurrent_jobs,
        process_types=args.process_types,
    )


if __name__ == "__main__":
    main()
