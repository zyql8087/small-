"""Train inverse diffusion on Miura force-displacement curves and run closed-loop validation."""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

import joblib
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = SCRIPT_DIR.parent
REPO_ROOT = SCRIPT_DIR.parents[3]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

from origami_experiments.modules.origami_curve_models import (  # noqa: E402
    OrigamiCurveConditionalDiffusion,
    OrigamiCurveGNNTransformerForward,
    build_parameter_adjacency,
)
from train_curve_forward_gnn_transformer import (  # noqa: E402
    apply_continuous_feature_stats,
    denormalized_curve_metrics,
)


DEFAULT_DATA_DIR = EXPERIMENT_DIR / "data_random_quality_filtered"
DEFAULT_FORWARD_RESULT_DIR = EXPERIMENT_DIR / "training_results" / "curve_forward_quality_filtered_random_50ep_v13"
DEFAULT_RESULT_DIR = EXPERIMENT_DIR / "training_results" / "inverse_diffusion_quality_filtered"
INPUT_COLS = ["pattern", "m", "n", "tcrease", "tpanel", "W", "creaseE", "panelE"]


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def json_ready(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    return value


def load_json(path: Path) -> dict:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "utf-8", "gbk"):
        try:
            return json.loads(data.decode(encoding))
        except Exception:  # noqa: BLE001 - try common local encodings.
            pass
    raise UnicodeError(f"Could not decode JSON file: {path}")


def load_npz_pair(data_dir: Path) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    train_path = data_dir / "origami_curve_train.npz"
    test_path = data_dir / "origami_curve_test.npz"
    if not train_path.exists() or not test_path.exists():
        raise FileNotFoundError(f"Missing train/test NPZ under {data_dir}")
    train = dict(np.load(train_path))
    test = dict(np.load(test_path))
    required = ["X", "X_raw", "curve_raw", "converged", "sample_id"]
    for name, split in [("train", train), ("test", test)]:
        missing = [key for key in required if key not in split]
        if missing:
            raise KeyError(f"{name} split missing keys: {missing}")
        if split["curve_raw"].shape[1:] != (6, 80, 2):
            raise ValueError(f"{name} curve_raw shape must be [N, 6, 80, 2], got {split['curve_raw'].shape}")
        if not split["converged"].all():
            raise ValueError(f"{name} split contains unconverged curve steps")
    return train, test


class CurveChannelScaler:
    def __init__(self) -> None:
        self.mean: np.ndarray | None = None
        self.std: np.ndarray | None = None

    def fit(self, curves: np.ndarray) -> "CurveChannelScaler":
        self.mean = curves.mean(axis=(0, 1, 2), keepdims=True).astype(np.float32)
        std = curves.std(axis=(0, 1, 2), keepdims=True)
        self.std = np.where(std < 1e-12, 1.0, std).astype(np.float32)
        return self

    def transform(self, curves: np.ndarray) -> np.ndarray:
        if self.mean is None or self.std is None:
            raise RuntimeError("CurveChannelScaler must be fitted before transform")
        return ((curves - self.mean) / self.std).astype(np.float32)

    def inverse_transform(self, curves: np.ndarray) -> np.ndarray:
        if self.mean is None or self.std is None:
            raise RuntimeError("CurveChannelScaler must be fitted before inverse_transform")
        return (curves * self.std + self.mean).astype(np.float32)

    def state_dict(self) -> dict[str, list[float]]:
        if self.mean is None or self.std is None:
            raise RuntimeError("CurveChannelScaler must be fitted before serialization")
        return {"mean": self.mean.reshape(-1).tolist(), "std": self.std.reshape(-1).tolist()}


class DiffusionSchedule:
    def __init__(self, steps: int, beta_start: float, beta_end: float, device: torch.device) -> None:
        if steps < 2:
            raise ValueError("Diffusion steps must be at least 2")
        self.steps = steps
        self.betas = torch.linspace(beta_start, beta_end, steps, dtype=torch.float32, device=device)
        self.alphas = 1.0 - self.betas
        self.alpha_bars = torch.cumprod(self.alphas, dim=0)

    def q_sample(self, x0: torch.Tensor, t: torch.Tensor, noise: torch.Tensor) -> torch.Tensor:
        alpha_bar = self.alpha_bars[t].view(-1, 1)
        return alpha_bar.sqrt() * x0 + (1.0 - alpha_bar).sqrt() * noise


