from __future__ import annotations

import pathlib

import yaml

from npc_lims.metadata.ephys_tracking import (
    ReconciledSession,
    _is_deep_insertion,
    get_uncommented_upload_paths,
    session_key,
    update_tracked_sessions_text,
)
from npc_lims.status.tracked_sessions import (
    FileContents,
    _session_info_from_file_contents,
)


def test_get_uncommented_upload_paths(tmp_path: pathlib.Path) -> None:
    batch = tmp_path / "upload.bat"
    batch.write_text(
        "@REM upload_dr_ecephys ignored\n"
        'upload_dr_ecephys "//allen/path/DRpilot_123456_20260101"\n'
        "  upload_dr_ecephys //allen/path/DRpilot_123456_20260102\n",
        encoding="utf-8",
    )

    assert get_uncommented_upload_paths(batch) == (
        "//allen/path/DRpilot_123456_20260101",
        "//allen/path/DRpilot_123456_20260102",
    )


def test_ephys_day_is_supported_by_yaml_reader() -> None:
    contents: FileContents = {
        "ephys": {
            "DynamicRouting": [
                {"//allen/path/DRpilot_123456_20260101": {"ephys_day": 7}}
            ]
        }
    }

    assert _session_info_from_file_contents(contents)[0].experiment_day == 7


def test_deep_insertion_is_strictly_greater_than_3800_um() -> None:
    assert not _is_deep_insertion((3000, 3800))
    assert _is_deep_insertion((3801,))


def test_update_tracked_sessions_deduplicates_by_session_id(
    tmp_path: pathlib.Path,
) -> None:
    tracked = tmp_path / "tracked_sessions.yaml"
    tracked.write_text(
        """ephys:
  DynamicRouting:
    - //allen/old/DRpilot_123456_20260101:
        day: 1
        session_kwargs:
          custom_value: keep-me
  TempletonPilotSession:
    - //allen/duplicate/DRpilot_123456_20260101:
        ephys_day: 2
behavior_with_sync:
  DynamicRouting: []
behavior:
  DynamicRouting: []
""",
        encoding="utf-8",
    )
    session = ReconciledSession(
        path="//allen/new/DRpilot_123456_20260101",
        project="TempletonPilotSession",
        ephys_day=3,
        probe_letters_to_skip="C",
        authoritative_fields=frozenset({"probe_letters_to_skip"}),
    )

    updated = update_tracked_sessions_text((session,), tracked)
    contents = yaml.safe_load(updated)
    matching = []
    for project, entries in contents["ephys"].items():
        for item in entries or ():
            path, config = next(iter(item.items()))
            if session_key(path) == session.key:
                matching.append((project, path, config))

    assert matching == [
        (
            "TempletonPilotSession",
            session.path,
            {
                "ephys_day": 3,
                "session_kwargs": {
                    "custom_value": "keep-me",
                    "probe_letters_to_skip": "C",
                },
            },
        )
    ]
