from __future__ import annotations

import dataclasses
from typing import ClassVar, Literal

import npc_session
from typing_extensions import Self

@dataclasses.dataclass
class Record:
    
    def to_db(self) -> dict[str, str | int | float | None]:
        row = self.__dict__.copy()
        row.pop("table", None)  # not actually needed for dataclass ClassVar
        for k in row:
            if not isinstance(row[k], (str, int, float, type(None))):
                row[k] = str(row[k])
        return row

    @classmethod
    def from_db(cls, row: dict[str, str | int | float | None]) -> Self:
        for k, v in row.items():
            if not isinstance(v, str):
                continue
            if all(ends in '()[]{{}}' for ends in (v[0], v[-1])):
                row[k] = eval(v)
        return cls(**row)  # type: ignore
    
@dataclasses.dataclass
class Subject(Record):
    """
    >>> from npc_lims import tracked, NWBSqliteDBHub as DB
    >>> all_subjects = DB().get_records(Subject)
    """

    table: ClassVar[str] = "subjects"

    subject_id: int | npc_session.SubjectRecord
    sex: Literal["M", "F", "U"] | None = None
    date_of_birth: str | npc_session.DateRecord | None = None
    genotype: str | None = None
    """e.g., Sst-IRES-Cre/wt;Ai148(TIT2L-GC6f-ICL-tTA2)/wt"""
    description: str | None = None
    strain: str | None = None
    """e.g., C57BL/6J"""
    notes: str | None = None


@dataclasses.dataclass
class Session(Record):
    """
    >>> from npc_lims import tracked, NWBSqliteDBHub as DB
    >>> all_sessions = DB().get_records(Session)
    """

    table: ClassVar[str] = "sessions"

    session_id: str | npc_session.SessionRecord
    subject_id: int | npc_session.SubjectRecord
    session_start_time: str | npc_session.TimeRecord | None = None
    stimulus_notes: str | None = None
    experimenter: str | None = None
    experiment_description: str | None = None
    epoch_tags: list[str] = dataclasses.field(default_factory=list)
    source_script: str | None = None
    identifier: str | None = None
    notes: str | None = None


@dataclasses.dataclass
class Epoch(Record):
    """
    >>> from npc_lims import NWBSqliteDBHub as DB

    >>> epoch = Epoch('626791_2022-08-15', '11:23:36', '12:23:54', ['DynamicRouting1'])
    >>> DB().add_records(epoch)

    >>> all_epochs = DB().get_records(Epoch)
    >>> assert epoch in all_epochs, f"{epoch=} not in {all_epochs=}"
    >>> session_epochs = DB().get_records(Epoch, session_id='626791_2022-08-15')
    >>> session_epochs[0].tags
    ['DynamicRouting1']
    """

    table: ClassVar = "epochs"

    session_id: str | npc_session.SessionRecord
    start_time: str | npc_session.TimeRecord
    stop_time: str | npc_session.TimeRecord
    tags: list[str]
    notes: str | None = None


@dataclasses.dataclass
class File(Record):
    
    table: ClassVar = "files"

    session_id: str | npc_session.SessionRecord
    name: str
    suffix: str
    size: int
    timestamp: str | npc_session.TimeRecord
    s3_path: str | None = None
    allen_path: str | None = None
    data_asset_id: str | None = None
    notes: str | None = None

    
# TODO files, folders

if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