def fit_curve_scaler(train: dict[str, np.ndarray], test: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, CurveChannelScaler]:
    scaler = CurveChannelScaler().fit(train["curve_raw"].astype(np.float32))
    return (
        scaler.transform(train["curve_raw"].astype(np.float32)),
        scaler.transform(test["curve_raw"].astype(np.float32)),
        scaler,
    )


def make_loader(curve_scaled: np.ndarray, x_scaled: np.ndarray, batch_size: int, shuffle: bool) -> DataLoader:
    dataset = TensorDataset(
        torch.tensor(curve_scaled, dtype=torch.float32),
        torch.tensor(x_scaled.astype(np.float32), dtype=torch.float32),
    )
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)


def category_values_from_raw(*x_raw_splits: np.ndarray) -> list[np.ndarray]:
    stacked = np.concatenate([split[:, :3] for split in x_raw_splits], axis=0)
    return [np.unique(stacked[:, i].astype(np.float32)) for i in range(3)]


def snap_and_clip_raw_parameters(
    raw: np.ndarray,
    category_values: list[np.ndarray],
    continuous_min: np.ndarray,
    continuous_max: np.ndarray,
) -> np.ndarray:
    snapped = raw.astype(np.float32).copy()
    for col, values in enumerate(category_values):
        distances = np.abs(snapped[:, col : col + 1] - values.reshape(1, -1))
        snapped[:, col] = values[np.argmin(distances, axis=1)]
    snapped[:, 3:] = np.clip(snapped[:, 3:], continuous_min.reshape(1, -1), continuous_max.reshape(1, -1))
    return snapped.astype(np.float32)


def category_ids_from_raw(raw: np.ndarray, category_values: list[np.ndarray]) -> np.ndarray:
    ids = []
    for col, values in enumerate(category_values):
        value_to_id = {float(value): idx for idx, value in enumerate(values.astype(float).tolist())}
        ids.append(np.array([value_to_id[float(value)] for value in raw[:, col]], dtype=np.int64))
    return np.stack(ids, axis=1)


def curve_channel_metrics(pred_curve: np.ndarray, target_curve: np.ndarray) -> dict[str, float]:
    pred_curve = pred_curve.astype(np.float32)
    target_curve = target_curve.astype(np.float32)
    metrics = denormalized_curve_metrics(pred_curve, target_curve)
    metrics["negative_displacement_fraction"] = float(np.mean(pred_curve[..., 0] < 0.0))
    metrics["negative_force_fraction"] = float(np.mean(pred_curve[..., 1] < 0.0))
    return metrics


def parameter_metrics(pred_scaled: np.ndarray, target_scaled: np.ndarray, pred_raw: np.ndarray, target_raw: np.ndarray) -> dict[str, float]:
    scaled_diff = pred_scaled - target_scaled
    raw_diff = pred_raw - target_raw
    metrics: dict[str, float] = {
        "scaled_mse": float(np.mean(scaled_diff**2)),
        "scaled_rmse": float(np.sqrt(np.mean(scaled_diff**2))),
        "raw_mae_mean": float(np.mean(np.abs(raw_diff))),
    }
    for idx, name in enumerate(INPUT_COLS):
        metrics[f"{name}_raw_mae"] = float(np.mean(np.abs(raw_diff[:, idx])))
        metrics[f"{name}_scaled_rmse"] = float(np.sqrt(np.mean(scaled_diff[:, idx] ** 2)))
    return metrics


def reasonableness_metrics(raw_before: np.ndarray, raw_after: np.ndarray, category_values: list[np.ndarray]) -> dict[str, float]:
    category_valid = []
    for col, values in enumerate(category_values):
        valid = np.isin(raw_after[:, col], values.astype(raw_after.dtype))
        category_valid.append(valid)
    category_valid_array = np.stack(category_valid, axis=1)
    return {
        "category_valid_fraction": float(np.mean(category_valid_array)),
        "category_adjustment_mae": float(np.mean(np.abs(raw_before[:, :3] - raw_after[:, :3]))),
        "continuous_clip_fraction": float(np.mean(np.abs(raw_before[:, 3:] - raw_after[:, 3:]) > 1e-8)),
        "continuous_adjustment_mae": float(np.mean(np.abs(raw_before[:, 3:] - raw_after[:, 3:]))),
    }


