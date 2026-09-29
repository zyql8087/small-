# -*- coding: utf-8 -*-
"""M08 per-case solve-result processing + extraction (AFTER termination).

1. status from real termination evidence:
   - .sta contains 'THE ANALYSIS HAS COMPLETED SUCCESSFULLY' -> completed
   - .log failure markers / .dat ***ERROR -> solver_error (signature kept)
   - otherwise -> unknown
2. abaqus python extract_odb.py (M05 audited script; read-only ODB export):
   NPZ + sidecar with U field, S/SENER element fields, per-node drive
   histories (RF3/U3 on M05_ZDRIVE), ALL* energies. Status arg passed
   empty because the M05 log marker set is Standard-specific; m08 status
   is recorded in results/solve_result.json from step 1 evidence.
3. post-process (Anaconda python): curve.csv, history_energies.csv,
   energy_ratios.json (gate: max ALLKE/ALLIE and ALLAE/ALLIE <= 5%),
   mass_scaling.json (greps), figures, solve_result.json.

Usage: python m08_extract_case.py <case_id>
"""
import csv
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
M05 = ("F:/small++/paper_A_reliable_inverse_design/"
       "audits/m05_small_mechanism_pilot_20260919/scripts")
ABAQUS_BAT = r"F:\SIMULIA\Commands\abaqus.bat"
H0 = 40.0
A0 = 1600.0

FAILURE_MARKERS = ("has not been completed", "exited with an error",
                   "analysis aborted", "aborted", "exited with a error")


def sh(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, **kw)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_status(solver, job):
    sta_p = os.path.join(solver, job + ".sta")
    log_p = os.path.join(solver, "solve.log")
    dat_p = os.path.join(solver, job + ".dat")
    msg_p = os.path.join(solver, job + ".msg")
    sta = open(sta_p, encoding="utf-8", errors="replace").read() \
        if os.path.isfile(sta_p) else ""
    log = open(log_p, encoding="utf-8", errors="replace").read() \
        if os.path.isfile(log_p) else ""
    dat = open(dat_p, encoding="utf-8", errors="replace").read() \
        if os.path.isfile(dat_p) else ""
    msg = open(msg_p, encoding="utf-8", errors="replace").read() \
        if os.path.isfile(msg_p) else ""
    sigs = []
    for blob in (dat, sta, msg):
        for ln in blob.splitlines():
            if "***ERROR" in ln:
                t = re.sub(r"\s+", " ", ln.split("***ERROR", 1)[1]
                           .lstrip(": ").strip())[:90]
                if t and t not in sigs:
                    sigs.append(t)
    log_fail = [m for m in FAILURE_MARKERS if m in log.lower()]
    if sigs or log_fail:
        status = "solver_error"
        # deadline-window graceful termination (env set by the scheduler at
        # the 12:00 hard stop) is a distinct, planned category
        if os.environ.get("M08_DEADLINE_TERMINATE") == "1" and any(
                "external request" in s for s in sigs):
            status = "deadline_terminated"
    elif "THE ANALYSIS HAS COMPLETED SUCCESSFULLY" in sta:
        status = "completed"
    else:
        status = "unknown_no_termination_evidence"
    if log_fail:
        sigs.append("log_markers: " + "; ".join(sorted(set(log_fail))))
    sta_tail = [ln for ln in sta.splitlines() if ln.strip()][-3:]
    return {"status": status, "error_signature": sigs[:5],
            "sta_tail": sta_tail, "sta_path": sta_p, "log_path": log_p,
            "sta_sha256": sha256(sta_p) if os.path.isfile(sta_p) else None,
            "log_sha256": sha256(log_p) if os.path.isfile(log_p) else None}


def mass_scaling_report(solver, job):
    """Grep mass-scaling evidence from .dat/.msg/.sta (explicit prints)."""
    out = {"grep_lines": []}
    for ext in (".dat", ".msg", ".sta"):
        p = os.path.join(solver, job + ext)
        if not os.path.isfile(p):
            continue
        with open(p, encoding="utf-8", errors="replace") as f:
            for i, ln in enumerate(f):
                if re.search(r"mass", ln, re.I) and not ln.strip().startswith("*"):
                    out["grep_lines"].append(f"{ext}:{i+1}: {ln.strip()[:160]}")
    out["grep_lines"] = out["grep_lines"][:40]
    return out


