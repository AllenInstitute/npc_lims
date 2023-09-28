from __future__ import annotations

import contextlib
import dataclasses
import json
from collections.abc import Mapping, MutableSequence
from typing import Literal

import npc_session
import upath
import yaml
from typing_extensions import TypeAlias

import npc_lims.metadata.codeocean as codeocean

_TRACKED_SESSIONS_FILE = upath.UPath(
    "https://raw.githubusercontent.com/AllenInstitute/npc_lims/main/tracked_sessions.yaml"
)

FileContents: TypeAlias = dict[
    Literal["ephys", "behavior_with_sync", "behavior"], dict[str, str]
]


@dataclasses.dataclass(frozen=True, eq=True)
class SessionInfo:
    """Minimal session metadata obtained quickly from a database.

    Currently using:
    https://raw.githubusercontent.com/AllenInstitute/npc_lims/main/tracked_sessions.yaml
    """

    id: npc_session.SessionRecord
    day: int
    """Recording day, starting from 1 for each subject."""
    project: npc_session.ProjectRecord
    is_ephys: bool
    is_sync: bool
    """The session has sync data, implying more than a behavior-box."""
    allen_path: upath.UPath
    session_kwargs: dict[str, str] = dataclasses.field(default_factory=dict)
    notes: str = dataclasses.field(default="")

    @property
    def idx(self) -> int:
        """Recording index, starting from 0 for each subject on each day/
        Currently one session per day, so index isn't specified - implicitly equal to 0.
        """
        return self.id.idx

    @property
    def subject(self) -> npc_session.SubjectRecord:
        return self.id.subject

    @property
    def date(self) -> npc_session.DateRecord:
        """YY-MM-DD"""
        return self.id.date

    @property
    def is_uploaded(self) -> bool:
        """The session's raw data has been uploaded to S3 and can be found in
        CodeOcean.

        >>> any(session.is_uploaded for session in get_tracked_sessions())
        True
        """
        try:
            return bool(codeocean.get_raw_data_root(self.id))
        except (FileNotFoundError, ValueError):
            return False

    @property
    def is_sorted(self) -> bool:
        """The AIND sorting pipeline has yielded a Result asset for this
        session.

        >>> any(session.is_sorted for session in get_tracked_sessions())
        True
        """
        try:
            return any(
                asset
                for asset in codeocean.get_session_data_assets(self.id)
                if "sorted" in asset["name"]
            )
        except (FileNotFoundError, ValueError):
            return False


def get_tracked_sessions() -> tuple[SessionInfo, ...]:
    """Quickly get a sequence of all tracked sessions.

    Each object in the sequence has info about one session:
    >>> sessions = get_tracked_sessions()
    >>> sessions[0].__class__.__name__
    'SessionInfo'
    >>> sessions[0].is_ephys
    True
    >>> any(s for s in sessions if s.date.year < 2021)
    False
    """
    return _get_session_info_from_local_file()


def get_session_info(session: str | npc_session.SessionRecord) -> SessionInfo:
    """Get the SessionInfo instance for a specific session, if it's in the list of
    tracked sessions.

    >>> assert isinstance(get_session_info("DRpilot_667252_20230927"), SessionInfo)
    """
    with contextlib.suppress(StopIteration):
        return next(
            s
            for s in get_tracked_sessions()
            if s.id == (record := npc_session.SessionRecord(session))
        )
    raise ValueError(f"{record} not found in tracked sessions")


def _get_session_info_from_local_file() -> tuple[SessionInfo, ...]:
    """Load yaml and parse sessions.
    - currently assumes all sessions include behavior data

    >>> assert len(_get_session_info_from_local_file()) > 0
    """
    f = _session_info_from_file_contents
    if _TRACKED_SESSIONS_FILE.suffix == ".json":
        return f(json.loads(_TRACKED_SESSIONS_FILE.read_text()))
    if _TRACKED_SESSIONS_FILE.suffix == ".yaml":
        return f(yaml.load(_TRACKED_SESSIONS_FILE.read_bytes(), Loader=yaml.FullLoader))
    raise ValueError(
        f"Add loader for {_TRACKED_SESSIONS_FILE.suffix}"
    )  # pragma: no cover


def _session_info_from_file_contents(contents: FileContents) -> tuple[SessionInfo, ...]:
    sessions: MutableSequence[SessionInfo] = []
    for session_type, projects in contents.items():
        if not projects:
            continue
        is_sync = any(tag in session_type for tag in ("sync", "ephys"))
        is_ephys = "ephys" in session_type
        for project_name, session_info in projects.items():
            if not session_info:
                continue
            all_session_records = tuple(
                npc_session.SessionRecord(
                    tuple(session_id.keys())[0]
                    if isinstance(session_id, Mapping)
                    else str(session_id)
                )
                for session_id in session_info
            )

            def _get_day_from_sessions(record: npc_session.SessionRecord) -> int:
                subject_days = sorted(
                    str(s.date)
                    for s in all_session_records
                    if s.subject == record.subject
                )
                return subject_days.index(str(record.date)) + 1

            for info in session_info:
                if isinstance(info, Mapping):
                    assert len(info) == 1
                    allen_path: str = tuple(info.keys())[0]
                    session_config = tuple(info.values())[0]
                else:
                    allen_path = info
                    session_config = {}
                record = npc_session.SessionRecord(allen_path)
                if (idx := session_config.get("idx", None)) is not None:
                    record = record.with_idx(idx)
                sessions.append(
                    SessionInfo(
                        id=record,
                        day=session_config.get("day", _get_day_from_sessions(record)),
                        project=npc_session.ProjectRecord(project_name),
                        is_ephys=is_ephys,
                        is_sync=is_sync,
                        allen_path=upath.UPath(allen_path),
                        session_kwargs=session_config.get("session_kwargs", {}),
                        notes=session_config.get("notes", ""),
                    )
                )
    return tuple(sessions)


if __name__ == "__main__":
    import doctest

    import dotenv

    dotenv.load_dotenv(dotenv.find_dotenv(usecwd=True))
    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
