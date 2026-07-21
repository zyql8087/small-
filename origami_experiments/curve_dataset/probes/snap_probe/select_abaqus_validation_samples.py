# -*- coding: utf-8 -*-
"""Select a small SWOMPS<->Abaqus validation set + write a comparison manifest.

Picks ~N samples that (1) cover the categorical/continuous parameter space and
(2) include representatives of each curve-shape category from the diversity
detector -- prioritising snap_through / snap_back / plateau / multi_peak, since
those large-deformation features are exactly where the bar-and-hinge reduced
model is most likely to disagree with high-fidelity FEA.

Inputs:
  --params      jobs parameters.csv (sample_id, pattern, m, n, tcrease, tpanel, W, creaseE, panelE)
  --per-curve   *_per_curve.csv produced by detect_curve_diversity.py (sample_id, curve_id, label)
Outputs (in --out-dir):
  abaqus_validation_manifest.csv   one row per (sample, condition) to reproduce in Abaqus
  abaqus_validation_plan.md        human checklist (BC, mesh, material, what to compare)
"""
from __future__ import annotations
import argparse, os
import numpy as np
import pandas as pd

PRIORITY = ["snap_back", "snap_through", "multi_peak", "plateau",
            "monotone_softening", "monotone_hardening"]
CONDITIONS = {0: ("bending", 0.3, "z"), 1: ("bending", 0.6, "z"), 2: ("bending", 0.9, "z"),
              3: ("axial", 0.3, "x"), 4: ("axial", 0.6, "x"), 5: ("axial", 0.9, "x")}