def main():
    case_id = sys.argv[1]
    row = {r["case_id"]: r for r in csv.DictReader(
        open(os.path.join(ROOT, "selection_manifest_m08.csv"),
             encoding="utf-8"))}[case_id]
    job = row["job_name"]
    solver = os.path.join(ROOT, "cases", case_id, "solver")
    results = os.path.join(ROOT, "cases", case_id, "results")
    os.makedirs(results, exist_ok=True)
    odb = os.path.join(solver, job + ".odb")

    ev = resolve_status(solver, job)
    print(f"{case_id}: status={ev['status']} sig={ev['error_signature']}",
          flush=True)

    npz = os.path.join(results, f"{case_id}_extract.npz")
    extracted = False
    if os.path.isfile(odb):
        comspec = os.environ.get("COMSPEC") or r"C:\Windows\System32\cmd.exe"
        # status arg empty: M05 marker set is Standard-specific; m08 status
        # recorded from .sta evidence in solve_result.json instead
        r = sh([comspec, "/c", ABAQUS_BAT, "python",
                os.path.join(M05, "extract_odb.py"), odb, npz, "z", "40",
                "PART-1-1", "M05_ZDRIVE", "M05_ZFIX", "",
                ev["log_path"]], cwd=results)
        extracted = (r.returncode == 0 and os.path.isfile(npz))
        print(f"{case_id}: extract_odb exit={r.returncode}", flush=True)
        if not extracted:
            ev["extraction"] = "FAILED"
    else:
        ev["extraction"] = "NO_ODB"

    ms = mass_scaling_report(solver, job)
    result = {"case_id": case_id, "job": job, **ev,
              "mass_scaling_grep": ms["grep_lines"]}
    if extracted:
        try:
            _postprocess(case_id, results, result, npz)
        except Exception as e:
            import traceback
            traceback.print_exc()
            result["postprocess_error"] = str(e)[:300]
    # judgment
    if ev["status"] == "deadline_terminated":
        result["judgment"] = "deadline_terminated"
    elif ev["status"] == "completed" and extracted:
        qs = result.get("energy_gate", {}).get("quasi_static", "MISSING")
        result["judgment"] = ("success" if qs == "PASS"
                              else "completed_quasi_static_failed")
    elif ev["status"] == "completed" and not extracted:
        result["judgment"] = "completed_extraction_failed"
    else:
        result["judgment"] = ev["status"]
    with open(os.path.join(results, "solve_result.json"), "w",
              encoding="utf-8") as f:
        json.dump(result, f, indent=1)
    print(f"{case_id}: JUDGMENT {result['judgment']}", flush=True)


