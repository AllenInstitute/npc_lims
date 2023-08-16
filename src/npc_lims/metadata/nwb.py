from __future__ import annotations

import dataclasses

import npc_session

import npc_lims.metadata.dbhub as dbhub


@dataclasses.dataclass
class Epoch:
    session_id: str | npc_session.SessionRecord
    start_time: str | npc_session.TimeRecord
    stop_time: str | npc_session.TimeRecord
    tags: list[str]
    notes: str | None = None

    def to_db(self) -> dict[str, str]:
        row = self.__dict__
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


def add_epochs_to_db(*epochs: Epoch) -> None:
    """
    >>> epoch = Epoch('626791_2022-08-15', '11:23:36', '12:23:54', ['DynamicRouting1'])
    >>> add_epochs_to_db(epoch)
    """
    dbhub.NWBSqliteDBHub().insert("epochs", *(epoch.to_db() for epoch in epochs))


def get_epochs_from_db(
    session: str | npc_session.SessionRecord | None = None,
) -> tuple[Epoch, ...]:
    """
    >>> all = get_epochs_from_db()
    >>> assert all
    >>> epochs = get_epochs_from_db('626791_2022-08-15')
    >>> epochs[0].tags
    ['DynamicRouting1']
    """

    if session:
        query = f"SELECT * FROM epochs WHERE session_id = '{session}'"
    else:
        query = "SELECT * FROM epochs"
    rows = dbhub.NWBSqliteDBHub().query(query)
    if not rows:
        return ()
    epochs = []
    for row in rows:
        epochs.append(Epoch.from_db(row))
    return tuple(epochs)


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
