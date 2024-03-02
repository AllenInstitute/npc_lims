from __future__ import annotations

import functools
import os
import re
import uuid
import warnings
from collections.abc import Mapping, Sequence
from typing import Any, Literal

import npc_session
import requests
import upath
from aind_codeocean_api import codeocean as aind_codeocean_api
from aind_codeocean_api.models import data_assets_requests as aind_codeocean_requests
from aind_codeocean_api.models.computations_requests import (
    ComputationDataAsset,
    RunCapsuleRequest,
)
from typing_extensions import TypeAlias

import npc_lims.exceptions as exceptions

DataAssetAPI: TypeAlias = dict[
    Literal[
        "created",
        "custom_metadata",
        "description",
        "files",
        "id",
        "last_used",
        "name",
        "size",
        "sourceBucket",
        "state",
        "tags",
        "type",
    ],
    Any,
]
"""Result from CodeOcean API when querying data assets."""

RunCapsuleResponseAPI: TypeAlias = dict[
    Literal["created", "has_results", "id", "name", "run_time", "state"], Any
]
CapsuleComputationAPI: TypeAlias = dict[
    Literal["created", "end_status", "has_results", "id", "name", "run_time", "state"],
    Any,
]
"""Result from CodeOceanAPI when querying for computations for a capsule"""

ResultItemAPI: TypeAlias = dict[Literal["name", "path", "size", "type"], Any]
"""Result from CodeOceanAPI when querying for results from a computation"""

MODEL_CAPSULE_PIPELINE_MAPPING: dict[str, str] = {
    "dlc_eye": "4cf0be83-2245-4bb1-a55c-a78201b14bfe",
    "dlc_side": "facff99f-d3aa-4ecd-8ef8-a343c38197aa",
    "dlc_face": "a561aa4c-2066-4ff2-a916-0db86b918cdf",
    "facemap": "670de0b3-f73d-4d22-afe6-6449c45fada4",
}


class SessionIndexError(IndexError):
    pass


class ModelCapsuleMappingError(KeyError):
    pass


@functools.cache
def get_codeocean_client() -> aind_codeocean_api.CodeOceanClient:
    token = os.getenv(
        key="CODE_OCEAN_API_TOKEN",
        default=next(
            (v for v in os.environ.values() if v.lower().startswith("cop_")), None
        ),
    )
    if token is None:
        raise exceptions.MissingCredentials(
            "`CODE_OCEAN_API_TOKEN` not found in environment variables"
        )
    return aind_codeocean_api.CodeOceanClient(
        domain=os.getenv(
            key="CODE_OCEAN_DOMAIN",
            default="https://codeocean.allenneuraldynamics.org",
        ),
        token=token,
    )


def get_subject_data_assets(subject: str | int) -> tuple[DataAssetAPI, ...]:
    """
    All assets associated with a subject ID.

    Examples:
        >>> assets = get_subject_data_assets(668759)
        >>> assert len(assets) > 0
    """
    response = get_codeocean_client().search_all_data_assets(
        query=f"subject id: {npc_session.SubjectRecord(subject)}"
    )
    response.raise_for_status()
    return response.json()["results"]


def get_session_data_assets(
    session: str | npc_session.SessionRecord,
) -> tuple[DataAssetAPI, ...]:
    session = npc_session.SessionRecord(session)
    assets = get_subject_data_assets(session.subject)
    return tuple(
        asset
        for asset in assets
        if re.match(
            f"ecephys_{session.subject}_{session.date}_{npc_session.PARSE_TIME}(_[a-z]*_[a-z]*)*",
            asset["name"],
        )
    )


def get_session_result_data_assets(
    session: str | npc_session.SessionRecord,
) -> tuple[DataAssetAPI, ...]:
    """
    Examples:
        >>> result_data_assets = get_session_result_data_assets('668759_20230711')
        >>> assert len(result_data_assets) > 0
    """
    session_data_assets = get_session_data_assets(session)
    result_data_assets = tuple(
        data_asset
        for data_asset in session_data_assets
        if data_asset["type"] == "result"
    )

    return result_data_assets


