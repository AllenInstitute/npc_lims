"""Re-launch B5 trigger for given subjects; appends new computation id to the Trigger run column."""
import re, sys, time, pathlib
from codeocean.computation import RunParams, Param
import npc_lims.metadata.codeocean_utils as u
doc = pathlib.Path("docs/ibl_tracking.md")
c = u.get_codeocean_client()
for subject in sys.argv[1:]:
    lines = doc.read_text().split("\n")
    for i, line in enumerate(lines):
        cells = line.split("|")
        if line.startswith(f"| {subject} |") and len(cells) > 8 and "`" in cells[6]:
            asset = cells[6].strip().strip("`")
            comp = c.computations.run_capsule(RunParams(capsule_id="d89073c0-e1ff-44e8-8ca1-4130b4964fba", named_parameters=[
                Param(param_name="probe-annotations-asset-id", value=asset),
                Param(param_name="compute-capsule-id", value="09e00815-6730-479c-8b50-355bffb0b2b9"),
                Param(param_name="cleanup-on-failure", value="0"),
                Param(param_name="reuse-intermediates", value="1"),
                Param(param_name="max-in-flight", value="1"),
            ]))
            cells[7] = cells[7].rstrip() + f", `{comp.id}` (retrigger) "
            lines[i] = "|".join(cells)
            doc.write_text("\n".join(lines))
            print(subject, comp.id, flush=True)
    time.sleep(1)
