"""
Prepare origami sheet dataset for TPMS model training.

Reads MaterialProperty TXT files (Miura + TMP), concatenates,
splits train/test, applies StandardScaler, saves as .npz.

Input columns (8):  pattern, m, n, tcrease, tpanel, W, creaseE, panelE
Output columns (6): bendstiff30, bendstiff60, bendstiff90, axialstiff30, axialstiff60, axialstiff90
"""

import os
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

DATA_ROOT = Path(__file__).resolve().parent.parent / "external" / "GenerateOrigamiDataSet"
OUTPUT_DIR = Path(__file__).resolve().parent / "data"
RANDOM_SEED = 42

INPUT_COLS = ["pattern", "m", "n", "tcrease", "tpanel", "W", "creaseE", "panelE"]
OUTPUT_COLS = [
    "bendstiff30", "bendstiff60", "bendstiff90",
    "axialstiff30", "axialstiff60", "axialstiff90",
]

TXT_FILES = [
    DATA_ROOT / "Data_Origami_Sheet_MaterialProperty" / "Miura" / "MiuraSheetMat.txt",
    DATA_ROOT / "Data_Origami_Sheet_MaterialProperty" / "TMP" / "TMPSheetMat.txt",
]


def load_txt(path: Path) -> np.ndarray:
    """Load space-delimited origami TXT file as numpy array."""
    data = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data.append([float(x) for x in line.split(",")])
    return np.array(data)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load and concatenate all data
    arrays = []
    for path in TXT_FILES:
        if not path.exists():
            print(f"[WARN] File not found: {path}")
            continue
        arr = load_txt(path)
        print(f"  Loaded {path.name}: {arr.shape[0]} samples, {arr.shape[1]} columns")
        arrays.append(arr)

    data_all = np.concatenate(arrays, axis=0)
    print(f"\nTotal samples: {data_all.shape[0]}")

    # Columns: 0-7 = inputs (8), 8-13 = outputs (6)
    X = data_all[:, :8].astype(np.float32)
    y = data_all[:, 8:14].astype(np.float32)

    print(f"  X shape: {X.shape}  (8 input features)")
    print(f"  y shape: {y.shape}  (6 output targets)")

    # Summary statistics
    print("\n--- Input feature statistics ---")
    for i, col in enumerate(INPUT_COLS):
        vals = X[:, i]
        print(f"  {col:>12s}: min={vals.min():.4e}, max={vals.max():.4e}, mean={vals.mean():.4e}")

    print("\n--- Output target statistics ---")
    for i, col in enumerate(OUTPUT_COLS):
        vals = y[:, i]
        print(f"  {col:>12s}: min={vals.min():.2f}, max={vals.max():.2f}, mean={vals.mean():.2f}")

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED
    )

    # Standardization
    scaler_x = StandardScaler()
    scaler_y = StandardScaler()
    X_train_scaled = scaler_x.fit_transform(X_train)
    y_train_scaled = scaler_y.fit_transform(y_train)
    X_test_scaled = scaler_x.transform(X_test)
    y_test_scaled = scaler_y.transform(y_test)

    # Save
    train_path = OUTPUT_DIR / "origami_train.npz"
    test_path = OUTPUT_DIR / "origami_test.npz"
    np.savez(train_path, X=X_train_scaled, y=y_train_scaled, X_raw=X_train, y_raw=y_train)
    np.savez(test_path, X=X_test_scaled, y=y_test_scaled, X_raw=X_test, y_raw=y_test)

    # Save scalers
    import joblib
    joblib.dump(scaler_x, OUTPUT_DIR / "scaler_x.pkl")
    joblib.dump(scaler_y, OUTPUT_DIR / "scaler_y.pkl")

    print(f"\nSaved:")
    print(f"  Train: {train_path} ({X_train.shape[0]} samples)")
    print(f"  Test:  {test_path} ({X_test.shape[0]} samples)")
    print(f"  Scalers: scaler_x.pkl, scaler_y.pkl")
    print("[DONE]")


if __name__ == "__main__":
    main()
