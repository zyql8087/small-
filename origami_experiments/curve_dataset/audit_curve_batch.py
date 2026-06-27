"""Audit exported origami force-displacement curve CSV files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


INPUT_COLS = ["pattern", "m", "n", "tcrease", "tpanel", "W", "creaseE", "panelE"]
STIFFNESS_BY_CURVE = {
    0: "bendstiff30",
    1: "bendstiff60",
    2: "bendstiff90",
    3: "axialstiff30",
    4: "axialstiff60",
    5: "axialstiff90",
}
REQUIRED_CURVE_COLS = {
    "sample_id",
    "curve_id",
    "load_case",
    "deployment",
    "response_axis",
    "step",
    "force",
    "displacement",
    "converged",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-dir", type=Path, required=True)
    parser.add_argument("--curves-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--curve-points", type=int, default=30)
    parser.add_argument("--final-load", type=float, default=3.0)
    parser.add_argument("--expected-samples", type=int, default=None)
    parser.add_argument("--max-rel-stiff-error", type=float, default=0.10)
    parser.add_argument("--audit-mode", choices=["linear", "nonlinear"], default="linear")
    parser.add_argument("--min-secant-change-ratio", type=float, default=0.0)
    parser.add_argument("--min-mean-secant-change-ratio", type=float, default=0.0)
    parser.add_argument("--min-max-secant-change-ratio", type=float, default=0.0)
    parser.add_argument("--min-mean-linearity-error", type=float, default=0.0)
    return parser.parse_args()


def summarize(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "max": None, "p95": None}
    arr = np.asarray(values, dtype=np.float64)
    return {
        "count": int(arr.size),
        "mean": float(arr.mean()),
        "max": float(arr.max()),
        "p95": float(np.percentile(arr, 95)),
    }


def as_bool_array(series: pd.Series) -> np.ndarray:
    if pd.api.types.is_bool_dtype(series):
        return series.to_numpy(dtype=bool)
    if pd.api.types.is_numeric_dtype(series):
        return series.to_numpy(dtype=float) != 0
    text = series.astype(str).str.strip().str.lower()
    return text.isin(["true", "1", "yes"]).to_numpy(dtype=bool)


def monotonic_non_decreasing(values: np.ndarray, tolerance: float = 1e-10) -> bool:
    return bool(np.all(np.diff(values) >= -tolerance))


def audit_one_sample(
    param_row: pd.Series,
    curves_dir: Path,
    curve_points: int,
    final_load: float,
    max_rel_stiff_error: float,
    audit_mode: str,
    min_secant_change_ratio: float,
) -> tuple[list[dict], list[str]]:
    sample_id = str(param_row["sample_id"])
    issues: list[str] = []
    rows: list[dict] = []

    if str(param_row.get("source_name", "")) != "miura":
        issues.append(f"{sample_id}: source_name is not miura")
    if int(param_row["pattern"]) != 1:
        issues.append(f"{sample_id}: pattern is not 1")
    if not sample_id.startswith("miura_"):
        issues.append(f"{sample_id}: sample_id does not start with miura_")

    path = curves_dir / f"{sample_id}.csv"
    if not path.exists():
        issues.append(f"{sample_id}: missing curve CSV {path}")
        return rows, issues

    curve_df = pd.read_csv(path)
    curve_df.columns = [str(col).strip() for col in curve_df.columns]
    missing = REQUIRED_CURVE_COLS - set(curve_df.columns)
    if missing:
        issues.append(f"{sample_id}: missing columns {sorted(missing)}")
        return rows, issues

    if len(curve_df) != len(STIFFNESS_BY_CURVE) * curve_points:
        issues.append(f"{sample_id}: expected {len(STIFFNESS_BY_CURVE) * curve_points} rows, got {len(curve_df)}")

    curve_df["curve_id"] = curve_df["curve_id"].astype(int)
    curve_df["step"] = curve_df["step"].astype(int)

    actual_curve_ids = sorted(curve_df["curve_id"].unique().tolist())
    expected_curve_ids = sorted(STIFFNESS_BY_CURVE)
    if actual_curve_ids != expected_curve_ids:
        issues.append(f"{sample_id}: curve_id values {actual_curve_ids}, expected {expected_curve_ids}")

    for curve_id, stiffness_col in STIFFNESS_BY_CURVE.items():
        sub = curve_df.loc[curve_df["curve_id"] == curve_id].sort_values("step")
        if sub.empty:
            continue

        expected_steps = np.arange(1, curve_points + 1)
        actual_steps = sub["step"].to_numpy(dtype=int)
        if not np.array_equal(actual_steps, expected_steps):
            issues.append(f"{sample_id} curve {curve_id}: invalid steps {actual_steps.tolist()}")
            continue

        force = sub["force"].to_numpy(dtype=np.float64)
        displacement = sub["displacement"].to_numpy(dtype=np.float64)
        converged = as_bool_array(sub["converged"])

        if not np.isfinite(force).all() or not np.isfinite(displacement).all():
            issues.append(f"{sample_id} curve {curve_id}: contains NaN or Inf")
            continue
        if not converged.all():
            issues.append(f"{sample_id} curve {curve_id}: contains unconverged steps")
        if np.any(displacement <= 0):
            issues.append(f"{sample_id} curve {curve_id}: displacement contains non-positive values")
        if not monotonic_non_decreasing(force):
            issues.append(f"{sample_id} curve {curve_id}: force is not monotonic")
        if not monotonic_non_decreasing(displacement):
            issues.append(f"{sample_id} curve {curve_id}: displacement is not monotonic")
        expected_final_load = final_load
        if "final_load" in sub.columns:
            expected_final_load = float(sub["final_load"].iloc[0])
        if not np.isclose(force[-1], expected_final_load, rtol=1e-6, atol=1e-6):
            issues.append(f"{sample_id} curve {curve_id}: final force {force[-1]} != {expected_final_load}")

        source_stiff = float(param_row[stiffness_col])
        curve_final_stiff = float(abs(force[-1]) / displacement[-1])
        rel_stiff_error = abs(curve_final_stiff - source_stiff) / max(abs(source_stiff), 1e-12)
        secant = force / displacement
        secant_stiff_cv = float(np.std(secant) / max(abs(np.mean(secant)), 1e-12))
        secant_change_ratio = float(abs(secant[-1] / max(abs(secant[0]), 1e-12) - 1.0))
        linear_force = displacement * source_stiff
        max_linearity_error = float(np.max(np.abs(force - linear_force)) / max(abs(force[-1]), 1e-12))

        if audit_mode == "linear" and rel_stiff_error > max_rel_stiff_error:
            issues.append(
                f"{sample_id} curve {curve_id}: rel stiffness error {rel_stiff_error:.4g} "
                f"> {max_rel_stiff_error:.4g}"
            )
        if audit_mode == "nonlinear" and secant_change_ratio < min_secant_change_ratio:
            issues.append(
                f"{sample_id} curve {curve_id}: secant change ratio {secant_change_ratio:.4g} "
                f"< {min_secant_change_ratio:.4g}"
            )

        rows.append(
            {
                "sample_id": sample_id,
                "source_name": param_row.get("source_name", "miura"),
                "pattern": int(param_row["pattern"]),
                "curve_id": curve_id,
                "load_case": str(sub["load_case"].iloc[0]),
                "deployment": float(sub["deployment"].iloc[0]),
                "source_stiff": source_stiff,
                "curve_final_stiff": curve_final_stiff,
                "rel_stiff_error": float(rel_stiff_error),
                "secant_stiff_cv": secant_stiff_cv,
                "secant_change_ratio": secant_change_ratio,
                "max_linearity_error": max_linearity_error,
                "force_final": float(force[-1]),
                "expected_final_load": float(expected_final_load),
                "disp_final": float(displacement[-1]),
                "disp_min": float(displacement.min()),
                "disp_max": float(displacement.max()),
            }
        )

    return rows, issues


def main() -> None:
    args = parse_args()
    if args.curve_points < 2:
        raise ValueError("--curve-points must be at least 2")
    if args.final_load <= 0:
        raise ValueError("--final-load must be positive")

    parameter_path = args.job_dir / "parameters.csv"
    if not parameter_path.exists():
        raise FileNotFoundError(f"Missing parameter table: {parameter_path}")
    if not args.curves_dir.exists():
        raise FileNotFoundError(f"Missing curves directory: {args.curves_dir}")

    parameters = pd.read_csv(parameter_path)
    missing_param_cols = set(INPUT_COLS + list(STIFFNESS_BY_CURVE.values()) + ["sample_id"]) - set(parameters.columns)
    if missing_param_cols:
        raise ValueError(f"Parameter table missing columns: {sorted(missing_param_cols)}")

    audit_params = parameters
    if args.expected_samples is not None:
        audit_params = parameters.head(args.expected_samples)

    all_rows: list[dict] = []
    issues: list[str] = []
    for _, param_row in audit_params.iterrows():
        rows, sample_issues = audit_one_sample(
            param_row,
            args.curves_dir,
            args.curve_points,
            args.final_load,
            args.max_rel_stiff_error,
            args.audit_mode,
            args.min_secant_change_ratio,
        )
        all_rows.extend(rows)
        issues.extend(sample_issues)

    tmp_files = sorted(path.name for path in args.curves_dir.glob("tmp_*.csv"))
    if tmp_files:
        issues.append(f"Found TMP files in Miura-only output directory: {tmp_files[:5]}")

    failure_log = args.curves_dir / "failures.log"
    if failure_log.exists() and failure_log.stat().st_size > 0:
        issues.append(f"Non-empty failures.log found: {failure_log}")

    audit_df = pd.DataFrame(all_rows)
    rel_errors = audit_df["rel_stiff_error"].tolist() if not audit_df.empty else []
    secant_cvs = audit_df["secant_stiff_cv"].tolist() if not audit_df.empty else []
    secant_change_ratios = audit_df["secant_change_ratio"].tolist() if not audit_df.empty else []
    linearity_errors = audit_df["max_linearity_error"].tolist() if not audit_df.empty else []
    rel_error_summary = summarize(rel_errors)
    secant_cv_summary = summarize(secant_cvs)
    secant_change_summary = summarize(secant_change_ratios)
    linearity_error_summary = summarize(linearity_errors)

    if args.audit_mode == "nonlinear":
        mean_secant_change = secant_change_summary["mean"]
        max_secant_change = secant_change_summary["max"]
        mean_linearity_error = linearity_error_summary["mean"]
        if mean_secant_change is not None and mean_secant_change < args.min_mean_secant_change_ratio:
            issues.append(
                "Mean secant change ratio "
                f"{mean_secant_change:.4g} < {args.min_mean_secant_change_ratio:.4g}"
            )
        if max_secant_change is not None and max_secant_change < args.min_max_secant_change_ratio:
            issues.append(
                "Max secant change ratio "
                f"{max_secant_change:.4g} < {args.min_max_secant_change_ratio:.4g}"
            )
        if mean_linearity_error is not None and mean_linearity_error < args.min_mean_linearity_error:
            issues.append(
                "Mean max-linearity error "
                f"{mean_linearity_error:.4g} < {args.min_mean_linearity_error:.4g}"
            )

    worst = (
        audit_df.sort_values("rel_stiff_error", ascending=False).head(10).to_dict(orient="records")
        if not audit_df.empty
        else []
    )

    summary = {
        "audited_samples": int(len(audit_params)),
        "curve_csv_files": int(len(list(args.curves_dir.glob("miura_*.csv")))),
        "expected_samples": args.expected_samples,
        "curve_points": int(args.curve_points),
        "final_load": float(args.final_load),
        "audit_mode": args.audit_mode,
        "nonlinear_thresholds": {
            "min_mean_secant_change_ratio": float(args.min_mean_secant_change_ratio),
            "min_max_secant_change_ratio": float(args.min_max_secant_change_ratio),
            "min_mean_linearity_error": float(args.min_mean_linearity_error),
        },
        "issues_count": int(len(issues)),
        "issues": issues,
        "rel_stiff_error": rel_error_summary,
        "secant_stiff_cv": secant_cv_summary,
        "secant_change_ratio": secant_change_summary,
        "max_linearity_error": linearity_error_summary,
        "worst_rel_stiff_errors": worst,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    audit_df.to_csv(args.output_dir / "miura_curve_audit.csv", index=False)
    (args.output_dir / "miura_curve_audit.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
