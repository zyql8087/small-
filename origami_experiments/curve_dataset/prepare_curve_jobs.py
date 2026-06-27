"""Create parameter/job tables for the origami curve-response dataset.

The original dataset maps:
    8 design parameters -> 6 scalar stiffness values

This script reuses the same 8 design parameters and loading cases, but
prepares jobs for:
    8 design parameters -> multi-condition force-displacement curves
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = EXPERIMENT_DIR.parent
DATA_ROOT = PROJECT_ROOT / "external" / "GenerateOrigamiDataSet"

INPUT_COLS = ["pattern", "m", "n", "tcrease", "tpanel", "W", "creaseE", "panelE"]
STIFFNESS_COLS = [
    "bendstiff30",
    "bendstiff60",
    "bendstiff90",
    "axialstiff30",
    "axialstiff60",
    "axialstiff90",
]

SOURCE_FILE_MAP = {
    "miura": DATA_ROOT / "Data_Origami_Sheet_MaterialProperty" / "Miura" / "MiuraSheetMat.txt",
    "tmp": DATA_ROOT / "Data_Origami_Sheet_MaterialProperty" / "TMP" / "TMPSheetMat.txt",
}
SOURCE_ORDER = ["miura", "tmp"]

CONDITIONS = [
    {"curve_id": 0, "load_case": "bending", "deployment": 0.3, "response_axis": "z"},
    {"curve_id": 1, "load_case": "bending", "deployment": 0.6, "response_axis": "z"},
    {"curve_id": 2, "load_case": "bending", "deployment": 0.9, "response_axis": "z"},
    {"curve_id": 3, "load_case": "axial", "deployment": 0.3, "response_axis": "x"},
    {"curve_id": 4, "load_case": "axial", "deployment": 0.6, "response_axis": "x"},
    {"curve_id": 5, "load_case": "axial", "deployment": 0.9, "response_axis": "x"},
]


def load_txt(path: Path) -> np.ndarray:
    rows: list[list[float]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append([float(value) for value in line.split(",")])
    if not rows:
        raise ValueError(f"No rows found in {path}")
    return np.asarray(rows, dtype=np.float64)


def selected_source_files(source: str) -> list[tuple[str, Path]]:
    if source == "all":
        return [(name, SOURCE_FILE_MAP[name]) for name in SOURCE_ORDER]
    return [(source, SOURCE_FILE_MAP[source])]


def load_source_parameters(source: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for source_name, path in selected_source_files(source):
        if not path.exists():
            raise FileNotFoundError(f"Missing source file: {path}")

        arr = load_txt(path)
        if arr.shape[1] < len(INPUT_COLS) + len(STIFFNESS_COLS):
            raise ValueError(f"{path} has {arr.shape[1]} columns; expected at least 14")

        df = pd.DataFrame(arr[:, :14], columns=INPUT_COLS + STIFFNESS_COLS)
        df.insert(0, "source_row", np.arange(1, len(df) + 1, dtype=np.int64))
        df.insert(0, "source_name", source_name)
        df.insert(0, "sample_id", [f"{source_name}_{i:05d}" for i in range(1, len(df) + 1)])
        frames.append(df)

    out = pd.concat(frames, ignore_index=True)
    out["pattern"] = out["pattern"].astype(int)
    out["m"] = out["m"].astype(int)
    out["n"] = out["n"].astype(int)
    return out


def sample_rows(df: pd.DataFrame, sample_count: int | None, seed: int) -> pd.DataFrame:
    if sample_count is None or sample_count >= len(df):
        return df.sort_values("sample_id").reset_index(drop=True)
    if sample_count <= 0:
        raise ValueError("--sample-count must be positive")

    rng = np.random.default_rng(seed)
    per_source = max(1, sample_count // df["source_name"].nunique())
    sampled_parts = []
    for _, group in df.groupby("source_name", sort=True):
        take = min(per_source, len(group))
        sampled_parts.append(group.sample(n=take, random_state=int(rng.integers(0, 2**31 - 1))))

    sampled = pd.concat(sampled_parts, ignore_index=True)
    remaining = sample_count - len(sampled)
    if remaining > 0:
        rest = df.loc[~df["sample_id"].isin(sampled["sample_id"])]
        sampled = pd.concat(
            [
                sampled,
                rest.sample(n=min(remaining, len(rest)), random_state=int(rng.integers(0, 2**31 - 1))),
            ],
            ignore_index=True,
        )
    return sampled.sort_values("sample_id").reset_index(drop=True)


def build_simulation_jobs(parameters: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, param_row in parameters.iterrows():
        for condition in CONDITIONS:
            row = {
                "sample_id": param_row["sample_id"],
                "source_name": param_row["source_name"],
                "source_row": int(param_row["source_row"]),
                **condition,
            }
            for col in INPUT_COLS:
                row[col] = param_row[col]
            rows.append(row)
    return pd.DataFrame(rows)


def write_spec(output_dir: Path, parameters: pd.DataFrame, curve_points: int, seed: int, source: str) -> None:
    source_label = "Miura/TMP" if source == "all" else source.capitalize()
    spec = {
        "dataset_name": "origami_force_displacement_curve",
        "source": f"GenerateOrigamiDataSet MaterialProperty {source_label} parameter rows",
        "source_filter": source,
        "source_files": {name: str(path) for name, path in selected_source_files(source)},
        "mapping": "X_original_parameters -> 6 force-displacement response curves",
        "input_columns": INPUT_COLS,
        "original_stiffness_columns_kept_for_qc": STIFFNESS_COLS,
        "curve_points": curve_points,
        "conditions": CONDITIONS,
        "num_samples": int(len(parameters)),
        "random_seed": seed,
        "notes": [
            "Each curve is a discretized load path, matching GraphMetaMat's dataset idea of storing a full physical response as an array.",
            "For SWOMPS NR loading, force is prescribed step-by-step and displacement is measured from Uhis.",
            "The original scalar stiffness labels are not used as ML targets in this new dataset.",
        ],
    }
    (output_dir / "dataset_spec.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=SCRIPT_DIR / "jobs",
        help="Directory for parameters.csv, simulation_jobs.csv, and dataset_spec.json.",
    )
    parser.add_argument(
        "--sample-count",
        type=int,
        default=None,
        help="Optional subset size for smoke tests or staged simulations. Default: all rows.",
    )
    parser.add_argument(
        "--source",
        choices=["miura", "tmp", "all"],
        default="all",
        help="Source pattern family to include in the generated job tables.",
    )
    parser.add_argument(
        "--curve-points",
        type=int,
        default=30,
        help="Number of discrete loading steps per force-displacement curve.",
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.curve_points < 2:
        raise ValueError("--curve-points must be at least 2")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    parameters = sample_rows(load_source_parameters(args.source), args.sample_count, args.seed)
    jobs = build_simulation_jobs(parameters)
    conditions = pd.DataFrame(CONDITIONS)

    parameters.to_csv(args.output_dir / "parameters.csv", index=False)
    jobs.to_csv(args.output_dir / "simulation_jobs.csv", index=False)
    conditions.to_csv(args.output_dir / "condition_schema.csv", index=False)
    write_spec(args.output_dir, parameters, args.curve_points, args.seed, args.source)

    print(f"Saved parameters: {args.output_dir / 'parameters.csv'} ({len(parameters)} samples)")
    print(f"Saved jobs:       {args.output_dir / 'simulation_jobs.csv'} ({len(jobs)} rows)")
    print(f"Saved conditions: {args.output_dir / 'condition_schema.csv'}")
    print(f"Curve points per condition: {args.curve_points}")


if __name__ == "__main__":
    main()
