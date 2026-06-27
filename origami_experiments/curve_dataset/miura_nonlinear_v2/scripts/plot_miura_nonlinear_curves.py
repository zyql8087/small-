"""Plot Miura nonlinear force-displacement curves against linear stiffness references."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = SCRIPT_DIR.parent
STIFFNESS_BY_CURVE = {
    0: "bendstiff30",
    1: "bendstiff60",
    2: "bendstiff90",
    3: "axialstiff30",
    4: "axialstiff60",
    5: "axialstiff90",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-dir", type=Path, default=EXPERIMENT_DIR / "jobs_miura")
    parser.add_argument("--curves-dir", type=Path, default=EXPERIMENT_DIR / "raw_curves")
    parser.add_argument("--output-dir", type=Path, default=EXPERIMENT_DIR / "smoke_results")
    parser.add_argument("--samples", nargs="+", default=None)
    parser.add_argument("--max-samples", type=int, default=3)
    return parser.parse_args()


def choose_samples(parameters: pd.DataFrame, curves_dir: Path, samples: list[str] | None, max_samples: int) -> list[str]:
    if samples:
        return samples
    available = []
    for sample_id in parameters["sample_id"].astype(str):
        if (curves_dir / f"{sample_id}.csv").exists():
            available.append(sample_id)
        if len(available) >= max_samples:
            break
    return available


def plot_one_sample(param_row: pd.Series, curve_df: pd.DataFrame, output_path: Path) -> None:
    sample_id = str(param_row["sample_id"])
    curve_ids = sorted(curve_df["curve_id"].astype(int).unique().tolist())
    if curve_ids != sorted(STIFFNESS_BY_CURVE):
        raise ValueError(f"{sample_id}: expected curve ids 0..5, got {curve_ids}")

    fig, axes = plt.subplots(2, 3, figsize=(12, 7), constrained_layout=True)
    fig.suptitle(
        f"{sample_id} nonlinear force-displacement curves\n"
        "solid: SWOMPS large-load response, dashed: original small-load stiffness line",
        fontsize=13,
    )

    for ax, curve_id in zip(axes.ravel(), curve_ids):
        sub = curve_df.loc[curve_df["curve_id"].astype(int) == curve_id].sort_values("step")
        displacement = sub["displacement"].to_numpy(dtype=np.float64)
        force = sub["force"].to_numpy(dtype=np.float64)
        load_case = str(sub["load_case"].iloc[0])
        deployment = float(sub["deployment"].iloc[0])
        ref_stiffness = float(param_row[STIFFNESS_BY_CURVE[curve_id]])

        ax.plot(displacement, force, lw=2, label="large-load")
        ax.plot(displacement, ref_stiffness * displacement, "--", lw=1.5, label="linear ref")
        ax.set_title(f"curve {curve_id}: {load_case}, deploy {deployment:g}")
        ax.set_xlabel("Displacement")
        ax.set_ylabel("Force")
        ax.grid(True, alpha=0.35)
        ax.ticklabel_format(axis="x", style="sci", scilimits=(-2, 2))

    axes.ravel()[0].legend(loc="best", fontsize=8)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    parameter_path = args.job_dir / "parameters.csv"
    if not parameter_path.exists():
        raise FileNotFoundError(f"Missing parameter table: {parameter_path}")
    if not args.curves_dir.exists():
        raise FileNotFoundError(f"Missing curves directory: {args.curves_dir}")

    parameters = pd.read_csv(parameter_path)
    by_sample = {str(row["sample_id"]): row for _, row in parameters.iterrows()}
    sample_ids = choose_samples(parameters, args.curves_dir, args.samples, args.max_samples)
    if not sample_ids:
        raise RuntimeError(f"No curve CSV files found in {args.curves_dir}")

    written = []
    for sample_id in sample_ids:
        if sample_id not in by_sample:
            raise KeyError(f"Sample {sample_id} is not present in {parameter_path}")
        curve_path = args.curves_dir / f"{sample_id}.csv"
        if not curve_path.exists():
            raise FileNotFoundError(f"Missing curve CSV: {curve_path}")
        curve_df = pd.read_csv(curve_path)
        out_path = args.output_dir / f"{sample_id}_nonlinear_vs_linear.png"
        plot_one_sample(by_sample[sample_id], curve_df, out_path)
        written.append(str(out_path))

    print("\n".join(written))


if __name__ == "__main__":
    main()
