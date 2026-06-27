"""Evaluate true SWOMPS curves for inverse-diffusion generated parameters."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = SCRIPT_DIR.parent
DEFAULT_VALIDATION_DIR = EXPERIMENT_DIR / "validation" / "inverse_swomps_top10_v1"
DEFAULT_SELECTED_CSV = DEFAULT_VALIDATION_DIR / "selected_candidates.csv"
DEFAULT_TARGET_CURVES_DIR = EXPERIMENT_DIR / "raw_curves"
DEFAULT_GENERATED_CURVES_DIR = DEFAULT_VALIDATION_DIR / "raw_curves_nonlinear"
DEFAULT_OUTPUT_DIR = DEFAULT_VALIDATION_DIR / "results"


def stack_curve_channels(curve_df: pd.DataFrame, curve_points: int) -> np.ndarray:
    required = {"curve_id", "step", "force", "displacement"}
    missing = required - set(curve_df.columns)
    if missing:
        raise ValueError(f"curve CSV missing columns: {sorted(missing)}")
    curves = []
    for curve_id in range(6):
        curve = curve_df[curve_df["curve_id"].astype(int) == curve_id].sort_values("step")
        if len(curve) != curve_points:
            raise ValueError(f"curve {curve_id} has {len(curve)} rows, expected {curve_points}")
        curves.append(curve[["displacement", "force"]].to_numpy(dtype=np.float32))
    return np.stack(curves, axis=0)


def curve_metrics(pred_curve: np.ndarray, target_curve: np.ndarray) -> dict[str, float]:
    diff = pred_curve - target_curve
    disp_diff = diff[..., 0]
    force_diff = diff[..., 1]
    target_disp = target_curve[..., 0]
    target_force = target_curve[..., 1]
    disp_std = float(np.std(target_disp))
    force_std = float(np.std(target_force))
    disp_range = float(np.ptp(target_disp))
    force_range = float(np.ptp(target_force))
    displacement_rmse = float(np.sqrt(np.mean(disp_diff**2)))
    force_rmse = float(np.sqrt(np.mean(force_diff**2)))
    return {
        "displacement_mae": float(np.mean(np.abs(disp_diff))),
        "displacement_rmse": displacement_rmse,
        "force_mae": float(np.mean(np.abs(force_diff))),
        "force_rmse": force_rmse,
        "displacement_nrmse_std_percent": float(displacement_rmse / max(disp_std, 1e-12) * 100.0),
        "force_nrmse_std_percent": float(force_rmse / max(force_std, 1e-12) * 100.0),
        "displacement_nrmse_range_percent": float(displacement_rmse / max(disp_range, 1e-12) * 100.0),
        "force_nrmse_range_percent": float(force_rmse / max(force_range, 1e-12) * 100.0),
        "negative_displacement_fraction": float(np.mean(pred_curve[..., 0] < 0.0)),
        "negative_force_fraction": float(np.mean(pred_curve[..., 1] < 0.0)),
    }


def convergence_fraction(curve_df: pd.DataFrame) -> float | None:
    if "converged" not in curve_df.columns:
        return None
    values = curve_df["converged"]
    if pd.api.types.is_bool_dtype(values):
        return float(values.mean())
    text = values.astype(str).str.lower().str.strip()
    return float(text.isin(["true", "1", "yes"]).mean())


def evaluate_one_candidate(
    selected_row: pd.Series,
    target_df: pd.DataFrame,
    generated_df: pd.DataFrame,
    curve_points: int,
) -> dict[str, float | int | str | None]:
    target_curve = stack_curve_channels(target_df, curve_points=curve_points)
    generated_curve = stack_curve_channels(generated_df, curve_points=curve_points)
    metrics = curve_metrics(generated_curve, target_curve)
    return {
        "rank": int(selected_row.get("rank", 0)),
        "target_sample_id": str(selected_row.get("target_sample_id", selected_row["sample_id"])),
        "validation_sample_id": str(selected_row["validation_sample_id"]),
        "closed_loop_scaled_mse": float(selected_row.get("closed_loop_scaled_mse", np.nan)),
        "swomps_converged_fraction": convergence_fraction(generated_df),
        **metrics,
    }


def summarize_metrics(rows: list[dict]) -> dict[str, float | int | None]:
    summary: dict[str, float | int | None] = {"samples": len(rows)}
    numeric_keys = [
        "displacement_rmse",
        "force_rmse",
        "displacement_nrmse_std_percent",
        "force_nrmse_std_percent",
        "negative_displacement_fraction",
        "negative_force_fraction",
        "swomps_converged_fraction",
    ]
    frame = pd.DataFrame(rows)
    for key in numeric_keys:
        if key not in frame:
            continue
        values = pd.to_numeric(frame[key], errors="coerce").dropna()
        if values.empty:
            summary[f"{key}_mean"] = None
            summary[f"{key}_max"] = None
        else:
            summary[f"{key}_mean"] = float(values.mean())
            summary[f"{key}_max"] = float(values.max())
    return summary


def plot_summary(rows: list[dict], output_path: Path) -> Path:
    import matplotlib.pyplot as plt

    frame = pd.DataFrame(rows).sort_values("rank")
    x = np.arange(len(frame))
    fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
    ax.bar(x - 0.18, frame["displacement_nrmse_std_percent"], width=0.36, label="displacement")
    ax.bar(x + 0.18, frame["force_nrmse_std_percent"], width=0.36, label="force")
    ax.set_xticks(x)
    ax.set_xticklabels(frame["rank"].astype(str))
    ax.set_xlabel("Selected candidate rank")
    ax.set_ylabel("True SWOMPS std-NRMSE (%)")
    ax.set_title("Inverse-generated parameters: true SWOMPS validation")
    ax.legend(frameon=False)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_candidate_curves(target_df: pd.DataFrame, generated_df: pd.DataFrame, output_path: Path, title: str) -> Path:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 3, figsize=(10, 5.8), constrained_layout=True)
    for curve_id, ax in enumerate(axes.ravel()):
        target = target_df[target_df["curve_id"].astype(int) == curve_id].sort_values("step")
        generated = generated_df[generated_df["curve_id"].astype(int) == curve_id].sort_values("step")
        ax.plot(target["displacement"], target["force"], color="#111827", label="target")
        ax.plot(generated["displacement"], generated["force"], color="#E45756", linestyle="--", label="generated SWOMPS")
        ax.set_title(f"curve {curve_id}")
        ax.set_xlabel("Displacement")
        ax.set_ylabel("Force")
    axes.ravel()[0].legend(frameon=False)
    fig.suptitle(title)
    fig.savefig(output_path, dpi=190, bbox_inches="tight")
    plt.close(fig)
    return output_path


def run_evaluation(
    selected_csv: Path,
    target_curves_dir: Path,
    generated_curves_dir: Path,
    output_dir: Path,
    curve_points: int,
    plot_count: int,
) -> dict:
    selected = pd.read_csv(selected_csv)
    output_dir.mkdir(parents=True, exist_ok=True)
    curve_plot_dir = output_dir / "curve_plots"
    curve_plot_dir.mkdir(exist_ok=True)

    rows = []
    plot_paths = []
    for _, row in selected.iterrows():
        target_sample_id = str(row.get("target_sample_id", row["sample_id"]))
        validation_sample_id = str(row["validation_sample_id"])
        target_path = target_curves_dir / f"{target_sample_id}.csv"
        generated_path = generated_curves_dir / f"{validation_sample_id}.csv"
        if not target_path.exists():
            raise FileNotFoundError(f"missing target curve: {target_path}")
        if not generated_path.exists():
            raise FileNotFoundError(f"missing generated SWOMPS curve: {generated_path}")
        target_df = pd.read_csv(target_path)
        generated_df = pd.read_csv(generated_path)
        metrics = evaluate_one_candidate(row, target_df, generated_df, curve_points=curve_points)
        rows.append(metrics)
        if len(plot_paths) < plot_count:
            plot_path = curve_plot_dir / f"{validation_sample_id}_true_swomps.png"
            plot_candidate_curves(target_df, generated_df, plot_path, f"True SWOMPS validation: {validation_sample_id}")
            plot_paths.append(plot_path)

    per_candidate_path = output_dir / "swomps_validation_metrics.csv"
    pd.DataFrame(rows).to_csv(per_candidate_path, index=False)
    summary = summarize_metrics(rows)
    summary_plot = plot_summary(rows, output_dir / "swomps_validation_nrmse.png")
    payload = {
        "summary": summary,
        "paths": {
            "per_candidate_metrics": str(per_candidate_path),
            "summary_plot": str(summary_plot),
            "curve_plots": [str(path) for path in plot_paths],
        },
    }
    (output_dir / "swomps_validation_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected-csv", type=Path, default=DEFAULT_SELECTED_CSV)
    parser.add_argument("--target-curves-dir", type=Path, default=DEFAULT_TARGET_CURVES_DIR)
    parser.add_argument("--generated-curves-dir", type=Path, default=DEFAULT_GENERATED_CURVES_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--curve-points", type=int, default=80)
    parser.add_argument("--plot-count", type=int, default=6)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = run_evaluation(
        selected_csv=args.selected_csv,
        target_curves_dir=args.target_curves_dir,
        generated_curves_dir=args.generated_curves_dir,
        output_dir=args.output_dir,
        curve_points=args.curve_points,
        plot_count=args.plot_count,
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
