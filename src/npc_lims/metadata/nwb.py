from __future__ import annotations

import dataclasses
from typing import ClassVar

import npc_session


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
    def from_db(cls, row: dict[str, str]) -> Epoch:
        row.pop("epoch_id", None)
        # basic check before eval
        if row["tags"][0] != "[" or row["tags"][-1] != "]":
            raise RuntimeError(f"Trying to load epoch with malformed tags: {row=}")
        row["tags"] = eval(row["tags"])
        return Epoch(**row)  # type: ignore


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
