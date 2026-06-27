"""Prepare paper-oriented Origami validation splits.

The taskfit training scripts consume NPZ files with:
  X_raw: pattern, m, n, tcrease, tpanel, W, creaseE, panelE
  y_raw: bendstiff30, bendstiff60, bendstiff90,
         axialstiff30, axialstiff60, axialstiff90

This script keeps that format and generates split strategies that are more
useful for paper validation than a single random split.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.preprocessing import StandardScaler


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_ROOT = SCRIPT_DIR.parent / "external" / "GenerateOrigamiDataSet"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "data_validation_splits"

INPUT_COLS = ["pattern", "m", "n", "tcrease", "tpanel", "W", "creaseE", "panelE"]
OUTPUT_COLS = [
    "bendstiff30",
    "bendstiff60",
    "bendstiff90",
    "axialstiff30",
    "axialstiff60",
    "axialstiff90",
]
ALL_COLS = INPUT_COLS + OUTPUT_COLS

TXT_FILES = [
    DATA_ROOT / "Data_Origami_Sheet_MaterialProperty" / "Miura" / "MiuraSheetMat.txt",
    DATA_ROOT / "Data_Origami_Sheet_MaterialProperty" / "TMP" / "TMPSheetMat.txt",
]


def load_source_data() -> pd.DataFrame:
    frames = []
    for path in TXT_FILES:
        if not path.exists():
            raise FileNotFoundError(f"Missing source data: {path}")
        frame = pd.read_csv(path, header=None, sep=r"[\s,]+", engine="python")
        if frame.shape[1] != len(ALL_COLS):
            raise ValueError(f"Expected {len(ALL_COLS)} columns in {path}, found {frame.shape[1]}")
        frame.columns = ALL_COLS
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)
    for col in ALL_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna().reset_index(drop=True)
    for col in OUTPUT_COLS:
        df = df[df[col] > 0]
    return df.reset_index(drop=True)


def split_random(df: pd.DataFrame, test_size: float, seed: int) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    train_df, test_df = train_test_split(df, test_size=test_size, random_state=seed, shuffle=True)
    meta = {"split": "random", "test_size": test_size, "seed": seed}
    return train_df.reset_index(drop=True), test_df.reset_index(drop=True), meta


def split_group_pattern_mn(
    df: pd.DataFrame,
    test_size: float,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    groups = df[["pattern", "m", "n"]].astype(str).agg("_".join, axis=1)
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_idx, test_idx = next(splitter.split(df, groups=groups))
    train_df = df.iloc[train_idx].reset_index(drop=True)
    test_df = df.iloc[test_idx].reset_index(drop=True)
    train_groups = set(train_df[["pattern", "m", "n"]].astype(str).agg("_".join, axis=1))
    test_groups = set(test_df[["pattern", "m", "n"]].astype(str).agg("_".join, axis=1))
    meta = {
        "split": "group_pattern_mn",
        "test_size": test_size,
        "seed": seed,
        "train_groups": len(train_groups),
        "test_groups": len(test_groups),
        "group_overlap": len(train_groups.intersection(test_groups)),
    }
    return train_df, test_df, meta


def split_extrapolate_high(
    df: pd.DataFrame,
    column: str,
    test_size: float,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    threshold = float(df[column].quantile(1.0 - test_size))
    train_df = df[df[column] <= threshold].reset_index(drop=True)
    test_df = df[df[column] > threshold].reset_index(drop=True)
    meta = {
        "split": f"extrapolate_high_{column}",
        "column": column,
        "threshold": threshold,
        "train_max": float(train_df[column].max()),
        "test_min": float(test_df[column].min()),
        "requested_test_size": test_size,
        "actual_test_size": len(test_df) / len(df),
    }
    return train_df, test_df, meta


def save_npz_pair(train_df: pd.DataFrame, test_df: pd.DataFrame, out_dir: Path, stem: str, meta: dict) -> None:
    split_dir = out_dir / stem
    split_dir.mkdir(parents=True, exist_ok=True)

    x_train = train_df[INPUT_COLS].to_numpy(dtype=np.float32)
    y_train = train_df[OUTPUT_COLS].to_numpy(dtype=np.float32)
    x_test = test_df[INPUT_COLS].to_numpy(dtype=np.float32)
    y_test = test_df[OUTPUT_COLS].to_numpy(dtype=np.float32)

    scaler_x = StandardScaler()
    scaler_y = StandardScaler()
    x_train_scaled = scaler_x.fit_transform(x_train)
    y_train_scaled = scaler_y.fit_transform(y_train)
    x_test_scaled = scaler_x.transform(x_test)
    y_test_scaled = scaler_y.transform(y_test)

    np.savez(split_dir / "origami_train.npz", X=x_train_scaled, y=y_train_scaled, X_raw=x_train, y_raw=y_train)
    np.savez(split_dir / "origami_test.npz", X=x_test_scaled, y=y_test_scaled, X_raw=x_test, y_raw=y_test)
    train_df.to_csv(split_dir / "train.csv", index=False)
    test_df.to_csv(split_dir / "test.csv", index=False)

    meta = {
        **meta,
        "n_total": int(len(train_df) + len(test_df)),
        "n_train": int(len(train_df)),
        "n_test": int(len(test_df)),
        "input_cols": INPUT_COLS,
        "output_cols": OUTPUT_COLS,
    }
    (split_dir / "split_metadata.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[saved] {stem}: train={len(train_df)} test={len(test_df)} -> {split_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["random", "group_pattern_mn", "extrapolate_high_W"],
        choices=["random", "group_pattern_mn", "extrapolate_high_W"],
    )
    parser.add_argument("--test_size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = load_source_data()
    print(f"[data] loaded {len(df)} samples")

    for split_name in args.splits:
        if split_name == "random":
            train_df, test_df, meta = split_random(df, args.test_size, args.seed)
        elif split_name == "group_pattern_mn":
            train_df, test_df, meta = split_group_pattern_mn(df, args.test_size, args.seed)
        elif split_name == "extrapolate_high_W":
            train_df, test_df, meta = split_extrapolate_high(df, "W", args.test_size)
        else:
            raise ValueError(f"Unknown split: {split_name}")
        save_npz_pair(train_df, test_df, args.output_dir, split_name, meta)


if __name__ == "__main__":
    main()
