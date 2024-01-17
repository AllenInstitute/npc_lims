from __future__ import annotations

import typing
from typing import Literal

import npc_session
import packaging.version
import requests
import upath
from typing_extensions import TypeAlias

from npc_lims.paths.s3 import S3_SCRATCH_ROOT

CACHE_ROOT = S3_SCRATCH_ROOT / "cache" / "nwb_components"

NWBComponentStr: TypeAlias = Literal[
    "session",
    "subject",
    "epochs",
    "trials",
    "performance",
    "vis_rf_mapping",
    "aud_rf_mapping",
    "optotagging",
    "invalid_times",
    "devices",
    "electrode_groups",
    "electrodes",
    "units",
    # TODO licks, pupil area, xy pos, running speed (zarr?)
]

CACHED_FILE_EXTENSIONS: dict[str, str] = dict.fromkeys(
    typing.get_args(NWBComponentStr), ".parquet"
)
"""Mapping of NWB component name to file extension"""

assert CACHED_FILE_EXTENSIONS.keys() == set(
    typing.get_args(NWBComponentStr)
), "CACHED_FILE_EXTENSIONS must have keys for all NWBComponent values"
assert all(
    v.startswith(".") for v in CACHED_FILE_EXTENSIONS.values()
), "CACHED_FILE_EXTENSIONS must have values that start with a period"


def get_cache_file_suffix(nwb_component: NWBComponentStr) -> str:
    """
    >>> get_cache_file_suffix("session")
    '.parquet'
    """
    if (ext := CACHED_FILE_EXTENSIONS.get(nwb_component, None)) is None:
        raise ValueError(
            f"Unknown NWB component {nwb_component!r} - must be one of {NWBComponentStr}"
        )
    return ext


def get_current_cache_version() -> str:
    """The current version of npc_sessions, formatted as a string starting with
    'v'.

    >>> (get_cache_path(nwb_component="units", session_id="366122_2023-12-31", version="v0.0.0").parent / 'test.txt').touch()
    >>> v = get_current_cache_version()
    >>> assert v >= 'v0.0.0'
    """
    if not (version_dirs := sorted(CACHE_ROOT.glob("v*"))):
        raise FileNotFoundError(f"No cache versions found in {CACHE_ROOT}")
    npc_sessions_info = requests.get("https://pypi.org/pypi/npc_sessions/json").json()
    return _parse_version(npc_sessions_info["info"]["version"])


def _parse_version(version: str) -> str:
    """
    >>> _parse_version("0.0.0")
    'v0.0.0'
    >>> _parse_version("v0.0.0")
    'v0.0.0'
    >>> _parse_version("test")
    Traceback (most recent call last):
    ...
    ValueError: Invalid version 'test'
    """
    try:
        return f"v{packaging.version.parse(str(version))}"
    except packaging.version.InvalidVersion:
        raise ValueError(f"Invalid version {version!r}")


def _parse_cache_path(
    nwb_component: NWBComponentStr,
    session_id: str | npc_session.SessionRecord | None = None,
    version: str | None = None,
) -> upath.UPath:
    if version is not None:
        try:
            version = _parse_version(version)
        except ValueError:
            version = version
    else:
        version = get_current_cache_version()
    d = CACHE_ROOT / version / nwb_component
    if session_id is None:
        return d
    return (
        d
        / f"{npc_session.SessionRecord(session_id)}{get_cache_file_suffix(nwb_component)}"
    )


def get_cache_path(
    nwb_component: NWBComponentStr,
    session_id: str | npc_session.SessionRecord | None = None,
    version: str | None = None,
    consolidated: bool = True,
) -> upath.UPath:
    """
    If version is not specified, the latest version currently in the cache will be
    used, ie. will point to the most recent version of the file.

    >>> get_cache_path(nwb_component="units", version="1.0.0")
    S3Path('s3://aind-scratch-data/ben.hardcastle/cache/nwb_components/v1.0.0/units')
    >>> get_cache_path(nwb_component="units", session_id="366122_2023-12-31", version="1.0.0")
    S3Path('s3://aind-scratch-data/ben.hardcastle/cache/nwb_components/v1.0.0/units/366122_2023-12-31.parquet')
    >>> get_cache_path(nwb_component="trials", version="1.0.0")
    S3Path('s3://aind-scratch-data/ben.hardcastle/cache/nwb_components/v1.0.0/consolidated/trials.parquet')
    """
    path = _parse_cache_path(
        session_id=session_id, nwb_component=nwb_component, version=version
    )
    if consolidated and session_id is None and nwb_component != "units":
        path = path.parent / "consolidated" / f"{nwb_component}.parquet"
    return path


def get_all_cache_paths(
    nwb_component: NWBComponentStr,
    version: str | None = None,
) -> tuple[upath.UPath, ...]:
    """
    For a particular NWB component, return cached file paths for all sessions, for
    the latest version (default) or a specific version.

    >>> get_all_cache_paths("units", version="0.0.0")
    ()
    """
    dir_path = get_cache_path(nwb_component=nwb_component, version=version, consolidated=False)
    if not dir_path.exists():
        raise FileNotFoundError(
            f"Cache directory for {nwb_component} {version=} does not exist"
        )
    return tuple(
        path for path in dir_path.glob(f"*{get_cache_file_suffix(nwb_component)}")
    )


if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )
