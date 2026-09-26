#!/usr/bin/env python

# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "npc-lims[polars]",
#     "pydantic-settings>=2.0",
#     "tqdm>=4.0",
# ]
#
# [tool.uv.sources]
# npc_lims = { git = "https://github.com/AllenInstitute/npc_lims" }
# ///

from __future__ import annotations

import concurrent.futures as cf
import contextlib
from pathlib import Path
from typing import Any

import aind_session
from pydantic_settings import BaseSettings, SettingsConfigDict
from tqdm import tqdm

import npc_lims
from npc_lims.paths import s3

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


MAX_WORKERS = 16


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
    is_uploaded = s.is_uploaded
    # The status properties below all inspect the same Code Ocean asset list. Fetch
    # that list once and use it directly instead of resolving each property through
    # the much more expensive AIND session model. Unuploaded sessions do not need
    # this lookup at all.
    session_assets = npc_lims.get_session_data_assets(s.id) if is_uploaded else ()
    if is_uploaded:
        raw_asset_id = npc_lims.get_session_raw_data_asset(s.id).id
    else:
        raw_asset_id = ""
    if s.is_surface_channels:
        surface_channels_asset_id = npc_lims.get_surface_channel_raw_data_asset(s.id).id
    else:
        surface_channels_asset_id = None
    if surface_channels_asset_id:
        try:
            surface_channel_assets = npc_lims.get_session_data_assets(s.id.with_idx(1))
        except npc_lims.SessionIndexError:
            # If the main recording failed, the surface-channel recording can be
            # the only asset and therefore occupy index 0.
            surface_channel_assets = (
                session_assets
                if is_uploaded
                else npc_lims.get_session_data_assets(s.id)
            )
    else:
        surface_channel_assets = ()
    is_video = s.is_video if is_uploaded else None
    is_gamma_encoding = (
        _has_asset(session_assets, "GammaEncoding") if is_video else None
    )
    return {
        "date": s.date,
        "session_id": aind_session_id,
        "raw_asset_id": raw_asset_id,
        "surface_channels_asset_id": surface_channels_asset_id,
        "is_uploaded": is_uploaded,
        "is_sorted": (
            is_sorted := (_has_sorted_asset(session_assets) if is_uploaded else None)
        ),
        "is_surface_channels_sorted": (
            _has_surface_channels_sorted(surface_channel_assets)
            if surface_channels_asset_id
            else None
        ),
        "is_annotated": (_is_annotated(s, aind_session_id) if is_sorted else None),
        "is_video": is_video,
        "is_dlc_eye": _has_asset(session_assets, "dlc_eye") if is_video else None,
        "is_facemap": _has_asset(session_assets, "facemap") if is_video else None,
        "is_gamma_encoding": is_gamma_encoding,
        "is_LPFaceParts": (
            _has_asset(session_assets, "LPFaceParts")
            if is_video and is_gamma_encoding
            else False if is_video else None
        ),
        "is_session_json": s.is_session_json if is_uploaded else None,
        "is_rig_json": s.is_rig_json if is_uploaded else None,
    }


def _has_asset(assets: tuple[Any, ...], name: str) -> bool:
    return any(name in asset.name for asset in assets)


def _has_sorted_asset(assets: tuple[Any, ...]) -> bool:
    """Return whether a session has a sorted result asset.

    The old ``SessionInfo.is_sorted`` implementation resolves an AIND session and
    inspects each sorting asset's files and output. That is useful when the caller
    needs the selected asset, but this script only needs the status boolean. The
    Code Ocean asset naming convention is the same one used by AIND's sorted-asset
    detection and is already available in the per-subject asset listing.
    """
    return any("_sorted_" in asset.name for asset in assets)


def _has_surface_channels_sorted(assets: tuple[Any, ...]) -> bool:
    return any("sorted" in asset.name and asset.files > 6 for asset in assets)


def _is_annotated(session: npc_lims.SessionInfo, aind_session_id: str) -> bool:
    with contextlib.suppress(FileNotFoundError, ValueError):
        return bool(s3.get_tissuecyte_annotation_files_from_s3(session))
    with contextlib.suppress(FileNotFoundError, ValueError, IndexError, KeyError):
        return bool(aind_session.ecephys.get_latest_ibl_annotations(aind_session_id))
    return False


def _preload_session_assets(session: npc_lims.SessionInfo) -> None:
    """Warm the shared subject-asset cache before session workers start."""
    npc_lims.get_session_data_assets(session.id)


def main() -> None:
    settings = Settings()

    # sync sqlite dbs with xlsx sheets on s3
    print("Starting update of training DBs on S3...")
    npc_lims.update_training_dbs()
    print("Successfully updated training DBs on s3.")

    print("Fetching current information for session in tracking system...")
    sessions = list(npc_lims.get_session_info(is_ephys=True))
    sessions_by_subject = {session.subject.id: session for session in sessions}
    with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        list(executor.map(_preload_session_assets, sessions_by_subject.values()))
    with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
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
