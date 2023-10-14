from __future__ import annotations

import functools
import typing
import npc_session

import upath
import npc_lims

import npc_lims.paths

INVALID_SUBJECT_KEYS = (
    'test',
    '366122',
    '000000',
    '555555',
    'retired',
    'sound',
)

@typing.overload
def get_subject_folders_from_data_repo(subject: int | str) -> upath.UPath: ...

@typing.overload
def get_subject_folders_from_data_repo() -> dict[npc_session.SubjectRecord, upath.UPath]: ...

@functools.cache
def get_subject_folders_from_data_repo(subject: int | str | None = None) -> dict[npc_session.SubjectRecord, upath.UPath] | upath.UPath:
    """
    >>> all_subjects = get_subject_folder()
    >>> len(all_subjects)                               # doctest: +SKIP
    93
    
    >>> get_subject_folder(366122).name
    '366122'
    """
    if subject is not None:
        if not (path := npc_lims.paths.DR_DATA_REPO / str(npc_session.SubjectRecord(subject))).exists():
            raise FileNotFoundError(f"{path=} does not exist")
        return path
    subject_to_folder: dict[npc_session.SubjectRecord, upath.UPath] = {}
    for path in npc_lims.paths.DR_DATA_REPO.iterdir():
        if path.is_file():
            continue
        if any(invalid_key in path.name for invalid_key in INVALID_SUBJECT_KEYS):
            continue
        try:
            _subject = npc_session.SubjectRecord(path.name)
        except ValueError:
            continue
        if _subject in subject_to_folder:
            raise ValueError(f"Duplicate path for {_subject=}: {path}")
        subject_to_folder[_subject] = path
    return subject_to_folder

@typing.overload
def get_sessions_from_data_repo() -> dict[npc_session.SubjectRecord, tuple[npc_session.SessionRecord, ...]]: ...

@typing.overload
def get_sessions_from_data_repo(subject: int | str) -> tuple[npc_session.SessionRecord, ...]: ...

@functools.cache
def get_sessions_from_data_repo(subject: int | str | None = None) -> tuple[npc_session.SessionRecord, ...] | dict[npc_session.SubjectRecord, tuple[npc_session.SessionRecord, ...]]:
    """
    
    # get a dict of all subjects mapped to their sessions
    >>> all_subjects_sessions = get_sessions()
    >>> len(all_subjects_sessions)                      # doctest: +SKIP
    93
    
    >>> len(tuple(all_subjects_sessions.values())[0])   # doctest: +SKIP
    45
    
    # get a specific subject's sessions as a sequence
    >>> get_sessions(366122)[0]
    '366122_2023-01-30'
    
    """
    def _get_sessions_from_subfolders(folder: upath.UPath) -> tuple[npc_session.SessionRecord, ...]:
        sessions = set()
        for path in folder.iterdir():
            try:
                session = npc_session.SessionRecord(path.as_posix())
            except ValueError:
                continue
            sessions.add(session)
        return tuple(sorted(sessions))
    
    if subject is not None:
        return _get_sessions_from_subfolders(get_subject_folders_from_data_repo(subject))
    
    subject_to_sessions: dict[npc_session.SubjectRecord, tuple[npc_session.SessionRecord, ...]] = {}
    for _subject, folder in get_subject_folders_from_data_repo().items():
        subject_to_sessions.setdefault(_subject, _get_sessions_from_subfolders(folder))
    return subject_to_sessions

if __name__ == "__main__":
    import doctest

    import dotenv

    dotenv.load_dotenv(dotenv.find_dotenv(usecwd=True))
    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