def _postprocess(case_id, results, result, npz):
    data = np.load(npz, allow_pickle=True)
    sidecar = json.load(open(npz + ".json", encoding="utf-8"))
    hk = [str(k) for k in sidecar["history_keys"]]
    series = [(f"hist_{i}", k) for i, k in enumerate(hk)]
    rf3 = [(a, b) for a, b in series if b.endswith("|RF3")]
    u3 = [(a, b) for a, b in series if b.endswith("|U3")]
    alls = [(a, b) for a, b in series if "|ALL" in b]
    # curve: sum RF3 over drive nodes; U3 from the first U3 history
    # (an early fatal may leave only the t=0 point in every history)
    if rf3:
        t0 = data[rf3[0][0]][:, 0]
        rf_total = np.zeros(len(t0))
        for a, _ in rf3:
            arr = data[a]
            if arr.shape[0] != len(t0):
                continue
            rf_total = rf_total + arr[:, 1]
    else:
        t0 = np.array([0.0])
        rf_total = np.array([0.0])
    u3_ref = None
    for a, _ in u3:
        arr = data[a]
        if np.allclose(arr[:, 0], t0):
            u3_ref = arr[:, 1]
            break
    if u3_ref is None:
        # fallback: SMOOTH STEP analytic u3(t) = -10*(3s^2-2s^3), s=t/T
        s = t0 / 0.1
        u3_ref = -10.0 * (3 * s**2 - 2 * s**3)
        result["u3_source"] = "analytic_smoothstep_fallback"
    result["u3_source"] = result.get("u3_source", "history")
    with open(os.path.join(results, "curve.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["step_time", "u3_drive_mm", "RF3_total_N",
                    "eps_engineering", "sigma_nominal_MPa",
                    "n_drive_nodes"])
        for i in range(len(t0)):
            eps = abs(u3_ref[i]) / H0
            w.writerow([t0[i], u3_ref[i], rf_total[i], round(eps, 6),
                        rf_total[i] / A0, len(rf3)])
    # energies + gate (empty or single-point histories -> not evaluable)
    en = {}
    for a, b in alls:
        q = b.split("|")[-1]
        en[q] = data[a]
    with open(os.path.join(results, "history_energies.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["quantity", "time", "value_Nmm"])
        for q, arr in en.items():
            for t, v in arr:
                w.writerow([q, t, v])
    gate = {}
    if "ALLIE" in en and en["ALLIE"].shape[0] >= 2:
        allie = en["ALLIE"][:, 1]
        mask = np.abs(allie) > 1e-9
        for q, key in (("ALLKE", "ke_ratio_max"),
                       ("ALLAE", "ae_ratio_max"),
                       ("ALLPD", "pd_ratio_max")):
            if q in en:
                ratio = np.abs(en[q][mask, 1] / allie[mask])
                gate[key] = float(ratio.max())
                gate[key + "_at_time"] = float(en[q][mask, 1][ratio.argmax()])
            else:
                gate[key] = None
        gate["allie_peak_Nmm"] = float(np.abs(allie).max())
        gate["allke_peak_Nmm"] = float(np.abs(en["ALLKE"][:, 1]).max()) \
            if "ALLKE" in en else None
        gate["allae_peak_Nmm"] = float(np.abs(en["ALLAE"][:, 1]).max()) \
            if "ALLAE" in en else None
        gate["etotal_final_Nmm"] = float(en["ETOTAL"][-1, 1]) \
            if "ETOTAL" in en else None
        passed = (gate.get("ke_ratio_max") is not None
                  and gate.get("ae_ratio_max") is not None
                  and gate["ke_ratio_max"] <= 0.05
                  and gate["ae_ratio_max"] <= 0.05)
        gate["quasi_static"] = "PASS" if passed else "FAILED"
    else:
        gate["quasi_static"] = "NOT_EVALUABLE_no_energy_history"
    result["energy_gate"] = gate
    result["n_drive_nodes"] = len(rf3)
    result["final_step_time"] = float(t0[-1])
    result["final_u3_mm"] = float(u3_ref[-1]) if u3_ref is not None else None
    result["frames"] = len(t0)
    write_figures(case_id, results, data)


def write_figures(case_id, results, data):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig_dir = os.path.join(results, "figures")
    os.makedirs(fig_dir, exist_ok=True)
    coords = data["node_coords"]
    U = data["U"]
    avail = np.flatnonzero(data["U_frame_available"])
    # stress-strain overlay curve from histories
    try:
        c = np.genfromtxt(os.path.join(results, "curve.csv"), delimiter=",",
                          names=True)
        fig, ax = plt.subplots(figsize=(6, 4.5), dpi=130)
        ax.plot(c["eps_engineering"] * 100, c["sigma_nominal_MPa"], ".-")
        ax.set_xlabel("engineering strain (%)")
        ax.set_ylabel("nominal stress (MPa)")
        ax.set_title(f"{case_id} z-compression explicit")
        fig.tight_layout()
        fig.savefig(os.path.join(fig_dir, "curve.png"))
        plt.close(fig)
    except Exception as e:
        print("curve figure skipped:", e, flush=True)
    # deformed shapes initial/mid/end (subsampled scatter, true scale)
    if avail.size:
        for name, fi in (("initial", avail[0]),
                         ("mid", avail[len(avail) // 2]),
                         ("end", avail[-1])):
            disp = U[fi]
            deformed = coords + disp
            fig = plt.figure(figsize=(6, 5), dpi=120)
            ax = fig.add_subplot(111, projection="3d")
            mag = np.linalg.norm(disp, axis=1)
            ax.scatter(deformed[::4, 0], deformed[::4, 1], deformed[::4, 2],
                       s=0.2, c=mag[::4], cmap="viridis", linewidths=0)
            ax.set_title(f"{case_id} {name} frame {fi} (scale 1.0)")
            fig.tight_layout()
            fig.savefig(os.path.join(fig_dir, f"deform_{name}_frame{fi}.png"))
            plt.close(fig)


if __name__ == "__main__":
    main()
