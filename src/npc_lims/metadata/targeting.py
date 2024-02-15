from __future__ import annotations

import functools
import sqlite3
import tempfile
from typing import Any

import npc_session
import upath

S3_PROBE_TARGET_DB_PATH = upath.UPath(
    "s3://aind-scratch-data/arjun.sridhar/probe_targeting/dr_master.db"
)


@functools.cache
def get_probe_target_db() -> sqlite3.Connection:
    """
    Download db to tempdir, open connection, return connection.

    Examples:
        >>> assert get_probe_target_db()
    """
    db_path = upath.UPath(tempfile.mkstemp(suffix=".db")[1])

    db_path.write_bytes(S3_PROBE_TARGET_DB_PATH.read_bytes())
    con = sqlite3.connect(db_path)

    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    con.row_factory = dict_factory
    return con


def get_probe_insertion_info(
    probe_insertion_default: dict[str, Any], metadata: dict[str, str | int]
) -> dict[str, Any]:
    probe_letters = ["A", "B", "C", "D", "E", "F"]
    for letter in probe_letters:
        probe_insertion_default["probe_insertions"][f"probe{letter}"]["letter"] = letter
        probe_insertion_default["probe_insertions"][f"probe{letter}"]["hole"] = (
            metadata[f"Probe{letter}"]
        )

    probe_insertion_default["probe_insertions"]["implant"] = metadata["implant"]
    return probe_insertion_default


@functools.cache
def get_probe_insertion_metadata(
    session: str | npc_session.SessionRecord,
) -> dict[str, Any]:
    """
    >>> probe_insertion = get_probe_insertion_metadata('676909_2023-12-12')
    >>> probe_insertion['probe_insertions']['probeA']['hole']
    'F1'
    """
    session = npc_session.SessionRecord(session)
    target_db_connection = get_probe_target_db()

    cursor = target_db_connection.execute(
        f"SELECT * FROM session_metadata sm WHERE sm.session = '{session.subject}_{session.date}'"
    )
    metadata = cursor.fetchall()

    if len(metadata) == 0:
        raise ValueError(f"Session {session} has no implant hole information")

    metadata_dict = metadata[0]
    probe_insertions_default = {
        "probe_insertions": {
            "probeA": {},
            "probeB": {},
            "probeC": {},
            "probeD": {},
            "probeE": {},
            "probeF": {},
            "implant": "",
        }
    }

    return get_probe_insertion_info(probe_insertions_default, metadata_dict)


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
