from __future__ import annotations

import concurrent.futures
import datetime
import functools
import json
import logging
import time
from typing import Union

import npc_session
import upath
from codeocean.computation import Computation, ComputationState, RunParams
from codeocean.data_asset import ComputationSource, DataAsset, DataAssetParams, Source
from typing_extensions import TypeAlias

import npc_lims

logger = logging.getLogger()

SessionID: TypeAlias = Union[str, npc_session.SessionRecord]


JobID: TypeAlias = str

SORTING_PIPELINE_ID = "1f8f159a-7670-47a9-baf1-078905fc9c2e"
JSON_PATH = upath.UPath("sorting_jobs.json")
MAX_RUNNING_JOBS = 4

EXAMPLE_JOB_STATUS = {
    "created": 1708570920,
    "has_results": True,
    "id": "eadd2f5e-6f3b-4179-8788-5d6e798b1f92",
    "name": "Run 8570920",
    "run_time": 92774,
    "state": "completed",
    "end_status": "succeeded",
}


def get_run_sorting_request(session_id: SessionID) -> RunParams:
    return RunParams(
        pipeline_id=SORTING_PIPELINE_ID,
        data_assets=[
            DataAsset(
                id=npc_lims.get_session_raw_data_asset(session_id).id,
                mount="ecephys",
            ),
        ],
    )


def read_json() -> dict[str, Computation | None]:
    return npc_lims.read_computation_queue(JSON_PATH)


def add_to_json(
    session_id: SessionID,
    computation: Computation | None,
) -> None:
    return npc_lims.add_to_computation_queue(JSON_PATH, session_id, computation)


def is_in_json(session_id: SessionID) -> bool:
    if not JSON_PATH.exists():
        return False
    return session_id in read_json()


def is_started(session_id: SessionID) -> bool:
    return is_in_json(session_id)


def is_bad_docker_run(session_id: SessionID) -> bool:
    session_id = npc_session.SessionRecord(session_id).id
    queue = read_json()
    if session_id not in queue:
        raise ValueError(f"{session_id} not in queue")

    queued = queue[session_id]
    if queued is None:
        raise ValueError(f"{session_id} has no queued job")

    dt = datetime.datetime.fromtimestamp(queued.created)
    return datetime.datetime(2024, 3, 12) <= dt < datetime.datetime(2024, 3, 20)


def has_bad_docker_asset(session_id: SessionID) -> bool:
    try:
        sorted_asset = npc_lims.get_session_sorted_data_asset(session_id)
    except ValueError:
        return False
    dt: datetime.date = npc_session.DateRecord(
        sorted_asset.name.split("sorted_")[-1]
    ).dt
    return datetime.date(2024, 3, 12) <= dt < datetime.date(2024, 3, 20)


@functools.lru_cache(maxsize=1)
def get_current_job_status(
    job_or_session_id: str,
) -> Computation | None:
    """
    >>> status = get_current_job_status("633d9d0d-511a-4601-884c-5a7f4a63365f")
    """
    return npc_lims.get_current_queue_computation(
        JSON_PATH,
        job_or_session_id,
    )


def sync_json() -> None:
    current = read_json()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        session_to_future = {
            session_id: executor.submit(get_current_job_status, session_id)
            for session_id in current
        }
    for session_id, future in session_to_future.items():
        current[session_id] = npc_lims.serialize_computation(future.result())
        logger.info(f"Updated {session_id} status")

    JSON_PATH.write_text(json.dumps(current, indent=4))
    logger.info("Wrote updated json")


def sync_and_get_num_running_jobs() -> int:
    sync_json()
    return sum(
        1
        for job in read_json().values()
        if job
        and job.state in (ComputationState.Running, ComputationState.Initializing)
    )


def start(session_id: SessionID) -> None:
    computation = npc_lims.get_codeocean_client().computations.run_capsule(
        get_run_sorting_request(session_id)
    )
    logger.info(f"Started job for {session_id}")
    add_to_json(
        session_id,
        computation,
    )


def get_create_data_asset_request(session_id: SessionID) -> DataAssetParams:
    computation = get_current_job_status(session_id)
    if computation is None:
        raise ValueError(f"No computation found for {session_id}")

    session = npc_session.SessionRecord(session_id)
    asset_name = get_data_asset_name(session_id)
    return DataAssetParams(
        name=asset_name,
        mount=asset_name,
        source=Source(
            computation=ComputationSource(
                id=computation.id,
            )
        ),
        tags=[str(session.subject), "derived", "ephys", "results"],
        custom_metadata={
            "data level": "derived data",
            "experiment type": "ecephys",
            "modality": "Extracellular electrophysiology",
            "subject id": str(session.subject),
        },
    )


def get_data_asset_name(session_id: SessionID) -> str:
    computation = get_current_job_status(session_id)
    if computation is None:
        raise ValueError(f"No computation found for {session_id}")
    created_dt = (
        npc_session.DatetimeRecord(datetime.datetime.fromtimestamp(computation.created))
        .replace(" ", "_")
        .replace(":", "-")
    )
    return f"{npc_lims.get_raw_data_root(session_id).name}_sorted_{created_dt}"


def create_data_asset(session_id: SessionID) -> None:
    asset = npc_lims.get_codeocean_client().data_assets.create_data_asset(
        get_create_data_asset_request(session_id)
    )
    while not asset_exists(session_id):
        time.sleep(10)
    logger.info(f"Created data asset for {session_id}")
    npc_lims.set_asset_viewable_for_everyone(asset.id)


def asset_exists(session_id: SessionID) -> bool:
    name = get_data_asset_name(session_id)
    return any(
        asset.name == name for asset in npc_lims.get_session_data_assets(session_id)
    )


def create_all_data_assets() -> None:
    sync_json()
    for session_id in read_json():
        job_status = get_current_job_status(session_id)
        if npc_lims.is_computation_errored(
            job_status
        ) or not npc_lims.is_computation_finished(job_status):
            continue
        if asset_exists(session_id):
            continue
        create_data_asset(session_id)


def main(
    rerun_errored_jobs: bool = False,
    reverse: bool = False,
) -> None:
    sessions = npc_lims.get_session_info(is_ephys=True, is_uploaded=True)
    if reverse:
        sessions = tuple(reversed(sessions))
    for session_info in sessions:
        session_ids = [session_info.id]
        if session_info.is_surface_channels:
            session_ids.append(session_info.id.with_idx(1))

        for session_id in session_ids:
            is_skippable = (
                is_started(session_id)
                and not is_bad_docker_run(session_id)
                and not has_bad_docker_asset(session_id)
            )
            if is_skippable:
                logger.debug(f"Already started: {session_id}")

                if not rerun_errored_jobs:
                    continue
                if not npc_lims.is_computation_errored(
                    get_current_job_status(session_id)
                ):
                    continue

            # to avoid overloading CodeOcean
            while sync_and_get_num_running_jobs() >= MAX_RUNNING_JOBS:
                time.sleep(600)
            start(session_id)

    while sync_and_get_num_running_jobs() > 0:
        time.sleep(600)
    create_all_data_assets()


if __name__ == "__main__":
    import doctest

    doctest.testmod(raise_on_error=True)
    # logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    # sync_json()
    # main(rerun_errored_jobs=True, reverse=False)
    # create_all_data_assets()
    # sync_json()