def pick(params: pd.DataFrame, per_curve: pd.DataFrame, n_samples: int) -> pd.DataFrame:
    params = params.copy()
    params["sample_id"] = params["sample_id"].astype(str)
    per_curve["sample_id"] = per_curve["sample_id"].astype(str)

    # the "most interesting" label seen for each sample, by priority
    rank = {lab: i for i, lab in enumerate(PRIORITY)}
    per_curve["rk"] = per_curve["label"].map(lambda l: rank.get(l, len(PRIORITY)))
    best = per_curve.sort_values("rk").groupby("sample_id").first().reset_index()
    # Only samples with completed probe labels can be selected for Abaqus overlay.
    # Selecting from the full parameter table would request FEA for samples that
    # have no SWOMPS curve to compare against.
    df = params.merge(best[["sample_id", "label", "curve_id", "rk"]], on="sample_id", how="inner")

    chosen, used = [], set()
    # (a) one representative per shape category (rarest/most-interesting first)
    for lab in PRIORITY:
        cand = df[(df["label"] == lab) & (~df["sample_id"].isin(used))]
        if len(cand):
            r = cand.iloc[len(cand) // 2]            # middle-of-pack representative
            chosen.append((r["sample_id"], f"shape={lab}")); used.add(r["sample_id"])
    # (b) parameter extremes: hardest cases for a reduced model
    for col, how, tag in [("creaseE", "min", "softest crease"), ("panelE", "max", "stiffest panel"),
                          ("tpanel", "min", "thinnest panel"), ("W", "min", "narrowest crease"),
                          ("m", "max", "most cells m"), ("n", "max", "most cells n")]:
        cand = df[~df["sample_id"].isin(used)]
        if not len(cand):
            break
        idx = cand[col].idxmin() if how == "min" else cand[col].idxmax()
        sid = df.loc[idx, "sample_id"]
        chosen.append((sid, f"extreme:{tag}")); used.add(sid)
        if len(chosen) >= n_samples:
            break

    # (c) fill any remaining slots with evenly spaced completed probe samples
    # so --n-samples is honored whenever enough labeled samples exist.
    if len(chosen) < n_samples:
        cand = df[~df["sample_id"].isin(used)].sort_values("sample_id").reset_index(drop=True)
        need = min(n_samples - len(chosen), len(cand))
        if need > 0:
            positions = np.linspace(0, len(cand) - 1, need).round().astype(int)
            for pos in positions:
                r = cand.iloc[int(pos)]
                sid = r["sample_id"]
                if sid not in used:
                    chosen.append((sid, "coverage:completed probe quantile")); used.add(sid)
            if len(chosen) < n_samples:
                for _, r in cand.iterrows():
                    sid = r["sample_id"]
                    if sid not in used:
                        chosen.append((sid, "coverage:completed probe fill")); used.add(sid)
                    if len(chosen) >= n_samples:
                        break

    chosen = chosen[:n_samples]
    out = df[df["sample_id"].isin([c[0] for c in chosen])].copy()
    reason = {sid: why for sid, why in chosen}
    out["select_reason"] = out["sample_id"].map(reason)
    order = {sid: i for i, (sid, _) in enumerate(chosen)}
    out["selection_order"] = out["sample_id"].map(order)
    out = out.sort_values("selection_order").drop(columns=["selection_order"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", required=True)
    ap.add_argument("--per-curve", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--n-samples", type=int, default=10)
    # which conditions to reproduce in FEA (axial folding + 90% bending are most nonlinear)
    ap.add_argument("--conditions", default="2,3,4,5")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    params = pd.read_csv(args.params)
    per_curve = pd.read_csv(args.per_curve)
    sel = pick(params, per_curve, args.n_samples)
    cond_ids = [int(x) for x in str(args.conditions).split(",") if x.strip() != ""]

    rows = []
    for _, r in sel.iterrows():
        for cid in cond_ids:
            lc, dep, ax = CONDITIONS[cid]
            rows.append({
                "sample_id": r["sample_id"], "select_reason": r["select_reason"],
                "swomps_shape_label": r.get("label", ""),
                "curve_id": cid, "load_case": lc, "deployment": dep, "response_axis": ax,
                "pattern": int(r["pattern"]), "m": int(r["m"]), "n": int(r["n"]),
                "tcrease": r["tcrease"], "tpanel": r["tpanel"], "W": r["W"],
                "creaseE": r["creaseE"], "panelE": r["panelE"],
            })
    manifest = pd.DataFrame(rows)
    manifest_path = os.path.join(args.out_dir, "abaqus_validation_manifest.csv")
    manifest.to_csv(manifest_path, index=False)

    md = f"""# SWOMPS <-> Abaqus validation plan

Selected **{len(sel)} samples x {len(cond_ids)} conditions = {len(manifest)} curves** to reproduce in
high-fidelity FEA and overlay against the SWOMPS bar-and-hinge probe curves.

## Why these samples
{sel[['sample_id','select_reason','label']].to_string(index=False)}

## Abaqus setup (match SWOMPS as closely as possible)
- Geometry: same Miura sheet, L=0.2 m, gamma=70 deg, (m,n) per row, held at `deployment` then loaded.
  Export the SAME deployed mesh SWOMPS uses if possible (node coords), else rebuild from (a,b,gamma,Ext).
- Material: **linear-elastic isotropic**, E = `panelE` (panels) / `creaseE` (creases), nu = 0.3.
  (Shell/solid panels + reduced-stiffness crease zones, or a validated bar-and-hinge-equivalent shell model.)
- BC: clamp the min-x edge (all 6 DOF); drive the max-x edge with **displacement control** along the load axis
  (bending: -z, axial: +x). Use a static, geometrically-nonlinear step (NLGEOM=ON; Riks/arc-length if snap-back).
- Output: reaction force at the loaded edge vs its displacement -> force-displacement curve.

## What to compare (acceptance)
For each curve, overlay SWOMPS vs Abaqus and report:
- NRMSE of force vs displacement (target: SWOMPS within ~15-25% of FEA in the regime of interest);
- **qualitative agreement of features**: does Abaqus ALSO show the snap-through / plateau / peak that SWOMPS predicts? (most important — if the snap is a bar-and-hinge artifact, this is where it shows.)
- limit-point load and displacement (for snap cases).

> Decision: if SWOMPS reproduces the FEA *shape features* (even with magnitude offset), the fast SWOMPS
> dataset is defensible (cite the offset, validate final designs in FEA). If the snap features are artifacts,
> fall back to FEA-only data on a smaller design space, or pivot structure family.
"""
    md_path = os.path.join(args.out_dir, "abaqus_validation_plan.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(f"[saved] {manifest_path}  ({len(manifest)} curves)")
    print(f"[saved] {md_path}")


if __name__ == "__main__":
    main()
