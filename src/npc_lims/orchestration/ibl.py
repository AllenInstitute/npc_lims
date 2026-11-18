# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "aind-session>=0.3.25",
#   "codeocean>=0.3.1",
#   "npc-session>=0.1.36",
#   "universal-pathlib>=0.1.4",
# ]
# ///
import dataclasses
import datetime
from collections.abc import Mapping

import upath

from npc_lims.ibl import normalize_etag


@dataclasses.dataclass(frozen=True)
class S3ObjectMetadata:
    """Metadata used to identify one externally stored object."""

    uri: str
    etag: str
    size: int
    last_modified: str


@dataclasses.dataclass(frozen=True)
class NgJsonConfig:
    """Configuration for observing one annotated Neuroglancer JSON."""

    subject_id: int
    uri: str
    etag: str
    size: int
    last_modified: str


def _metadata_value(info: Mapping[str, object], *names: str) -> object | None:
    """Get metadata while tolerating common fsspec/S3 spellings."""
    for name in names:
        if (value := info.get(name)) is not None:
            return value
    return None


def get_s3_object_metadata(path: upath.UPath) -> S3ObjectMetadata | None:
    """Return object metadata without reading the annotation's contents.

    ``None`` means the object has no ETag and cannot be safely deduplicated.
    """
    info = path.stat()
    if not isinstance(info, Mapping):
        return None
    etag = normalize_etag(_metadata_value(info, "ETag", "etag"))
    if etag is None:
        return None

    size = _metadata_value(info, "size", "Size", "ContentLength")
    last_modified = _metadata_value(
        info, "LastModified", "last_modified", "mtime", "updated"
    )
    if isinstance(last_modified, datetime.datetime):
        last_modified = last_modified.isoformat()
    elif last_modified is None:
        last_modified = "unknown"
    else:
        last_modified = str(last_modified)

    return S3ObjectMetadata(
        uri=path.as_posix(),
        etag=etag,
        size=int(str(size)) if size is not None else 0,
        last_modified=last_modified,
    )
