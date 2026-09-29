# -*- coding: utf-8 -*-
"""M08 summary data assembly + overlay plots.

Reads per-case evidence (solve_result.json / curve.csv / datacheck_result.json /
prep_status.json), the manifest, the author response curves (test.xlsx s1..s20,
s=N hypothesis, NOT an acceptance reference), and the implicit reference curves
(M06 six cases + M05 pilots, x-load). Writes summary_data.json + figures:
  figures/overlay_explicit_all.png       all explicit curves, colored by class
  figures/overlay_exp_vs_implicit.png    same-design explicit vs implicit
  figures/overlay_exp_vs_author.png      explicit vs author s=N curves
"""
import csv
import json
import os
import glob

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
M06 = ("F:/small++/paper_A_reliable_inverse_design/"
       "audits/m06_m1m3_c3d4_night_20260923/cases")
M05 = ("F:/small++/paper_A_reliable_inverse_design/"
       "audits/m05_small_mechanism_pilot_20260919/cases")
TEST_XLSX = ("F:/Inverse-design-of-graded-TPMS-main/"
             "Inverse-design-of-graded-TPMS-main/"
             "dataset used for training/test.xlsx")

IMPLICIT_CURVE_OF = {
    "m1_class1_944": os.path.join(M05, "m1_class1_944", "results", "curve.csv"),
    "m3_class12_665": os.path.join(M05, "m3_class12_665", "results", "curve.csv"),
    "m2_class2_1383": os.path.join(M05, "m2_class2_1383", "results",
                                   "curve.csv"),
    "m1_class1_1424": os.path.join(M06, "m1_class1_1424", "results", "curve.csv"),
    "m1_class1_763": os.path.join(M06, "m1_class1_763", "results", "curve.csv"),
    "m1_class1_1145": os.path.join(M06, "m1_class1_1145", "results", "curve.csv"),
    "m3_class12_1390": os.path.join(M06, "m3_class12_1390", "results", "curve.csv"),
    "m3_class12_61": os.path.join(M06, "m3_class12_61", "results", "curve.csv"),
    "m3_class12_26": os.path.join(M06, "m3_class12_26", "results", "curve.csv"),
}


def read_curve(p):
    if not os.path.isfile(p):
        return None
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    if not rows:
        return None
    eps = np.array([float(r["eps_engineering"]) for r in rows])
    sig = np.array([float(r["sigma_nominal_MPa"]) for r in rows])
    return {"eps": (eps * 100).tolist(), "sigma_MPa": sig.tolist(),
            "n": len(rows)}


def author_curve(sheet, row):
    wb = openpyxl.load_workbook(TEST_XLSX, read_only=True, data_only=True)
    ws = wb[sheet]
    try:
        ws.reset_dimensions()  # read_only sheets may carry truncated dims
    except Exception:
        pass
    vals = [r for r in ws.iter_rows(min_row=row, max_row=row,
                                    values_only=True)][0]
    s = list(vals[9:29])
    wb.close()
    if any(v is None for v in s):
        return None
    return {"eps_pct": [round(i * 1.25, 2) for i in range(1, 21)],
            "s_N": [float(v) for v in s]}


