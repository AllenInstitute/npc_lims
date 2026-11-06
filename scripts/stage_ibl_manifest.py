"""Build + stage an IBL manifest for one subject, create the CO "probe annotations" asset (B4) and trigger B5.

Usage: stage_ibl_manifest.py [--force] [--apply] <subject_id>
  --force  skip annotation layers whose session has no raw/sorted asset yet (instead of failing)
  --apply  stage to S3, create CO asset, launch trigger capsule, record in ibl-orchestration/ibl_tracking.md
Run scripts/normalize_ng_json.py <subject_id> first (ibl-orchestration/ibl.md, B4).
"""
import csv, datetime, io, json, pathlib, re, subprocess, sys, tempfile, time
import npc_lims.ibl as ibl
import npc_lims.metadata.codeocean_utils as u

args = sys.argv[1:]
force, apply = "--force" in args, "--apply" in args
(s,) = [a for a in args if not a.startswith("--")]
SRC = f"s3://aind-scratch-data/dynamic-routing/annotated_neuroglancer_jsons/{s}_annotated.json"
TRACK = pathlib.Path("ibl-orchestration/ibl_tracking.md")
TRIGGER, WORKER = "d89073c0-e1ff-44e8-8ca1-4130b4964fba", "cba3374d-cd09-4297-a17d-152c371e117d"

head = json.loads(subprocess.run(["aws", "s3api", "head-object", "--bucket", "aind-scratch-data", "--key", SRC.split("aind-scratch-data/")[1]], capture_output=True, check=True).stdout)
etag = head["ETag"].strip('"')[:16]
mtime = datetime.datetime.fromisoformat(head["LastModified"]).astimezone(datetime.timezone.utc)
d = pathlib.Path(tempfile.mkdtemp())
src = d / f"{s}_annotated.json"
subprocess.run(["aws", "s3", "cp", SRC, str(src), "--quiet"], check=True)

state = json.loads(src.read_text())
stitched = {m.group(1) for l in state["layers"] if l.get("type") == "image" for m in [re.search(r"aind-open-data/([^/]+_stitched_[^/]+)/", str(l.get("source")))] if m}
assert len(stitched) == 1, stitched
acq = re.search(rf"{s}_(\d{{4}}-\d{{2}}-\d{{2}}_\d{{2}}-\d{{2}}-\d{{2}})_stitched", stitched.pop()).group(1)
stem = f"SmartSPIM_{s}_{acq}_neuroglancer-state_{mtime:%Y-%m-%d_%H-%M-%S}"

build = ibl.build_manifest(src, skip_missing_sessions=force)
rows = sorted(build.records, key=lambda r: (r["sorted_recording"], r["probe_name"]))
cols = ["index", "mouseid", "sorted_recording", "probe_file", "probe_name", "probe_shank", "probe_id", "surface_finding", "annotation_format"]
out = io.StringIO()
w = csv.writer(out, lineterminator="\n")
w.writerow(cols)
for i, r in enumerate(rows):
    w.writerow([i, r["mouseid"], r["sorted_recording"], stem, r["probe_name"], r.get("probe_shank") or "", r["probe_id"], r.get("surface_finding") or "", r.get("annotation_format") or "json"])
print(out.getvalue())
print("skipped:", *build.skipped, sep="\n  ")
if not apply:
    sys.exit()

asset_dir = d / "asset"
asset_dir.mkdir()
src.rename(asset_dir / f"{stem}.json")
(asset_dir / f"{s}_data_converter_manifest.csv").write_text(out.getvalue())
prefix = f"dynamic-routing/ibl_conv/probe_annotations/{s}/{etag}/asset"
subprocess.run(["aws", "s3", "cp", str(asset_dir), f"s3://aind-scratch-data/{prefix}/", "--recursive", "--quiet"], check=True)

from codeocean.data_asset import DataAssetParams, Source, AWSS3Source
from codeocean.computation import RunParams, Param
c = u.get_codeocean_client()
today = time.strftime("%Y-%m-%d", time.gmtime())
name = f"ibl_manifest_{s}_{today}"
asset = c.data_assets.create_data_asset(DataAssetParams(name=name, mount=name, tags=["ibl", s, "manifest"],
    source=Source(aws=AWSS3Source(bucket="aind-scratch-data", prefix=prefix, keep_on_external_storage=False)),
    custom_metadata={"data level": "derived data", "experiment type": "ecephys", "institution": "AIND", "modality": "extracellular electrophysiology", "subject id": s, "subject species": "Mus musculus"}))
print("asset", asset.id, flush=True)
while (st := str(c.data_assets.get_data_asset(asset.id).state).split(".")[-1].lower()) != "ready":
    assert st != "failed", st
    time.sleep(5)
comp = c.computations.run_capsule(RunParams(capsule_id=TRIGGER, named_parameters=[
    Param(param_name="probe-annotations-asset-id", value=asset.id), Param(param_name="compute-capsule-id", value=WORKER),
    Param(param_name="cleanup-on-failure", value="0"), Param(param_name="reuse-intermediates", value="1"), Param(param_name="max-in-flight", value="4")]))
print("computation", comp.id, flush=True)

lines = TRACK.read_text().split("\n")
for i, l in enumerate(lines):
    cells = l.split("|")
    if l.startswith(f"| {s} |") and len(cells) == 12:  # main table only
        cells[4], cells[5] = " yes ", " yes "
        cells[6] = f" `{asset.id}` "
        cells[7] = f" `{comp.id}` (worker cba3374d, reuse=1, max-in-flight=4) "
        skipped = ", ".join(f"`{x.split(':')[0].strip(chr(39))}`" for x in build.skipped)
        if build.skipped:
            cells[-2] = cells[-2].rstrip() + f" {today}: built with --force; layers omitted: {skipped} "
        lines[i] = "|".join(cells)
TRACK.write_text("\n".join(lines))
