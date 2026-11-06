"""Normalize annotation JSONs and rebuild + retrigger their IBL manifest assets.

Usage: renormalize_ibl_assets.py [--dry-run] subject ...
Env: REUSE (default 0), MAX_IN_FLIGHT (default 3) - trigger capsule params.

Per subject:
1. normalize the source annotation JSON in S3 (scripts/normalize_ng_json.py) -> new ETag / last-modified
2. take the files from the subject's latest CO manifest asset (column "CO asset (B4)" in
   ibl-orchestration/ibl_tracking.md), so earlier fixes (e.g. restitched sources, surface channels) are kept
3. normalize the staged JSON, rename it with the new last-modified timestamp, update `probe_file` in the manifest
4. stage to probe_annotations/<subject>/<new etag>/asset/, create the CO asset, trigger B5
5. update the ETag, CO asset, trigger run and notes columns in ibl_tracking.md
"""
import datetime, json, os, pathlib, re, subprocess, sys, tempfile, time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import normalize_ng_json as ng
import npc_lims.metadata.codeocean_utils as u
from codeocean.data_asset import DataAssetParams, Source, AWSS3Source
from codeocean.computation import RunParams, Param

BUCKET = "aind-scratch-data"
PA = "dynamic-routing/ibl_conv/probe_annotations"
SRC = "dynamic-routing/annotated_neuroglancer_jsons"
TRIGGER = "d89073c0-e1ff-44e8-8ca1-4130b4964fba"
WORKER = "cba3374d-cd09-4297-a17d-152c371e117d"
TRACK = pathlib.Path("ibl-orchestration/ibl_tracking.md")
REUSE = os.environ.get("REUSE", "0")
MAX_IN_FLIGHT = os.environ.get("MAX_IN_FLIGHT", "3")
c = u.get_codeocean_client()


def aws(*args, capture=False):
    r = subprocess.run(["aws", *args], check=True, capture_output=capture, text=True)
    return r.stdout if capture else None


def head(key):
    h = json.loads(aws("s3api", "head-object", "--bucket", BUCKET, "--key", key, capture=True))
    lm = datetime.datetime.fromisoformat(h["LastModified"]).astimezone(datetime.timezone.utc)
    return h["ETag"].strip('"')[:16], lm


def track_row(s):
    for i, line in enumerate(TRACK.read_text().split("\n")):
        cells = line.split("|")
        if line.startswith(f"| {s} |") and len(cells) > 10 and "ecephys_" not in line:
            return i, cells
    raise ValueError(f"{s} not in {TRACK}")


def rebuild(s, dry):
    _, cells = track_row(s)
    assets = re.findall(r"`([0-9a-f-]{36})`", cells[6])
    if not assets:
        print(s, "SKIP: no manifest asset in tracking doc (build one first)"); return
    old = c.data_assets.get_data_asset(assets[-1])
    old_prefix = old.source_bucket.prefix.rstrip("/")

    src_key = f"{SRC}/{s}_annotated.json"
    ng.main((["--dry-run"] if dry else []) + [f"s3://{BUCKET}/{src_key}"])
    etag, lm = head(src_key)
    if dry:
        print(s, f"would restage {old.name} ({old_prefix}) -> {PA}/{s}/{etag}/asset"); return

    d = pathlib.Path(tempfile.mkdtemp())
    aws("s3", "cp", f"s3://{BUCKET}/{old_prefix}/", str(d), "--recursive", "--quiet")
    (j_old,) = d.glob("SmartSPIM_*.json")
    (m,) = d.glob("*_data_converter_manifest.csv")
    ng.main([str(j_old)])
    stem = re.sub(r"_neuroglancer-state_.*", "", j_old.stem) + f"_neuroglancer-state_{lm:%Y-%m-%d_%H-%M-%S}"
    j_new = j_old.rename(d / f"{stem}.json")
    text = m.read_text()
    assert j_old.stem in text, f"{j_old.stem} not in manifest"
    m.write_text(text.replace(j_old.stem, stem))

    dst = f"{PA}/{s}/{etag}"
    aws("s3", "cp", f"s3://{BUCKET}/{src_key}", f"s3://{BUCKET}/{dst}/{s}_annotated.json", "--quiet")
    aws("s3", "cp", str(d), f"s3://{BUCKET}/{dst}/asset/", "--recursive", "--quiet")
    today = time.strftime("%Y-%m-%d", time.gmtime())
    name = f"ibl_manifest_{s}_{today}"
    asset = c.data_assets.create_data_asset(DataAssetParams(
        name=name, mount=name, tags=["ibl", s, "manifest"],
        source=Source(aws=AWSS3Source(bucket=BUCKET, prefix=f"{dst}/asset", keep_on_external_storage=False)),
        custom_metadata={"data level": "derived data", "experiment type": "ecephys", "institution": "AIND",
                         "modality": "extracellular electrophysiology", "subject id": s, "subject species": "Mus musculus"}))
    while (st := str(c.data_assets.get_data_asset(asset.id).state).split(".")[-1].lower()) != "ready":
        if st == "failed": raise RuntimeError(f"{s}: asset {asset.id} failed")
        time.sleep(5)
    comp = c.computations.run_capsule(RunParams(capsule_id=TRIGGER, named_parameters=[
        Param(param_name="probe-annotations-asset-id", value=asset.id),
        Param(param_name="compute-capsule-id", value=WORKER),
        Param(param_name="cleanup-on-failure", value="0"),
        Param(param_name="reuse-intermediates", value=REUSE),
        Param(param_name="max-in-flight", value=MAX_IN_FLIGHT)]))

    lines = TRACK.read_text().split("\n")
    i, cells = track_row(s)
    cells[2] = f" {lm:%Y-%m-%d %H:%M} "
    cells[3] = f" `{etag}` "
    cells[6] = cells[6].rstrip() + f", `{asset.id}` ({today}, normalized dims) "
    cells[7] = cells[7].rstrip() + f", `{comp.id}` ({today} normalized dims, reuse={REUSE}, max-in-flight={MAX_IN_FLIGHT}) "
    cells[-2] = cells[-2].rstrip() + f" {today}: list-form dimensions normalized (preprocessing skipped all probes); restaged from `{old_prefix.split('/')[-2]}` in `{etag}/`. "
    lines[i] = "|".join(cells)
    TRACK.write_text("\n".join(lines))
    print(s, "asset", asset.id, "computation", comp.id, flush=True)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    for s in (a for a in sys.argv[1:] if not a.startswith("--")):
        rebuild(s, dry)
        time.sleep(2)  # stagger CO API calls
