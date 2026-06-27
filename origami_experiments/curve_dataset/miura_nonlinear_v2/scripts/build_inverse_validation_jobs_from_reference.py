"""Build nonlinear SWOMPS jobs after estimating reference stiffness curves."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = SCRIPT_DIR.parent
DEFAULT_VALIDATION_DIR = EXPERIMENT_DIR / "validation" / "inverse_swomps_top10_v1"

INPUT_COLS = ["pattern", "m", "n", "tcrease", "tpanel", "W", "creaseE", "panelE"]
STIFFNESS_BY_CURVE = {
    0: "bendstiff30",
    1: "bendstiff60",
    2: "bendstiff90",
    3: "axialstiff30",
    4: "axialstiff60",
    5: "axialstiff90",
}
CONDITION_COLS = ["curve_id", "load_case", "deployment", "response_axis"]


def read_reference_stiffness(curve_df: pd.DataFrame, curve_points: int) -> dict[str, float]:
    required = {"curve_id", "step", "force", "displacement"}
    missing = required - set(curve_df.columns)
    if missing:
        raise ValueError(f"reference curve missing columns: {sorted(missing)}")

    stiffness: dict[str, float] = {}
    for curve_id, column in STIFFNESS_BY_CURVE.items():
        curve = curve_df[curve_df["curve_id"].astype(int) == curve_id].sort_values("step")
        if len(curve) < curve_points:
            raise ValueError(f"curve {curve_id} has {len(curve)} rows, expected at least {curve_points}")
        final = curve.iloc[curve_points - 1]
        force = float(final["force"])
        displacement = float(final["displacement"])
        if not np.isfinite(force) or not np.isfinite(displacement) or displacement <= 0.0:
            raise ValueError(f"invalid final force/displacement for curve {curve_id}: {force}, {displacement}")
        stiffness[column] = force / displacement
    return stiffness


def attach_reference_stiffness(parameters: pd.DataFrame, reference_curves_dir: Path, curve_points: int) -> pd.DataFrame:
    enriched = parameters.copy()
    for idx, row in enriched.iterrows():
        sample_id = str(row["sample_id"])
        curve_path = reference_curves_dir / f"{sample_id}.csv"
        if not curve_path.exists():
            raise FileNotFoundError(f"missing reference curve CSV: {curve_path}")
        stiffness = read_reference_stiffness(pd.read_csv(curve_path), curve_points=curve_points)
        for column, value in stiffness.items():
            enriched.loc[idx, column] = value
    return enriched


def load_condition_schema(reference_job_dir: Path) -> pd.DataFrame:
    path = reference_job_dir / "condition_schema.csv"
    if path.exists():
        return pd.read_csv(path)[CONDITION_COLS].sort_values("curve_id").reset_index(drop=True)
    jobs = pd.read_csv(reference_job_dir / "simulation_jobs.csv")
    return jobs[CONDITION_COLS].drop_duplicates().sort_values("curve_id").reset_index(drop=True)


def make_simulation_jobs(parameters: pd.DataFrame, conditions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    parameter_cols = ["sample_id", "target_sample_id", "source_name", "source_row"] + INPUT_COLS
    for _, param in parameters.iterrows():
        for _, cond in conditions.iterrows():
            row = {name: param[name] for name in parameter_cols if name in parameters.columns}
            for name in CONDITION_COLS:
                row[name] = cond[name]
            rows.append(row)
    ordered = ["sample_id", "target_sample_id", "source_name", "source_row"] + CONDITION_COLS + INPUT_COLS
    return pd.DataFrame(rows)[ordered]


def write_nonlinear_jobs(reference_job_dir: Path, reference_curves_dir: Path, output_job_dir: Path, curve_points: int) -> dict:
    parameters = pd.read_csv(reference_job_dir / "parameters.csv")
    conditions = load_condition_schema(reference_job_dir)
    enriched = attach_reference_stiffness(parameters, reference_curves_dir, curve_points=curve_points)
    jobs = make_simulation_jobs(enriched, conditions)

    output_job_dir.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(output_job_dir / "parameters.csv", index=False)
    jobs.to_csv(output_job_dir / "simulation_jobs.csv", index=False)
    conditions.to_csv(output_job_dir / "condition_schema.csv", index=False)
    stiffness_cols = list(STIFFNESS_BY_CURVE.values())
    enriched[["sample_id"] + stiffness_cols].to_csv(output_job_dir / "estimated_reference_stiffness.csv", index=False)
    metadata = {
        "reference_job_dir": str(reference_job_dir),
        "reference_curves_dir": str(reference_curves_dir),
        "output_job_dir": str(output_job_dir),
        "curve_points_for_reference": int(curve_points),
        "stiffness_formula": "final_force / final_displacement at fixed small-load response",
    }
    (output_job_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-job-dir", type=Path, default=DEFAULT_VALIDATION_DIR / "jobs_reference")
    parser.add_argument("--reference-curves-dir", type=Path, default=DEFAULT_VALIDATION_DIR / "raw_curves_reference")
    parser.add_argument("--output-job-dir", type=Path, default=DEFAULT_VALIDATION_DIR / "jobs_nonlinear")
    parser.add_argument("--curve-points", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = write_nonlinear_jobs(
        reference_job_dir=args.reference_job_dir,
        reference_curves_dir=args.reference_curves_dir,
        output_job_dir=args.output_job_dir,
        curve_points=args.curve_points,
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
