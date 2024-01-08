from __future__ import annotations

from typing import Literal
import typing 

import npc_session
import packaging.version
import upath
from typing_extensions import TypeAlias
import npc_lims.paths.s3

CACHE_ROOT = npc_lims.paths.s3.S3_SCRATCH_ROOT / "session-caches"

NWBComponentStr: TypeAlias = Literal[
    "session",
    "subject",
    "units",
    "epochs",
    "intervals",
    "invalid_times",
    "electrodes",
    "electrode_groups",
    "devices",
]

CACHED_FILE_EXTENSIONS: dict[str, str] = dict.fromkeys(str(typing.get_args(NWBComponentStr)), '.parquet')
"""Mapping of NWB component name to file extension"""

assert CACHED_FILE_EXTENSIONS.keys() == set(
    typing.get_args(NWBComponentStr)
), "CACHED_FILE_EXTENSIONS must have keys for all NWBComponent values"
assert all(v.startswith(".") for v in CACHED_FILE_EXTENSIONS.values()), (
    "CACHED_FILE_EXTENSIONS must have values that start with a period"
)

def get_cache_ext(nwb_component: NWBComponentStr) -> str:
    """
    >>> get_cache_ext("session")
    '.parquet'
    """
    if (ext := CACHED_FILE_EXTENSIONS.get(nwb_component, None)) is None:
        raise ValueError(
            f"Unknown NWB component {nwb_component!r} - must be one of {NWBComponentStr}"
        )
    return ext

def get_current_cache_version() -> str:
    """
    >>> (get_cache_path("366122_2023-12-31", "units", "v0.0.0").parent / 'test.txt').touch()
    >>> v = get_current_cache_version()
    >>> assert v >= 'v0.0.0'
    """
    if not (version_dirs := sorted(CACHE_ROOT.glob("v*"))):
        raise FileNotFoundError(f"No cache versions found in {CACHE_ROOT}")
    return version_dirs[-1].name

def _parse_version(version: str) -> str:
    return f"v{packaging.version.parse(str(version))}"

def _parse_cache_path(session: str | npc_session.SessionRecord, nwb_component: NWBComponentStr, version: str | None = None) -> upath.UPath:
    session = npc_session.SessionRecord(session)
    version = _parse_version(version)  if version else get_current_cache_version() 
    return CACHE_ROOT / version / nwb_component / f"{session}_{nwb_component}{get_cache_ext(nwb_component)}"
 
def get_cache_path(
    session: str | npc_session.SessionRecord,
    nwb_component: NWBComponentStr,
    version: str | None = None,
    check_exists: bool = False,
) -> upath.UPath:
    """
    If version is not specified, the latest version currently in the cache will be
    used, ie. will point to the most recent version of the file.

    >>> get_cache_path(session="366122_2023-12-31", nwb_component="units", version="1.0.0")
    S3Path('s3://aind-scratch-data/ben.hardcastle/session-caches/v1.0.0/units/366122_2023-12-31_units.parquet')
    """
    session = npc_session.SessionRecord(session)
    path = _parse_cache_path(session, nwb_component, version) 
    if check_exists and not path.exists():
        raise FileNotFoundError(f"Cache file for {session} {nwb_component} {version} does not exist")
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
    dummy_path = _parse_cache_path("366122_2023-12-31", nwb_component, version)
    if not dummy_path.parent.exists():
        raise FileNotFoundError(f"Cache directory for {nwb_component} {version} does not exist")
    return tuple(
        path for path in dummy_path.parent.glob(f"*{dummy_path.suffix}")
    )
    
if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )