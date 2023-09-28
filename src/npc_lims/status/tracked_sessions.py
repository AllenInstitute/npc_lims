import dataclasses
import json
from collections.abc import MutableSequence
from typing import Literal

import npc_session
import upath
import yaml
from typing_extensions import TypeAlias

import npc_lims.metadata.codeocean as codeocean

_TRACKED_SESSIONS_FILE = upath.UPath('https://raw.githubusercontent.com/AllenInstitute/npc_lims/main/tracked_sessions.yaml')

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

        >>> any(session.is_uploaded for session in get_session_info())
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

        >>> any(session.is_sorted for session in get_session_info())
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


def get_session_info() -> tuple[SessionInfo, ...]:
    """Quickly get a sequence of all tracked sessions.

    Each object in the sequence has info about one session:
    >>> sessions = get_session_info()
    >>> sessions[0].__class__.__name__
    'SessionInfo'
    >>> sessions[0].is_ephys
    True
    >>> any(s for s in sessions if s.date.year < 2021)
    False
    """
    return _get_session_info_from_local_file()


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
    raise ValueError(f"Add loader for {_TRACKED_SESSIONS_FILE.suffix}")  # pragma: no cover


def _session_info_from_file_contents(contents: FileContents) -> tuple[SessionInfo, ...]:
    sessions: MutableSequence[SessionInfo] = []
    for session_type, projects in contents.items():
        if not projects:
            continue
        sync = any(tag in session_type for tag in ("sync", "ephys"))
        ephys = "ephys" in session_type
        for project_name, session_ids in projects.items():
            if not session_ids:
                continue
            for session_id in session_ids:
                s = npc_session.SessionRecord(session_id)
                sessions.append(
                    SessionInfo(
                        *(s, s.subject, s.date, s.idx),
                        project=npc_session.ProjectRecord(project_name),
                        is_ephys=ephys,
                        is_sync=sync,
                        allen_path=upath.UPath(session_id),
                    )
                )
    return tuple(sessions)


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
