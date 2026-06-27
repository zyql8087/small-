"""Prepare SWOMPS validation jobs for inverse-diffusion generated Miura parameters."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = SCRIPT_DIR.parent
DEFAULT_RESULT_DIR = EXPERIMENT_DIR / "training_results" / "inverse_diffusion_quality_filtered_150ep_v2_physical"
DEFAULT_GENERATED_CSV = DEFAULT_RESULT_DIR / "generated_parameters_closed_loop.csv"
DEFAULT_ORIGINAL_JOB_DIR = EXPERIMENT_DIR / "jobs_miura"
DEFAULT_OUTPUT_DIR = EXPERIMENT_DIR / "validation" / "inverse_swomps_top10_v1"

INPUT_COLS = ["pattern", "m", "n", "tcrease", "tpanel", "W", "creaseE", "panelE"]
STIFFNESS_COLS = [
    "bendstiff30",
    "bendstiff60",
    "bendstiff90",
    "axialstiff30",
    "axialstiff60",
    "axialstiff90",
]
CONDITION_COLS = ["curve_id", "load_case", "deployment", "response_axis"]


def select_generated_candidates(
    generated: pd.DataFrame,
    top_k: int,
    metric: str = "closed_loop_scaled_mse",
) -> pd.DataFrame:
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    required = {"sample_id", metric} | {f"generated_{name}" for name in INPUT_COLS}
    missing = required - set(generated.columns)
    if missing:
        raise ValueError(f"generated CSV missing columns: {sorted(missing)}")

    selected = generated.sort_values(metric, kind="mergesort").head(top_k).copy()
    selected.insert(0, "rank", range(1, len(selected) + 1))
    selected["target_sample_id"] = selected["sample_id"].astype(str)
    selected["validation_sample_id"] = [
        f"invval_{rank:04d}_{sample_id}" for rank, sample_id in zip(selected["rank"], selected["target_sample_id"])
    ]
    return selected.reset_index(drop=True)


def make_parameter_table(selected: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for _, row in selected.iterrows():
        out: dict[str, float | int | str] = {
            "sample_id": row["validation_sample_id"],
            "target_sample_id": row["target_sample_id"],
            "source_name": "inverse_diffusion",
            "source_row": int(row["rank"]),
            "closed_loop_scaled_mse": float(row["closed_loop_scaled_mse"]),
        }
        if "closed_loop_selection_score" in row:
            out["closed_loop_selection_score"] = float(row["closed_loop_selection_score"])
        for name in INPUT_COLS:
            out[name] = float(row[f"generated_{name}"])
        for name in STIFFNESS_COLS:
            out[name] = 1.0
        rows.append(out)
    return pd.DataFrame(rows)


def load_condition_schema(original_job_dir: Path) -> pd.DataFrame:
    condition_path = original_job_dir / "condition_schema.csv"
    if condition_path.exists():
        conditions = pd.read_csv(condition_path)
    else:
        jobs_path = original_job_dir / "simulation_jobs.csv"
        if not jobs_path.exists():
            raise FileNotFoundError(f"No condition_schema.csv or simulation_jobs.csv in {original_job_dir}")
        jobs = pd.read_csv(jobs_path)
        missing = set(CONDITION_COLS) - set(jobs.columns)
        if missing:
            raise ValueError(f"simulation_jobs.csv missing condition columns: {sorted(missing)}")
        conditions = jobs[CONDITION_COLS].drop_duplicates().sort_values("curve_id")
    conditions = conditions[CONDITION_COLS].sort_values("curve_id").reset_index(drop=True)
    expected = list(range(len(conditions)))
    actual = conditions["curve_id"].astype(int).tolist()
    if actual != expected:
        raise ValueError(f"curve_id must be contiguous 0..{len(conditions)-1}; got {actual}")
    return conditions


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


def write_validation_inputs(
    generated_csv: Path,
    original_job_dir: Path,
    output_dir: Path,
    top_k: int,
    metric: str,
) -> dict[str, str | int]:
    generated = pd.read_csv(generated_csv)
    selected = select_generated_candidates(generated, top_k=top_k, metric=metric)
    parameters = make_parameter_table(selected)
    conditions = load_condition_schema(original_job_dir)
    jobs = make_simulation_jobs(parameters, conditions)

    reference_job_dir = output_dir / "jobs_reference"
    reference_job_dir.mkdir(parents=True, exist_ok=True)
    selected_path = output_dir / "selected_candidates.csv"
    selected.to_csv(selected_path, index=False)
    parameters.to_csv(reference_job_dir / "parameters.csv", index=False)
    jobs.to_csv(reference_job_dir / "simulation_jobs.csv", index=False)
    conditions.to_csv(reference_job_dir / "condition_schema.csv", index=False)

    metadata = {
        "generated_csv": str(generated_csv),
        "original_job_dir": str(original_job_dir),
        "top_k": int(len(selected)),
        "selection_metric": metric,
        "reference_job_dir": str(reference_job_dir),
        "selected_candidates": str(selected_path),
        "reference_stiffness_workflow": "Run fixed FinalLoad=3, CurvePoints=3 SWOMPS curves, then compute stiffness=final_force/final_displacement.",
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated-csv", type=Path, default=DEFAULT_GENERATED_CSV)
    parser.add_argument("--original-job-dir", type=Path, default=DEFAULT_ORIGINAL_JOB_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--metric", default="closed_loop_scaled_mse")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = write_validation_inputs(
        generated_csv=args.generated_csv,
        original_job_dir=args.original_job_dir,
        output_dir=args.output_dir,
        top_k=args.top_k,
        metric=args.metric,
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
