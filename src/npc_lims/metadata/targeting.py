from __future__ import annotations

import contextlib
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
def _get_shield_definition_text() -> str:
    return upath.UPath(
        "https://raw.githubusercontent.com/AllenInstitute/npc_shields/main/src/npc_shields/shields.py"
    ).read_text()


def _get_shield_drawing_id(
    shield_id: str,
) -> str:
    """
    See
    https://github.com/AllenInstitute/npc_shields/blob/main/src/npc_shields/shields.py

    >>> _get_shield_drawing_id('2002')
    '0283-200-002'
    """
    txt = _get_shield_definition_text()
    definition = f'name="{shield_id}",'
    if definition not in txt:
        raise ValueError(
            f"Shield {shield_id} not found in shield definitions - needs adding to `npc_shields`"
        )
    return str(txt.split(definition)[1].split('drawing_id="')[1].split('",')[0])


@functools.cache
def get_probe_insertion_metadata(
    session: str | npc_session.SessionRecord,
) -> dict[str, Any]:
    """
    >>> probe_insertion = get_probe_insertion_metadata('676909_2023-12-12')
    >>> probe_insertion['probes']['A']
    'F1'
    """
    session = npc_session.SessionRecord(session)
    target_db_connection = get_probe_target_db()

    cursor = target_db_connection.execute(
        f"SELECT * FROM session_metadata sm WHERE sm.session = '{session.subject}_{session.date}'"
    )
    metadata = cursor.fetchall()

    if len(metadata) == 0:
        raise ValueError(
            f"{session=} has no implant hole information in targeting database"
        )

    from_db = metadata[0]
    insertions: dict[str, Any] = {
        "shield": {"name": None, "drawing_id": None},
        "probes": {
            "A": None,
            "B": None,
            "C": None,
            "D": None,
            "E": None,
            "F": None,
        },
        "notes": {"A": None, "B": None, "C": None, "D": None, "E": None, "F": None},
        "session": None,
        "experiment_day": None,
    }
    for k in from_db:
        with contextlib.suppress(ValueError):
            probe = npc_session.ProbeRecord(k)
            insertions["probes"][probe] = from_db[k]
            continue
    insertions["shield"]["name"] = from_db["implant"]
    insertions["shield"]["drawing_id"] = _get_shield_drawing_id(from_db["implant"])
    insertions["session"] = session.id
    insertions["experiment_day"] = from_db["day"]
    return insertions


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
