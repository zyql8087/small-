# Per-node history RF3/U3: 5803 nodes x 21 frames. Sum RF3, take max-|U3| as drive displacement.
import odbAccess, csv, os
odb = odbAccess.openOdb(path=r"F:/small++/paper_A_reliable_inverse_design/audits/m08_explicit_z27_20260925/cases/m3_class12_26_clean/solver/m08_m3_26_clean.odb", readOnly=True)
step = odb.steps["Step-1"]
hr = step.historyRegions
times = None; rf_sums = None; u3_vals = None
n_nodes = 0
for k, v in hr.items():
    if "RF3" not in v.historyOutputs: continue
    n_nodes += 1
    ro = v.historyOutputs["RF3"].data
    uo = v.historyOutputs["U3"].data
    if times is None:
        times = [x[0] for x in ro]
        rf_sums = [0.0]*len(times)
        u3_vals = [0.0]*len(times)
    if len(ro) == len(times):
        for i, x in enumerate(ro):
            rf_sums[i] += x[1]
        for i, x in enumerate(uo):
            u3_vals[i] = max(u3_vals[i], abs(x[1]))
print("history nodes summed:", n_nodes)
outdir = r"F:/small++/paper_A_reliable_inverse_design/audits/m08_explicit_z27_20260925/cases/m3_class12_26_clean/results"
os.makedirs(outdir, exist_ok=True)
with open(os.path.join(outdir, "curve.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["time", "u3_drive_mm", "RF3_total_N", "eps_engineering"])
    for t, u3, rf in zip(times, u3_vals, rf_sums):
        w.writerow(["%.9f" % t, "%.9f" % u3, "%.9f" % rf, "%.9f" % (abs(u3)/40.0)])
print("EXTRACT_OK frames=%d last: u3=%.4f RF=%.4f eps=%.5f" % (len(times), u3_vals[-1], rf_sums[-1], abs(u3_vals[-1])/40.0))
# energies from whole-model history if present
en = {}
for k, v in hr.items():
    if k.startswith("Assemble") or "ALL" in str(v.historyOutputs.keys()[:1]) or "ALLIE" in v.historyOutputs:
        for q in ("ALLIE","ALLKE","ALLAE","ALLPD"):
            if q in v.historyOutputs:
                en[q] = v.historyOutputs[q].data
with open(os.path.join(outdir, "history_energies.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["quantity","time","value_Nmm"])
    for q, data in en.items():
        for t, val in data:
            w.writerow([q, "%.9f" % t, "%.9f" % val])
print("energies:", list(en.keys()))
odb.close()
