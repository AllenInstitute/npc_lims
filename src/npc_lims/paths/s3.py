from __future__ import annotations

import dataclasses
import functools
import operator
from collections.abc import Iterator

import npc_session
import upath

import npc_lims.metadata.codeocean as codeocean

DR_DATA_REPO = upath.UPath(
    "s3://aind-scratch-data/ben.hardcastle/DynamicRoutingTask/Data"
)
NWB_REPO = upath.UPath("s3://aind-scratch-data/ben.hardcastle/nwb/nwb")

CODE_OCEAN_DATA_BUCKET = upath.UPath("s3://codeocean-s3datasetsbucket-1u41qdg42ur9")


@functools.cache
def get_raw_data_paths_from_s3(
    session: str | npc_session.SessionRecord,
) -> tuple[upath.UPath, ...]:
    """All top-level files and folders from the `ephys` & `behavior`
    subdirectories in a session's raw data folder on s3.

    >>> files = get_raw_data_paths_from_s3 ('668759_20230711')
    >>> assert len(files) > 0
    """
    raw_data_root = codeocean.get_raw_data_root(session)
    if not raw_data_root:
        return ()
    directories: Iterator = (
        directory for directory in raw_data_root.iterdir() if directory.is_dir()
    )
    first_level_files_directories: Iterator = (
        tuple(directory.iterdir()) for directory in directories
    )

    return functools.reduce(operator.add, first_level_files_directories)


@functools.cache
def get_sorted_data_paths_from_s3(
    session: str | npc_session.SessionRecord,
) -> tuple[upath.UPath, ...]:
    """
    Gets the top level files/folders for the sorted data
    >>> sorted_data_s3_paths = get_sorted_data_paths_from_s3('668759_20230711')
    >>> assert len(sorted_data_s3_paths) > 0
    """
    sorted_data_asset = codeocean.get_session_sorted_data_asset(session)
    return tuple((CODE_OCEAN_DATA_BUCKET / sorted_data_asset["id"]).iterdir())


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
            f"Subject {session.subject} hdf5s not on s3: may have been run by NSB, in which case they are on lims2"
        )
    file_glob = f"*_{session.subject}_{session.date.replace('-', '')}_??????.hdf5"
    return tuple(StimFile(path, session) for path in root.glob(file_glob))


@functools.cache
def get_nwb_file_from_s3(
    session: str | npc_session.SessionRecord,
) -> upath.UPath | None:
    """
    >>> get_nwb_file_from_s3('636766_20230125')
    S3Path('s3://aind-scratch-data/ben.hardcastle/nwb/nwb/DRpilot_636766_20230125.nwb')
    """
    session = npc_session.SessionRecord(session)
    root = NWB_REPO
    glob = f"*_{session.replace('-', '')}.nwb"
    result = next(root.glob(glob), None)
    if not result:
        print(f"No NWB file found at {root}/{glob}")
    return result


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