def train_epoch(
    model: OrigamiCurveConditionalDiffusion,
    loader: DataLoader,
    schedule: DiffusionSchedule,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> float:
    model.train()
    total = 0.0
    seen = 0
    for curve, x0 in loader:
        curve = curve.to(device)
        x0 = x0.to(device)
        t = torch.randint(0, schedule.steps, (x0.size(0),), dtype=torch.long, device=device)
        noise = torch.randn_like(x0)
        x_t = schedule.q_sample(x0, t, noise)
        optimizer.zero_grad(set_to_none=True)
        pred_x0 = model(x_t, t, curve)
        loss = F.mse_loss(pred_x0, x0)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        total += loss.detach().item() * x0.size(0)
        seen += x0.size(0)
    return total / max(seen, 1)


@torch.no_grad()
def evaluate_denoise_mse(
    model: OrigamiCurveConditionalDiffusion,
    loader: DataLoader,
    schedule: DiffusionSchedule,
    device: torch.device,
) -> float:
    model.eval()
    total = 0.0
    seen = 0
    for curve, x0 in loader:
        curve = curve.to(device)
        x0 = x0.to(device)
        t = torch.full((x0.size(0),), schedule.steps // 2, dtype=torch.long, device=device)
        noise = torch.randn_like(x0)
        x_t = schedule.q_sample(x0, t, noise)
        pred_x0 = model(x_t, t, curve)
        total += F.mse_loss(pred_x0, x0, reduction="sum").item()
        seen += x0.numel()
    return total / max(seen, 1)


@torch.no_grad()
def sample_ddim(
    model: OrigamiCurveConditionalDiffusion,
    curve: torch.Tensor,
    schedule: DiffusionSchedule,
    sample_steps: int,
    device: torch.device,
) -> torch.Tensor:
    model.eval()
    sample_steps = min(sample_steps, schedule.steps)
    step_indices = torch.linspace(schedule.steps - 1, 0, sample_steps, device=device).long()
    x_t = torch.randn(curve.size(0), model.target_dim, dtype=curve.dtype, device=device)
    for step_pos, t_value in enumerate(step_indices):
        t = torch.full((curve.size(0),), int(t_value.item()), dtype=torch.long, device=device)
        pred_x0 = model(x_t, t, curve)
        if step_pos == len(step_indices) - 1:
            x_t = pred_x0
            break
        prev_t = step_indices[step_pos + 1]
        alpha_bar_t = schedule.alpha_bars[t_value].clamp_min(1e-8)
        alpha_bar_prev = schedule.alpha_bars[prev_t].clamp_min(1e-8)
        eps = (x_t - alpha_bar_t.sqrt() * pred_x0) / (1.0 - alpha_bar_t).sqrt().clamp_min(1e-8)
        x_t = alpha_bar_prev.sqrt() * pred_x0 + (1.0 - alpha_bar_prev).sqrt() * eps
    return x_t


def load_forward_model(result_dir: Path, device: torch.device) -> tuple[OrigamiCurveGNNTransformerForward, dict]:
    metrics = load_json(result_dir / "metrics.json")
    config = metrics["config"]
    metadata = metrics["metadata"]
    model = OrigamiCurveGNNTransformerForward(
        cont_dim=int(metadata.get("continuous_feature_dim", 5)),
        hidden_dim=int(config["hidden_dim"]),
        gnn_heads=int(config["gnn_heads"]),
        num_heads=int(config["num_heads"]),
        encoder_layers=int(config["encoder_layers"]),
        decoder_layers=int(config["decoder_layers"]),
        temporal_refiner_layers=int(config.get("temporal_refiner_layers", 2)),
        temporal_kernel_size=int(config.get("temporal_kernel_size", 5)),
        num_curve_points=80,
        curve_channels=1 if config.get("force_conditioned_decoder", False) else 2,
        physics_channels=7 if float(config.get("aux_physics_weight", 0.0)) > 0.0 else 0,
        monotonic_displacement=not bool(config.get("allow_nonmonotonic_displacement_output", False)),
        dropout=float(config.get("dropout", 0.05)),
    ).to(device)
    checkpoint = torch.load(result_dir / "curve_forward_gnn_transformer_best.pth", map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state"], strict=False)
    model.eval()
    return model, metrics


def forward_continuous_inputs(raw: np.ndarray, scaled: np.ndarray, forward_metadata: dict) -> np.ndarray:
    stats = forward_metadata.get("continuous_feature_stats", {"enabled": False})
    if stats.get("enabled"):
        return apply_continuous_feature_stats(raw.astype(np.float32), scaled[:, 3:].astype(np.float32), stats, augment=True)
    return scaled[:, 3:].astype(np.float32)


@torch.no_grad()
def predict_curves_with_forward(
    forward_model: OrigamiCurveGNNTransformerForward,
    raw_params: np.ndarray,
    scaled_params: np.ndarray,
    category_values: list[np.ndarray],
    forward_metadata: dict,
    device: torch.device,
    batch_size: int,
) -> np.ndarray:
    preds = []
    adj = build_parameter_adjacency(device=device, num_nodes=forward_model.num_nodes)
    cat_ids_all = category_ids_from_raw(raw_params, category_values)
    cont_all = forward_continuous_inputs(raw_params, scaled_params, forward_metadata)
    for start in range(0, raw_params.shape[0], batch_size):
        end = min(start + batch_size, raw_params.shape[0])
        cat = torch.tensor(cat_ids_all[start:end], dtype=torch.long, device=device)
        cont = torch.tensor(cont_all[start:end], dtype=torch.float32, device=device)
        if forward_model.physics_channels > 0:
            pred = forward_model.forward_with_aux(cat, cont, adj)["curve"]
        else:
            pred = forward_model(cat, cont, adj)
        preds.append(pred.detach().cpu().numpy())
    return np.concatenate(preds, axis=0).astype(np.float32)


def inverse_transform_and_project(
    x_scaled: np.ndarray,
    x_scaler,
    category_values: list[np.ndarray],
    continuous_min: np.ndarray,
    continuous_max: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    raw_before = x_scaler.inverse_transform(x_scaled).astype(np.float32)
    raw_after = snap_and_clip_raw_parameters(raw_before, category_values, continuous_min, continuous_max)
    scaled_after = x_scaler.transform(raw_after).astype(np.float32)
    return raw_before, raw_after, scaled_after


@torch.no_grad()
def sample_inverse_candidates(
    model: OrigamiCurveConditionalDiffusion,
    curve_scaled: np.ndarray,
    schedule: DiffusionSchedule,
    sample_steps: int,
    samples_per_target: int,
    device: torch.device,
    batch_size: int,
) -> np.ndarray:
    all_samples = []
    repeated = np.repeat(curve_scaled.astype(np.float32), samples_per_target, axis=0)
    for start in range(0, repeated.shape[0], batch_size):
        end = min(start + batch_size, repeated.shape[0])
        curve = torch.tensor(repeated[start:end], dtype=torch.float32, device=device)
        x_scaled = sample_ddim(model, curve, schedule, sample_steps, device)
        all_samples.append(x_scaled.detach().cpu().numpy())
    stacked = np.concatenate(all_samples, axis=0)
    return stacked.reshape(curve_scaled.shape[0], samples_per_target, -1).astype(np.float32)


def candidate_selection_scores(
    curve_mse: np.ndarray,
    pred_curve_raw: np.ndarray,
    negative_curve_weight: float,
) -> np.ndarray:
    if negative_curve_weight <= 0.0:
        return curve_mse.astype(np.float32)
    negative_displacement = np.mean(pred_curve_raw[..., 0] < 0.0, axis=(2, 3))
    negative_force = np.mean(pred_curve_raw[..., 1] < 0.0, axis=(2, 3))
    return (curve_mse + negative_curve_weight * (negative_displacement + negative_force)).astype(np.float32)


def select_closed_loop_candidates(
    candidate_scaled: np.ndarray,
    target_curve_scaled: np.ndarray,
    x_scaler,
    category_values: list[np.ndarray],
    continuous_min: np.ndarray,
    continuous_max: np.ndarray,
    forward_model: OrigamiCurveGNNTransformerForward,
    forward_metadata: dict,
    forward_curve_mean: np.ndarray,
    forward_curve_std: np.ndarray,
    device: torch.device,
    batch_size: int,
    negative_curve_weight: float,
) -> dict[str, np.ndarray]:
    n_targets, samples_per_target, target_dim = candidate_scaled.shape
    flat_scaled = candidate_scaled.reshape(n_targets * samples_per_target, target_dim)
    raw_before, raw_after, scaled_after = inverse_transform_and_project(
        flat_scaled,
        x_scaler,
        category_values,
        continuous_min,
        continuous_max,
    )
    pred_curve_scaled = predict_curves_with_forward(
        forward_model,
        raw_after,
        scaled_after,
        category_values,
        forward_metadata,
        device,
        batch_size,
    )
    target_repeated = np.repeat(target_curve_scaled.astype(np.float32), samples_per_target, axis=0)
    curve_mse = np.mean((pred_curve_scaled - target_repeated) ** 2, axis=(1, 2, 3)).reshape(n_targets, samples_per_target)
    pred_curve_raw = pred_curve_scaled * forward_curve_std.reshape(1, 1, 1, 2) + forward_curve_mean.reshape(1, 1, 1, 2)
    pred_curve_raw_candidates = pred_curve_raw.reshape(n_targets, samples_per_target, *pred_curve_raw.shape[1:])
    selection_scores = candidate_selection_scores(curve_mse, pred_curve_raw_candidates, negative_curve_weight)
    best_idx = np.argmin(selection_scores, axis=1)
    flat_best = np.arange(n_targets) * samples_per_target + best_idx
    return {
        "best_indices": best_idx.astype(np.int64),
        "selected_scaled": scaled_after[flat_best],
        "selected_raw": raw_after[flat_best],
        "selected_raw_before_projection": raw_before[flat_best],
        "selected_curve_scaled": pred_curve_scaled[flat_best],
        "selected_curve_raw": pred_curve_raw[flat_best].astype(np.float32),
        "all_curve_mse": curve_mse.astype(np.float32),
        "all_selection_scores": selection_scores.astype(np.float32),
        "selected_curve_mse": curve_mse[np.arange(n_targets), best_idx].astype(np.float32),
        "selected_selection_scores": selection_scores[np.arange(n_targets), best_idx].astype(np.float32),
    }


def write_history(path: Path, history: list[dict[str, float]]) -> None:
    if not history:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(history[0].keys()))
        writer.writeheader()
        writer.writerows(history)


def plot_training_history(history: list[dict[str, float]], output_path: Path) -> Path:
    import matplotlib.pyplot as plt

    epochs = [row["epoch"] for row in history]
    fig, ax = plt.subplots(figsize=(7.0, 4.0), constrained_layout=True)
    ax.plot(epochs, [row["train_loss"] for row in history], label="train")
    ax.plot(epochs, [row["val_denoise_mse"] for row in history], label="val")
    ax.set_yscale("log")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("x0 denoise MSE")
    ax.set_title("Inverse diffusion training")
    ax.legend()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_closed_loop_summary(metrics: dict[str, float], output_path: Path) -> Path:
    import matplotlib.pyplot as plt

    values = [metrics["displacement_nrmse_std_percent"], metrics["force_nrmse_std_percent"]]
    fig, ax = plt.subplots(figsize=(6.4, 4.0), constrained_layout=True)
    bars = ax.bar(["Displacement", "Force"], values, color=["#4C78A8", "#54A24B"], width=0.58)
    ax.axhline(5.0, color="#E45756", linestyle="--", linewidth=1.2, label="5% reference")
    ax.set_ylabel("Closed-loop std-NRMSE (%)")
    ax.set_title("Inverse diffusion -> forward model closed-loop")
    ax.set_ylim(0, max(6.0, max(values) + 1.0))
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.1, f"{value:.2f}%", ha="center", va="bottom")
    ax.legend()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_typical_closed_loop_curves(
    pred_curve: np.ndarray,
    target_curve: np.ndarray,
    sample_ids: np.ndarray,
    output_dir: Path,
    max_samples: int,
) -> list[Path]:
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    count = min(max_samples, pred_curve.shape[0])
    for idx in range(count):
        fig, axes = plt.subplots(2, 3, figsize=(10, 5.8), constrained_layout=True)
        for curve_id, ax in enumerate(axes.ravel()):
            ax.plot(target_curve[idx, curve_id, :, 0], target_curve[idx, curve_id, :, 1], color="#111827", label="target")
            ax.plot(pred_curve[idx, curve_id, :, 0], pred_curve[idx, curve_id, :, 1], color="#E45756", linestyle="--", label="closed-loop")
            ax.set_title(f"curve {curve_id}")
            ax.set_xlabel("Displacement")
            ax.set_ylabel("Force")
        axes.ravel()[0].legend(frameon=False)
        fig.suptitle(f"Inverse closed-loop: {sample_ids[idx]}")
        path = output_dir / f"{sample_ids[idx]}_closed_loop.png"
        fig.savefig(path, dpi=190, bbox_inches="tight")
        plt.close(fig)
        paths.append(path)
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--forward-result-dir", type=Path, default=DEFAULT_FORWARD_RESULT_DIR)
    parser.add_argument("--result-dir", type=Path, default=DEFAULT_RESULT_DIR)
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--eval-batch-size", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=384)
    parser.add_argument("--cond-dim", type=int, default=160)
    parser.add_argument("--time-dim", type=int, default=64)
    parser.add_argument("--encoder-layers", type=int, default=2)
    parser.add_argument("--num-heads", type=int, default=4)
    parser.add_argument("--dropout", type=float, default=0.08)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-5)
    parser.add_argument("--diffusion-steps", type=int, default=200)
    parser.add_argument("--beta-start", type=float, default=1e-4)
    parser.add_argument("--beta-end", type=float, default=2e-2)
    parser.add_argument("--sample-steps", type=int, default=80)
    parser.add_argument("--samples-per-target", type=int, default=8)
    parser.add_argument("--negative-curve-weight", type=float, default=0.25)
    parser.add_argument("--plot-samples", type=int, default=6)
    parser.add_argument("--log-every", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"], default="auto")
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
    train_curve_scaled, test_curve_scaled, curve_scaler = fit_curve_scaler(train, test)
    x_train = train["X"].astype(np.float32)
    x_test = test["X"].astype(np.float32)
    x_scaler = joblib.load(args.data_dir / "scaler_x.pkl")
    category_values = category_values_from_raw(train["X_raw"].astype(np.float32), test["X_raw"].astype(np.float32))
    continuous_min = train["X_raw"].astype(np.float32)[:, 3:].min(axis=0)
    continuous_max = train["X_raw"].astype(np.float32)[:, 3:].max(axis=0)

    model = OrigamiCurveConditionalDiffusion(
        target_dim=x_train.shape[1],
        curve_channels=2,
        physics_channels=0,
        time_dim=args.time_dim,
        cond_dim=args.cond_dim,
        hidden_dim=args.hidden_dim,
        num_curve_points=80,
        encoder_layers=args.encoder_layers,
        num_heads=args.num_heads,
        dropout=args.dropout,
    ).to(device)
    schedule = DiffusionSchedule(args.diffusion_steps, args.beta_start, args.beta_end, device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    train_loader = make_loader(train_curve_scaled, x_train, args.batch_size, shuffle=True)
    test_loader = make_loader(test_curve_scaled, x_test, args.eval_batch_size, shuffle=False)

    args.result_dir.mkdir(parents=True, exist_ok=True)
    history = []
    best_state = None
    best_epoch = 0
    best_val = float("inf")
    for epoch in range(1, args.epochs + 1):
        train_loss = train_epoch(model, train_loader, schedule, optimizer, device)
        if epoch == 1 or epoch % args.log_every == 0 or epoch == args.epochs:
            val_mse = evaluate_denoise_mse(model, test_loader, schedule, device)
            row = {"epoch": epoch, "train_loss": train_loss, "val_denoise_mse": val_mse}
            history.append(row)
            print(f"[inverse_diffusion] e{epoch} train={train_loss:.6f} val={val_mse:.6f}")
            if val_mse < best_val:
                best_val = val_mse
                best_epoch = epoch
                best_state = {key: value.detach().cpu() for key, value in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)

    forward_model, forward_metrics = load_forward_model(args.forward_result_dir, device)
    forward_metadata = forward_metrics["metadata"]
    forward_curve_mean = np.asarray(forward_metadata["curve_scaler"]["mean"], dtype=np.float32)
    forward_curve_std = np.asarray(forward_metadata["curve_scaler"]["std"], dtype=np.float32)
    candidate_scaled = sample_inverse_candidates(
        model,
        test_curve_scaled,
        schedule,
        args.sample_steps,
        args.samples_per_target,
        device,
        args.eval_batch_size,
    )
    selected = select_closed_loop_candidates(
        candidate_scaled,
        test_curve_scaled,
        x_scaler,
        category_values,
        continuous_min,
        continuous_max,
        forward_model,
        forward_metadata,
        forward_curve_mean,
        forward_curve_std,
        device,
        args.eval_batch_size,
        args.negative_curve_weight,
    )
    target_curve_raw = test["curve_raw"].astype(np.float32)
    closed_loop_metrics = curve_channel_metrics(selected["selected_curve_raw"], target_curve_raw)
    param_metrics = parameter_metrics(
        selected["selected_scaled"],
        x_test,
        selected["selected_raw"],
        test["X_raw"].astype(np.float32),
    )
    reason_metrics = reasonableness_metrics(
        selected["selected_raw_before_projection"],
        selected["selected_raw"],
        category_values,
    )

    history_path = args.result_dir / "inverse_diffusion_history.csv"
    write_history(history_path, history)
    training_plot = plot_training_history(history, args.result_dir / "inverse_diffusion_training.png")
    closed_loop_plot = plot_closed_loop_summary(closed_loop_metrics, args.result_dir / "closed_loop_nrmse.png")
    curve_plots = plot_typical_closed_loop_curves(
        selected["selected_curve_raw"],
        target_curve_raw,
        test["sample_id"].astype(str),
        args.result_dir / "closed_loop_curves",
        args.plot_samples,
    )

    rows = []
    for idx, sample_id in enumerate(test["sample_id"].astype(str)):
        row = {"sample_id": sample_id, "best_candidate": int(selected["best_indices"][idx])}
        for col, name in enumerate(INPUT_COLS):
            row[f"true_{name}"] = float(test["X_raw"][idx, col])
            row[f"generated_{name}"] = float(selected["selected_raw"][idx, col])
        row["closed_loop_scaled_mse"] = float(selected["selected_curve_mse"][idx])
        row["closed_loop_selection_score"] = float(selected["selected_selection_scores"][idx])
        rows.append(row)
    csv_path = args.result_dir / "generated_parameters_closed_loop.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    checkpoint_path = args.result_dir / "inverse_curve_diffusion_best.pth"
    torch.save(
        {
            "model_state": best_state,
            "best_epoch": best_epoch,
            "best_val_denoise_mse": best_val,
            "config": vars(args),
            "curve_scaler": curve_scaler.state_dict(),
            "category_values": [values.tolist() for values in category_values],
            "continuous_min": continuous_min.tolist(),
            "continuous_max": continuous_max.tolist(),
        },
        checkpoint_path,
    )

    metrics = {
        "best_epoch": best_epoch,
        "best_val_denoise_mse": best_val,
        "closed_loop_curve_metrics": closed_loop_metrics,
        "parameter_metrics": param_metrics,
        "parameter_reasonableness": reason_metrics,
        "train_samples": int(x_train.shape[0]),
        "test_samples": int(x_test.shape[0]),
        "samples_per_target": int(args.samples_per_target),
        "paths": {
            "history": history_path,
            "training_plot": training_plot,
            "closed_loop_plot": closed_loop_plot,
            "curve_plots": curve_plots,
            "generated_parameters": csv_path,
            "checkpoint": checkpoint_path,
        },
        "config": vars(args),
    }
    metrics_path = args.result_dir / "inverse_diffusion_closed_loop_metrics.json"
    metrics_path.write_text(json.dumps(json_ready(metrics), indent=2), encoding="utf-8")
    print(f"[Saved] {metrics_path}")
    print(json.dumps(json_ready(metrics["closed_loop_curve_metrics"]), indent=2))


if __name__ == "__main__":
    main()
