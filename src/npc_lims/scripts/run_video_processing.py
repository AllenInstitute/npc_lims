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
import threading
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
MAX_CONCURRENT_SESSIONS = 3
LAUNCH_PAUSE_SECONDS = 10.0
POLL_INTERVAL = 60.0
THREAD_STATUS_CHECK_INTERVAL = 0.1


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


def wait_for_computation(computation: Computation) -> None:
    """Poll one dispatcher computation until it succeeds or fails."""
    client = npc_lims.get_codeocean_client()
    while True:
        status = client.computations.get_computation(computation.id)
        if status.state == ComputationState.Failed or getattr(
            status, "end_status", None
        ) in (ComputationEndStatus.Failed, ComputationEndStatus.Stopped):
            raise RuntimeError(f"Computation failed: {computation.id}")
        if status.state == ComputationState.Completed:
            if npc_lims.is_computation_errored(status):
                raise RuntimeError(f"Computation failed: {computation.id}")
            return
        time.sleep(POLL_INTERVAL)


def process_video_session(
    raw_data_asset_id: str, process_types: Sequence[str] | None = None
) -> None:
    """Run and poll the full video-processing pipeline for one session."""
    process_label = (
        "all video processing"
        if process_types is None
        else ", ".join(process_types)
    )
    print(f"Launching {process_label} for {raw_data_asset_id}")
    wait_for_computation(trigger_video_processing(raw_data_asset_id, process_types))


def _process_video_session_in_thread(
    raw_data_asset_id: str,
    error: list[Exception],
    process_types: Sequence[str] | None,
) -> None:
    try:
        process_video_session(raw_data_asset_id, process_types)
    except Exception as exc:
        error.append(exc)


def _start_video_session_thread(
    raw_data_asset_id: str,
    process_types: Sequence[str] | None,
) -> tuple[threading.Thread, list[Exception]]:
    error: list[Exception] = []
    thread = threading.Thread(
        target=_process_video_session_in_thread,
        args=(raw_data_asset_id, error, process_types),
    )
    thread.start()
    return thread, error


def _wait_for_next_launch(last_launch_at: float | None) -> None:
    if last_launch_at is None:
        return
    elapsed = time.monotonic() - last_launch_at
    if elapsed < LAUNCH_PAUSE_SECONDS:
        time.sleep(LAUNCH_PAUSE_SECONDS - elapsed)


def process_video_sessions(
    raw_data_asset_ids: list[str],
    max_concurrent_sessions: int = MAX_CONCURRENT_SESSIONS,
    process_types: Sequence[str] | None = None,
) -> None:
    """Run video processing with bounded, explicitly tracked worker threads."""
    if max_concurrent_sessions < 1:
        raise ValueError("max_concurrent_sessions must be at least 1")

    active_threads: dict[threading.Thread, list[Exception]] = {}
    first_error: Exception | None = None
    next_session_index = 0
    last_launch_at: float | None = None

    while active_threads or next_session_index < len(raw_data_asset_ids):
        while (
            next_session_index < len(raw_data_asset_ids)
            and len(active_threads) < max_concurrent_sessions
        ):
            _wait_for_next_launch(last_launch_at)
            thread, error = _start_video_session_thread(
                raw_data_asset_ids[next_session_index], process_types
            )
            active_threads[thread] = error
            next_session_index += 1
            last_launch_at = time.monotonic()

        completed_threads = []
        for thread, error in list(active_threads.items()):
            if not thread.is_alive():
                thread.join()
                if error and first_error is None:
                    first_error = error[0]
                completed_threads.append(thread)

        for thread in completed_threads:
            del active_threads[thread]

        if active_threads and not completed_threads:
            time.sleep(THREAD_STATUS_CHECK_INTERVAL)

    if first_error is not None:
        raise first_error


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
        "--max-concurrent-sessions",
        type=int,
        default=MAX_CONCURRENT_SESSIONS,
        help=(
            "Maximum number of sessions to process concurrently "
            f"(default: {MAX_CONCURRENT_SESSIONS})."
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

    process_video_sessions(
        raw_data_asset_ids,
        max_concurrent_sessions=args.max_concurrent_sessions,
        process_types=args.process_types,
    )


if __name__ == "__main__":
    main()
