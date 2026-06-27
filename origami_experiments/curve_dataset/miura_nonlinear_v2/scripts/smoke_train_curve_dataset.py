"""Smoke train simple MLPs on the force-displacement curve dataset.

This is intentionally small and self-contained. It verifies that the new
curve dataset can be loaded and optimized before adapting the full models.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = SCRIPT_DIR.parent
DEFAULT_DATA_DIR = EXPERIMENT_DIR / "data"
DEFAULT_RESULT_DIR = EXPERIMENT_DIR / "smoke_results"


class SmokeMLP(nn.Module):
    def __init__(self, input_dim: int, output_dim: int, hidden_dim: int, dropout: float) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_npz_pair(data_dir: Path) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    train_path = data_dir / "origami_curve_train.npz"
    test_path = data_dir / "origami_curve_test.npz"
    if not train_path.exists() or not test_path.exists():
        raise FileNotFoundError(f"Missing train/test npz under {data_dir}")

    train = dict(np.load(train_path))
    test = dict(np.load(test_path))
    required = ["X", "y", "X_raw", "y_raw", "force_raw", "curve_raw", "converged"]
    for split_name, split in [("train", train), ("test", test)]:
        missing = [key for key in required if key not in split]
        if missing:
            raise KeyError(f"{split_name} split missing keys: {missing}")
        if not split["converged"].all():
            raise ValueError(f"{split_name} split contains unconverged loading steps")
        if split["y_raw"].ndim != 3 or split["curve_raw"].ndim != 4:
            raise ValueError(f"{split_name} split has unexpected curve dimensions")
    return train, test


def make_loader(x: np.ndarray, y: np.ndarray, batch_size: int, shuffle: bool) -> DataLoader:
    dataset = TensorDataset(
        torch.tensor(x, dtype=torch.float32),
        torch.tensor(y, dtype=torch.float32),
    )
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)


def standardize_from_train(train_values: np.ndarray, test_values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = train_values.mean(axis=0, keepdims=True)
    std = train_values.std(axis=0, keepdims=True)
    std = np.where(std < 1e-12, 1.0, std)
    return (train_values - mean) / std, (test_values - mean) / std


def flatten_physics(split: dict[str, np.ndarray], split_name: str) -> np.ndarray:
    if "physics_raw" not in split:
        raise KeyError(f"{split_name} split missing physics_raw")
    physics = split["physics_raw"].astype(np.float32)
    if not np.isfinite(physics).all():
        raise ValueError(
            f"{split_name} split physics_raw contains NaN/Inf. "
            "Use displacement-only mode for archived legacy data."
        )
    return physics.reshape(physics.shape[0], -1)


def prepare_targets(
    train: dict[str, np.ndarray],
    test: dict[str, np.ndarray],
    target_mode: str,
) -> tuple[np.ndarray, np.ndarray, dict[str, int | str]]:
    displacement_train = train["y"].astype(np.float32)
    displacement_test = test["y"].astype(np.float32)
    target_info: dict[str, int | str] = {
        "target_mode": target_mode,
        "displacement_target_dim": int(displacement_train.shape[1]),
        "physics_target_dim": 0,
    }

    if target_mode == "displacement":
        return displacement_train, displacement_test, target_info

    physics_train_raw = flatten_physics(train, "train")
    physics_test_raw = flatten_physics(test, "test")
    physics_train, physics_test = standardize_from_train(physics_train_raw, physics_test_raw)
    target_info["physics_target_dim"] = int(physics_train.shape[1])

    if target_mode == "physics":
        return physics_train.astype(np.float32), physics_test.astype(np.float32), target_info
    if target_mode == "displacement_physics":
        return (
            np.concatenate([displacement_train, physics_train.astype(np.float32)], axis=1),
            np.concatenate([displacement_test, physics_test.astype(np.float32)], axis=1),
            target_info,
        )
    raise ValueError(f"Unsupported target mode: {target_mode}")


@torch.no_grad()
def evaluate(model: nn.Module, x: np.ndarray, y: np.ndarray, device: torch.device) -> float:
    model.eval()
    x_tensor = torch.tensor(x, dtype=torch.float32, device=device)
    y_tensor = torch.tensor(y, dtype=torch.float32, device=device)
    pred = model(x_tensor)
    return torch.mean((pred - y_tensor) ** 2).item()


def train_model(
    name: str,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    y_test: np.ndarray,
    args: argparse.Namespace,
    device: torch.device,
) -> tuple[dict[str, float], list[dict[str, float]]]:
    model = SmokeMLP(
        input_dim=x_train.shape[1],
        output_dim=y_train.shape[1],
        hidden_dim=args.hidden_dim,
        dropout=args.dropout,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    loss_fn = nn.MSELoss()
    loader = make_loader(x_train, y_train, args.batch_size, shuffle=True)

    initial_train_mse = evaluate(model, x_train, y_train, device)
    initial_test_mse = evaluate(model, x_test, y_test, device)
    history: list[dict[str, float]] = []

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        seen = 0
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(batch_x), batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * batch_x.size(0)
            seen += batch_x.size(0)

        if epoch == 1 or epoch % args.log_every == 0 or epoch == args.epochs:
            train_mse = evaluate(model, x_train, y_train, device)
            test_mse = evaluate(model, x_test, y_test, device)
            history.append(
                {
                    "model": name,
                    "epoch": epoch,
                    "batch_train_mse": total_loss / max(seen, 1),
                    "train_mse": train_mse,
                    "test_mse": test_mse,
                }
            )

    final_train_mse = evaluate(model, x_train, y_train, device)
    final_test_mse = evaluate(model, x_test, y_test, device)
    metrics = {
        "initial_train_mse": initial_train_mse,
        "initial_test_mse": initial_test_mse,
        "final_train_mse": final_train_mse,
        "final_test_mse": final_test_mse,
        "train_mse_reduction": initial_train_mse - final_train_mse,
        "train_mse_reduction_ratio": (initial_train_mse - final_train_mse) / max(initial_train_mse, 1e-12),
    }
    return metrics, history


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--result-dir", type=Path, default=DEFAULT_RESULT_DIR)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--dropout", type=float, default=0.0)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--log-every", type=int, default=25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"], default="cpu")
    parser.add_argument(
        "--target-mode",
        choices=["displacement", "physics", "displacement_physics"],
        default="displacement_physics",
        help="Smoke-test target. displacement_physics uses the optimized physical histories as ML targets.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but torch.cuda.is_available() is false")

    train, test = load_npz_pair(args.data_dir)
    x_train = train["X"].astype(np.float32)
    x_test = test["X"].astype(np.float32)
    y_train, y_test, target_info = prepare_targets(train, test, args.target_mode)

    args.result_dir.mkdir(parents=True, exist_ok=True)

    forward_metrics, forward_history = train_model(
        "forward_x_to_curve",
        x_train,
        y_train,
        x_test,
        y_test,
        args,
        device,
    )
    inverse_metrics, inverse_history = train_model(
        "inverse_curve_to_x",
        y_train,
        x_train,
        y_test,
        x_test,
        args,
        device,
    )

    metrics = {
        "device": str(device),
        "torch_version": torch.__version__,
        "train_samples": int(x_train.shape[0]),
        "test_samples": int(x_test.shape[0]),
        "diagnostic_only": bool(x_train.shape[0] < 10 or x_test.shape[0] < 5),
        "diagnostic_note": (
            "Training metrics are protocol-only because train/test sample counts are small."
            if x_train.shape[0] < 10 or x_test.shape[0] < 5
            else ""
        ),
        "x_dim": int(x_train.shape[1]),
        "curve_dim": int(y_train.shape[1]),
        "curve_raw_shape_train": list(train["curve_raw"].shape),
        "curve_raw_shape_test": list(test["curve_raw"].shape),
        "target": target_info,
        "forward_x_to_curve": forward_metrics,
        "inverse_curve_to_x": inverse_metrics,
    }
    (args.result_dir / "curve_smoke_metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    pd.DataFrame(forward_history + inverse_history).to_csv(
        args.result_dir / "curve_smoke_history.csv",
        index=False,
    )

    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
