from __future__ import annotations

import dataclasses
from typing import ClassVar, Literal, Optional

from typing_extensions import Self
import npc_session

import npc_lims.metadata.dbhub as dbhub
import npc_lims.metadata.types as types

@dataclasses.dataclass
class Subject:
    """
    >>> from npc_lims import tracked, NWBSqliteDBHub as DB
    >>> for session in tracked:
    ...     DB().add_records(Subject(session.subject))
    >>> all_subjects = DB().get_records(Subject)
    """
    table: ClassVar[str] = "subjects"
    
    subject_id: int | npc_session.SubjectRecord
    sex: Optional[Literal['M', 'F', 'U']] = None
    date_of_birth: Optional[str | npc_session.DateRecord] = None
    genotype: Optional[str] = None
    description: Optional[str] = None
    strain: Optional[str] = None
    notes: Optional[str] = None
    
    def to_db(self) -> dict[str, str | int | float | None]:
        return self.__dict__.copy()

    @classmethod
    def from_db(cls, row: dict[str, str | int | float | None]) -> Self:
        return cls(**row)  # type: ignore
    
    
@dataclasses.dataclass
class Session:
    """
    >>> from npc_lims import tracked, NWBSqliteDBHub as DB
    >>> for session in tracked:
    ...     DB().add_records(Session(session.session, session.subject))
    >>> all_sessions = DB().get_records(Session)
    """
    table: ClassVar[str] = "sessions"
    
    session_id: str | npc_session.SessionRecord
    subject_id: int | npc_session.SubjectRecord
    session_start_time: Optional[str | npc_session.TimeRecord] = None
    stimulus_notes: Optional[str] = None
    experimenter: Optional[str] = None
    experiment_description: Optional[str] = None
    epoch_tags: Optional[str] = None
    source_script: Optional[str] = None
    identifier: Optional[str] = None
    notes: Optional[str] = None
    
    def to_db(self) -> dict[str, str | int | float | None]:
        return self.__dict__.copy()

    @classmethod
    def from_db(cls, row: dict[str, str | int | float | None]) -> Self:
        return cls(**row)  # type: ignore
    

@dataclasses.dataclass
class Epoch:
    """
    >>> from npc_lims import NWBSqliteDBHub as DB

    >>> epoch = Epoch('626791_2022-08-15', '11:23:36', '12:23:54', ['DynamicRouting1'])
    >>> DB().add_records(epoch)

    >>> all_epochs = DB().get_records(Epoch)
    >>> assert epoch in all_epochs, f"{epoch=} not in {all_epochs=}"
    >>> session_epochs = DB().get_records(Epoch, '626791_2022-08-15')
    >>> session_epochs[0].tags
    ['DynamicRouting1']
    """

    table: ClassVar = "epochs"

    session_id: str | npc_session.SessionRecord
    start_time: str | npc_session.TimeRecord
    stop_time: str | npc_session.TimeRecord
    tags: list[str]
    notes: str | None = None

    def to_db(self) -> dict[str, str]:
        row = self.__dict__.copy()
        row.pop("table", None)  # not actually needed for dataclass ClassVar
        row["tags"] = str(self.tags)
        return row

    @classmethod
    def from_db(cls, row: dict[str, str]) -> Self:
        row.pop("epoch_id", None)
        # basic check before eval
        if row["tags"][0] != "[" or row["tags"][-1] != "]":
            raise RuntimeError(f"Trying to load epoch with malformed tags: {row=}")
        row["tags"] = eval(row["tags"])
        return cls(**row)  # type: ignore


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
