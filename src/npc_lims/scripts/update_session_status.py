#!/usr/bin/env python

from __future__ import annotations

import os

import pydbhub.dbhub as dbhub

import npc_lims

DB_NAME = "jobs.db"
DB_OWNER = "svc_neuropix"
API_KEY = os.getenv("DBHUB_API_KEY")


def main() -> None:
    # sync sqlite dbs with xlsx sheets on s3
    npc_lims.update_training_dbs()
    print("Successfully updated training DBs on s3.")

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
            is_sorted BOOLEAN DEFAULT NULL,
            is_annotated BOOLEAN DEFAULT NULL,
            is_dlc_eye BOOLEAN DEFAULT NULL,
            is_dlc_side BOOLEAN DEFAULT NULL,
            is_dlc_face BOOLEAN DEFAULT NULL,
            is_facemap BOOLEAN DEFAULT NULL
        );
        """
    )
    statement = "INSERT INTO status (date, subject_id, project, is_uploaded, is_sorted, is_annotated, is_dlc_eye, is_dlc_side, is_dlc_face, is_facemap) VALUES "
    for s in sorted(npc_lims.get_session_info(), key=lambda s: s.date, reverse=True):
        if not s.is_ephys:
            continue
        statement += f"\n\t('{s.date}', '{s.subject}', '{s.project}', {int(s.is_uploaded)}, {int(s.is_sorted)}, {int(s.is_annotated)}, {int(s.is_dlc_eye)}, {int(s.is_dlc_side)}, {int(s.is_dlc_face)}, {int(s.is_facemap)}),"
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
