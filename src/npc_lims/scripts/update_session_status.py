#!/usr/bin/env python

# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "npc-lims[polars]",
#     "pydantic-settings>=2.0",
#     "tqdm>=4.0",
# ]
# ///

from __future__ import annotations

import concurrent.futures as cf
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict
from tqdm import tqdm

import npc_lims

try:
    import polars as pl
except ImportError:
    raise ImportError(
        "polars is required: run `pip install npc_lims[polars]`"
    ) from None


class Settings(BaseSettings):
    csv_output_path: Path | None = None

    model_config = SettingsConfigDict(
        cli_kebab_case=True,
        cli_parse_args=True,
    )


def get_status(session: str | npc_lims.SessionInfo) -> dict[str, Any]:
    s = (
        session
        if isinstance(session, npc_lims.SessionInfo)
        else npc_lims.get_session_info(session=session)
    )
    try:
        aind_session_id = npc_lims.get_codoecean_session_id(s.id)
    except ValueError:
        aind_session_id = f"ecephys_{s.subject.id}_{s.date}_??-??-??"
    if s.is_uploaded:
        raw_asset_id = npc_lims.get_session_raw_data_asset(s.id).id
    else:
        raw_asset_id = ""
    if s.is_surface_channels:
        surface_channels_asset_id = npc_lims.get_surface_channel_raw_data_asset(s.id).id
    else:
        surface_channels_asset_id = None
    return {
        "date": s.date,
        "session_id": aind_session_id,
        "raw_asset_id": raw_asset_id,
        "surface_channels_asset_id": surface_channels_asset_id,
        "is_uploaded": (is_uploaded := s.is_uploaded),
        "is_sorted": (is_sorted := (s.is_sorted if is_uploaded else None)),
        "is_surface_channels_sorted": (
            s.is_surface_channels_sorted if surface_channels_asset_id else None
        ),
        "is_annotated": s.is_annotated if is_sorted else None,
        "is_video": (is_video := (s.is_video if is_uploaded else None)),
        "is_dlc_eye": s.is_dlc_eye if is_video else None,
        "is_facemap": s.is_facemap if is_video else None,
        "is_gamma_encoding": s.is_gamma_encoding if is_video else None,
        "is_LPFaceParts": s.is_LPFaceParts if is_video else None,
        "is_session_json": s.is_session_json if is_uploaded else None,
        "is_rig_json": s.is_rig_json if is_uploaded else None,
    }


def main() -> None:
    settings = Settings()

    # sync sqlite dbs with xlsx sheets on s3
    print("Starting update of training DBs on S3...")
    npc_lims.update_training_dbs()
    print("Successfully updated training DBs on s3.")

    print("Fetching current information for session in tracking system...")
    sessions = list(npc_lims.get_session_info(is_ephys=True))
    with cf.ThreadPoolExecutor() as executor:
        futures = [executor.submit(get_status, session) for session in sessions]
        results = [
            future.result()
            for future in tqdm(
                cf.as_completed(futures),
                total=len(futures),
                desc="Fetching session status",
            )
        ]
    path = npc_lims.S3_SCRATCH_ROOT / "status" / "status.parquet"
    df = pl.DataFrame(results).sort("date", descending=True)
    print("Dataframe with rows:", len(df))
    print(f"Writing updated session status to {path}...")
    df.write_parquet(path)
    print(f"Successfully updated {path}")
    if settings.csv_output_path is not None:
        csv_path = settings.csv_output_path
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Writing updated session status to {csv_path}...")
        df.write_csv(csv_path)
        print(f"Successfully updated {csv_path}")


if __name__ == "__main__":
    main()
