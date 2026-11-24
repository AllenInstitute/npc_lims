from __future__ import annotations

import contextlib
import functools
import logging
import sqlite3
import tempfile
from typing import Any

import npc_session
import npc_shields.shields
import upath

logger = logging.getLogger(__name__)

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
    con = sqlite3.connect(db_path, check_same_thread=False)

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


def _get_shield(implant: str) -> npc_shields.shields.Shield | None:
    """Shield definition from npc_shields, by name, drawing ID or alias (e.g. 'TS5'),
    or None if not defined.

    >>> _get_shield('2002').drawing_id
    '0283-200-002'
    >>> _get_shield('TS5').name
    '3001'
    >>> _get_shield('unknown') is None
    True
    """
    try:
        return npc_shields.shields.get_shield(implant)
    except ValueError:
        return None


def _get_shield_drawing_id(
    shield_id: str,
) -> str | None:
    """
    >>> _get_shield_drawing_id('2002')
    '0283-200-002'
    """
    shield = _get_shield(shield_id)
    return None if shield is None else str(shield.drawing_id)


@functools.cache
def get_probe_insertion_metadata(
    session: str | npc_session.SessionRecord,
) -> dict[str, Any]:
    """
    >>> probe_insertion = get_probe_insertion_metadata('676909_2023-12-12')
    >>> probe_insertion['probes']['A']
    'F1'

    Implant and hole names in the targeting database are converted to the names used
    in `npc_shields` (the database's own names are kept under 'targeting_db'):
    >>> probe_insertion = get_probe_insertion_metadata('620263_2022-07-27')
    >>> probe_insertion['shield']
    {'name': '3001', 'drawing_id': '0283-300-01'}
    >>> probe_insertion['probes']['A'], probe_insertion['targeting_db']['probes']['A']
    ('4', 'E')
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
    insertions["targeting_db"] = {
        "implant": from_db["implant"],
        "probes": dict(insertions["probes"]),
    }
    shield = _get_shield(from_db["implant"])
    if shield is None:
        logger.warning(
            f"Implant {from_db['implant']!r} for {session.id} is not defined in npc_shields: using names from targeting database"
        )
        insertions["shield"]["name"] = from_db["implant"]
    else:
        insertions["shield"]["name"] = shield.name
        insertions["shield"]["drawing_id"] = str(shield.drawing_id)
        for probe, hole in insertions["probes"].items():
            if hole is None:
                continue
            try:
                insertions["probes"][probe] = shield.get_hole_label(str(hole))
            except KeyError:
                logger.warning(
                    f"Hole {hole!r} (probe {probe}, {session.id}) is not in npc_shields definition of {shield.name!r}: keeping name from targeting database"
                )
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
