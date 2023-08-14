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

CODE_OCEAN_DATA_BUCKET = upath.UPath(
    'PATH TO BUCKET'
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
def get_sorted_data_paths_from_s3(session:str | npc_session.SessionRecord):
    """
    Gets the top level files/folders for the sorted data 
    >>> sorted_data_s3_paths = get_sorted_data_paths_from_s3('668759_20230711')
    >>> assert len(sorted_data_s3_paths) > 0
    """
    sorted_data_assets = codeocean.get_session_sorted_data_assets(session)
    # session sorted more than once, only grab assets that have more than build log and output (ones that did not fail)
    sorted_data_s3_paths = tuple((CODE_OCEAN_DATA_BUCKET / data_asset['id']).iterdir() for data_asset 
                       in sorted_data_assets if len(tuple((CODE_OCEAN_DATA_BUCKET / data_asset['id']).iterdir())) > 2)
    
    if not sorted_data_s3_paths:
        raise ValueError(f'{session} has either not been sorted yet or failed')
    
    return sorted_data_s3_paths

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