def main():
    manifest = sorted(csv.DictReader(open(os.path.join(
        ROOT, "selection_manifest_m08.csv"), encoding="utf-8")),
        key=lambda r: int(r["queue_order"]))
    cases = []
    for row in manifest:
        c = row["case_id"]
        base = os.path.join(ROOT, "cases", c)
        res = {}
        p = os.path.join(base, "results", "solve_result.json")
        if os.path.isfile(p):
            res = json.load(open(p, encoding="utf-8"))
        dc = {}
        p = os.path.join(base, "solver", "datacheck", "datacheck_result.json")
        if os.path.isfile(p):
            d = json.load(open(p, encoding="utf-8"))
            dc = {"gate_pass": d.get("gate_pass"),
                  "n_warning_lines": d.get("n_warning_lines"),
                  "unstable_warning_lines": d.get("unstable_warning_lines"),
                  "distorted": d.get("distorted_elements_dat"),
                  "errors": d.get("errors", [])}
        prep_failed = os.path.isfile(os.path.join(base, "solver",
                                                  "prep_status.json"))
        mesh_ok = os.path.isfile(os.path.join(base, "mesh", "outputs",
                                              "verify.json"))
        mesh_gates = None
        if mesh_ok:
            mesh_gates = json.load(open(os.path.join(
                base, "mesh", "outputs", "verify.json"),
                encoding="utf-8")).get("all_gates_passed")
        cases.append({
            "case_id": c, "job": row["job_name"],
            "queue_order": int(row["queue_order"]),
            "method": row["method"],
            "parent_design_id": row["parent_design_id"],
            "rv": float(row["archived_relativeVolume"]),
            "mesh_source": row["mesh_source"],
            "selection_kind": row["selection_kind"],
            "mesh_staged": mesh_ok, "mesh_gates": mesh_gates,
            "prep_failed": prep_failed,
            "datacheck": dc,
            "judgment": res.get("judgment", "not_solved"),
            "status_detail": res.get("status", ""),
            "error_signature": res.get("error_signature", []),
            "final_step_time": res.get("final_step_time"),
            "final_u3_mm": res.get("final_u3_mm"),
            "wall_s": res.get("wall_s"),
            "solve_start_time": res.get("solve_start_time"),
            "energy_gate": res.get("energy_gate", {}),
            "com_values": res.get("com_values"),
            "mass_scaling_grep": (res.get("mass_scaling_grep") or [])[:6],
            "sta_tail": res.get("sta_tail", []),
            "explicit_curve": read_curve(os.path.join(base, "results",
                                                      "curve.csv")),
        })

    # author curves per design
    ac = {}
    for c in cases:
        try:
            sheet = ("class1" if "class1" in c["parent_design_id"]
                     else "class2" if "class2" in c["parent_design_id"]
                     else "class12")
            q = author_curve(sheet, int(c["parent_design_id"].split(":")[1]))
            if q:
                ac[c["case_id"]] = q
        except Exception as e:
            print("author curve fail", c["case_id"], e)
    # implicit reference curves
    imp = {}
    for c_id, p in IMPLICIT_CURVE_OF.items():
        q = read_curve(p)
        if q:
            imp[c_id] = q

    out = {"generated": __import__("time").strftime(
        "%Y-%m-%d %H:%M:%S"),
        "note_author_curve": ("test.xlsx s1..s20 (sha256 b4544b09...), s=N "
                              "hypothesis (总反力 N, 未除面积), 20 points at "
                              "1.25% strain steps; disclosure only, NOT an "
                              "acceptance reference"),
        "note_implicit_ref": ("M06 六例 + M05 pilots 的隐式 x 向曲线(同设计、"
                              "不同加载轴与求解器, 仅共同应变区间内探索性对照)"),
        "cases": cases, "author_curves": ac, "implicit_curves": imp}
    with open(os.path.join(ROOT, "summary_data.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("summary_data.json written;", len(cases), "cases,",
          len(ac), "author curves,", len(imp), "implicit curves")
    make_plots(out)


def _plot_curves(curves, ax, cmap_key):
    colors = plt.get_cmap("tab20")(np.linspace(0, 1, 20))
    for i, (label, cur) in enumerate(curves):
        if cur and cur["n"] > 1:
            ax.plot(cur["eps"], cur["sigma_MPa"], "-", lw=1.2,
                    color=colors[i % 20], label=label)


def make_plots(data):
    fig_dir = os.path.join(ROOT, "figures")
    os.makedirs(fig_dir, exist_ok=True)
    cases = data["cases"]

    def curve_of(c):
        ec = c.get("explicit_curve")
        if ec and ec["n"] > 1:
            return (c["eps"], c["sigma"]) if False else (
                ec["eps"], ec["sigma_MPa"])
        return None

    # 1. all explicit
    fig, ax = plt.subplots(figsize=(9, 6), dpi=130)
    palette = {"M1": "tab:blue", "M2": "tab:orange", "M3": "tab:green"}
    for c in cases:
        cur = c.get("explicit_curve")
        if cur and cur["n"] > 1:
            ax.plot(cur["eps"], cur["sigma_MPa"], lw=1.1,
                    color=palette[c["method"]])
    handles = [plt.Line2D([], [], color=v, lw=1.5, label=k)
               for k, v in palette.items()]
    ax.set_xlabel("engineering strain (%)")
    ax.set_ylabel("nominal stress (MPa)")
    ax.set_title("M08 explicit z-compression: all curves (blue=M1 orange=M2 green=M3)")
    ax.legend(handles=handles, fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(fig_dir, "overlay_explicit_all.png"))
    plt.close(fig)

    # 2. explicit vs implicit (same design)
    have_imp = [c for c in cases if c["case_id"] in data["implicit_curves"]]
    if have_imp:
        n = len(have_imp)
        cols = 3
        rows = (n + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 3.6 * rows),
                                 dpi=120, squeeze=False)
        for k, c in enumerate(have_imp):
            ax = axes[k // cols][k % cols]
            ic = data["implicit_curves"][c["case_id"]]
            ec = c.get("explicit_curve")
            if ec and ec["n"] > 1:
                ax.plot(ec["eps"], ec["sigma_MPa"], "-",
                        label="explicit z (m08)")
            ax.plot(ic["eps"], ic["sigma_MPa"], "--",
                    label="implicit x (M06/M05)")
            ax.set_title(f"{c['case_id']} rv={c['rv']}", fontsize=9)
            ax.set_xlabel("strain (%)", fontsize=8)
            ax.set_ylabel("nominal stress (MPa)", fontsize=8)
            ax.legend(fontsize=7)
        for k in range(n, rows * cols):
            axes[k // cols][k % cols].axis("off")
        fig.tight_layout()
        fig.savefig(os.path.join(fig_dir, "overlay_exp_vs_implicit.png"))
        plt.close(fig)

    # 3. explicit vs author s=N
    have_au = [c for c in cases if c["case_id"] in data["author_curves"]]
    if have_au:
        n = len(have_au)
        cols = 3
        rows = (n + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 3.6 * rows),
                                 dpi=120, squeeze=False)
        for k, c in enumerate(have_au):
            ax = axes[k // cols][k % cols]
            au = data["author_curves"][c["case_id"]]
            ec = c.get("explicit_curve")
            if ec and ec["n"] > 1:
                ax.plot(ec["eps"], ec["sigma_MPa"], "-",
                        label="explicit z (m08)")
            ax.plot(au["eps_pct"], [s / 1600.0 for s in au["s_N"]], ":",
                    label="author s=N (/1600, disclose-only)")
            ax.plot(au["eps_pct"], au["s_N"], ":",
                    label="author s (N)", alpha=0.4)
            ax.set_title(f"{c['case_id']} rv={c['rv']}", fontsize=9)
            ax.set_xlabel("strain (%)", fontsize=8)
            ax.set_ylabel("force N / stress MPa", fontsize=8)
            ax.legend(fontsize=7)
        for k in range(n, rows * cols):
            axes[k // cols][k % cols].axis("off")
        fig.tight_layout()
        fig.savefig(os.path.join(fig_dir, "overlay_exp_vs_author.png"))
        plt.close(fig)
    print("figures written to", fig_dir)


if __name__ == "__main__":
    main()
