from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import NoReturn

import aind_session
import npc_session
import pytest
import upath

import npc_lims
from npc_lims.metadata import codeocean_utils
from npc_lims.paths import s3
from npc_lims.scripts.update_session_status import get_status


def test_get_status_does_not_reresolve_session_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = npc_lims.SessionInfo(
        id=npc_session.SessionRecord("123456_2024-01-02"),
        project="test",
        is_ephys=True,
        is_sync=True,
        allen_path=upath.UPath("s3://test/123456/2024-01-02"),
    )
    for name, value in {
        "is_uploaded": False,
        "is_surface_channels": False,
    }.items():
        object.__setattr__(session, name, value)

    def fail_if_called(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("an existing SessionInfo should not be resolved again")

    monkeypatch.setattr(npc_lims, "get_session_info", fail_if_called)
    monkeypatch.setattr(npc_lims, "get_session_data_assets", fail_if_called)
    monkeypatch.setattr(
        npc_lims,
        "get_codoecean_session_id",
        lambda _: "ecephys_123456_2024-01-02_12-34-56",
    )

    result = get_status(session)

    assert result["session_id"] == "ecephys_123456_2024-01-02_12-34-56"
    assert result["is_uploaded"] is False
    assert result["is_sorted"] is None


def test_get_status_uses_session_assets_for_derived_statuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = npc_lims.SessionInfo(
        id=npc_session.SessionRecord("123456_2024-01-02"),
        project="test",
        is_ephys=True,
        is_sync=True,
        allen_path=upath.UPath("s3://test/123456/2024-01-02"),
    )
    for name, value in {
        "is_uploaded": True,
        "is_surface_channels": False,
        "is_video": True,
        "is_annotated": False,
        "is_session_json": True,
        "is_rig_json": True,
    }.items():
        object.__setattr__(session, name, value)

    assets = (
        SimpleNamespace(name="ecephys_123456_2024-01-02_sorted_2024-01-03", files=10),
        SimpleNamespace(name="ecephys_123456_2024-01-02_dlc_eye_2024-01-03", files=1),
    )
    subject_assets = (
        SimpleNamespace(name="subject_123456_smartspim", files=1),
    )
    monkeypatch.setattr(npc_lims, "get_session_data_assets", lambda _: assets)
    monkeypatch.setattr(npc_lims, "get_subject_data_assets", lambda _: subject_assets)
    monkeypatch.setattr(
        npc_lims,
        "get_codoecean_session_id",
        lambda _: "ecephys_123456_2024-01-02_12-34-56",
    )
    monkeypatch.setattr(
        npc_lims,
        "get_session_raw_data_asset",
        lambda _: SimpleNamespace(id="raw-asset"),
    )
    monkeypatch.setattr(
        npc_lims.paths.s3,
        "get_tissuecyte_annotation_files_from_s3",
        lambda _: (),
    )
    monkeypatch.setattr(
        aind_session.ecephys,
        "get_latest_ibl_annotations",
        lambda _: {},
    )

    def fail_if_aind_sorting_is_resolved(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("the AIND sorting model should not be resolved")

    monkeypatch.setattr(
        npc_lims.metadata.codeocean_utils,
        "get_session_sorted_data_asset",
        fail_if_aind_sorting_is_resolved,
    )

    result = get_status(session)

    assert result["is_sorted"] is True
    assert result["is_dlc_eye"] is True
    assert result["is_facemap"] is False
    assert result["is_gamma_encoding"] is False
    assert result["is_LPFaceParts"] is False
    assert result["is_imaged"] is True


def test_annotation_lookup_reuses_session_info(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    session = npc_lims.SessionInfo(
        id=npc_session.SessionRecord("123456_2024-01-02"),
        project="test",
        is_ephys=True,
        is_sync=True,
        allen_path=upath.UPath("s3://test/123456/2024-01-02"),
        experiment_day=2,
    )
    subject_path = tmp_path / "123456"
    subject_path.mkdir()
    expected = (
        subject_path / "Probe_A2_channels_123456_warped_processed_new_sorting.csv"
    )
    expected.touch()

    def fail_if_called(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("an existing SessionInfo should not be resolved again")

    s3.get_tissuecyte_annotation_files_from_s3.cache_clear()
    monkeypatch.setattr(s3, "TISSUECYTE_REPO", upath.UPath(tmp_path))
    monkeypatch.setattr(s3.tracked_sessions, "get_session_info", fail_if_called)

    assert s3.get_tissuecyte_annotation_files_from_s3(session) == (
        upath.UPath(expected),
    )


def test_surface_channels_sorted_falls_back_to_index_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = npc_lims.SessionInfo(
        id=npc_session.SessionRecord("123456_2024-01-02"),
        project="test",
        is_ephys=True,
        is_sync=True,
        allen_path=upath.UPath("s3://test/123456/2024-01-02"),
    )
    object.__setattr__(session, "is_surface_channels", True)

    def get_assets(requested: npc_session.SessionRecord) -> tuple[object, ...]:
        if requested.idx == 1:
            raise codeocean_utils.SessionIndexError
        return (SimpleNamespace(name="surface_sorted", files=7),)

    monkeypatch.setattr(codeocean_utils, "get_session_data_assets", get_assets)

    assert session.is_surface_channels_sorted is True


def test_get_status_surface_channels_sorted_falls_back_to_index_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = npc_lims.SessionInfo(
        id=npc_session.SessionRecord("840160_2026-04-28"),
        project="test",
        is_ephys=True,
        is_sync=True,
        allen_path=upath.UPath("s3://test/840160/2026-04-28"),
    )
    for name, value in {
        "is_uploaded": True,
        "is_surface_channels": True,
        "is_video": False,
        "is_session_json": True,
        "is_rig_json": True,
    }.items():
        object.__setattr__(session, name, value)

    main_assets = (SimpleNamespace(name="surface_sorted", files=7),)

    def get_assets(requested: npc_session.SessionRecord) -> tuple[object, ...]:
        if requested.idx == 1:
            raise codeocean_utils.SessionIndexError
        return main_assets

    monkeypatch.setattr(npc_lims, "get_session_data_assets", get_assets)
    monkeypatch.setattr(
        npc_lims,
        "get_codoecean_session_id",
        lambda _: "ecephys_840160_2026-04-28_12-21-46",
    )
    monkeypatch.setattr(
        npc_lims,
        "get_session_raw_data_asset",
        lambda _: SimpleNamespace(id="raw-asset"),
    )
    monkeypatch.setattr(
        npc_lims,
        "get_surface_channel_raw_data_asset",
        lambda _: SimpleNamespace(id="surface-asset"),
    )

    result = get_status(session)

    assert result["is_surface_channels_sorted"] is True
