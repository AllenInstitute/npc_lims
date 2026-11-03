"""Rewrite the stitched asset name in a staged IBL manifest JSON, stage it, create a new CO manifest asset, trigger B5."""
import re, subprocess, tempfile, pathlib, sys
from codeocean.data_asset import DataAssetParams, Source, AWSS3Source, Target
from codeocean.computation import RunParams, Param
import npc_lims.metadata.codeocean_utils as u
c = u.get_codeocean_client()
B = "s3://aind-scratch-data/dynamic-routing/ibl_conv/probe_annotations"
DATE = "2026-10-24"
FIX = {  # subject: (etag, old stitched, new stitched)
 "822061": ("e3cf8fa12557efec", "SmartSPIM_822061_2026-02-17_14-46-20_stitched_2026-03-17_10-14-58", "SmartSPIM_822061_2026-02-17_14-46-20_stitched_2026-04-24_03-38-35"),
 "831994": ("064d40b116f72b23", "SmartSPIM_831994_2026-02-17_10-45-50_stitched_2026-03-17_10-00-26", "SmartSPIM_831994_2026-02-17_10-45-50_stitched_2026-04-24_23-43-37"),
 "834408": ("ee1d8d5c6168de10", "SmartSPIM_834408_2026-02-16_13-42-28_stitched_2026-03-17_09-46-36", "SmartSPIM_834408_2026-02-16_13-42-28_stitched_2026-04-24_02-13-01"),
 "841308": ("f9507aa99017fcb8", "SmartSPIM_841308_2026-06-03_18-15-22_stitched_2026-06-05_09-48-35", "SmartSPIM_841308_2026-06-03_18-15-22_stitched_2026-06-10_07-38-10"),
}
for s, (etag, old, new) in FIX.items():
    src = f"{B}/{s}/{etag}/asset/"
    dst = f"{B}/{s}/{etag}_restitched/asset/"
    d = pathlib.Path(tempfile.mkdtemp())
    subprocess.run(["aws", "s3", "cp", src, str(d), "--recursive", "--quiet"], check=True)
    j = next(d.glob("SmartSPIM_*.json"))
    t = j.read_text(); n = t.count(old); assert n > 0
    j.write_text(t.replace(old, new))
    subprocess.run(["aws", "s3", "cp", str(d), dst, "--recursive", "--quiet"], check=True)
    name = f"ibl_manifest_{s}_{DATE}"
    asset = c.data_assets.create_data_asset(DataAssetParams(
        name=name, mount=name, tags=["ibl", s, "manifest"],
        source=Source(aws=AWSS3Source(bucket="aind-scratch-data", prefix=f"dynamic-routing/ibl_conv/probe_annotations/{s}/{etag}_restitched/asset", keep_on_external_storage=False)),
        custom_metadata={"data level": "derived data", "experiment type": "ecephys", "institution": "AIND", "modality": "extracellular electrophysiology", "subject id": s, "subject species": "Mus musculus"}))
    print(s, "replaced", n, "refs; asset", asset.id, flush=True)
