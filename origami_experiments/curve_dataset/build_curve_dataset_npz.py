"""Pack exported force-displacement curves into train/test NPZ files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.preprocessing import StandardScaler


SCRIPT_DIR = Path(__file__).resolve().parent

INPUT_COLS = ["pattern", "m", "n", "tcrease", "tpanel", "W", "creaseE", "panelE"]
REQUIRED_CURVE_COLS = {"curve_id", "step", "force", "displacement"}
PHYSICS_COLS = [
    "strain_energy_total",
    "strain_energy_crease",
    "strain_energy_panel",
    "max_bar_stress",
    "max_bar_strain",
    "max_crease_moment",
    "max_crease_rotation",
]


def load_spec(job_dir: Path) -> dict:
    spec_path = job_dir / "dataset_spec.json"
    if not spec_path.exists():
        return {}
    return json.loads(spec_path.read_text(encoding="utf-8"))


def load_condition_schema(job_dir: Path, spec: dict) -> pd.DataFrame:
    condition_path = job_dir / "condition_schema.csv"
    if condition_path.exists():
        conditions = pd.read_csv(condition_path)
    elif "conditions" in spec:
        conditions = pd.DataFrame(spec["conditions"])
    else:
        raise FileNotFoundError(f"No condition schema found in {job_dir}")

    conditions = conditions.sort_values("curve_id").reset_index(drop=True)
    expected = list(range(len(conditions)))
    actual = conditions["curve_id"].astype(int).tolist()
    if actual != expected:
        raise ValueError(f"curve_id must be contiguous 0..{len(conditions) - 1}; got {actual}")
    return conditions


def read_curve_file(curves_dir: Path, sample_id: str) -> pd.DataFrame:
    path = curves_dir / f"{sample_id}.csv"
    if not path.exists():
        raise FileNotFoundError(str(path))
    df = pd.read_csv(path)
    df.columns = [str(col).strip() for col in df.columns]
    missing = REQUIRED_CURVE_COLS - set(df.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
    return df


def stack_one_sample(
    curve_df: pd.DataFrame,
    conditions: pd.DataFrame,
    curve_points: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    force = np.full((len(conditions), curve_points), np.nan, dtype=np.float32)
    displacement = np.full_like(force, np.nan)
    converged = np.zeros_like(force, dtype=bool)
    physics = np.full((len(conditions), curve_points, len(PHYSICS_COLS)), np.nan, dtype=np.float32)

    curve_df = curve_df.copy()
    curve_df["curve_id"] = curve_df["curve_id"].astype(int)
    curve_df["step"] = curve_df["step"].astype(int)

    for curve_id in conditions["curve_id"].astype(int).tolist():
        sub = curve_df.loc[curve_df["curve_id"] == curve_id].sort_values("step")
        if sub.empty:
            raise ValueError(f"curve_id {curve_id} is missing")

        expected_steps = np.arange(1, curve_points + 1)
        actual_steps = sub["step"].to_numpy()
        if not np.array_equal(actual_steps, expected_steps):
            raise ValueError(
                f"curve_id {curve_id} has steps {actual_steps.tolist()}, "
                f"expected {expected_steps.tolist()}"
            )

        force[curve_id, :] = sub["force"].to_numpy(dtype=np.float32)
        displacement[curve_id, :] = sub["displacement"].to_numpy(dtype=np.float32)
        for physics_index, column in enumerate(PHYSICS_COLS):
            if column in sub.columns:
                physics[curve_id, :, physics_index] = sub[column].to_numpy(dtype=np.float32)
        if "converged" in sub.columns:
            converged[curve_id, :] = sub["converged"].astype(bool).to_numpy()
        else:
            converged[curve_id, :] = True

    if not np.isfinite(force).all() or not np.isfinite(displacement).all():
        raise ValueError("curve contains NaN or infinite values")
    if np.isfinite(physics).any() and not np.isfinite(physics).all():
        raise ValueError("physical summary columns are partially missing or contain NaN/Inf")
    if not converged.all():
        raise ValueError("curve has unconverged loading steps")

    return force, displacement, converged, physics


def load_available_curves(
    parameters: pd.DataFrame,
    curves_dir: Path,
    conditions: pd.DataFrame,
    curve_points: int,
    allow_partial: bool,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    complete_rows = []
    forces = []
    displacements = []
    converged_all = []
    physics_all = []
    failures: list[str] = []

    for _, param_row in parameters.iterrows():
        sample_id = str(param_row["sample_id"])
        try:
            curve_df = read_curve_file(curves_dir, sample_id)
            force, displacement, converged, physics = stack_one_sample(curve_df, conditions, curve_points)
        except Exception as exc:  # noqa: BLE001 - collect all sample-level failures for a useful report.
            failures.append(f"{sample_id}: {exc}")
            continue

        complete_rows.append(param_row)
        forces.append(force)
        displacements.append(displacement)
        converged_all.append(converged)
        physics_all.append(physics)

    if failures and not allow_partial:
        preview = "\n".join(failures[:10])
        raise RuntimeError(
            f"{len(failures)} samples are missing or invalid. "
            f"Use --allow-partial to pack complete samples only.\n{preview}"
        )
    if not complete_rows:
        preview = "\n".join(failures[:10])
        raise RuntimeError(f"No complete curve files found in {curves_dir}\n{preview}")

    physics_array = np.stack(physics_all, axis=0)
    if np.isfinite(physics_array).any() and not np.isfinite(physics_array).all():
        raise RuntimeError(
            "Physical summary columns are present for only part of the packed samples. "
            "Use a curves directory where all samples have the physics columns, or none do."
        )

    complete_parameters = pd.DataFrame(complete_rows).reset_index(drop=True)
    return (
        complete_parameters,
        np.stack(forces, axis=0),
        np.stack(displacements, axis=0),
        np.stack(converged_all, axis=0),
        physics_array,
    )


def split_indices(parameters: pd.DataFrame, split: str, test_size: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    indices = np.arange(len(parameters))
    if split == "random":
        return train_test_split(indices, test_size=test_size, random_state=seed, shuffle=True)

    if split == "group_pattern_mn":
        groups = (
            parameters["pattern"].astype(str)
            + "_"
            + parameters["m"].astype(str)
            + "_"
            + parameters["n"].astype(str)
        )
        splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
        return next(splitter.split(indices, groups=groups))

    if split == "extrapolate_high_W":
        threshold = parameters["W"].quantile(1.0 - test_size)
        test_idx = indices[parameters["W"].to_numpy() >= threshold]
        train_idx = indices[parameters["W"].to_numpy() < threshold]
        return train_idx, test_idx

    raise ValueError(f"Unknown split: {split}")


def save_npz(
    path: Path,
    x_scaled: np.ndarray,
    y_scaled: np.ndarray,
    parameters: pd.DataFrame,
    force: np.ndarray,
    displacement: np.ndarray,
    converged: np.ndarray,
    physics: np.ndarray,
    conditions: pd.DataFrame,
) -> None:
    curve = np.stack([displacement, force], axis=-1).astype(np.float32)
    np.savez_compressed(
        path,
        X=x_scaled.astype(np.float32),
        y=y_scaled.astype(np.float32),
        X_raw=parameters[INPUT_COLS].to_numpy(dtype=np.float32),
        y_raw=displacement.astype(np.float32),
        force_raw=force.astype(np.float32),
        curve_raw=curve,
        physics_raw=physics.astype(np.float32),
        converged=converged,
        sample_id=parameters["sample_id"].astype(str).to_numpy(dtype="U"),
        input_cols=np.asarray(INPUT_COLS),
        physics_cols=np.asarray(PHYSICS_COLS),
        condition_curve_id=conditions["curve_id"].to_numpy(dtype=np.int64),
        condition_load_case=conditions["load_case"].astype(str).to_numpy(dtype="U"),
        condition_deployment=conditions["deployment"].to_numpy(dtype=np.float32),
        condition_response_axis=conditions["response_axis"].astype(str).to_numpy(dtype="U"),
    )


def write_metadata(
    output_dir: Path,
    split: str,
    curve_points: int,
    conditions: pd.DataFrame,
    train_params: pd.DataFrame,
    test_params: pd.DataFrame,
    allow_partial: bool,
) -> None:
    metadata = {
        "dataset_name": "origami_force_displacement_curve",
        "split": split,
        "curve_points": curve_points,
        "num_conditions": int(len(conditions)),
        "target_for_model": "y is displacement magnitude flattened as [condition, step]",
        "full_curve_storage": "curve_raw stores [displacement, force] at each condition and step",
        "physics_storage": "physics_raw stores per-step physical summaries listed in physics_cols",
        "input_columns": INPUT_COLS,
        "physics_columns": PHYSICS_COLS,
        "train_samples": int(len(train_params)),
        "test_samples": int(len(test_params)),
        "allow_partial": allow_partial,
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-dir", type=Path, default=SCRIPT_DIR / "jobs")
    parser.add_argument("--curves-dir", type=Path, default=SCRIPT_DIR / "raw_curves")
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR / "data")
    parser.add_argument(
        "--split",
        choices=["random", "group_pattern_mn", "extrapolate_high_W"],
        default="random",
    )
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--curve-points", type=int, default=None)
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Pack only samples with complete curve CSV files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spec = load_spec(args.job_dir)
    curve_points = int(args.curve_points or spec.get("curve_points", 30))
    if curve_points < 2:
        raise ValueError("--curve-points must be at least 2")
    if not (0.0 < args.test_size < 1.0):
        raise ValueError("--test-size must be between 0 and 1")

    parameter_path = args.job_dir / "parameters.csv"
    if not parameter_path.exists():
        raise FileNotFoundError(f"Missing parameter table: {parameter_path}")
    parameters = pd.read_csv(parameter_path)
    conditions = load_condition_schema(args.job_dir, spec)

    parameters, force, displacement, converged, physics = load_available_curves(
        parameters,
        args.curves_dir,
        conditions,
        curve_points,
        args.allow_partial,
    )

    train_idx, test_idx = split_indices(parameters, args.split, args.test_size, args.seed)
    train_params = parameters.iloc[train_idx].reset_index(drop=True)
    test_params = parameters.iloc[test_idx].reset_index(drop=True)

    x_scaler = StandardScaler()
    y_scaler = StandardScaler()
    x_train_raw = train_params[INPUT_COLS].to_numpy(dtype=np.float32)
    x_test_raw = test_params[INPUT_COLS].to_numpy(dtype=np.float32)
    y_train_raw = displacement[train_idx].reshape(len(train_idx), -1)
    y_test_raw = displacement[test_idx].reshape(len(test_idx), -1)

    x_train = x_scaler.fit_transform(x_train_raw)
    x_test = x_scaler.transform(x_test_raw)
    y_train = y_scaler.fit_transform(y_train_raw)
    y_test = y_scaler.transform(y_test_raw)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_npz(
        args.output_dir / "origami_curve_train.npz",
        x_train,
        y_train,
        train_params,
        force[train_idx],
        displacement[train_idx],
        converged[train_idx],
        physics[train_idx],
        conditions,
    )
    save_npz(
        args.output_dir / "origami_curve_test.npz",
        x_test,
        y_test,
        test_params,
        force[test_idx],
        displacement[test_idx],
        converged[test_idx],
        physics[test_idx],
        conditions,
    )
    joblib.dump(x_scaler, args.output_dir / "scaler_x.pkl")
    joblib.dump(y_scaler, args.output_dir / "scaler_y.pkl")
    train_params.to_csv(args.output_dir / "train_samples.csv", index=False)
    test_params.to_csv(args.output_dir / "test_samples.csv", index=False)
    write_metadata(
        args.output_dir,
        args.split,
        curve_points,
        conditions,
        train_params,
        test_params,
        args.allow_partial,
    )

    print(f"Packed complete samples: {len(parameters)}")
    print(f"Train/test: {len(train_idx)} / {len(test_idx)}")
    print(f"Target displacement shape: {displacement.shape}")
    print(f"Saved: {args.output_dir}")


if __name__ == "__main__":
    main()
