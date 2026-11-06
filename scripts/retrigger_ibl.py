"""Re-launch B5 trigger for given subjects; appends new computation id to the Trigger run column."""
import os, re, sys, time, pathlib
from codeocean.computation import RunParams, Param
import npc_lims.metadata.codeocean_utils as u
doc = pathlib.Path("ibl-orchestration/ibl_tracking.md")
c = u.get_codeocean_client()
for subject in sys.argv[1:]:
    lines = doc.read_text().split("\n")
    for i, line in enumerate(lines):
        cells = line.split("|")
        if line.startswith(f"| {subject} |") and len(cells) > 8 and "`" in cells[6]:
            asset = re.findall(r"`([0-9a-f-]{36})`", cells[6])[-1]
            comp = c.computations.run_capsule(RunParams(capsule_id="d89073c0-e1ff-44e8-8ca1-4130b4964fba", named_parameters=[
                Param(param_name="probe-annotations-asset-id", value=asset),
                Param(param_name="compute-capsule-id", value="cba3374d-cd09-4297-a17d-152c371e117d"),
                Param(param_name="cleanup-on-failure", value="0"),
                Param(param_name="reuse-intermediates", value=os.environ.get("REUSE", "1")),
                Param(param_name="max-in-flight", value=os.environ.get("MAX_IN_FLIGHT", "1")),
            ]))
            cells[7] = cells[7].rstrip() + f", `{comp.id}` (retrigger, worker cba3374d) "
            lines[i] = "|".join(cells)
            doc.write_text("\n".join(lines))
            print(subject, comp.id, flush=True)
    time.sleep(1)
