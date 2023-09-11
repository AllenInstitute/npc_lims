from __future__ import annotations

import os

import npc_session
import pydbhub.dbhub as dbhub

DB_NAME = "jobs.db"
DB_OWNER = "svc_neuropix"
API_KEY = os.getenv("DBHUB_API_KEY")


def get_day(session: str | npc_session.SessionRecord) -> int:
    """
    >>> get_day('670180_2023-07-26')
    2
    """
    session = npc_session.SessionRecord(session)

    connection = dbhub.Dbhub(API_KEY, db_name=DB_NAME, db_owner=DB_OWNER)
    statement = (
        f"""SELECT date FROM STATUS WHERE subject_id = {str(session.subject.id)}"""
    )
    response = connection.Query(statement)[0]
    if response is not None:
        dates = sorted([date["date"] for date in response])
    else:
        raise ValueError(f"{session.id} not in Status table for jobs database")

    day = tuple(
        dates.index(date) + 1
        for date in dates
        if f"{session.subject}_{date}" in session
    )[0]

    return day


if __name__ == "__main__":
    import doctest

    import dotenv

    dotenv.load_dotenv(dotenv.find_dotenv(usecwd=True))
    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
