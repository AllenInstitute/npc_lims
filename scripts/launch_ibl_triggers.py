"""Launch IBL B5 trigger capsule for each tracked subject with a CO asset and no trigger run yet.
Max 3 in flight; records computation ids into docs/ibl_tracking.md as they launch."""
import re, time, pathlib
from codeocean.computation import RunParams, PipelineProcessParams, Param, ComputationState
import npc_lims.metadata.codeocean_utils as u

TRIGGER = "d89073c0-e1ff-44e8-8ca1-4130b4964fba"
WORKER = "09e00815-6730-479c-8b50-355bffb0b2b9"
MAX_CONCURRENT = 1000  # user override: launch all at once
doc = pathlib.Path("docs/ibl_tracking.md")
c = u.get_codeocean_client()

def rows():
    out = []
    for line in doc.read_text().splitlines():
        cells = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(cells) >= 9 and re.fullmatch(r"\d{6}", cells[0]) and cells[5].startswith("`") and cells[6] == "":
            out.append((cells[0], cells[5].strip("`")))
    return out

def record(subject, comp_id):
    lines = doc.read_text().split("\n")
    for i, line in enumerate(lines):
        if line.startswith(f"| {subject} |") and "`" in line.split("|")[6]:
            cells = line.split("|")
            cells[7] = f" `{comp_id}` "
            lines[i] = "|".join(cells)
    doc.write_text("\n".join(lines))

running = {}
def active():
    for s, cid in list(running.items()):
        st = c.computations.get_computation(cid).state
        if st in (ComputationState.Completed, ComputationState.Failed):
            print(f"{s} {cid} {st}", flush=True); del running[s]
    return len(running)

for subject, asset in rows():
    if subject in running: continue
    while active() >= MAX_CONCURRENT:
        time.sleep(60)
    comp = c.computations.run_capsule(RunParams(capsule_id=TRIGGER, named_parameters=[
        Param(param_name="probe-annotations-asset-id", value=asset),
        Param(param_name="compute-capsule-id", value=WORKER),
        Param(param_name="cleanup-on-failure", value="0"),
        Param(param_name="reuse-intermediates", value="1"),
        Param(param_name="max-in-flight", value="1"),
    ]))
    running[subject] = comp.id
    record(subject, comp.id)
    print(f"LAUNCHED {subject} asset={asset} computation={comp.id}", flush=True)
    time.sleep(1)
print("DONE")
