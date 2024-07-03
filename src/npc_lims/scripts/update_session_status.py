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
            session_id VARCHAR(35),
            raw_asset_id VARCHAR(36) DEFAULT NULL,
            surface_channel_asset_id VARCHAR(36) DEFAULT NULL,
            is_uploaded BOOLEAN DEFAULT NULL,
            is_sorted BOOLEAN DEFAULT NULL,
            is_annotated BOOLEAN DEFAULT NULL,
            is_dlc_eye BOOLEAN DEFAULT NULL,
            is_dlc_side BOOLEAN DEFAULT NULL,
            is_dlc_face BOOLEAN DEFAULT NULL,
            is_facemap BOOLEAN DEFAULT NULL, 
            is_session_json BOOLEAN DEFAULT NULL,
            is_rig_json BOOLEAN DEFAULT NULL
        );
        """
    )
    statement = "INSERT INTO status (date, session_id, raw_asset_id, surface_channel_asset_id, is_uploaded, is_sorted, is_annotated, is_dlc_eye, is_dlc_side, is_dlc_face, is_facemap, is_session_json, is_rig_json) VALUES "
    for s in sorted(npc_lims.get_session_info(), key=lambda s: s.date, reverse=True):
        if not s.is_ephys:
            continue
        try:
            aind_session_id = npc_lims.get_codoecean_session_id(s.id)
        except ValueError:
            aind_session_id = f"ecephys_{s.subject.id}_{s.date}_??-??-??"
        if s.is_uploaded:
            raw_asset_id = npc_lims.get_session_raw_data_asset(s.id)["id"]
        else:
            raw_asset_id = ""
        if s.is_surface_channels:
            surface_channel_asset_id = npc_lims.get_surface_channel_raw_data_asset(
                s.id
            )["id"]
        else:
            surface_channel_asset_id = ""
        statement += f"\n\t('{s.date}', '{aind_session_id}', '{raw_asset_id}', '{surface_channel_asset_id}', {int(s.is_uploaded)}, {int(s.is_sorted)}, {int(s.is_annotated)}, {int(s.is_dlc_eye)}, {int(s.is_dlc_side)}, {int(s.is_dlc_face)}, {int(s.is_facemap)}, {int(s.is_session_json)}, {int(s.is_rig_json)}),"

    statement = statement[:-1] + ";"
    response = connection.Execute(statement)
    if response[1]:
        print(
            f"Error inserting values into `status` table on dbhub: {response[1].get('error', 'Unknown error')}"
        )
    else:
        print(
            "Successfully updated `status` table on dbhub: https://dbhub.io/svc_neuropix/jobs.db"
        )


if __name__ == "__main__":
    main()
