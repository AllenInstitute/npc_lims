import dataclasses
import json
import pathlib
from collections.abc import MutableSequence
from typing import Literal

import npc_session
import upath
import yaml
from typing_extensions import TypeAlias

import npc_lims.metadata.codeocean as codeocean

_LOCAL_FILE = pathlib.Path(__file__).parent.parent / "tracked_sessions.yaml"

FileContents: TypeAlias = dict[
    Literal["ephys", "behavior_with_sync", "behavior"], dict[str, str]
]


@dataclasses.dataclass(frozen=True, eq=True)
class SessionInfo:
    """Minimal session metadata obtained quickly from a database.

    Currently using:
    https://github.com/AllenInstitute/npc_lims/blob/main/src/npc_lims/tracked_sessions.yaml
    """

    id: npc_session.SessionRecord
    subject: npc_session.SubjectRecord
    date: npc_session.DateRecord
    """YY-MM-DD"""
    idx: int
    project: npc_session.ProjectRecord
    is_ephys: bool
    is_sync: bool
    """The session has sync data, implying more than a behavior-box."""
    allen_path: upath.UPath

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
    """
    f = _session_info_from_file_contents
    if _LOCAL_FILE.suffix == ".json":
        return f(json.loads(_LOCAL_FILE.read_text()))
    if _LOCAL_FILE.suffix == ".yaml":
        return f(yaml.load(_LOCAL_FILE.read_bytes(), yaml.FullLoader))
    raise ValueError(f"Add loader for {_LOCAL_FILE.suffix}")  # pragma: no cover


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