def get_single_data_asset(
    session: str | npc_session.SessionRecord,
    data_assets: Sequence[DataAssetAPI],
    data_asset_type: str,
) -> DataAssetAPI:
    if not data_assets:
        raise ValueError(
            f"No {data_asset_type} data assets found for session {session}"
        )

    session = npc_session.SessionRecord(session)

    if len(data_assets) == 1 and session.idx == 0:
        return data_assets[0]

    asset_names = tuple(asset["name"] for asset in data_assets)
    session_times = sorted(
        {
            time
            for time in map(npc_session.extract_isoformat_time, asset_names)
            if time is not None
        }
    )
    sessions_times_to_assets = {
        session_time: tuple(
            asset
            for asset in data_assets
            if npc_session.extract_isoformat_time(asset["name"]) == session_time
        )
        for session_time in session_times
    }
    if 0 < len(session_times) < session.idx + 1:  # 0-indexed
        raise SessionIndexError(
            f"Number of assets is less than expected: cannot extract asset for session idx = {session.idx} from {asset_names = }"
        )
    data_assets = sessions_times_to_assets[session_times[session.idx]]
    if len(data_assets) > 1:
        warnings.warn(
            f"There is more than one asset for {session = }. Defaulting to most recent: {asset_names}"
        )
        created_timestamps = [data_asset["created"] for data_asset in data_assets]
        most_recent_index = created_timestamps.index(max(created_timestamps))
        return data_assets[most_recent_index]
    return data_assets[0]


def get_session_sorted_data_asset(
    session: str | npc_session.SessionRecord,
) -> DataAssetAPI:
    """
    Examples:
        >>> sorted_data_asset = get_session_sorted_data_asset('668759_20230711')
        >>> assert isinstance(sorted_data_asset, dict)
    """
    session_result_data_assets = get_session_data_assets(session)
    sorted_data_assets = tuple(
        data_asset
        for data_asset in session_result_data_assets
        if is_sorted_data_asset(data_asset) and data_asset["files"] > 2
    )

    if not sorted_data_assets:
        raise ValueError(f"Session {session} has no sorted data assets")

    return get_single_data_asset(session, sorted_data_assets, "sorted")


@functools.cache
def get_sessions_with_data_assets(
    subject: str | int,
) -> tuple[npc_session.SessionRecord, ...]:
    """
    Examples:
        >>> sessions = get_sessions_with_data_assets(668759)
        >>> assert len(sessions) > 0
    """
    assets = get_subject_data_assets(subject)
    sessions = set()
    for asset in assets:
        try:
            session = npc_session.SessionRecord(asset["name"])
        except ValueError:
            continue
        sessions.add(session)
    return tuple(sessions)


def get_data_asset(asset: str | uuid.UUID | DataAssetAPI) -> DataAssetAPI:
    """Converts an asset uuid to dict of info from CodeOcean API."""
    if not isinstance(asset, Mapping):
        response = get_codeocean_client().get_data_asset(str(asset))
        response.raise_for_status()
        asset = response.json()
    assert isinstance(asset, Mapping), f"Unexpected {type(asset) = }, {asset = }"
    return asset


def is_raw_data_asset(asset: str | DataAssetAPI) -> bool:
    """
    Examples:
        >>> is_raw_data_asset('83636983-f80d-42d6-a075-09b60c6abd5e')
        True
        >>> is_raw_data_asset('173e2fdc-0ca3-4a4e-9886-b74207a91a9a')
        False
    """
    asset = get_data_asset(asset)
    if is_sorted_data_asset(asset):
        return False
    return asset.get("custom_metadata", {}).get(
        "data level"
    ) == "raw data" or "raw" in asset.get("tags", [])


def is_sorted_data_asset(asset: str | DataAssetAPI) -> bool:
    """
    Examples:
        >>> is_sorted_data_asset('173e2fdc-0ca3-4a4e-9886-b74207a91a9a')
        True
        >>> is_sorted_data_asset('83636983-f80d-42d6-a075-09b60c6abd5e')
        False
    """
    asset = get_data_asset(asset)
    if "ecephys" not in asset["name"]:
        return False
    return "sorted" in asset["name"]


def get_session_raw_data_asset(
    session: str | npc_session.SessionRecord,
) -> DataAssetAPI:
    """
    Examples:
        >>> get_session_raw_data_asset('668759_20230711')["id"]
        '83636983-f80d-42d6-a075-09b60c6abd5e'
    """
    session = npc_session.SessionRecord(session)
    raw_assets = tuple(
        asset for asset in get_session_data_assets(session) if is_raw_data_asset(asset)
    )

    if not raw_assets:
        raise ValueError(f"Session {session} has no raw data assets")

    return get_single_data_asset(session, raw_assets, "raw")


def get_surface_channel_root(session: str | npc_session.SessionRecord) -> upath.UPath:
    """Reconstruct path to surface channel data in bucket (e.g. on s3) using data-asset
    info from Code Ocean.

    Examples:
        >>> get_surface_channel_root('660023_20230808')
        S3Path('s3://aind-ephys-data/ecephys_660023_2023-08-08_15-11-14')
        >>> assert get_surface_channel_root('660023_20230808') != get_raw_data_root('660023_20230808')
        >>> get_surface_channel_root('649943_20230216')
        Traceback (most recent call last):
        ...
        FileNotFoundError: 649943_20230216 has no surface channel data assets
    """
    session = npc_session.SessionRecord(session)
    raw_assets = tuple(
        asset for asset in get_session_data_assets(session) if is_raw_data_asset(asset)
    )
    try:
        raw_asset = get_single_data_asset(session.with_idx(1), raw_assets, "raw")
    except SessionIndexError:
        raise FileNotFoundError(
            f"{session} has no surface channel data assets"
        ) from None
    return get_path_from_data_asset(raw_asset)


@functools.cache
def get_raw_data_root(session: str | npc_session.SessionRecord) -> upath.UPath:
    """Reconstruct path to raw data in bucket (e.g. on s3) using data-asset
    info from Code Ocean.

        >>> get_raw_data_root('668759_20230711')
        S3Path('s3://aind-ephys-data/ecephys_668759_2023-07-11_13-07-32')
    """
    raw_asset = get_session_raw_data_asset(session)

    return get_path_from_data_asset(raw_asset)


def get_path_from_data_asset(asset: DataAssetAPI) -> upath.UPath:
    """Reconstruct path to raw data in bucket (e.g. on s3) using data asset
    uuid or dict of info from Code Ocean API."""
    if "sourceBucket" not in asset:
        raise ValueError(
            f"Asset {asset['id']} has no `sourceBucket` info - not sure how to create UPath:\n{asset!r}"
        )
    bucket_info = asset["sourceBucket"]
    roots = {"aws": "s3", "gcs": "gs"}
    if bucket_info["origin"] not in roots:
        raise RuntimeError(
            f"Unknown bucket origin - not sure how to create UPath: {bucket_info = }"
        )
    return upath.UPath(
        f"{roots[bucket_info['origin']]}://{bucket_info['bucket']}/{bucket_info['prefix']}"
    )


@functools.cache
def get_session_units_data_asset(
    session_id: str | npc_session.SessionRecord,
) -> DataAssetAPI:
    """
    Examples:
        >>> units_data_asset = get_session_units_data_asset('668759_20230711')
        >>> assert units_data_asset is not None
    """
    session = npc_session.SessionRecord(session_id)
    session_data_assets = get_session_data_assets(session)
    session_units_data_assets = tuple(
        data_asset
        for data_asset in session_data_assets
        if "units" in data_asset["name"] and "peak" not in data_asset["name"]
    )
    session_units_data_asset = get_single_data_asset(
        session, session_units_data_assets, "units"
    )

    return session_units_data_asset


@functools.cache
def get_session_units_spikes_with_peak_channels_data_asset(
    session_id: str | npc_session.SessionRecord,
) -> DataAssetAPI:
    """
    Examples:
        >>> units_peak_channel_data_asset = get_session_units_spikes_with_peak_channels_data_asset('668759_20230711')
        >>> assert units_peak_channel_data_asset is not None
    """
    session = npc_session.SessionRecord(session_id)
    session_data_assets = get_session_data_assets(session)
    session_units_spikes_peak_channel_data_assets = tuple(
        data_asset
        for data_asset in session_data_assets
        if "units_with_peak_channels" in data_asset["name"]
    )

    session_units_spikes_peak_channel_data_asset = get_single_data_asset(
        session, session_units_spikes_peak_channel_data_assets, "units"
    )

    return session_units_spikes_peak_channel_data_asset


