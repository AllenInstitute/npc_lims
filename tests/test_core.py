import sqlite3

import npc_lims
from npc_lims.status import behavior_sessions


def test_import_package():
    pass


def _training_db_with_table(
    subject: str,
    exclusion_column: str,
) -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")

    def dict_factory(cursor, row):
        return {
            column[0]: row[index] for index, column in enumerate(cursor.description)
        }

    db.row_factory = dict_factory
    db.execute(
        f'CREATE TABLE "{subject}" ('
        '"ID" INTEGER, '
        '"start_time" TEXT, '
        f'"{exclusion_column}" INTEGER'
        ")"
    )
    db.executemany(
        f'INSERT INTO "{subject}" VALUES (?, ?, ?)',
        (
            (1, "2023-03-07 12:56:27", 0),
            (2, "2023-03-08 12:56:27", 1),
            (3, "", 0),
        ),
    )
    return db


def test_get_sessions_from_training_db_supports_renamed_ignore_column(monkeypatch):
    dbs = {
        False: _training_db_with_table("123456", "noLicks"),
        True: _training_db_with_table("654321", "ignore"),
    }

    monkeypatch.setattr(
        npc_lims.metadata,
        "get_training_db",
        lambda nsb=False: dbs[nsb],
    )
    behavior_sessions.get_sessions_from_training_db.cache_clear()

    try:
        sessions = behavior_sessions.get_sessions_from_training_db()
    finally:
        behavior_sessions.get_sessions_from_training_db.cache_clear()

    assert [row["ID"] for row in sessions[123456]] == [1]
    assert sessions[123456][0]["nsb"] is False
    assert [row["ID"] for row in sessions[654321]] == [1]
    assert sessions[654321][0]["nsb"] is True
