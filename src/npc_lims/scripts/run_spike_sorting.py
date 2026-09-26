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
    RunParams,
)
from codeocean.data_asset import DataAsset

import npc_lims

SPIKE_SORTING_PIPELINE_ID = "1f8f159a-7670-47a9-baf1-078905fc9c2e"
STATUS_CSV_URL = (
    "https://raw.githubusercontent.com/AllenInstitute/npc_lims/main/tables/status.csv"
)
MAX_CONCURRENT_ASSETS = 3
LAUNCH_PAUSE_SECONDS = 10.0
POLL_INTERVAL = 60.0
THREAD_STATUS_CHECK_INTERVAL = 0.1


def get_unsorted_asset_ids(status: pl.DataFrame) -> list[str]:
    """Return uploaded main and surface assets that have not been sorted."""
    asset_ids: list[str] = []
    for row in status.iter_rows(named=True):
        if row.get("is_uploaded") is not True:
            continue

        raw_asset_id = row.get("raw_asset_id")
        if raw_asset_id and row.get("is_sorted") is not True:
            asset_ids.append(str(raw_asset_id))

        surface_asset_id = row.get("surface_channels_asset_id")
        if surface_asset_id and row.get("is_surface_channels_sorted") is not True:
            asset_ids.append(str(surface_asset_id))

    return asset_ids


def get_run_params(raw_data_asset_id: str) -> RunParams:
    return RunParams(
        pipeline_id=SPIKE_SORTING_PIPELINE_ID,
        data_assets=[DataAsset(id=raw_data_asset_id, mount="ecephys")],
    )


def trigger_spike_sorting(raw_data_asset_id: str) -> Computation:
    """Start spike sorting for one raw data asset."""
    return npc_lims.get_codeocean_client().computations.run_capsule(
        get_run_params(raw_data_asset_id)
    )


def wait_for_computation(computation: Computation) -> None:
    """Poll a computation until it succeeds or fails."""
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


def process_asset(raw_data_asset_id: str) -> None:
    print(f"Launching spike sorting for {raw_data_asset_id}")
    wait_for_computation(trigger_spike_sorting(raw_data_asset_id))


def _process_asset_in_thread(
    raw_data_asset_id: str, error: list[Exception]
) -> None:
    try:
        process_asset(raw_data_asset_id)
    except Exception as exc:
        error.append(exc)


def process_assets(
    raw_data_asset_ids: list[str],
    max_concurrent_assets: int = MAX_CONCURRENT_ASSETS,
) -> None:
    """Run spike sorting with bounded concurrency."""
    if max_concurrent_assets < 1:
        raise ValueError("max_concurrent_assets must be at least 1")

    active_threads: dict[threading.Thread, list[Exception]] = {}
    first_error: Exception | None = None
    next_asset_index = 0
    last_launch_at: float | None = None

    while active_threads or next_asset_index < len(raw_data_asset_ids):
        while (
            next_asset_index < len(raw_data_asset_ids)
            and len(active_threads) < max_concurrent_assets
        ):
            if last_launch_at is not None:
                elapsed = time.monotonic() - last_launch_at
                if elapsed < LAUNCH_PAUSE_SECONDS:
                    time.sleep(LAUNCH_PAUSE_SECONDS - elapsed)

            error: list[Exception] = []
            thread = threading.Thread(
                target=_process_asset_in_thread,
                args=(raw_data_asset_ids[next_asset_index], error),
            )
            thread.start()
            active_threads[thread] = error
            next_asset_index += 1
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
        description="Run spike sorting for unsorted uploaded assets."
    )
    parser.add_argument(
        "--max-concurrent-assets",
        type=int,
        default=MAX_CONCURRENT_ASSETS,
        help=(
            "Maximum number of assets to sort concurrently "
            f"(default: {MAX_CONCURRENT_ASSETS})."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    status = pl.read_csv(STATUS_CSV_URL, null_values=[""])
    asset_ids = get_unsorted_asset_ids(status)
    print(f"Found {len(asset_ids)} unsorted assets")
    process_assets(asset_ids, args.max_concurrent_assets)


if __name__ == "__main__":
    main()
