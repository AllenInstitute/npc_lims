from __future__ import annotations

import functools
import logging
import typing
from typing import Any

import npc_session
import upath

import npc_lims
import npc_lims.metadata
import npc_lims.paths

logger = logging.getLogger(__name__)

INVALID_SUBJECT_KEYS = (
    "test",
    "366122",
    "000000",
    "555555",
    "retired",
    "sound",
)


@functools.cache
def get_subjects_from_training_db(
    nsb: bool = False,
) -> dict[npc_session.SubjectRecord, dict[str, Any]]:
    """
    Dynamic Routing training spreadsheet info.

    {subject: ({spreadsheet row}, ... )}

    Examples:
        >>> subjects = get_subjects_from_training_db(nsb=True)
        >>> assert len(subjects) > 0
        >>> subjects[659250]                       # doctest: +SKIP
        {'ID': 50, 'mouse_id': '659250', 'alive': 'False', 'genotype': 'PV Cre x Ai32', 'sex': 'male', 'birthdate': '2022-11-21 00:00:00', 'surgery_week': '2023-01-30 00:00:00', 'craniotomy': 'True', 'trainer': 'Sam', 'regimen': '7', 'wheel_fixed': 'False', 'timeouts': 'True', 'next_task_version': 'dead'}
    """
    db = npc_lims.metadata.get_training_db(nsb)

    # use entries in `all_mice` table
    subjects = tuple(
        {
            npc_session.SubjectRecord(result["mouse_id"])
            for result in db.execute("SELECT * FROM all_mice").fetchall()
        }
    )

    return {
        subject: db.execute(
            "SELECT * FROM 'all_mice' WHERE mouse_id=?", (subject,)
        ).fetchone()
        for subject in subjects
    }


def get_session_id_from_db_row(
    subject: int | str, row: dict[str, Any]
) -> npc_session.SessionRecord:
    """
    Examples:
        >>> get_session_id_from_db_row(366122, {'start_time': '2023-01-30 12:56:27'})
        '366122_2023-01-30'
    """
    return npc_session.SessionRecord(
        f"{subject} {row[next(k for k in row.keys() if 'start' in k and any(t in k for t in ('date', 'time')))]}"
    )


@functools.cache
def get_sessions_from_training_db() -> dict[int, tuple[dict[str, Any], ...]]:
    """
    Includes NSB sessions.

    {subject: ({spreadsheet row}, ... )}

    Examples:
        >>> sessions = get_sessions_from_training_db()
        >>> assert len(sessions) > 0
        >>> sessions[659250][0]                         # doctest: +SKIP
        {'ID': 1, 'start_time': '2023-03-07 12:56:27', 'rig_name': 'B2', 'task_version': 'stage 0 moving', 'hits': '0', 'dprime_same_modality': '', 'dprime_other_modality_go_stim': '', 'pass': '1', 'ignore': '0'}
    """
    sessions: dict[int, tuple[dict[str, Any], ...]] = {}
    for nsb in (False, True):
        db = npc_lims.metadata.get_training_db(nsb)
        ## using tables other than `all_mice`
        subjects = tuple(
            npc_session.SubjectRecord(table["name"])
            for table in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            if str(table["name"]).isnumeric()
        )
        for subject in subjects:
            sessions[subject] = tuple(
                row | {"nsb": nsb}
                for row in db.execute(
                    f"SELECT * FROM '{subject}' WHERE ignore != 1"
                ).fetchall()
                if row["start_time"]  # ie not empty
            )
    return sessions


@typing.overload
def get_subject_folders_from_data_repo(subject: int | str) -> upath.UPath: ...


@typing.overload
def get_subject_folders_from_data_repo() -> (
    dict[npc_session.SubjectRecord, upath.UPath]
): ...


@functools.cache
def get_subject_folders_from_data_repo(
    subject: int | str | None = None,
) -> dict[npc_session.SubjectRecord, upath.UPath] | upath.UPath:
    """
    Examples:
        >>> all_subjects = get_subject_folders_from_data_repo()
        >>> len(all_subjects)                               # doctest: +SKIP
        93

        >>> get_subject_folders_from_data_repo(366122).name
        '366122'
    """
    if subject is not None:
        if not (
            path := npc_lims.paths.DR_DATA_REPO
            / str(npc_session.SubjectRecord(subject))
        ).exists():
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
def get_sessions_from_data_repo() -> (
    dict[npc_session.SubjectRecord, tuple[npc_session.SessionRecord, ...]]
): ...


@typing.overload
def get_sessions_from_data_repo(
    subject: int | str,
) -> tuple[npc_session.SessionRecord, ...]: ...


@functools.cache
def get_sessions_from_data_repo(
    subject: int | str | None = None,
) -> (
    tuple[npc_session.SessionRecord, ...]
    | dict[npc_session.SubjectRecord, tuple[npc_session.SessionRecord, ...]]
):
    """
    Globs synced behavior data repo for sessions.

    Examples:
        get a dict of all subjects mapped to their sessions:
        >>> all_subjects_sessions = get_sessions_from_data_repo()
        >>> len(all_subjects_sessions)                      # doctest: +SKIP
        93

        >>> len(tuple(all_subjects_sessions.values())[0])   # doctest: +SKIP
        45

        get a specific subject's sessions as a sequence:
        >>> get_sessions_from_data_repo(366122)[0]
        '366122_2023-01-30'

    """

    def _get_sessions_from_subfolders(
        folder: upath.UPath,
    ) -> tuple[npc_session.SessionRecord, ...]:
        sessions = set()
        for path in folder.iterdir():
            try:
                session = npc_session.SessionRecord(path.as_posix())
            except ValueError:
                continue
            sessions.add(session)
        return tuple(sorted(sessions))

    if subject is not None:
        return _get_sessions_from_subfolders(
            get_subject_folders_from_data_repo(subject)
        )

    subject_to_sessions: dict[
        npc_session.SubjectRecord, tuple[npc_session.SessionRecord, ...]
    ] = {}
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
