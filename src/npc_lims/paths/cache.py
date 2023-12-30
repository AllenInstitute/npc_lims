from __future__ import annotations

from typing import Literal
import typing 

import npc_session
import packaging.version
import upath

import npc_lims.paths.s3

CACHE_ROOT = npc_lims.paths.s3.S3_SCRATCH_ROOT / "session-caches"

NWBComponentStr = Literal[
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

CACHED_FILE_EXTENSIONS = {
    "session": ".parquet",
    "subject": ".parquet",
    "units": ".parquet",
    "epochs": ".parquet",
    "intervals": ".parquet",
    "invalid_times": ".parquet",
    "electrodes": ".parquet",
    "electrode_groups": ".parquet",
    "devices": ".parquet",
}
"""Mapping from NWB component to file extension"""

assert CACHED_FILE_EXTENSIONS.keys() == set(
    typing.get_args(NWBComponentStr)
), "CACHED_FILE_EXTENSIONS must have keys for all NWBComponent values"
assert all(v.startswith(".") for v in CACHED_FILE_EXTENSIONS.values()), (
    "CACHED_FILE_EXTENSIONS must have values that start with a period"
)

def get_cache_ext(nwb_component: NWBComponentStr) -> str:
    """
    >>> get_cache_ext("session")
    '.json'
    """
    if (ext := CACHED_FILE_EXTENSIONS.get(nwb_component, None)) is None:
        raise ValueError(
            f"Unknown NWB component {nwb_component!r} - must be one of {NWBComponentStr}"
        )
    return ext

def get_current_cache_version() -> str:
    """
    >>> v = get_current_cache_version()
    >>> assert v > 'v0.0.0'
    """
    if not (version_dirs := sorted(CACHE_ROOT.glob("v*"))):
        raise FileNotFoundError(f"No cache versions found in {CACHE_ROOT}")
    return version_dirs[-1].name

def get_cache_path(
    session: str | npc_session.SessionRecord,
    nwb_component: NWBComponentStr,
    version: str | None = None,
) -> upath.UPath:
    """
    If version is not specified, the latest version currently in the cache will be
    used, ie. should point to the most recent version of the file.

    >>> get_cache_path(session="366122_2023-12-31", nwb_component="units", version="1.0.0")
    S3Path('s3://aind-scratch-data/ben.hardcastle/session-caches/v1.0.0/units/366122_2023-12-31_units.parquet')
    """
    session = npc_session.SessionRecord(session)
    version = f"v{packaging.version.parse(str(version))}" if version else get_current_cache_version()
    return (
        CACHE_ROOT
        / version
        / nwb_component
        / f"{session}_{nwb_component}{get_cache_ext(nwb_component)}"
    )

if __name__ == "__main__":
    import doctest

    doctest.testmod(
        optionflags=(doctest.IGNORE_EXCEPTION_DETAIL | doctest.NORMALIZE_WHITESPACE)
    )