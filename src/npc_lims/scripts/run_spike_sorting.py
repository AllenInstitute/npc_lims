from __future__ import annotations

import datetime
import functools
import json
import logging
import time
from typing import TypedDict, Union

import npc_session
import requests
import upath
from aind_codeocean_api.models.computations_requests import (
    ComputationDataAsset,
    RunCapsuleRequest,
)
from aind_codeocean_api.models.data_assets_requests import (
    CreateDataAssetRequest,
    Source,
    Sources,
)
from typing_extensions import TypeAlias

import npc_lims

logger = logging.getLogger()

SessionID: TypeAlias = Union[str, npc_session.SessionRecord]


class JobStatus(TypedDict):
    """As returned from response.json()"""

    created: int
    has_results: bool
    id: str
    name: str
    run_time: int
    state: str
    end_status: str | None
    """Does not exist initially"""


JobID: TypeAlias = str

SORTING_PIPELINE_ID = "1f8f159a-7670-47a9-baf1-078905fc9c2e"
JSON_PATH = upath.UPath("sorting_jobs.json")
MAX_RUNNING_JOBS = 8

EXAMPLE_JOB_STATUS = {
    "created": 1708570920,
    "has_results": True,
    "id": "eadd2f5e-6f3b-4179-8788-5d6e798b1f92",
    "name": "Run 8570920",
    "run_time": 92774,
    "state": "completed",
    "end_status": "succeeded",
}


def get_run_sorting_request(session_id: SessionID) -> RunCapsuleRequest:
    return RunCapsuleRequest(
        pipeline_id=SORTING_PIPELINE_ID,
        data_assets=[
            ComputationDataAsset(
                id=npc_lims.get_session_raw_data_asset(session_id)["id"],
                mount="ecephys",
            ),
        ],
    )


def read_json() -> dict[str, JobStatus]:
    return json.loads(JSON_PATH.read_bytes())


def add_to_json(session_id: SessionID, response: requests.Response) -> None:
    if not JSON_PATH.exists():
        current = {}
    else:
        current = read_json()
    is_new = session_id not in current
    current.update({session_id: response.json()})
    JSON_PATH.write_text(json.dumps(current, indent=4))
    logger.info(
        f"{'Added' if is_new else 'Updated'} {session_id} {'to' if is_new else 'in'} json"
    )


def is_in_json(session_id: SessionID) -> bool:
    if not JSON_PATH.exists():
        return False
    return session_id in read_json()


def is_started(session_id: SessionID) -> bool:
    return is_in_json(session_id)


@functools.lru_cache(maxsize=1)
def get_current_job_status(
    job_or_session_id: str,
) -> JobStatus | npc_lims.CapsuleComputationAPI:
    """
    >>> get_current_job_status("633d9d0d-511a-4601-884c-5a7f4a63365f")
    {'created': 1709382940, 'end_status': 'succeeded', 'has_results': True, 'id': '4ff8ff2e-c9ae-447d-a44f-c021e515833b', 'name': 'Run 9382940', 'run_time': 48294, 'state': 'completed'}
    >>> get_current_job_status("690706_2023-11-28_0")
    {'created': 1709337736, 'end_status': 'succeeded', 'has_results': True, 'id': 'a1f19eb9-1561-4a52-804f-02d2afc88350', 'name': 'Run 9337736', 'run_time': 76306, 'state': 'completed'}
    """
    try:
        session_id = npc_session.SessionRecord(job_or_session_id).id
    except ValueError:
        job_id = job_or_session_id
    else:
        job_id = read_json()[session_id]["id"]
    job_status = npc_lims.get_job_status(job_id, check_files=True)

    return job_status


def sync_json() -> None:
    current = read_json()
    for session_id in current:
        current[session_id] = get_current_job_status(session_id)
        logger.info(f"Updated {session_id} status")

    JSON_PATH.write_text(json.dumps(current, indent=4))
    logger.info("Wrote updated json")


def sync_and_get_num_running_jobs() -> int:
    sync_json()
    return sum(
        1 for job in read_json().values() if job["state"] in ("running", "initializing")
    )


def start(session_id: SessionID) -> None:
    response = npc_lims.get_codeocean_client().run_capsule(
        get_run_sorting_request(session_id)
    )
    response.raise_for_status()
    logger.info(f"Started job for {session_id}")
    add_to_json(session_id, response)


def get_create_data_asset_request(session_id: SessionID) -> CreateDataAssetRequest:
    job_status = get_current_job_status(session_id)
    session = npc_session.SessionRecord(session_id)
    asset_name = get_data_asset_name(session_id)
    return CreateDataAssetRequest(
        name=asset_name,
        mount=asset_name,
        source=Source(
            computation=Sources.Computation(
                id=job_status["id"],
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
    created_dt = (
        npc_session.DatetimeRecord(
            datetime.datetime.fromtimestamp(
                get_current_job_status(session_id)["created"]
            )
        )
        .replace(" ", "_")
        .replace(":", "-")
    )
    return f"{npc_lims.get_raw_data_root(session_id).name}_sorted_{created_dt}"


def create_data_asset(session_id: SessionID) -> None:
    asset = npc_lims.get_codeocean_client().create_data_asset(
        get_create_data_asset_request(session_id)
    )
    asset.raise_for_status()
    while not asset_exists(session_id):
        time.sleep(10)
    logger.info(f"Created data asset for {session_id}")
    npc_lims.set_asset_viewable_for_everyone(asset.json()["id"])


def asset_exists(session_id: SessionID) -> bool:
    name = get_data_asset_name(session_id)
    return any(
        asset["name"] == name for asset in npc_lims.get_session_data_assets(session_id)
    )


def create_all_data_assets() -> None:
    sync_json()
    for session_id in read_json():
        job_status = get_current_job_status(session_id)
        if npc_lims.is_computation_errorred(
            job_status
        ) or not npc_lims.is_computation_finished(job_status):
            continue
        if asset_exists(session_id):
            continue
        create_data_asset(session_id)


def main(rerun_errorred_jobs: bool = False) -> None:
    for session_info in npc_lims.get_session_info(is_ephys=True, is_uploaded=True):
        session_id = session_info.id

        if is_started(session_id):
            logger.debug(f"Already started: {session_id}")
            if not rerun_errorred_jobs or not npc_lims.is_computation_errorred(
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

    doctest.testmod()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    main(rerun_errorred_jobs=False)
