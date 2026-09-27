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

EPHYS_TRIGGER_CAPSULE_ID = "eb5a26e4-a391-4d79-9da5-1ab65b71253f"
SPIKE_SORTING_PIPELINE_TYPE = "ecephys_ks25_v0.1.0"
STATUS_CSV_URL = (
    "https://raw.githubusercontent.com/AllenInstitute/npc_lims/main/tables/status.csv"
)
MAX_CONCURRENT_JOBS = 3
LAUNCH_PAUSE_SECONDS = 10.0
POLL_INTERVAL = 60.0


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
        capsule_id=EPHYS_TRIGGER_CAPSULE_ID,
        named_parameters=[
            NamedRunParam(
                param_name="pipeline_type",
                value=SPIKE_SORTING_PIPELINE_TYPE,
            ),
            NamedRunParam(
                param_name="input_data_asset_id",
                value=raw_data_asset_id,
            ),
        ],
    )


def trigger_spike_sorting(raw_data_asset_id: str) -> Computation:
    """Start spike sorting for one raw data asset."""
    return npc_lims.get_codeocean_client().computations.run_capsule(
        get_run_params(raw_data_asset_id)
    )


def launch_spike_sorting(raw_data_asset_id: str) -> Computation:
    """Launch spike sorting synchronously so API errors surface immediately."""
    print(f"Requesting spike sorting for {raw_data_asset_id}...", flush=True)
    try:
        computation = trigger_spike_sorting(raw_data_asset_id)
    except Exception as exc:
        raise RuntimeError(
            f"Could not launch spike sorting for {raw_data_asset_id}"
        ) from exc

    print(
        f"Launched spike sorting for {raw_data_asset_id} "
        f"(computation {computation.id})",
        flush=True,
    )
    return computation


def is_computation_complete(computation: Computation) -> bool:
    """Poll once, raising on failure and returning whether the job is complete."""
    status = npc_lims.get_codeocean_client().computations.get_computation(
        computation.id
    )
    if status.state == ComputationState.Failed or getattr(
        status, "end_status", None
    ) in (ComputationEndStatus.Failed, ComputationEndStatus.Stopped):
        raise RuntimeError(f"Computation failed: {computation.id}")
    if status.state == ComputationState.Completed:
        if npc_lims.is_computation_errored(status):
            raise RuntimeError(f"Computation failed: {computation.id}")
        return True
    return False


def wait_for_computation(computation: Computation) -> None:
    """Poll a computation until it succeeds or fails."""
    while not is_computation_complete(computation):
        time.sleep(POLL_INTERVAL)


def process_asset(raw_data_asset_id: str) -> None:
    computation = launch_spike_sorting(raw_data_asset_id)
    try:
        wait_for_computation(computation)
    except Exception as exc:
        raise RuntimeError(
            f"Spike sorting failed for {raw_data_asset_id} "
            f"(computation {computation.id})"
        ) from exc


def _wait_for_next_launch(last_launch_at: float | None) -> None:
    if last_launch_at is None:
        return
    elapsed = time.monotonic() - last_launch_at
    if elapsed < LAUNCH_PAUSE_SECONDS:
        remaining = LAUNCH_PAUSE_SECONDS - elapsed
        print(f"Waiting {remaining:.1f}s before next launch...", flush=True)
        time.sleep(remaining)


def process_assets(
    raw_data_asset_ids: list[str],
    max_concurrent_jobs: int = MAX_CONCURRENT_JOBS,
) -> None:
    """Launch and poll spike sorting with bounded remote concurrency."""
    if max_concurrent_jobs < 1:
        raise ValueError("max_concurrent_jobs must be at least 1")

    active_computations: dict[str, tuple[Computation, str]] = {}
    next_asset_index = 0
    last_launch_at: float | None = None

    while active_computations or next_asset_index < len(raw_data_asset_ids):
        while (
            next_asset_index < len(raw_data_asset_ids)
            and len(active_computations) < max_concurrent_jobs
        ):
            _wait_for_next_launch(last_launch_at)
            raw_data_asset_id = raw_data_asset_ids[next_asset_index]
            computation = launch_spike_sorting(raw_data_asset_id)
            active_computations[computation.id] = (
                computation,
                raw_data_asset_id,
            )
            next_asset_index += 1
            last_launch_at = time.monotonic()

        completed_ids: list[str] = []
        for computation_id, (
            computation,
            raw_data_asset_id,
        ) in active_computations.items():
            try:
                is_complete = is_computation_complete(computation)
            except Exception as exc:
                raise RuntimeError(
                    f"Spike sorting failed for {raw_data_asset_id} "
                    f"(computation {computation_id})"
                ) from exc
            if is_complete:
                print(
                    f"Completed spike sorting for {raw_data_asset_id} "
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
        description="Run spike sorting for unsorted uploaded assets."
    )
    parser.add_argument(
        "--max-concurrent-jobs",
        type=int,
        default=MAX_CONCURRENT_JOBS,
        help=(
            "Maximum number of sorting jobs to run concurrently "
            f"(default: {MAX_CONCURRENT_JOBS})."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    status = pl.read_csv(STATUS_CSV_URL, null_values=[""])
    asset_ids = get_unsorted_asset_ids(status)
    print(f"Found {len(asset_ids)} unsorted assets")
    process_assets(asset_ids, args.max_concurrent_jobs)


if __name__ == "__main__":
    main()
