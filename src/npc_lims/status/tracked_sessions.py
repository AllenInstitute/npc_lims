from __future__ import annotations

import contextlib
import dataclasses
import functools
import json
import typing
from collections.abc import Iterator, Mapping, MutableSequence
from typing import Any, Literal, TypedDict

import npc_session
import upath
import yaml
from typing_extensions import NotRequired, TypeAlias, Unpack

import npc_lims.exceptions as exceptions
import npc_lims.metadata.codeocean as codeocean
import npc_lims.paths.s3 as s3
import npc_lims.status.behavior_sessions as behavior_sessions

_TRACKED_SESSIONS_FILE = upath.UPath(
    "https://raw.githubusercontent.com/AllenInstitute/npc_lims/main/tracked_sessions.yaml"
)

FileContents: TypeAlias = dict[
    Literal["ephys", "behavior_with_sync", "behavior"], dict[str, str]
]

DR_DATA_REPO_ISILON = upath.UPath(
    "//allen/programs/mindscope/workgroups/dynamicrouting/DynamicRoutingTask/Data"
)


@dataclasses.dataclass(frozen=True)
class SessionInfo:
    """Minimal session metadata obtained quickly from a database.

    Currently using:
    https://raw.githubusercontent.com/AllenInstitute/npc_lims/main/tracked_sessions.yaml
    and training spreadsheets.
    """

    id: npc_session.SessionRecord
    project: npc_session.ProjectRecord
    is_ephys: bool
    is_sync: bool
    """The session has sync data, implying more than a behavior-box."""
    allen_path: upath.UPath
    experiment_day: int | None = None
    """Experiment day (ephys recording, or opto experiment), starting from 1 for
    each subject. `None` for training behavior-only sessions."""
    session_kwargs: dict[str, Any] = dataclasses.field(default_factory=dict)
    notes: str = dataclasses.field(default="")
    issues: list[str] = dataclasses.field(default_factory=list)

    @property
    def idx(self) -> int:
        """Session index, starting from 0 for each subject on each day.
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

    @functools.cached_property
    def cloud_path(self) -> upath.UPath | None:
        with contextlib.suppress(FileNotFoundError, ValueError):
            return codeocean.get_raw_data_root(self.id)
        if DR_DATA_REPO_ISILON in self.allen_path.parents:
            return s3.DR_DATA_REPO / self.allen_path.relative_to(DR_DATA_REPO_ISILON)
        return None

    @functools.cached_property
    def behavior_day(self) -> int | None:
        if self.is_templeton:
            return None  # not accessible for Templeton sessions
        return self.training_info.get("ID")  # row of training spreadsheet

    @functools.cached_property
    def is_uploaded(self) -> bool:
        """All of the session's raw data has been uploaded to S3 and can be found in
        CodeOcean. Not the same as `cloud_path` being non-None: this property
        indicates a proper session upload via aind tools, with metadata etc.

        Examples:
            >>> next(session.is_uploaded for session in get_session_info() if session.is_uploaded)
            True
        """
        with contextlib.suppress(FileNotFoundError, ValueError):
            return bool(codeocean.get_raw_data_root(self.id))
        return False

    @functools.cached_property
    def raw_data_paths(self) -> tuple[upath.UPath, ...] | None:
        with contextlib.suppress(FileNotFoundError, ValueError):
            return s3.get_raw_data_paths_from_s3(self.id)
        return None

    @functools.cached_property
    def is_session_json(self) -> bool:
        if self.raw_data_paths is None:
            return False
        return any(p for p in self.raw_data_paths if p.name == "session.json")

    @functools.cached_property
    def is_rig_json(self) -> bool:
        if self.raw_data_paths is None:
            return False
        return any(p for p in self.raw_data_paths if p.name == "rig.json")

    @functools.cached_property
    def is_video(self) -> bool:
        """
        >>> get_session_info('2022-09-20_13-21-35_628801').is_video
        False
        >>> get_session_info('676909_20231212').is_video
        True
        """
        if not self.is_sync:
            return False

        if (v := self.session_kwargs.get("is_video")) is not None:
            return v

        # if ephys, we assume there is video
        return self.is_ephys

    @functools.cached_property
    def is_surface_channels(self) -> bool:
        """The session has ephys data collected separately to record surface
        channel.

        Examples:

            >>> get_session_info("DRpilot_660023_20230808").is_surface_channels
            True
        """
        if not self.is_ephys:
            return False
        if self.session_kwargs.get("probe_letters_with_surface_channel_recording"):
            return True
        try:
            _ = codeocean.get_surface_channel_root(self.id)
        except (FileNotFoundError, ValueError):
            return False
        return True

    def is_dlc(self, camera: Literal["eye", "side", "face"]) -> bool:
        if not self.is_video:
            return False
        try:
            return bool(
                codeocean.get_session_capsule_pipeline_data_asset(
                    self.id, f"dlc_{camera}"
                )
            )
        except (FileNotFoundError, ValueError):
            return False

    @functools.cached_property
    def is_dlc_eye(self) -> bool:
        """
        The dlc eye capsule has yielded a result for this session.
        >>> get_session_info("676909_2023-12-13").is_dlc_eye
        True
        """
        return self.is_dlc("eye")

    @functools.cached_property
    def is_dlc_side(self) -> bool:
        """
        The dlc side capsule has yielded a result for this session
        >>> get_session_info("676909_2023-12-13").is_dlc_side
        True
        """
        return self.is_dlc("side")

    @functools.cached_property
    def is_dlc_face(self) -> bool:
        """
        The dlc face capsule has yielded a result for this session
        >>> get_session_info("676909_2023-12-13").is_dlc_face
        True
        """
        return self.is_dlc("face")

    @functools.cached_property
    def is_facemap(self) -> bool:
        """
        The facemap capsule has yield a result for this session
        >>> get_session_info("676909_2023-12-13").is_facemap
        True
        >>> get_session_info('668759_2023-07-11').is_facemap
        True
        >>> get_session_info('706401_2024-04-22').is_facemap
        True
        """
        if not self.is_video:
            return False
        try:
            asset = codeocean.get_session_capsule_pipeline_data_asset(
                self.id, "facemap"
            )
        except (FileNotFoundError, ValueError):
            return False
        if "83636983-f80d-42d6-a075-09b60c6abd5e" in asset["provenance"]["data_assets"] and self.id != npc_session.SessionRecord("668759_2023-07-11"):  # type: ignore
            # the capsule had this asset permanently attached for assets made on April 24th/25th. should be resolved
            # the resulting data are only saved for the wrong asset
            return False
        return bool(asset)

    @functools.cached_property
    def is_sorted(self) -> bool:
        """The AIND sorting pipeline has yielded a Result asset for this
        session.

        Examples:

            >>> next(session.is_sorted for session in get_session_info() if session.is_sorted)
            True
        """
        if not self.is_ephys:
            return False
        try:
            return any(
                asset
                for asset in codeocean.get_session_data_assets(self.id)
                if "sorted" in asset["name"]
                and asset["files"]
                > 6  # number of files produced by sorting pipeline when errorred
            )
        except (FileNotFoundError, ValueError):
            return False

    @functools.cached_property
    def is_annotated(self) -> bool:
        """The subject associated with the sessions has CCF annotation data for
        probes available on S3.

        Examples:

            >>> next(session.is_annotated for session in get_session_info() if session.is_annotated)
            True
        """
        if not self.is_sorted:
            return False
        try:
            return bool(s3.get_tissuecyte_annotation_files_from_s3(self.id))
        except (FileNotFoundError, ValueError):
            return False

    @functools.cached_property
    def training_info(self) -> dict[str, Any]:
        """Session metadata from Sam's DR training database.
        - empty dict for Templeton sessions

        Examples:

            >>> next(get_session_info()).session_info                       # doctest: +SKIP
            {'ID': 1, 'start_time': '2023-03-07 12:56:27', 'rig_name': 'B2', 'task_version': 'stage 0 moving', 'hits': '0', 'dprime_same_modality': '', 'dprime_other_modality_go_stim': '', 'pass': '1', 'ignore': '0'}
            >>> assert next(session.training_info for session in get_session_info() if session.training_info)
        """
        return next(
            (
                s
                for s in behavior_sessions.get_sessions_from_training_db().get(
                    self.subject, {}
                )
                if (start := s.get("start_time"))
                and npc_session.DateRecord(start) == self.date
            ),
            {},
        )

    @functools.cached_property
    def is_templeton(self) -> bool:
        """Uses project in `tracked_sessions.yaml` if available, then infers from whether the session is in Sam's DR training
        database.

        Examples:
            >>> get_session_info("2023-05-15_09-50-06_662983").is_templeton
            True
            >>> get_session_info("DRpilot_644867_20230221").is_templeton
            False
        """
        if "templeton" in self.project.lower():
            return True
        # training_info not available for Templeton sessions:
        return self.subject not in (
            behavior_sessions.get_subjects_from_training_db()
            | behavior_sessions.get_subjects_from_training_db(nsb=True)
        )

    @property
    def rig(self) -> str:
        """From DR training spreadsheet (`NP2`, `B2`, 'BEH.E`).

        - does not necessarily match `AIBS_RIG_ID` on computer
        - `unknown` if not available (for Templeton sessions)
        """
        return self.training_info.get("rig_name", "unknown")

    @property
    def task_version(self) -> str:
        """From DR training spreadsheet (`stage 5 ori AMN moving timeouts
        repeats`).
        - `unknown` if not available (for Templeton sessions)
        """
        return self.training_info.get("task_version", "unknown")

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SessionInfo):
            return NotImplemented
        return self.id == other.id


class SessionFilterKwargs(TypedDict, total=False):
    is_ephys: NotRequired[bool]
    is_uploaded: NotRequired[bool]
    is_sync: NotRequired[bool]
    is_sorted: NotRequired[bool]
    is_annotated: NotRequired[bool]


@typing.overload
def get_session_info(
    **session_filter_kwargs: Unpack[SessionFilterKwargs],
) -> tuple[SessionInfo, ...]: ...


@typing.overload
def get_session_info(
    session: str | npc_session.SessionRecord,
    **session_filter_kwargs: Unpack[SessionFilterKwargs],
) -> SessionInfo: ...


def get_session_info(
    session: str | npc_session.SessionRecord | SessionInfo | None = None,
    **session_filter_kwargs: Unpack[SessionFilterKwargs],
) -> tuple[SessionInfo, ...] | SessionInfo:
    """Quickly get a sequence of all tracked sessions.

    Examples:

        Each object in the sequence has info about one session:
        >>> sessions = get_session_info()
        >>> sessions[0].__class__.__name__
        'SessionInfo'
        >>> sessions[0].is_ephys                    # doctest: +SKIP
        True
        >>> any(s for s in sessions if s.date.year < 2021)
        False

        Pass a session str or SessionRecord to get the info for that session:
        >>> info = get_session_info("DRpilot_667252_20230927")
        >>> assert isinstance(info, SessionInfo)
        >>> info.is_templeton
        False
    """
    if isinstance(session, SessionInfo):
        session = session.id
    tracked_sessions = set(
        _get_session_info_from_file(),
    )
    tracked_sessions.update(_get_session_info_from_data_repo())
    if session is None:
        filtered_sessions = (
            s
            for s in tracked_sessions
            if all(getattr(s, k) == v for k, v in session_filter_kwargs.items())
        )
        return tuple(sorted(filtered_sessions, key=lambda s: s.id.date, reverse=True))
    with contextlib.suppress(StopIteration):
        return next(
            s
            for s in tracked_sessions
            if s.id == (record := npc_session.SessionRecord(session))
        )
    raise exceptions.NoSessionInfo(f"{record} not found in tracked sessions")


@typing.overload
def get_session_issues() -> dict[npc_session.SessionRecord, list[str]]: ...


@typing.overload
def get_session_issues(session: str | npc_session.SessionRecord) -> list[str]: ...


def get_session_issues(
    session: str | npc_session.SessionRecord | None = None,
) -> list[str] | list | dict[npc_session.SessionRecord, list[str]]:
    """Get a dictionary of all sessions with issues mapped to their issue url.

    Examples:

        >>> issues = get_session_issues()
        >>> issues                                                              # doctest: +SKIP
        {
            '644867_2023-02-21': ['https://github.com/AllenInstitute/npc_sessions/issues/28'],
            '660023_2023-08-08': ['https://github.com/AllenInstitute/npc_sessions/issues/26'],
        }

        >>> single_session_issues = get_session_issues("DRPilot_644867_20230221")
        >>> assert isinstance(single_session_issues, typing.Sequence)
        >>> single_session_issues                                               # doctest: +SKIP
        ['https://github.com/AllenInstitute/npc_sessions/issues/28']
    """
    if session:
        try:
            return get_session_info(session).issues
        except exceptions.NoSessionInfo:
            return []
    return {
        session.id: session.issues for session in get_session_info() if session.issues
    }


@typing.overload
def get_session_kwargs() -> dict[npc_session.SessionRecord, dict]: ...


@typing.overload
def get_session_kwargs(session: str | npc_session.SessionRecord) -> dict[str, Any]: ...


def get_session_kwargs(
    session: str | npc_session.SessionRecord | None = None,
) -> dict[str, str] | dict | dict[npc_session.SessionRecord, dict[str, str]]:
    """Get a dictionary of all sessions mapped to their config kwargs. kwargs will
    be an empty dict if no kwargs have been specified.

    Examples:

        >>> kwargs = get_session_kwargs()
        >>> kwargs                                                          # doctest: +SKIP
        {   '670248_2023-08-02': {
                'is_task': False,
            },
            '667252_2023-09-25': {
                'invalid_times': [
                    {'start_time': 4996, 'stop_time': -1, 'reason': 'auditory stimulus not presented (amplifier power issue)'}
                ]
            },
        }
        >>> single_session_kwargs = get_session_kwargs("DRpilot_670248_20230802")
        >>> assert isinstance(single_session_kwargs, dict)
        >>> single_session_kwargs                                           # doctest: +SKIP
        {'is_task': False}
    """
    if session:
        try:
            return get_session_info(session).session_kwargs
        except exceptions.NoSessionInfo:
            return {}
    return {session.id: session.session_kwargs for session in get_session_info()}


def _get_session_info_from_data_repo() -> Iterator[SessionInfo]:
    """
    Examples:

    >>> session_info = next(_get_session_info_from_data_repo())
    """
    for subject, sessions in behavior_sessions.get_sessions_from_training_db().items():
        for session in sessions:
            yield SessionInfo(
                id=behavior_sessions.get_session_id_from_db_row(subject, session),
                project=npc_session.ProjectRecord("DynamicRouting"),
                is_ephys=False,  #! not enough info
                is_sync=False,  #! not enough info
                allen_path=DR_DATA_REPO_ISILON / str(subject),
            )


def _get_session_info_from_file() -> tuple[SessionInfo, ...]:
    """Load yaml and parse sessions.
    - currently assumes all sessions include behavior data

    Examples:

        >>> assert len(_get_session_info_from_file()) > 0
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
                    assert isinstance(info, str)
                    allen_path = info
                    session_config = {}
                record = npc_session.SessionRecord(allen_path)
                if (idx := session_config.get("idx", None)) is not None:
                    record = record.with_idx(idx)
                sessions.append(
                    SessionInfo(
                        id=record,
                        experiment_day=int(
                            session_config.get("day", _get_day_from_sessions(record))
                        ),
                        project=npc_session.ProjectRecord(project_name),
                        is_ephys=is_ephys,
                        is_sync=is_sync,
                        allen_path=upath.UPath(allen_path),
                        session_kwargs=session_config.get("session_kwargs", {}),
                        notes=session_config.get("notes", ""),
                        issues=session_config.get("issues", []),
                    )
                )
    return tuple(sessions)


if __name__ == "__main__":
    import doctest

    import dotenv

    dotenv.load_dotenv(dotenv.find_dotenv(usecwd=True))
    doctest.testmod(
        optionflags=(
            doctest.IGNORE_EXCEPTION_DETAIL
            | doctest.NORMALIZE_WHITESPACE
            | doctest.FAIL_FAST
        )
    )
