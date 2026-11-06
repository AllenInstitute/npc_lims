"""Normalize annotated neuroglancer JSONs so aind-ibl-ephys-alignment-preprocessing can read them.

Some neuroglancer versions save coordinate spaces as a list of objects:
    "dimensions": [{"name": "z", "scale": [2e-06, "m"]}, ...]
The preprocessing reader only accepts the canonical dict form:
    "dimensions": {"z": [2e-06, "m"], ...}
This rewrites `dimensions`, `outputDimensions`, `inputDimensions` and `localDimensions` (anywhere in the
JSON) to the dict form. Other content is unchanged. Files that are already normalized are not touched.

Run this before the manifest asset is created (ibl-orchestration/ibl.md, step B4).

Usage: normalize_ng_json.py [--dry-run] <subject_id | s3://... | local path> ...
Subject IDs resolve to s3://aind-scratch-data/dynamic-routing/annotated_neuroglancer_jsons/<id>_annotated.json.
Files are overwritten in place (the S3 bucket is versioned, so the previous version is kept).
"""
import json, re, subprocess, sys, tempfile, pathlib

ROOT = "s3://aind-scratch-data/dynamic-routing/annotated_neuroglancer_jsons"
DIM_KEYS = {"dimensions", "outputDimensions", "inputDimensions", "localDimensions"}


def to_dict(dims: list, where: str) -> dict:
    out = {}
    for d in dims:
        if not isinstance(d, dict) or "name" not in d or "scale" not in d:
            raise ValueError(f"{where}: unrecognized dimension entry {d!r}")
        extra = set(d) - {"name", "scale", "unit"}
        if extra:
            raise ValueError(f"{where}: unsupported keys {extra} in {d!r}")
        scale = d["scale"]
        if not isinstance(scale, list):  # {"name", "scale": float, "unit": str}
            scale = [scale, d.get("unit", "")]
        if d["name"] in out:
            raise ValueError(f"{where}: duplicate dimension {d['name']!r}")
        out[d["name"]] = scale
    return out


def normalize(obj, path: str = "") -> int:
    """Convert list-form dimensions in place; return number of conversions."""
    n = 0
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in DIM_KEYS and isinstance(v, list):
                obj[k] = to_dict(v, f"{path}/{k}")
                n += 1
            else:
                n += normalize(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            n += normalize(v, f"{path}[{i}]")
    return n


def main(args: list[str]) -> None:
    dry = "--dry-run" in args
    for target in (a for a in args if not a.startswith("--")):
        if re.fullmatch(r"\d{6}", target):
            target = f"{ROOT}/{target}_annotated.json"
        is_s3 = target.startswith("s3://")
        local = pathlib.Path(tempfile.mkdtemp()) / "ng.json" if is_s3 else pathlib.Path(target)
        if is_s3:
            subprocess.run(["aws", "s3", "cp", target, str(local), "--quiet"], check=True)
        data = json.loads(local.read_text())
        n = normalize(data)
        if not n:
            print(target, "already normalized")
            continue
        print(target, f"converted {n} dimension lists", "(dry run)" if dry else "")
        if dry:
            continue
        local.write_text(json.dumps(data, indent=2) + "\n")
        if is_s3:
            subprocess.run(["aws", "s3", "cp", str(local), target, "--quiet", "--content-type", "application/json"], check=True)


if __name__ == "__main__":
    main(sys.argv[1:])
