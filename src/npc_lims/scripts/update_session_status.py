#!/usr/bin/env python

from __future__ import annotations

import concurrent.futures as cf
from typing import Any

import npc_lims

try:
    import polars as pl
except ImportError:
    raise ImportError(
        "polars is required: run `pip install npc_lims[polars]`"
    ) from None


def get_status(session: str) -> dict[str, Any]:
    s = npc_lims.get_session_info(session=session)
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
        is_surface_channels_sorted = s.is_surface_channels_sorted
    else:
        surface_channels_asset_id = ""
        is_surface_channels_sorted = None
    return {
        "date": s.date,
        "session_id": aind_session_id,
        "raw_asset_id": raw_asset_id,
        "surface_channels_asset_id": surface_channels_asset_id,
        "is_uploaded": int(s.is_uploaded),
        "is_sorted": int(s.is_sorted),
        "is_surface_channels_sorted": (
            int(is_surface_channels_sorted)
            if is_surface_channels_sorted is not None
            else None
        ),
        "is_annotated": int(s.is_annotated),
        "is_dlc_eye": int(s.is_dlc_eye),
        "is_dlc_side": int(s.is_dlc_side),
        "is_dlc_face": int(s.is_dlc_face),
        "is_facemap": int(s.is_facemap),
        "is_gamma_encoding": int(s.is_gamma_encoding),
        "is_LPFaceParts": int(s.is_LPFaceParts),
        "is_session_json": int(s.is_session_json),
        "is_rig_json": int(s.is_rig_json),
    }


def main() -> None:
    # sync sqlite dbs with xlsx sheets on s3
    npc_lims.update_training_dbs()
    print("Successfully updated training DBs on s3.")

    with cf.ThreadPoolExecutor() as executor:
        results = list(
            executor.map(get_status, npc_lims.get_session_info(is_ephys=True))
        )

    path = npc_lims.S3_SCRATCH_ROOT / "status" / "status.parquet"
    df = pl.DataFrame(results).sort("date", descending=True)
    df.write_parquet(path)
    print(f"Successfully updated {path}")
    print(df)


if __name__ == "__main__":
    main()