def update_permissions_for_data_asset(data_asset: DataAssetAPI) -> None:
    response = get_codeocean_client().update_permissions(
        data_asset_id=data_asset["id"], everyone="viewer"
    )
    response.raise_for_status()


def run_capsule_or_pipeline(
    data_assets: list[ComputationDataAsset],
    model_name: str,
) -> requests.models.Response:
    if model_name not in MODEL_CAPSULE_PIPELINE_MAPPING:
        raise ModelCapsuleMappingError(
            f"No capsule associated with {model_name}. Check codeocean"
        )

    if "pipeline" in model_name:
        run_capsule_request = RunCapsuleRequest(
            pipeline_id=MODEL_CAPSULE_PIPELINE_MAPPING[model_name],
            data_assets=data_assets,
        )
    else:
        run_capsule_request = RunCapsuleRequest(
            capsule_id=MODEL_CAPSULE_PIPELINE_MAPPING[model_name],
            data_assets=data_assets,
        )

    response = get_codeocean_client().run_capsule(run_capsule_request)
    response.raise_for_status()
    return response


def get_model_data_asset(
    session: str | npc_session.SessionRecord, model_name: str
) -> DataAssetAPI:
    """
    Returns the data asset for a given model
    >>> model_asset = get_model_data_asset('676909_2023-12-13', 'dlc_eye')
    >>> model_asset['name']
    'ecephys_676909_2023-12-13_13-43-40_dlc_eye'
    """
    session = npc_session.SessionRecord(session)
    if model_name not in MODEL_CAPSULE_PIPELINE_MAPPING:
        raise ModelCapsuleMappingError(
            f"No capsule associated with {model_name}. Check codeocean"
        )

    session_data_assets = get_session_data_assets(session)
    session_model_asset = tuple(
        asset for asset in session_data_assets if model_name in asset["name"]
    )
    if not session_model_asset:
        raise FileNotFoundError(f"{session} has no {model_name} results")

    single_model_asset = get_single_data_asset(session, session_model_asset, model_name)
    if single_model_asset["files"] < 3:
        raise ValueError(
            f"{model_name} did not finish and was stopped abrutly. Rerun for session {session}"
        )

    return single_model_asset


def check_computation_result(
    session: npc_session.SessionRecord, computation_id: str, model_name: str
) -> None:
    response_result_items = get_codeocean_client().get_list_result_items(computation_id)
    response_result_items.raise_for_status()
    result_items = response_result_items.json()

    session_result_item = tuple(
        item for item in result_items["items"] if len(result_items["items"]) > 2
    )

    if not session_result_item:
        raise ValueError(
            f"Run {computation_id} for capsule {model_name} has no valid results"
        )


def create_session_data_asset(
    session: str | npc_session.SessionRecord, model_name: str, computation_id: str
) -> None:
    session = npc_session.SessionRecord(session)

    if model_name not in MODEL_CAPSULE_PIPELINE_MAPPING:
        raise ModelCapsuleMappingError(
            f"No capsule associated with {model_name}. Check codeocean"
        )

    check_computation_result(session, computation_id, model_name)

    data_asset_name = f"{get_session_raw_data_asset(session)['name']}_{model_name}"

    source = aind_codeocean_requests.Source(
        computation=aind_codeocean_requests.Sources.Computation(id=computation_id)
    )
    custom_metadata = {"subject id": str(session.subject)}
    tags = [model_name, "results"]
    create_data_asset_request = aind_codeocean_requests.CreateDataAssetRequest(
        name=data_asset_name,
        mount=data_asset_name,
        tags=tags,
        source=source,
        custom_metadata=custom_metadata,
    )

    get_codeocean_client().create_data_asset(
        create_data_asset_request
    ).raise_for_status()
    # TODO: add tests and function to get data asset


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
