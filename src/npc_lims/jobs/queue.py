from __future__ import annotations

import datetime
import functools
import json
import logging
import time
from typing import Union

import npc_session
import upath
from aind_codeocean_api.models.computations_requests import ComputationDataAsset
from typing_extensions import TypeAlias

import npc_lims
import npc_lims.metadata.codeocean as codeocean

logger = logging.getLogger()

SessionID: TypeAlias = Union[str, npc_session.SessionRecord]
JobID: TypeAlias = str

QUEUE_JSON_DIR = upath.UPath(
    "s3://aind-scratch-data/arjun.sridhar/queue"
)  # TODO figure out path
INITIAL_VALUE = "Added to Queue"
INITIAL_INT_VALUE = -1

MAX_RUNNING_JOBS = 8


def read_json(process_name: str) -> dict[str, npc_lims.CapsuleComputationAPI]:
    return json.loads((QUEUE_JSON_DIR / process_name).read_bytes())


def is_session_in_queue(
    session: str | npc_session.SessionRecord, process_name: str
) -> bool:

    if not (QUEUE_JSON_DIR / f"{process_name}.json").exists():
        return False

    return session in read_json(process_name)


def add_to_json(
    session_id: SessionID, process_name: str, response: npc_lims.CapsuleComputationAPI
) -> None:
    if not (QUEUE_JSON_DIR / f"{process_name}.json").exists():
        current = {}
    else:
        current = read_json(process_name)

    is_new = session_id not in current
    current.update({session_id: response})
    (QUEUE_JSON_DIR / f"{process_name}.json").write_text(json.dumps(current, indent=4))
    logger.info(
        f"{'Added' if is_new else 'Updated'} {session_id} {'to' if is_new else 'in'} json"
    )


def add_to_queue(
    session_id: str | npc_session.SessionRecord, process_name: str
) -> None:
    session = npc_session.SessionRecord(session_id)

    if not is_session_in_queue(session_id, process_name):
        request_dict: npc_lims.CapsuleComputationAPI = {
            "created": INITIAL_INT_VALUE,
            "end_status": INITIAL_VALUE,
            "has_results": False,
            "id": INITIAL_VALUE,
            "name": INITIAL_VALUE,
            "run_time": INITIAL_INT_VALUE,
            "state": INITIAL_VALUE,
        }
        add_to_json(session, process_name, request_dict)


@functools.lru_cache(maxsize=1)
def get_current_job_status(
    job_or_session_id: str, process_name: str
) -> npc_lims.CapsuleComputationAPI:
    try:
        session_id = npc_session.SessionRecord(job_or_session_id).id
    except ValueError:
        job_id = job_or_session_id
    else:
        job_id = read_json(process_name)[session_id]["id"]
    job_status = npc_lims.get_job_status(job_id, check_files=True)

    return job_status


def sync_json(process_name: str) -> None:
    current = read_json(process_name)
    for session_id in current:
        current[session_id] = get_current_job_status(session_id)
        logger.info(f"Updated {session_id} status")

    (QUEUE_JSON_DIR / f"{process_name}.json").write_text(json.dumps(current, indent=4))
    logger.info("Wrote updated json")


def get_data_asset_name(session_id: SessionID, process_name: str) -> str:
    created_dt = (
        npc_session.DatetimeRecord(
            datetime.datetime.fromtimestamp(
                get_current_job_status(session_id)["created"]
            )
        )
        .replace(" ", "_")
        .replace(":", "-")
    )
    return f"{npc_lims.get_raw_data_root(session_id).name}_{process_name}_{created_dt}"


def create_data_asset(session_id: SessionID, job_id: str, process_name: str) -> None:
    asset = codeocean.create_session_data_asset(session_id, job_id, process_name)

    if asset is None:
        logger.info(f"Failed to create data asset for {session_id}")
        return

    asset.raise_for_status()
    while not asset_exists(session_id, process_name):
        time.sleep(10)
    logger.info(f"Created data asset for {session_id}")
    npc_lims.set_asset_viewable_for_everyone(asset.json()["id"])


def asset_exists(session_id: SessionID, process_name: str) -> bool:
    name = get_data_asset_name(session_id, process_name)
    return any(
        asset["name"] == name for asset in npc_lims.get_session_data_assets(session_id)
    )


def create_all_data_assets(process_name: str, overwrite_existing_assets: bool) -> None:
    sync_json(process_name)

    for session_id in read_json(process_name):
        job_status = get_current_job_status(session_id)
        if npc_lims.is_computation_errorred(
            job_status
        ) or not npc_lims.is_computation_finished(job_status):
            continue
        if asset_exists(session_id, process_name) and not overwrite_existing_assets:
            continue
        create_data_asset(session_id, job_status["id"], process_name)


def sync_and_get_num_running_jobs(process_name: str) -> int:
    sync_json(process_name)
    return sum(
        1
        for job in read_json(process_name).values()
        if job["state"] in ("running", "initializing")
    )


def is_started(session_id: SessionID, process_name: str) -> bool:
    return read_json(process_name)[session_id]["state"] in ("running", "initializing")


def add_sessions_to_queue(process_name: str) -> None:
    for session_info in npc_lims.get_session_info(is_ephys=True, is_uploaded=True):
        session_id = session_info.id
        add_to_queue(session_id, process_name)


def start(
    session_id: SessionID, capsule_pipeline_info: codeocean.CapsulePipelineInfo
) -> None:
    data_assets = [
        ComputationDataAsset(
            id=npc_lims.get_session_raw_data_asset(session_id)["id"],
            mount="ecephys",
        ),
    ]
    response = npc_lims.run_capsule_or_pipeline(
        data_assets, capsule_pipeline_info.id, capsule_pipeline_info.is_pipeline
    )
    logger.info(f"Started job for {session_id}")
    add_to_json(session_id, capsule_pipeline_info.process_name, response)


def process_capsule_or_pipeline_queue(
    capsule_or_pipeline_id: str,
    process_name: str,
    is_pipeline: bool = False,
    rerun_errorred_jobs: bool = False,
    overwrite_existing_assets: bool = False,
) -> None:
    """
    adds jobs to queue for capsule/pipeline, then processes them - run capsule/pipeline and then create data asset
    example: process_queue('1f8f159a-7670-47a9-baf1-078905fc9c2e', 'sorted', is_pipeline=True)
    """
    capsule_pipeline_info = codeocean.CapsulePipelineInfo(
        capsule_or_pipeline_id, process_name, is_pipeline
    )

    add_sessions_to_queue(capsule_pipeline_info.process_name)

    for session_info in npc_lims.get_session_info(is_ephys=True, is_uploaded=True):
        session_id = session_info.id

        if is_started(session_id, capsule_pipeline_info.process_name):
            logger.debug(f"Already started: {session_id}")
            if not rerun_errorred_jobs or not npc_lims.is_computation_errorred(
                get_current_job_status(session_id)
            ):
                continue

        # to avoid overloading CodeOcean
        while (
            sync_and_get_num_running_jobs(capsule_pipeline_info.process_name)
            >= MAX_RUNNING_JOBS
        ):
            time.sleep(600)
        start(session_id, capsule_pipeline_info)

    while sync_and_get_num_running_jobs(capsule_pipeline_info.process_name) > 0:
        time.sleep(600)
    create_all_data_assets(
        capsule_pipeline_info.process_name, overwrite_existing_assets
    )


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
