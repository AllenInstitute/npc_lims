from __future__ import annotations

import functools
import os
import re
import uuid
import warnings
from collections.abc import Mapping, Sequence
from typing import Any, Literal

import npc_session
import upath
from aind_codeocean_api import codeocean as aind_codeocean_api  # type: ignore
from typing_extensions import TypeAlias

CODE_OCEAN_API_TOKEN = os.getenv("CODE_OCEAN_API_TOKEN", "")
CODE_OCEAN_DOMAIN = os.getenv("CODE_OCEAN_DOMAIN", "")

DataAsset: TypeAlias = dict[
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

codeocean_client = aind_codeocean_api.CodeOceanClient(
    domain=CODE_OCEAN_DOMAIN, token=CODE_OCEAN_API_TOKEN
)


@functools.cache
def get_subject_data_assets(subject: str | int) -> tuple[DataAsset, ...]:
    """
    >>> assets = get_subject_data_assets(668759)
    >>> assert len(assets) > 0
    """
    response = codeocean_client.search_data_assets(
        query=f"subject id: {npc_session.SubjectRecord(subject)}"
    )
    response.raise_for_status()
    return response.json()["results"]


@functools.cache
def get_session_data_assets(
    session: str | npc_session.SessionRecord,
) -> tuple[DataAsset, ...]:
    session = npc_session.SessionRecord(session)
    assets = get_subject_data_assets(session.subject)
    return tuple(
        asset
        for asset in assets
        if re.match(
            f"ecephys_{session.subject}_{session.date}_{npc_session.PARSE_TIME}",
            asset["name"],
        )
    )


def get_session_result_data_assets(
    session: str | npc_session.SessionRecord,
) -> tuple[DataAsset, ...]:
    """
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
    session: str | npc_session.SessionRecord, data_assets: Sequence[DataAsset]
) -> DataAsset | None:
    if not data_assets:
        return None

    if len(data_assets) == 1:
        return data_assets[0]

    session = npc_session.SessionRecord(session)
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
        raise ValueError(
            f"Number of assets is less than expected for the session idx specified:\n{data_assets = }\n{session = }"
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


@functools.cache
def get_session_sorted_data_asset(
    session: str | npc_session.SessionRecord,
) -> DataAsset | None:
    """
    >>> sorted_data_asset = get_session_sorted_data_asset('668759_20230711')
    >>> assert isinstance(sorted_data_asset, dict)
    """
    session_result_data_assets = get_session_data_assets(session)
    sorted_data_assets = tuple(
        data_asset
        for data_asset in session_result_data_assets
        if is_sorted_data_asset(data_asset) and data_asset["files"] > 2
    )
    return get_single_data_asset(session, sorted_data_assets)


@functools.cache
def get_sessions_with_data_assets(
    subject: str | int,
) -> tuple[npc_session.SessionRecord, ...]:
    """
    >>> sessions = get_sessions_with_data_assets(668759)
    >>> assert len(sessions) > 0
    """
    assets = get_subject_data_assets(subject)
    return tuple({npc_session.SessionRecord(asset["name"]) for asset in assets})


def get_data_asset(asset: str | uuid.UUID | DataAsset) -> DataAsset:
    """Converts an asset uuid to dict of info from CodeOcean API."""
    if not isinstance(asset, Mapping):
        response = codeocean_client.get_data_asset(str(asset))
        response.raise_for_status()
        asset = response.json()
    assert isinstance(asset, Mapping), f"Unexpected {type(asset) = }, {asset = }"
    return asset


def is_raw_data_asset(asset: str | DataAsset) -> bool:
    """
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


def is_sorted_data_asset(asset: str | DataAsset) -> bool:
    """
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
) -> DataAsset | None:
    """
    >>> get_session_raw_data_asset('668759_20230711')["id"]
    '83636983-f80d-42d6-a075-09b60c6abd5e'
    """
    session = npc_session.SessionRecord(session)
    raw_assets = tuple(
        asset for asset in get_session_data_assets(session) if is_raw_data_asset(asset)
    )
    return get_single_data_asset(session, raw_assets)


@functools.cache
def get_raw_data_root(session: str | npc_session.SessionRecord) -> upath.UPath | None:
    """Reconstruct path to raw data in bucket (e.g. on s3) using data-asset
    info from Code Ocean.

    >>> get_raw_data_root('668759_20230711')
    S3Path('s3://aind-ephys-data/ecephys_668759_2023-07-11_13-07-32')
    """
    session = npc_session.SessionRecord(session)
    raw_assets = tuple(
        asset for asset in get_session_data_assets(session) if is_raw_data_asset(asset)
    )
    raw_asset = get_single_data_asset(session, raw_assets)
    if not raw_asset:
        return None
    return get_path_from_data_asset(raw_asset)


def get_path_from_data_asset(asset: DataAsset) -> upath.UPath:
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


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
