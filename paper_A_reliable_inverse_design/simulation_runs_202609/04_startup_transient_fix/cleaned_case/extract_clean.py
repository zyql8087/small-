# Manual extraction for the cleaned-mesh validation case (not in manifest).
import odbAccess, sys, json, csv, os
odb = odbAccess.openOdb(path=r"F:/small++/paper_A_reliable_inverse_design/audits/m08_explicit_z27_20260925/cases/m3_class12_26_clean/solver/m08_m3_26_clean.odb", readOnly=True)
inst = list(odb.rootAssembly.instances.values())[0]
step = odb.steps["Step-1"]
outdir = r"F:/small++/paper_A_reliable_inverse_design/audits/m08_explicit_z27_20260925/cases/m3_class12_26_clean/results"
os.makedirs(outdir, exist_ok=True)
# drive reaction: sum RF3 over M05_ZDRIVE part set (or A_ZPOS fallback)
drv = inst.nodeSets["M05_ZDRIVE"] if "M05_ZDRIVE" in inst.nodeSets.keys() else odb.rootAssembly.nodeSets["A_ZPOS"]
if drv is None:
    drv = odb.rootAssembly.nodeSets["A_ZPOS"]
drive_labels = set(n.label for n in drv.nodes)
rows = []
energies = {}
for fr in step.frames:
    t = fr.frameValue
    u = fr.fieldOutputs["U"].getSubset(region=drv)
    u3 = sum(v.data[2] for v in u.values)
    rf3 = 0.0
    if "RF" in fr.fieldOutputs:
        rf = fr.fieldOutputs["RF"].getSubset(region=drv)
        rf3 = sum(v.data[2] for v in rf.values)
    eps = abs(u3) / 40.0
    rows.append((t, u3, rf3, eps))
    for q in ("ALLIE", "ALLKE", "ALLAE", "ALLPD"):
        if q in fr.fieldOutputs:
            energies.setdefault(q, []).append((t, fr.fieldOutputs[q].values[0].data))
with open(os.path.join(outdir, "curve.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["step_time", "u3_drive_mm", "RF3_total_N", "eps_engineering"])
    for r in rows:
        w.writerow(["%.9f" % r[0], "%.9f" % r[1], "%.9f" % r[2], "%.9f" % r[3]])
with open(os.path.join(outdir, "history_energies.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["quantity", "time", "value_Nmm"])
    for q, arr in energies.items():
        for t, v in arr:
            w.writerow([q, "%.9f" % t, "%.9f" % v])
print("EXTRACT_OK frames=%d last_eps=%.5f last_RF=%.4f" % (len(rows), rows[-1][3], rows[-1][2]))
odb.close()
