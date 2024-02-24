from __future__ import annotations

import npc_session
from aind_codeocean_api.models.computations_requests import ComputationDataAsset

import npc_lims.metadata.codeocean as codeocean
import npc_lims.status as status

# TODO: update this module


def check_capsule_exists(capsule_or_pipeline_name: str) -> None:
    """
    >>> check_capsule_exists('dlc_eye')
    """
    if capsule_or_pipeline_name not in codeocean.MODEL_CAPSULE_PIPELINE_MAPPING:
        raise codeocean.ModelCapsuleMappingError(
            f"No corresponding capsule for {capsule_or_pipeline_name}"
        )


def is_session_capsule_in_queue(
    session: str | npc_session.SessionRecord, capsule_or_pipeline_name: str
) -> bool:
    check_capsule_exists(capsule_or_pipeline_name)

    # if json path exits for session capsule
    # return True
    return True


def add_to_queue(
    session_id: str | npc_session.SessionRecord, capsule_or_pipeline_name: str
) -> None:
    # check if data asset already exists for session and capsule/pipeline
    try:
        codeocean.get_model_data_asset(session_id, capsule_or_pipeline_name)
        return
    except (FileNotFoundError, ValueError):
        pass

    check_capsule_exists(capsule_or_pipeline_name)

    session = npc_session.SessionRecord(session_id)

    if not is_session_capsule_in_queue(session_id, capsule_or_pipeline_name):
        # add to queue
        data_assets = [
            ComputationDataAsset(id=data_asset["id"], mount=data_asset["name"])
            for data_asset in [codeocean.get_session_raw_data_asset(session)]
        ]

        # write to queue:
        # setting priority depends on capsule/pipeline
        # {'data_assets': [id, name for data_asset in data_assets], 'run_id': 'Not started', 'session': session_id 'capsule_or_pipeline_name': capsule_or_pipeline_name, priority: 0}


def update_queue(session_json: dict[str, str | int]) -> None:
    # run_response: codeocean.RunCapsuleResponseAPI = codeocean.get_codeocean_client().get_computation(session_json['id'])
    # if run_response['state'] == 'completed' and run_response['end_status'] == 'succeeded':
    # codeocean.create_session_data_asset(session, capsule_or_pipeline_name, run_response['id'])

    # update permissions
    # data_asset = codeocean.get_model_data_asset(session, capsule_or_pipeline_name)
    # codeocean.update_permissions_for_data_asset(data_asset)

    # remove from queue
    # else:
    # overwrite with run_response parameters
    pass


def add_sessions_to_queue(capsule_or_pipeline_name: str) -> None:
    for session_info in status.get_session_info():
        if is_session_capsule_in_queue(session_info.id, capsule_or_pipeline_name):
            continue

        add_to_queue(session_info.id, capsule_or_pipeline_name)


def process_queue() -> None:
    pass
    # read json files from directory

    # check if it has been run:
    # session_json['run_id'] == 'not started'
    # check priority based on capsule/pipeline (session_json['capsule_or_pipeline_name'])
    # run the job
    # run_response: codeocean.RunCapsuleResponseAPI = codeocean.run_capsule_or_pipeline(json['data_assets'], capsule_or_pipeline_name)
    # overwrite json with new parameters using run_response
    # repeat running new jobs n times to not flood server?

    # if job is running: check state and create asset if done
    # update_queue(session_json)


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
