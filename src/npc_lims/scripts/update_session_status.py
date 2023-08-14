#!/usr/bin/env python

from __future__ import annotations

import os

import pydbhub.dbhub as dbhub

import npc_lims

DB_NAME = "jobs.db"
DB_OWNER = "svc_neuropix"
API_KEY = os.getenv("DBHUB_API_KEY")


def main() -> None:
    if not API_KEY:
        print("No API key found. Please set the `DBHUB_API_KEY` environment variable.")
        return

    connection = dbhub.Dbhub(API_KEY, db_name=DB_NAME, db_owner=DB_OWNER)
    connection.Execute("DROP TABLE IF EXISTS status;")
    connection.Execute(
        """
        CREATE TABLE status (
            date DATE,
            subject_id VARCHAR(30),
            project VARCHAR DEFAULT NULL,
            is_uploaded BOOLEAN DEFAULT NULL,
            is_sorted BOOLEAN DEFAULT NULL
        );
        """
    )
    statement = (
        "INSERT INTO status (date, subject_id, project, is_uploaded, is_sorted) VALUES "
    )
    for s in sorted(npc_lims.tracked, key=lambda s: s.date, reverse=True):
        statement += f"\n\t('{s.date}', '{s.subject}', '{s.project}', {int(s.is_uploaded)}, {int(s.is_sorted)}),"
    statement = statement[:-1] + ";"
    response = connection.Execute(statement)
    if response[1]:
        print(
            f"Error inserting values into `status` table ob dbhub: {response[1].get('error', 'Unknown error')}"
        )
    else:
        print(
            "Successfully updated `status` table on dbhub: https://dbhub.io/svc_neuropix/jobs.db"
        )


if __name__ == "__main__":
    main()
