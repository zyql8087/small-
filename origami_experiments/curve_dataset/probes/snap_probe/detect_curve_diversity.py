# -*- coding: utf-8 -*-
"""Classify force-displacement curve shapes and report dataset diversity.

Reads the snap-probe raw CSVs (one file per sample, columns include
sample_id, curve_id, step, force, displacement, signed_displacement, converged)
and assigns each (sample, condition) curve ONE shape label, then summarizes the
mix. The probe PASSES if a meaningful fraction of curves are qualitatively
"interesting" (snap / plateau / multi-peak / softening), not just monotone
hardening that differs only in magnitude.

Usage:
  python detect_curve_diversity.py --curves-dir <dir-of-csv> [--out summary.json]
                                   [--pass-threshold 0.25]
"""
from __future__ import annotations
import argparse, glob, json, os
from collections import Counter
import numpy as np
import pandas as pd

LABELS = ["monotone_hardening", "monotone_softening", "plateau",
          "snap_through", "snap_back", "multi_peak", "degenerate"]


def _smooth(y: np.ndarray, k: int = 5) -> np.ndarray:
    if len(y) < k:
        return y
    kernel = np.ones(k) / k
    return np.convolve(y, kernel, mode="same")


def classify_curve(disp: np.ndarray, force: np.ndarray,
                   signed_disp: np.ndarray | None = None) -> tuple[str, dict]:
    """Return (label, features) for one force-displacement curve (ordered by step)."""
    d = np.asarray(disp, float); f = np.asarray(force, float)
    ok = np.isfinite(d) & np.isfinite(f)
    d, f = d[ok], f[ok]
    if len(d) < 5 or (np.nanmax(f) - np.nanmin(f)) < 1e-9 or (np.nanmax(d) - np.nanmin(d)) < 1e-12:
        return "degenerate", {}

    fs = _smooth(f); ds = _smooth(d)
    fr = np.nanmax(fs) - np.nanmin(fs)               # force range
    dr = np.nanmax(np.abs(ds)) + 1e-12

    # snap-back: the *signed* control displacement reverses direction materially.
    # A monotone response can move in either positive or negative coordinates
    # depending on the load axis, so a single negative trend is not snap-back.
    sd = np.asarray(signed_disp, float)[ok] if signed_disp is not None else ds
    sd_s = _smooth(sd)
    dsd = np.diff(sd_s)
    sd_range = np.max(sd_s) - np.min(sd_s) + 1e-12
    step_eps = max(1e-12, 1e-6 * sd_range)
    pos_motion = float(np.sum(dsd[dsd > step_eps]))
    neg_motion = float(-np.sum(dsd[dsd < -step_eps]))
    pos_steps = int(np.sum(dsd > step_eps))
    neg_steps = int(np.sum(dsd < -step_eps))
    reversal_motion = min(pos_motion, neg_motion)
    dominant_motion = max(pos_motion, neg_motion, 1e-12)
    snap_back = (
        pos_steps >= 3
        and neg_steps >= 3
        and reversal_motion > 0.05 * sd_range
        and reversal_motion > 0.05 * dominant_motion
    )

    # tangent stiffness along the (monotone-resampled) displacement axis
    order = np.argsort(ds)
    dd = np.diff(ds[order]); df = np.diff(fs[order])
    valid = dd > 1e-12
    tang = np.full_like(dd, np.nan); tang[valid] = df[valid] / dd[valid]
    tang = tang[np.isfinite(tang)]
    neg_frac = float(np.mean(tang < 0)) if len(tang) else 0.0   # negative-stiffness fraction
    # plateau: extended low-|slope| region relative to the peak secant
    peak_secant = fr / dr
    plateau_frac = float(np.mean(np.abs(tang) < 0.1 * peak_secant)) if len(tang) else 0.0

    # force peaks (local maxima on smoothed force vs step)
    peaks = int(np.sum((fs[1:-1] > fs[:-2]) & (fs[1:-1] > fs[2:]) &
                       (fs[1:-1] > np.nanmin(fs) + 0.05 * fr)))

    # hardening vs softening: tangent trend (first third vs last third)
    if len(tang) >= 6:
        early = np.nanmedian(tang[: len(tang)//3]); late = np.nanmedian(tang[-len(tang)//3:])
    else:
        early = late = np.nan
    hardening = np.isfinite(early) and np.isfinite(late) and late > 1.15 * early
    softening = np.isfinite(early) and np.isfinite(late) and late < 0.85 * early

    feats = dict(neg_stiffness_frac=neg_frac, plateau_frac=plateau_frac,
                 force_peaks=peaks, snap_back=bool(snap_back),
                 hardening=bool(hardening), softening=bool(softening))

    # priority: snap-back > snap-through > multi-peak > plateau > softening > hardening
    if snap_back:                       return "snap_back", feats
    if neg_frac >= 0.08:                return "snap_through", feats
    if peaks >= 2:                      return "multi_peak", feats
    if plateau_frac >= 0.30:            return "plateau", feats
    if softening:                       return "monotone_softening", feats
    return "monotone_hardening", feats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--curves-dir", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--pass-threshold", type=float, default=0.25,
                    help="min fraction of 'interesting' curves to pass the probe")
    args = ap.parse_args()

    rows = []
    for csv in sorted(glob.glob(os.path.join(args.curves_dir, "*.csv"))):
        df = pd.read_csv(csv)
        df.columns = [c.strip() for c in df.columns]
        for (sid, cid), sub in df.groupby(["sample_id", "curve_id"]):
            sub = sub.sort_values("step")
            label, feats = classify_curve(
                sub["displacement"].to_numpy(),
                sub["force"].to_numpy(),
                sub["signed_displacement"].to_numpy() if "signed_displacement" in sub else None,
            )
            rows.append(dict(sample_id=sid, curve_id=int(cid), label=label, **feats))

    res = pd.DataFrame(rows)
    n = len(res)
    counts = Counter(res["label"])
    frac = {k: counts.get(k, 0) / max(n, 1) for k in LABELS}
    interesting = sum(frac[k] for k in ["snap_through", "snap_back", "multi_peak", "plateau", "monotone_softening"])
    # category entropy (0..1) as a second diversity signal
    p = np.array([frac[k] for k in LABELS if frac[k] > 0])
    entropy = float(-(p * np.log(p)).sum() / np.log(len(LABELS))) if len(p) > 1 else 0.0
    passed = interesting >= args.pass_threshold

    summary = dict(n_curves=n, label_fractions=frac,
                   interesting_fraction=round(interesting, 4),
                   shape_entropy=round(entropy, 4),
                   pass_threshold=args.pass_threshold, PASS=bool(passed))

    print("=" * 60)
    print(f"Curves classified: {n}")
    for k in LABELS:
        print(f"  {k:22s} {counts.get(k,0):5d}  {frac[k]*100:5.1f}%")
    print(f"interesting (non-trivial) fraction: {interesting*100:.1f}%  (need >= {args.pass_threshold*100:.0f}%)")
    print(f"shape entropy: {entropy:.3f}")
    print(f"PROBE {'PASS' if passed else 'FAIL'}")
    print("=" * 60)

    out = args.out or os.path.join(args.curves_dir, "curve_diversity_summary.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    res.to_csv(os.path.splitext(out)[0] + "_per_curve.csv", index=False)
    print(f"[saved] {out}")


if __name__ == "__main__":
    main()
