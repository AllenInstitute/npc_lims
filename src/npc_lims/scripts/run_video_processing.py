#!/usr/bin/env python

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "npc-lims[polars]",
# ]
#
# [tool.uv.sources]
# npc_lims = { git = "https://github.com/AllenInstitute/npc_lims" }
# ///

from __future__ import annotations

import time
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
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
MAX_CONCURRENT_SESSIONS = 3
POLL_INTERVAL = 60.0


def get_missing_processes(row: Mapping[str, Any]) -> list[str]:
    """Return video processes whose status is false or unavailable."""
    return [
        process_name
        for process_name, status_column in PROCESS_STATUS_COLUMNS.items()
        if row.get(status_column) is not True
    ]


def get_run_params(raw_data_asset_id: str) -> RunParams:
    """Create the argparse-style parameters expected by the dispatcher capsule."""
    parameters = {
        "raw_data_asset_id": raw_data_asset_id,
        "dry_run": "0",
        "skip_existing": "1",
    }

    return RunParams(
        capsule_id=VIDEO_PROCESSING_CAPSULE_ID,
        named_parameters=[
            NamedRunParam(param_name=k, value=v) for k, v in parameters.items()
        ],
    )


def trigger_video_processing(raw_data_asset_id: str) -> Computation:
    """Trigger a dispatcher computation without waiting for it to finish."""
    return npc_lims.get_codeocean_client().computations.run_capsule(
        get_run_params(raw_data_asset_id)
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


def process_video_session(raw_data_asset_id: str) -> None:
    """Run and poll the full video-processing pipeline for one session."""
    print(f"Launching all video processing for {raw_data_asset_id}")
    wait_for_computation(trigger_video_processing(raw_data_asset_id))


def main() -> None:
    status = pl.read_csv(STATUS_CSV_URL, null_values=[""])
    video_sessions = status.filter(
        pl.col("is_video") & pl.col("raw_asset_id").is_not_null()
    )

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SESSIONS) as executor:
        futures = []
        for row in video_sessions.iter_rows(named=True):
            raw_data_asset_id = str(row["raw_asset_id"])
            missing_processes = get_missing_processes(row)
            if not missing_processes:
                continue

            futures.append(
                executor.submit(
                    process_video_session,
                    raw_data_asset_id,
                )
            )

        for future in futures:
            future.result()


if __name__ == "__main__":
    main()
