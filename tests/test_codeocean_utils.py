from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import upath

from npc_lims.metadata import codeocean_utils


def test_surface_channel_asset_is_not_selected_as_main_raw_asset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    surface_asset = SimpleNamespace(
        name="ecephys_840160_2026-04-28_12-21-46",
        created=1,
        source_bucket=object(),
    )
    asset_root = upath.UPath(tmp_path)
    (tmp_path / "ecephys").mkdir()

    monkeypatch.setattr(
        codeocean_utils,
        "get_session_data_assets",
        lambda session: (surface_asset,),
    )
    monkeypatch.setattr(codeocean_utils, "is_raw_data_asset", lambda asset: True)
    monkeypatch.setattr(
        codeocean_utils,
        "get_path_from_data_asset",
        lambda asset: asset_root,
    )

    with pytest.raises(ValueError, match="no main raw data assets"):
        codeocean_utils.get_session_raw_data_asset("840160_2026-04-28")


def test_main_raw_asset_can_contain_behavior_videos_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    main_asset = SimpleNamespace(
        name="ecephys_840160_2026-04-28_12-21-46",
        created=1,
        source_bucket=object(),
    )
    asset_root = upath.UPath(tmp_path)
    (tmp_path / "behavior-videos").mkdir()

    monkeypatch.setattr(
        codeocean_utils,
        "get_session_data_assets",
        lambda session: (main_asset,),
    )
    monkeypatch.setattr(codeocean_utils, "is_raw_data_asset", lambda asset: True)
    monkeypatch.setattr(
        codeocean_utils,
        "get_path_from_data_asset",
        lambda asset: asset_root,
    )

    assert (
        codeocean_utils.get_session_raw_data_asset("840160_2026-04-28")
        is main_asset
    )
