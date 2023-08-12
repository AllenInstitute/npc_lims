from __future__ import annotations

import functools
import operator
import os
import re
from typing import Any, Iterator, Literal

import npc_session
import npc_session.parsing as parsing
import upath
from aind_codeocean_api import codeocean  # type: ignore
from typing_extensions import TypeAlias

CODE_OCEAN_API_TOKEN = os.getenv("CODE_OCEAN_API_TOKEN")
CODE_OCEAN_DOMAIN = os.getenv("CODE_OCEAN_DOMAIN")

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


@functools.cache
def get_subject_data_assets(subject: str | int) -> tuple[DataAsset, ...]:
    """
    >>> assets = get_subject_data_assets(668759)
    >>> assert len(assets) > 0
    """
    codeocean_client = codeocean.CodeOceanClient(
        domain=CODE_OCEAN_DOMAIN, token=CODE_OCEAN_API_TOKEN
    )
    response = codeocean_client.search_data_assets(
        query=f"subject id: {npc_session.SubjectRecord(subject)}"
    )
    response.raise_for_status()
    return response.json()["results"]


def get_sessions_with_data_assets(
    subject: str | int,
) -> tuple[npc_session.SessionRecord, ...]:
    """
    >>> sessions = get_sessions_with_data_assets(668759)
    >>> assert len(sessions) > 0
    """
    assets = get_subject_data_assets(subject)
    return tuple({npc_session.SessionRecord(asset["name"]) for asset in assets})


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
            f"ecephys_{session.subject}_{session.date}_{parsing._TIME}", asset["name"]
        )
    )


@functools.cache
def get_raw_data_root(session: str | npc_session.SessionRecord) -> upath.UPath:
    """
    >>> get_raw_data_root('668759_20230711')
    S3Path('s3://aind-ephys-data/ecephys_668759_2023-07-11_13-07-32')
    """
    session = npc_session.SessionRecord(session)
    raw_assets = tuple(
        asset
        for asset in get_session_data_assets(session)
        if asset["custom_metadata"].get("data level") == "raw data"
    )
    if len(raw_assets) < session.idx:
        raise ValueError(
            f"Number of paths raw sessions on s3 {len(raw_assets)} is less than  {session.idx = }"
        )

    raw_asset = raw_assets[session.idx]
    bucket_info = raw_asset["sourceBucket"]
    roots = {"aws": "s3", "gcs": "gs"}
    if bucket_info["origin"] not in roots:
        raise RuntimeError(
            f"Unknown bucket origin - not sure how to create UPath: {bucket_info = }"
        )
    return upath.UPath(
        f"{roots[bucket_info['origin']]}://{bucket_info['bucket']}/{bucket_info['prefix']}"
    )


@functools.cache
def get_raw_data_top_level_paths(
    session: str | npc_session.SessionRecord,
) -> tuple[upath.UPath, ...]:
    """
    >>> files = get_raw_data_top_level_paths('668759_20230711')
    >>> assert len(files) > 0
    """
    raw_data_root = get_raw_data_root(session)
    directories: Iterator = (
        directory for directory in raw_data_root.iterdir() if directory.is_dir()
    )
    first_level_files_directories: Iterator = (
        tuple(directory.iterdir()) for directory in directories
    )

    return functools.reduce(operator.add, first_level_files_directories)


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
