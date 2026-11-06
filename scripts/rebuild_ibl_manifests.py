"""Rebuild IBL manifests against current assets; with --apply stage + create CO assets + trigger B5.

Usage: rebuild_ibl_manifests.py [--apply] [subject ...]
Reuses the latest staged annotation JSON (keeps restitch fixes). Only subjects whose rebuilt rows differ are touched.
"""
import csv, io, re, subprocess, sys, tempfile, pathlib, time
import npc_lims.ibl as ibl
import npc_lims.metadata.codeocean_utils as u
c = u.get_codeocean_client()
TRACK = pathlib.Path("ibl-orchestration/ibl_tracking.md")
B = "s3://aind-scratch-data/dynamic-routing/ibl_conv/probe_annotations"
KEY = ("sorted_recording", "probe_name", "probe_id", "surface_finding")
apply = "--apply" in sys.argv
only = [a for a in sys.argv[1:] if not a.startswith("--")]

def tracked():
    for l in TRACK.read_text().splitlines():
        cells = [x.strip() for x in l.strip().strip("|").split("|")]
        if len(cells) >= 9 and re.fullmatch(r"\d{6}", cells[0]) and "ecephys_" not in l:
            ids = re.findall(r"`([0-9a-f-]{36})`", cells[5])
            if ids and (not only or cells[0] in only):
                yield cells[0], ids[-1]

def norm(rows):
    return sorted(tuple((r.get(k) or "") for k in KEY) for r in rows)

changed = {}
for s, aid in tracked():
    a = c.data_assets.get_data_asset(aid)
    prefix = a.source_bucket.prefix.rstrip("/")
    d = pathlib.Path(tempfile.mkdtemp())
    subprocess.run(["aws", "s3", "cp", f"s3://aind-scratch-data/{prefix}/", str(d), "--recursive", "--quiet"], check=True)
    j = next(d.glob("SmartSPIM_*.json"))
    old = list(csv.DictReader(open(next(d.glob("*manifest.csv")))))
    try:
        new = ibl.build_manifest(j).records
    except Exception as e:
        print(s, "BUILD FAILED", str(e)[:150]); continue
    if norm(old) != norm(new):
        so = {r["sorted_recording"]: r["surface_finding"] for r in old}
        sn = {r["sorted_recording"]: r["surface_finding"] for r in new}
        print(s, "CHANGED", f"rows {len(old)}->{len(new)}", {k[-30:]: (so.get(k), v) for k, v in sn.items() if so.get(k) != v}, flush=True)
        changed[s] = (prefix, d, j, new)
    else:
        print(s, "same", flush=True)
print("changed:", " ".join(changed))

if apply:
    from codeocean.data_asset import DataAssetParams, Source, AWSS3Source
    from codeocean.computation import RunParams, Param
    today = time.strftime("%Y-%m-%d", time.gmtime())
    WORKER = "cba3374d-cd09-4297-a17d-152c371e117d"  # per ibl-orchestration/ibl.md
    lines = TRACK.read_text().split("\n")
    for s, (prefix, d, j, new) in changed.items():
        etag = prefix.split("/")[-2].removesuffix("_surface")
        rows = sorted(new, key=lambda r: (r["sorted_recording"], r["probe_name"]))
        out = io.StringIO()
        w = csv.writer(out, lineterminator="\n")
        cols = ["index", "mouseid", "sorted_recording", "probe_file", "probe_name", "probe_shank", "probe_id", "surface_finding", "annotation_format"]
        w.writerow(cols)
        for i, r in enumerate(rows):
            w.writerow([i, r["mouseid"], r["sorted_recording"], r["probe_file"], r["probe_name"], r.get("probe_shank") or "", r["probe_id"], r.get("surface_finding") or "", r.get("annotation_format") or "json"])
        (d / f"{s}_data_converter_manifest.csv").write_text(out.getvalue())
        for f in d.glob("*manifest.csv"):
            if f.name != f"{s}_data_converter_manifest.csv": f.unlink()
        dst_prefix = f"dynamic-routing/ibl_conv/probe_annotations/{s}/{etag}_surface2"
        subprocess.run(["aws", "s3", "cp", str(d), f"s3://aind-scratch-data/{dst_prefix}/asset/", "--recursive", "--quiet"], check=True)
        name = f"ibl_manifest_{s}_{today}"
        asset = c.data_assets.create_data_asset(DataAssetParams(name=name, mount=name, tags=["ibl", s, "manifest"],
            source=Source(aws=AWSS3Source(bucket="aind-scratch-data", prefix=f"{dst_prefix}/asset", keep_on_external_storage=False)),
            custom_metadata={"data level": "derived data", "experiment type": "ecephys", "institution": "AIND", "modality": "extracellular electrophysiology", "subject id": s, "subject species": "Mus musculus"}))
        while str(c.data_assets.get_data_asset(asset.id).state).split(".")[-1].lower() != "ready":
            time.sleep(5)
        comp = c.computations.run_capsule(RunParams(capsule_id="d89073c0-e1ff-44e8-8ca1-4130b4964fba", named_parameters=[
            Param(param_name="probe-annotations-asset-id", value=asset.id), Param(param_name="compute-capsule-id", value=WORKER),
            Param(param_name="cleanup-on-failure", value="0"), Param(param_name="reuse-intermediates", value="1"), Param(param_name="max-in-flight", value="1")]))
        for i, l in enumerate(lines):
            cells = l.split("|")
            if l.startswith(f"| {s} |") and len(cells) > 8 and "`" in cells[6]:
                cells[6] = cells[6].rstrip() + f", `{asset.id}` ({today}, surface channels updated) "
                cells[7] = cells[7].rstrip() + f", `{comp.id}` ({today} surface retrigger, worker cba3374d, reuse=1, max-in-flight=1) "
                cells[-2] = cells[-2].rstrip() + f" {today}: manifest rebuilt with new surface assets in `{etag}_surface2/` "
                lines[i] = "|".join(cells)
        TRACK.write_text("\n".join(lines))
        print(s, "asset", asset.id, "computation", comp.id, flush=True)
