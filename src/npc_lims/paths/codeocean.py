from __future__ import annotations

import dataclasses
import functools
import operator
import os
import re
from collections.abc import Iterator

import npc_session
import upath
from aind_codeocean_api import codeocean

import npc_lims.metadata.codeocean as metadata

CODE_OCEAN_API_TOKEN = os.getenv("CODE_OCEAN_API_TOKEN")
CODE_OCEAN_DOMAIN = os.getenv("CODE_OCEAN_DOMAIN")

DR_DATA_REPO = upath.UPath(
    "s3://aind-scratch-data/ben.hardcastle/DynamicRoutingTask/Data"
)


@functools.cache
def get_codeocean_client() -> codeocean.CodeOceanClient:
    return codeocean.CodeOceanClient(
        domain=os.environ["CODE_OCEAN_DOMAIN"], token=os.environ["CODE_OCEAN_API_TOKEN"]
    )


@functools.cache
def get_subject_data_assets(subject: str | int) -> tuple[metadata.DataAssetAPI, ...]:
    """
    >>> assets = get_subject_data_assets(668759)
    >>> assert len(assets) > 0
    """
    response = get_codeocean_client().search_data_assets(
        query=f"subject id: {npc_session.SubjectRecord(subject)}"
    )
    response.raise_for_status()
    return response.json()["results"]


@functools.cache
def get_session_data_assets(
    session: str | npc_session.SessionRecord,
) -> tuple[metadata.DataAssetAPI, ...]:
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
def get_raw_data_root(session: str | npc_session.SessionRecord) -> upath.UPath:
    """Reconstruct path to raw data in bucket (e.g. on s3) using data-asset
    info from Code Ocean.

    >>> metadata.get_raw_data_root('668759_20230711')
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
def get_raw_data_paths_from_s3(
    session: str | npc_session.SessionRecord,
) -> tuple[upath.UPath, ...]:
    """All top-level files and folders from the `ephys` & `behavior`
    subdirectories in a session's raw data folder on s3.

    >>> files = get_raw_data_paths_from_s3 ('668759_20230711')
    >>> assert len(files) > 0
    """
    raw_data_root = metadata.get_raw_data_root(session)
    directories: Iterator = (
        directory for directory in raw_data_root.iterdir() if directory.is_dir()
    )
    first_level_files_directories: Iterator = (
        tuple(directory.iterdir()) for directory in directories
    )

    return functools.reduce(operator.add, first_level_files_directories)


@dataclasses.dataclass
class StimFile:
    path: upath.UPath
    session: npc_session.SessionRecord
    name = property(lambda self: self.path.stem.split("_")[0])
    date = property(lambda self: self.session.date)
    time = property(lambda self: npc_session.extract_isoformat_time(self.path.stem))


@functools.cache
def get_hdf5_stim_files_from_s3(
    session: str | npc_session.SessionRecord,
) -> tuple[StimFile, ...]:
    """All the stim files for a session, from the synced
    `DynamicRoutingTask/Data` folder on s3.

    >>> files = get_hdf5_stim_files_from_s3('668759_20230711')
    >>> assert len(files) > 0
    >>> files[0].name, files[0].time
    ('DynamicRouting1', '13:25:00')
    """
    session = npc_session.SessionRecord(session)
    root = DR_DATA_REPO / str(session.subject)
    if not root.exists():
        if not DR_DATA_REPO.exists():
            raise FileNotFoundError(f"{DR_DATA_REPO = } does not exist")
        raise FileNotFoundError(
            f"Subject {session.subject} may have been run by NSB: hdf5 files are in lims2"
        )
    file_glob = f"*_{session.subject}_{session.date.replace('-', '')}_??????.hdf5"
    return tuple(StimFile(path, session) for path in root.glob(file_glob))


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
