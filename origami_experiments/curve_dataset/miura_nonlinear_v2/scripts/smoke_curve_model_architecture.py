"""Smoke-test curve-aware forward and inverse models on the Miura nonlinear NPZ."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = SCRIPT_DIR.parent
REPO_ROOT = SCRIPT_DIR.parents[3]
sys.path.insert(0, str(REPO_ROOT))

from origami_experiments.modules.origami_curve_models import (  # noqa: E402
    OrigamiCurveConditionalDiffusion,
    OrigamiCurveGNNTransformerForward,
    build_parameter_adjacency,
)


DEFAULT_DATA_DIR = EXPERIMENT_DIR / "data"
DEFAULT_RESULT_DIR = EXPERIMENT_DIR / "smoke_results"


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_train_split(data_dir: Path) -> dict[str, np.ndarray]:
    train_path = data_dir / "origami_curve_train.npz"
    if not train_path.exists():
        raise FileNotFoundError(f"Missing train NPZ: {train_path}")
    split = dict(np.load(train_path))
    required = ["X", "X_raw", "curve_raw", "converged"]
    missing = [key for key in required if key not in split]
    if missing:
        raise KeyError(f"Train split missing keys: {missing}")
    if split["curve_raw"].ndim != 4 or split["curve_raw"].shape[1:] != (6, 80, 2):
        raise ValueError(f"Unexpected curve_raw shape: {split['curve_raw'].shape}")
    if not split["converged"].all():
        raise ValueError("Train split contains unconverged loading steps")
    return split


def category_ids_from_raw(x_raw: np.ndarray) -> np.ndarray:
    cats = []
    for col in range(3):
        values = np.unique(x_raw[:, col])
        value_to_id = {float(value): idx for idx, value in enumerate(sorted(values.tolist()))}
        cats.append(np.array([value_to_id[float(value)] for value in x_raw[:, col]], dtype=np.int64))
    return np.stack(cats, axis=1)


def normalize_curve(curve_raw: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = curve_raw.mean(axis=(0, 1, 2), keepdims=True)
    std = curve_raw.std(axis=(0, 1, 2), keepdims=True)
    std = np.where(std < 1e-12, 1.0, std)
    return ((curve_raw - mean) / std).astype(np.float32), mean.astype(np.float32), std.astype(np.float32)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--result-dir", type=Path, default=DEFAULT_RESULT_DIR)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"], default="cpu")
    parser.add_argument("--seed", type=int, default=42)
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

    split = load_train_split(args.data_dir)
    x_raw = split["X_raw"].astype(np.float32)
    x_scaled = split["X"].astype(np.float32)
    curve_scaled, curve_mean, curve_std = normalize_curve(split["curve_raw"].astype(np.float32))
    cat_ids = category_ids_from_raw(x_raw)
    cont_scaled = x_scaled[:, 3:].astype(np.float32)

    batch_size = min(args.batch_size, x_raw.shape[0])
    batch_cat = torch.tensor(cat_ids[:batch_size], dtype=torch.long, device=device)
    batch_cont = torch.tensor(cont_scaled[:batch_size], dtype=torch.float32, device=device)
    batch_curve = torch.tensor(curve_scaled[:batch_size], dtype=torch.float32, device=device)
    batch_target = torch.tensor(x_scaled[:batch_size], dtype=torch.float32, device=device)

    forward_model = OrigamiCurveGNNTransformerForward(
        hidden_dim=args.hidden_dim,
        gnn_heads=4,
        num_heads=4,
        encoder_layers=1,
        decoder_layers=1,
        num_curve_points=80,
        curve_channels=2,
        dropout=0.0,
    ).to(device)
    inverse_model = OrigamiCurveConditionalDiffusion(
        target_dim=8,
        curve_channels=2,
        physics_channels=0,
        hidden_dim=args.hidden_dim * 4,
        cond_dim=args.hidden_dim,
        time_dim=32,
        num_curve_points=80,
        encoder_layers=1,
        num_heads=4,
        dropout=0.0,
    ).to(device)

    adj = build_parameter_adjacency(device=device)
    forward_optim = torch.optim.AdamW(forward_model.parameters(), lr=1e-4)
    inverse_optim = torch.optim.AdamW(inverse_model.parameters(), lr=1e-4)

    forward_optim.zero_grad(set_to_none=True)
    pred_curve = forward_model(batch_cat, batch_cont, adj)
    forward_loss = F.mse_loss(pred_curve, batch_curve)
    forward_loss.backward()
    forward_optim.step()

    t = torch.randint(0, 1000, (batch_size,), dtype=torch.long, device=device)
    noise = torch.randn_like(batch_target)
    x_t = batch_target + noise * 0.1
    inverse_optim.zero_grad(set_to_none=True)
    pred_noise = inverse_model(x_t, t, batch_curve)
    inverse_loss = F.mse_loss(pred_noise, noise)
    inverse_loss.backward()
    inverse_optim.step()

    metrics = {
        "device": str(device),
        "batch_size": int(batch_size),
        "curve_raw_shape": list(split["curve_raw"].shape),
        "forward_output_shape": list(pred_curve.shape),
        "inverse_output_shape": list(pred_noise.shape),
        "forward_loss": float(forward_loss.detach().cpu()),
        "inverse_loss": float(inverse_loss.detach().cpu()),
        "curve_channel_mean": curve_mean.reshape(-1).tolist(),
        "curve_channel_std": curve_std.reshape(-1).tolist(),
    }

    args.result_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.result_dir / "curve_architecture_smoke.json"
    out_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"[Saved] {out_path}")


if __name__ == "__main__":
    main()
