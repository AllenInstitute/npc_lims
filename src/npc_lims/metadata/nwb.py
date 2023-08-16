from __future__ import annotations

import dataclasses
from typing import ClassVar, Protocol

import npc_session
from typing_extensions import Self

import npc_lims.metadata.dbhub as dbhub


class SupportsToDB(Protocol):
    table: ClassVar[str]

    def to_db(self) -> dict[str, str | int | float | None]:
        ...


class SupportsFromDB(Protocol):
    table: ClassVar[str]

    @classmethod
    def from_db(cls, row: dict[str, str | int | float | None]) -> Self:
        ...


@dataclasses.dataclass
class Epoch:
    table: ClassVar = "epochs"

    session_id: str | npc_session.SessionRecord
    start_time: str | npc_session.TimeRecord
    stop_time: str | npc_session.TimeRecord
    tags: list[str]
    notes: str | None = None

    def to_db(self) -> dict[str, str]:
        row = self.__dict__
        row.pop("table", None)  # not actually needed for dataclass ClassVar
        row["tags"] = str(self.tags)
        return row

    @classmethod
    def from_db(cls, row: dict[str, str]) -> Epoch:
        row.pop("epoch_id", None)
        # basic check before eval
        if row["tags"][0] != "[" or row["tags"][-1] != "]":
            raise RuntimeError(f"Trying to load epoch with malformed tags: {row=}")
        row["tags"] = eval(row["tags"])
        return Epoch(**row)  # type: ignore


def add_to_db(*rows: SupportsToDB) -> None:
    """
    >>> epoch = Epoch('626791_2022-08-15', '11:23:36', '12:23:54', ['DynamicRouting1'])
    >>> add_to_db(epoch)
    """
    table = rows[0].table
    dbhub.NWBSqliteDBHub().insert(table, *(row.to_db() for row in rows))


def get_from_db(
    cls: SupportsFromDB,
    session: str | npc_session.SessionRecord | None = None,
) -> tuple[SupportsFromDB, ...]:
    """
    >>> all = get_from_db(Epoch)
    >>> assert all
    >>> epochs = get_from_db(Epoch, '626791_2022-08-15')
    >>> epochs[0].tags
    ['DynamicRouting1']
    """
    table = cls.table
    if session:
        query = f"SELECT * FROM {table!r} WHERE session_id = {session!r}"
    else:
        query = f"SELECT * FROM {table!r}"
    rows = dbhub.NWBSqliteDBHub().query(query)
    if not rows:
        return ()
    instances = []
    for row in rows:
        instances.append(cls.from_db(row))
    return tuple(instances)


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
