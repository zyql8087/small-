"""Train the curve-aware GNN-Transformer forward model on Miura nonlinear data."""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = SCRIPT_DIR.parent
REPO_ROOT = SCRIPT_DIR.parents[3]
sys.path.insert(0, str(REPO_ROOT))

from origami_experiments.models.origami_curve_models import (  # noqa: E402
    OrigamiCurveGNNTransformerForward,
    build_parameter_adjacency,
)


DEFAULT_DATA_DIR = EXPERIMENT_DIR / "data"
DEFAULT_RESULT_DIR = EXPERIMENT_DIR / "training_results" / "curve_forward_gnn_transformer"


class CurveChannelScaler:
    """Channel-wise standardization for [displacement, force]."""

    def __init__(self) -> None:
        self.mean: np.ndarray | None = None
        self.std: np.ndarray | None = None

    def fit(self, values: np.ndarray) -> "CurveChannelScaler":
        self.mean = values.mean(axis=(0, 1, 2), keepdims=True).astype(np.float32)
        std = values.std(axis=(0, 1, 2), keepdims=True)
        self.std = np.where(std < 1e-12, 1.0, std).astype(np.float32)
        return self

    def transform(self, values: np.ndarray) -> np.ndarray:
        if self.mean is None or self.std is None:
            raise RuntimeError("CurveChannelScaler must be fitted before transform")
        return ((values - self.mean) / self.std).astype(np.float32)

    def inverse_transform(self, values: np.ndarray) -> np.ndarray:
        if self.mean is None or self.std is None:
            raise RuntimeError("CurveChannelScaler must be fitted before inverse_transform")
        return (values * self.std + self.mean).astype(np.float32)

    def fit_transform(self, values: np.ndarray) -> np.ndarray:
        return self.fit(values).transform(values)

    def state_dict(self) -> dict[str, list[float]]:
        if self.mean is None or self.std is None:
            raise RuntimeError("CurveChannelScaler must be fitted before serialization")
        return {
            "mean": self.mean.reshape(-1).tolist(),
            "std": self.std.reshape(-1).tolist(),
        }


class RobustLogPhysicsScaler:
    """Signed-log transform followed by robust per-channel scaling."""

    def __init__(self, clip: float = 8.0, eps: float = 1e-6) -> None:
        self.clip = clip
        self.eps = eps
        self.center: np.ndarray | None = None
        self.scale: np.ndarray | None = None

    @staticmethod
    def signed_log1p(values: np.ndarray) -> np.ndarray:
        return np.sign(values) * np.log1p(np.abs(values))

    def fit(self, values: np.ndarray) -> "RobustLogPhysicsScaler":
        if not np.isfinite(values).all():
            raise ValueError("physics values contain NaN/Inf")
        logged = self.signed_log1p(values.astype(np.float64))
        self.center = np.nanmedian(logged, axis=(0, 1, 2), keepdims=True).astype(np.float32)
        q25 = np.nanquantile(logged, 0.25, axis=(0, 1, 2), keepdims=True)
        q75 = np.nanquantile(logged, 0.75, axis=(0, 1, 2), keepdims=True)
        scale = q75 - q25
        self.scale = np.where(scale < self.eps, 1.0, scale).astype(np.float32)
        return self

    def transform(self, values: np.ndarray) -> np.ndarray:
        if self.center is None or self.scale is None:
            raise RuntimeError("RobustLogPhysicsScaler must be fitted before transform")
        logged = self.signed_log1p(values.astype(np.float64))
        scaled = (logged - self.center) / self.scale
        return np.clip(scaled, -self.clip, self.clip).astype(np.float32)

    def fit_transform(self, values: np.ndarray) -> np.ndarray:
        return self.fit(values).transform(values)

    def state_dict(self) -> dict[str, list[float] | float]:
        if self.center is None or self.scale is None:
            raise RuntimeError("RobustLogPhysicsScaler must be fitted before serialization")
        return {
            "transform": "signed_log1p_robust_iqr",
            "clip": float(self.clip),
            "center": self.center.reshape(-1).tolist(),
            "scale": self.scale.reshape(-1).tolist(),
        }


class CurveForwardDataset(Dataset):
    def __init__(
        self,
        cat_ids: np.ndarray,
        cont_scaled: np.ndarray,
        curve_scaled: np.ndarray,
        physics_scaled: np.ndarray | None = None,
        sample_ids: np.ndarray | None = None,
    ) -> None:
        self.cat_ids = torch.tensor(cat_ids, dtype=torch.long)
        self.cont_scaled = torch.tensor(cont_scaled, dtype=torch.float32)
        self.curve_scaled = torch.tensor(curve_scaled, dtype=torch.float32)
        self.physics_scaled = (
            torch.tensor(physics_scaled, dtype=torch.float32) if physics_scaled is not None else None
        )
        if sample_ids is None:
            sample_ids = np.asarray([f"sample_{idx:05d}" for idx in range(len(cat_ids))])
        self.sample_ids = np.asarray([str(sample_id) for sample_id in sample_ids])

    def __len__(self) -> int:
        return self.cat_ids.size(0)

    def __getitem__(self, idx: int):
        if self.physics_scaled is None:
            return self.cat_ids[idx], self.cont_scaled[idx], self.curve_scaled[idx]
        return self.cat_ids[idx], self.cont_scaled[idx], self.curve_scaled[idx], self.physics_scaled[idx]


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
        raise FileNotFoundError(f"Missing train/test NPZ under {data_dir}")
    train = dict(np.load(train_path))
    test = dict(np.load(test_path))
    required = ["X", "X_raw", "curve_raw", "converged"]
    for name, split in [("train", train), ("test", test)]:
        missing = [key for key in required if key not in split]
        if missing:
            raise KeyError(f"{name} split missing keys: {missing}")
        if split["curve_raw"].shape[1:] != (6, 80, 2):
            raise ValueError(f"{name} split has unexpected curve_raw shape: {split['curve_raw'].shape}")
        if not split["converged"].all():
            raise ValueError(f"{name} split contains unconverged loading steps")
    return train, test


def category_maps_from_splits(*splits: np.ndarray) -> list[dict[float, int]]:
    stacked = np.concatenate([split[:, :3] for split in splits], axis=0)
    maps = []
    for col in range(3):
        values = sorted(np.unique(stacked[:, col]).astype(float).tolist())
        maps.append({value: idx for idx, value in enumerate(values)})
    return maps


def category_ids_from_raw(x_raw: np.ndarray, maps: list[dict[float, int]]) -> np.ndarray:
    cats = []
    for col, value_to_id in enumerate(maps):
        cats.append(np.array([value_to_id[float(value)] for value in x_raw[:, col]], dtype=np.int64))
    return np.stack(cats, axis=1)


DERIVED_CONTINUOUS_FEATURE_NAMES = [
    "log_tcrease",
    "log_tpanel",
    "log_W",
    "log_creaseE",
    "log_panelE",
    "log_tcrease_over_tpanel",
    "log_creaseE_over_panelE",
    "log_creaseE_tcrease",
    "log_panelE_tpanel",
    "log_creaseE_tcrease_cubed",
    "log_panelE_tpanel_cubed",
    "log_W_over_tcrease",
    "log_W_over_tpanel",
]


def physics_inspired_feature_matrix(x_raw: np.ndarray) -> np.ndarray:
    raw = x_raw.astype(np.float64)
    eps = 1e-12
    tcrease = np.maximum(raw[:, 3], eps)
    tpanel = np.maximum(raw[:, 4], eps)
    width = np.maximum(raw[:, 5], eps)
    crease_e = np.maximum(raw[:, 6], eps)
    panel_e = np.maximum(raw[:, 7], eps)
    features = np.column_stack(
        [
            np.log(tcrease),
            np.log(tpanel),
            np.log(width),
            np.log(crease_e),
            np.log(panel_e),
            np.log(tcrease / tpanel),
            np.log(crease_e / panel_e),
            np.log(crease_e * tcrease),
            np.log(panel_e * tpanel),
            np.log(crease_e * tcrease**3),
            np.log(panel_e * tpanel**3),
            np.log(width / tcrease),
            np.log(width / tpanel),
        ]
    )
    return features.astype(np.float32)


def build_continuous_features(
    x_raw: np.ndarray,
    base_cont: np.ndarray,
    augment: bool = False,
) -> tuple[np.ndarray, dict[str, object]]:
    base = base_cont.astype(np.float32)
    if not augment:
        return base, {"enabled": False, "derived_names": []}
    derived = physics_inspired_feature_matrix(x_raw)
    mean = derived.mean(axis=0, keepdims=True)
    std = np.where(derived.std(axis=0, keepdims=True) < 1e-8, 1.0, derived.std(axis=0, keepdims=True))
    derived_scaled = ((derived - mean) / std).astype(np.float32)
    features = np.concatenate([base, derived_scaled], axis=1).astype(np.float32)
    return features, {
        "enabled": True,
        "derived_names": DERIVED_CONTINUOUS_FEATURE_NAMES,
        "derived_mean": mean.reshape(-1).astype(float).tolist(),
        "derived_std": std.reshape(-1).astype(float).tolist(),
    }


def apply_continuous_feature_stats(
    x_raw: np.ndarray,
    base_cont: np.ndarray,
    stats: dict[str, object],
    augment: bool = False,
) -> np.ndarray:
    base = base_cont.astype(np.float32)
    if not augment:
        return base
    if not stats.get("enabled"):
        raise ValueError("Continuous feature stats were not fitted with augment=True")
    derived = physics_inspired_feature_matrix(x_raw)
    mean = np.asarray(stats["derived_mean"], dtype=np.float32).reshape(1, -1)
    std = np.asarray(stats["derived_std"], dtype=np.float32).reshape(1, -1)
    derived_scaled = ((derived - mean) / std).astype(np.float32)
    return np.concatenate([base, derived_scaled], axis=1).astype(np.float32)


def maybe_limit(split: dict[str, np.ndarray], max_samples: int) -> dict[str, np.ndarray]:
    if max_samples <= 0:
        return split
    limited = {}
    for key, value in split.items():
        limited[key] = value[:max_samples] if hasattr(value, "shape") and value.shape[:1] == (len(split["X"]),) else value
    return limited


def prepare_datasets(args: argparse.Namespace) -> tuple[CurveForwardDataset, CurveForwardDataset, dict, CurveChannelScaler]:
    train, test = load_npz_pair(args.data_dir)
    train = maybe_limit(train, args.max_train_samples)
    test = maybe_limit(test, args.max_test_samples)

    maps = category_maps_from_splits(train["X_raw"].astype(np.float32), test["X_raw"].astype(np.float32))
    train_cat = category_ids_from_raw(train["X_raw"].astype(np.float32), maps)
    test_cat = category_ids_from_raw(test["X_raw"].astype(np.float32), maps)
    train_cont_base = train["X"].astype(np.float32)[:, 3:]
    test_cont_base = test["X"].astype(np.float32)[:, 3:]
    train_cont, continuous_feature_stats = build_continuous_features(
        train["X_raw"].astype(np.float32),
        train_cont_base,
        augment=args.augment_continuous_features,
    )
    test_cont = apply_continuous_feature_stats(
        test["X_raw"].astype(np.float32),
        test_cont_base,
        continuous_feature_stats,
        augment=args.augment_continuous_features,
    )

    curve_scaler = CurveChannelScaler()
    train_curve = curve_scaler.fit_transform(train["curve_raw"].astype(np.float32))
    test_curve = curve_scaler.transform(test["curve_raw"].astype(np.float32))

    physics_scaler = None
    train_physics = None
    test_physics = None
    if args.aux_physics_weight > 0.0:
        if "physics_raw" not in train or "physics_raw" not in test:
            raise KeyError("physics_raw is required when --aux-physics-weight is positive")
        physics_scaler = RobustLogPhysicsScaler(clip=args.physics_clip)
        train_physics = physics_scaler.fit_transform(train["physics_raw"].astype(np.float32))
        test_physics = physics_scaler.transform(test["physics_raw"].astype(np.float32))

    metadata = {
        "input_cols": [str(x) for x in train.get("input_cols", [])],
        "physics_cols": [str(x) for x in train.get("physics_cols", [])],
        "category_maps": [{str(key): value for key, value in mapping.items()} for mapping in maps],
        "curve_scaler": curve_scaler.state_dict(),
        "physics_scaler": physics_scaler.state_dict() if physics_scaler is not None else None,
        "continuous_feature_stats": continuous_feature_stats,
        "continuous_feature_dim": int(train_cont.shape[1]),
        "train_samples": int(train["X"].shape[0]),
        "test_samples": int(test["X"].shape[0]),
    }

    return (
        CurveForwardDataset(train_cat, train_cont, train_curve, train_physics, train.get("sample_id")),
        CurveForwardDataset(test_cat, test_cont, test_curve, test_physics, test.get("sample_id")),
        metadata,
        curve_scaler,
    )


def move_batch(batch, device: torch.device):
    return tuple(item.to(device) for item in batch)


def run_epoch(
    model: OrigamiCurveGNNTransformerForward,
    loader: DataLoader,
    adj: torch.Tensor,
    device: torch.device,
    aux_physics_weight: float,
    smoothness_weight: float,
    force_monotonic_weight: float,
    displacement_monotonic_weight: float,
    displacement_loss_weight: float,
    force_loss_weight: float,
    displacement_amplitude_weight: float,
    force_conditioned_decoder: bool,
    optimizer: torch.optim.Optimizer | None = None,
) -> dict[str, float]:
    is_train = optimizer is not None
    model.train(is_train)
    totals = {
        "total": 0.0,
        "curve": 0.0,
        "physics": 0.0,
        "smoothness": 0.0,
        "force_monotonic": 0.0,
        "displacement_monotonic": 0.0,
    }
    n_total = 0

    for batch in loader:
        batch = move_batch(batch, device)
        cat, cont, curve = batch[:3]
        physics = batch[3] if len(batch) == 4 else None
        with torch.set_grad_enabled(is_train):
            force_condition = curve[..., 1:2] if force_conditioned_decoder else None
            target_curve = curve[..., 0:1] if force_conditioned_decoder else curve
            if aux_physics_weight > 0.0:
                outputs = model.forward_with_aux(cat, cont, adj, force_condition=force_condition)
                pred_model_curve = outputs["curve"]
            else:
                outputs = {"curve": model(cat, cont, adj, force_condition=force_condition)}
                pred_model_curve = outputs["curve"]
            if force_conditioned_decoder:
                pred_curve = torch.cat([pred_model_curve, force_condition], dim=-1)
                curve_loss = F.mse_loss(pred_model_curve, target_curve)
            else:
                pred_curve = pred_model_curve
                curve_loss = weighted_curve_mse(
                    pred_curve,
                    target_curve,
                    displacement_weight=displacement_loss_weight,
                    force_weight=force_loss_weight,
                    displacement_amplitude_weight=displacement_amplitude_weight,
                )
            physics_loss = torch.tensor(0.0, dtype=curve_loss.dtype, device=device)
            if aux_physics_weight > 0.0:
                if physics is None or "physics" not in outputs:
                    raise RuntimeError("Physics auxiliary target/head missing")
                physics_loss = F.smooth_l1_loss(outputs["physics"], physics)
            regularizers = curve_regularization_losses(pred_curve)
            loss = (
                curve_loss
                + aux_physics_weight * physics_loss
                + smoothness_weight * regularizers["smoothness"]
                + force_monotonic_weight * regularizers["force_monotonic"]
                + displacement_monotonic_weight * regularizers["displacement_monotonic"]
            )

            if is_train:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

        batch_size = cat.size(0)
        n_total += batch_size
        totals["total"] += loss.detach().item() * batch_size
        totals["curve"] += curve_loss.detach().item() * batch_size
        totals["physics"] += physics_loss.detach().item() * batch_size
        totals["smoothness"] += regularizers["smoothness"].detach().item() * batch_size
        totals["force_monotonic"] += regularizers["force_monotonic"].detach().item() * batch_size
        totals["displacement_monotonic"] += regularizers["displacement_monotonic"].detach().item() * batch_size

    return {key: value / max(n_total, 1) for key, value in totals.items()}


def weighted_curve_mse(
    pred_curve: torch.Tensor,
    target_curve: torch.Tensor,
    displacement_weight: float = 1.0,
    force_weight: float = 1.0,
    displacement_amplitude_weight: float = 0.0,
) -> torch.Tensor:
    if pred_curve.shape != target_curve.shape:
        raise ValueError("pred_curve and target_curve must have matching shapes")
    if pred_curve.size(-1) != 2:
        raise ValueError("curve tensors must have exactly two channels: [displacement, force]")
    weights = pred_curve.new_tensor([displacement_weight, force_weight]).view(1, 1, 1, 2)
    if torch.any(weights <= 0):
        raise ValueError("curve channel loss weights must be positive")
    weights = weights.expand_as(pred_curve).clone()
    if displacement_amplitude_weight > 0.0:
        amplitude = target_curve[..., 0:1].abs()
        mean_amplitude = amplitude.detach().mean().clamp_min(1e-6)
        amplitude_scale = 1.0 + displacement_amplitude_weight * amplitude / mean_amplitude
        weights[..., 0:1] = weights[..., 0:1] * amplitude_scale
    return torch.mean((pred_curve - target_curve).pow(2) * weights) / torch.mean(weights)


def write_history(path: Path, history: list[dict[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(history[0].keys()))
        writer.writeheader()
        writer.writerows(history)


def read_history(path: Path) -> list[dict[str, float]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return [
            {key: float(value) for key, value in row.items() if value != ""}
            for row in csv.DictReader(handle)
        ]


def plot_training_history(history: list[dict[str, float]], output_path: Path) -> Path:
    if not history:
        raise ValueError("history must contain at least one epoch")

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epochs = [int(row.get("epoch", index + 1)) for index, row in enumerate(history)]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), constrained_layout=True)

    def plot_keys(ax, keys: list[tuple[str, str]]) -> None:
        positive_values = []
        for key, label in keys:
            if key not in history[0]:
                continue
            values = [float(row[key]) for row in history]
            ax.plot(epochs, values, lw=1.8, label=label)
            positive_values.extend(value for value in values if value > 0.0)
        if positive_values and len(positive_values) == sum(1 for key, _ in keys if key in history[0]) * len(history):
            ax.set_yscale("log")
        ax.grid(True, alpha=0.35)
        ax.set_xlabel("Epoch")
        if ax.lines:
            ax.legend(loc="best", fontsize=8)

    axes[0].set_title("Total and curve losses")
    axes[0].set_ylabel("Loss")
    plot_keys(
        axes[0],
        [
            ("train_total", "train total"),
            ("val_total", "val total"),
            ("train_curve", "train curve"),
            ("val_curve", "val curve"),
        ],
    )

    axes[1].set_title("Physics auxiliary loss")
    axes[1].set_ylabel("Loss")
    plot_keys(
        axes[1],
        [
            ("train_physics", "train physics"),
            ("val_physics", "val physics"),
        ],
    )

    axes[2].set_title("Curve regularizers")
    axes[2].set_ylabel("Penalty")
    plot_keys(
        axes[2],
        [
            ("train_smoothness", "train smooth"),
            ("val_smoothness", "val smooth"),
            ("train_force_monotonic", "train force mono"),
            ("val_force_monotonic", "val force mono"),
            ("train_displacement_monotonic", "train disp mono"),
            ("val_displacement_monotonic", "val disp mono"),
        ],
    )

    fig.suptitle("Curve forward GNN-Transformer training history")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def curve_regularization_losses(curve: torch.Tensor) -> dict[str, torch.Tensor]:
    if curve.dim() != 4:
        raise ValueError("curve must have shape [batch, conditions, points, channels]")
    zero = curve.new_tensor(0.0)
    if curve.size(2) >= 3:
        second_diff = curve[:, :, 2:, :] - 2.0 * curve[:, :, 1:-1, :] + curve[:, :, :-2, :]
        smoothness = torch.mean(second_diff.pow(2))
    else:
        smoothness = zero
    if curve.size(2) >= 2:
        deltas = curve[:, :, 1:, :] - curve[:, :, :-1, :]
        displacement_monotonic = torch.mean(F.relu(-deltas[..., 0]).pow(2))
        force_monotonic = torch.mean(F.relu(-deltas[..., 1]).pow(2))
    else:
        displacement_monotonic = zero
        force_monotonic = zero
    return {
        "smoothness": smoothness,
        "force_monotonic": force_monotonic,
        "displacement_monotonic": displacement_monotonic,
    }


def denormalized_curve_metrics(pred_curve: np.ndarray, target_curve: np.ndarray) -> dict[str, float]:
    diff = pred_curve - target_curve
    displacement = diff[..., 0]
    force = diff[..., 1]
    target_displacement = target_curve[..., 0]
    target_force = target_curve[..., 1]
    displacement_rmse = float(np.sqrt(np.mean(displacement**2)))
    force_rmse = float(np.sqrt(np.mean(force**2)))
    displacement_range = float(np.ptp(target_displacement))
    force_range = float(np.ptp(target_force))
    displacement_std = float(np.std(target_displacement))
    force_std = float(np.std(target_force))

    def nrmse_percent(rmse: float, denominator: float) -> float:
        if denominator <= 1e-12:
            return 0.0 if rmse <= 1e-12 else float("inf")
        return float(rmse / denominator * 100.0)

    return {
        "displacement_mae": float(np.mean(np.abs(displacement))),
        "displacement_rmse": displacement_rmse,
        "force_mae": float(np.mean(np.abs(force))),
        "force_rmse": force_rmse,
        "displacement_nrmse_range_percent": nrmse_percent(displacement_rmse, displacement_range),
        "force_nrmse_range_percent": nrmse_percent(force_rmse, force_range),
        "displacement_nrmse_std_percent": nrmse_percent(displacement_rmse, displacement_std),
        "force_nrmse_std_percent": nrmse_percent(force_rmse, force_std),
    }


def sample_curve_rmse(pred_curve: np.ndarray, target_curve: np.ndarray) -> np.ndarray:
    return np.sqrt(np.mean((pred_curve - target_curve) ** 2, axis=(1, 2, 3)))


def typical_sample_indices(pred_curve: np.ndarray, target_curve: np.ndarray, max_samples: int) -> list[int]:
    count = pred_curve.shape[0]
    if count == 0 or max_samples <= 0:
        return []
    errors = sample_curve_rmse(pred_curve, target_curve)
    if count <= max_samples:
        return list(range(count))
    quantile_positions = np.linspace(0.1, 0.9, max_samples)
    sorted_indices = np.argsort(errors)
    picks = []
    for position in quantile_positions:
        ranked = int(round(position * (count - 1)))
        picks.append(int(sorted_indices[ranked]))
    return sorted(set(picks), key=picks.index)


def plot_typical_curves(
    pred_curve: np.ndarray,
    target_curve: np.ndarray,
    sample_ids: np.ndarray,
    output_dir: Path,
    max_samples: int = 6,
) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    load_cases = ["bending", "bending", "bending", "axial", "axial", "axial"]
    deployments = [0.3, 0.6, 0.9, 0.3, 0.6, 0.9]

    for index in typical_sample_indices(pred_curve, target_curve, max_samples):
        sample_id = str(sample_ids[index]) if index < len(sample_ids) else f"sample_{index:05d}"
        fig, axes = plt.subplots(2, 3, figsize=(12, 7), constrained_layout=True)
        fig.suptitle(f"{sample_id} predicted vs target force-displacement curves")
        for curve_id, ax in enumerate(axes.ravel()):
            target = target_curve[index, curve_id]
            pred = pred_curve[index, curve_id]
            ax.plot(target[:, 0], target[:, 1], lw=2, label="target")
            ax.plot(pred[:, 0], pred[:, 1], "--", lw=1.6, label="pred")
            ax.set_title(f"curve {curve_id}: {load_cases[curve_id]}, deploy {deployments[curve_id]:g}")
            ax.set_xlabel("Displacement")
            ax.set_ylabel("Force")
            ax.grid(True, alpha=0.35)
        axes.ravel()[0].legend(loc="best")
        path = output_dir / f"{sample_id}_pred_vs_target.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)
        paths.append(path)
    return paths


@torch.no_grad()
def collect_curve_predictions(
    model: OrigamiCurveGNNTransformerForward,
    loader: DataLoader,
    adj: torch.Tensor,
    device: torch.device,
    aux_physics_weight: float,
    force_conditioned_decoder: bool,
) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    pred_batches = []
    target_batches = []
    for batch in loader:
        batch = move_batch(batch, device)
        cat, cont, curve = batch[:3]
        force_condition = curve[..., 1:2] if force_conditioned_decoder else None
        if aux_physics_weight > 0.0:
            pred = model.forward_with_aux(cat, cont, adj, force_condition=force_condition)["curve"]
        else:
            pred = model(cat, cont, adj, force_condition=force_condition)
        if force_conditioned_decoder:
            pred = torch.cat([pred, force_condition], dim=-1)
        pred_batches.append(pred.detach().cpu().numpy())
        target_batches.append(curve.detach().cpu().numpy())
    return np.concatenate(pred_batches, axis=0), np.concatenate(target_batches, axis=0)


def json_ready(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    return value


def load_initial_checkpoint(
    model: OrigamiCurveGNNTransformerForward,
    checkpoint_path: Path | None,
    device: torch.device,
) -> dict[str, object]:
    if checkpoint_path is None:
        return {"loaded": False, "path": None, "missing_keys": [], "unexpected_keys": []}
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Initial checkpoint does not exist: {checkpoint_path}")
    try:
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    except TypeError:
        checkpoint = torch.load(checkpoint_path, map_location=device)
    state = checkpoint["model_state"] if isinstance(checkpoint, dict) and "model_state" in checkpoint else checkpoint
    result = model.load_state_dict(state, strict=False)
    return {
        "loaded": True,
        "path": str(checkpoint_path),
        "missing_keys": list(result.missing_keys),
        "unexpected_keys": list(result.unexpected_keys),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--result-dir", type=Path, default=DEFAULT_RESULT_DIR)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--hidden-dim", type=int, default=96)
    parser.add_argument("--encoder-layers", type=int, default=2)
    parser.add_argument("--decoder-layers", type=int, default=2)
    parser.add_argument("--temporal-refiner-layers", type=int, default=2)
    parser.add_argument("--temporal-kernel-size", type=int, default=5)
    parser.add_argument("--num-heads", type=int, default=4)
    parser.add_argument("--gnn-heads", type=int, default=4)
    parser.add_argument("--dropout", type=float, default=0.05)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--aux-physics-weight", type=float, default=0.0)
    parser.add_argument("--physics-clip", type=float, default=8.0)
    parser.add_argument("--smoothness-weight", type=float, default=1e-2)
    parser.add_argument("--force-monotonic-weight", type=float, default=1e-2)
    parser.add_argument("--displacement-monotonic-weight", type=float, default=0.0)
    parser.add_argument("--displacement-loss-weight", type=float, default=1.0)
    parser.add_argument("--force-loss-weight", type=float, default=1.0)
    parser.add_argument("--displacement-amplitude-weight", type=float, default=0.0)
    parser.add_argument("--force-conditioned-decoder", action="store_true")
    parser.add_argument("--augment-continuous-features", action="store_true")
    parser.add_argument("--allow-nonmonotonic-displacement-output", action="store_true")
    parser.add_argument("--init-checkpoint", type=Path, default=None)
    parser.add_argument("--max-train-samples", type=int, default=0)
    parser.add_argument("--max-test-samples", type=int, default=0)
    parser.add_argument("--plot-samples", type=int, default=6)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"], default="auto")
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

    train_ds, test_ds, metadata, curve_scaler = prepare_datasets(args)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False)

    model = OrigamiCurveGNNTransformerForward(
        cont_dim=int(train_ds.cont_scaled.shape[1]),
        hidden_dim=args.hidden_dim,
        gnn_heads=args.gnn_heads,
        num_heads=args.num_heads,
        encoder_layers=args.encoder_layers,
        decoder_layers=args.decoder_layers,
        temporal_refiner_layers=args.temporal_refiner_layers,
        temporal_kernel_size=args.temporal_kernel_size,
        num_curve_points=80,
        curve_channels=1 if args.force_conditioned_decoder else 2,
        physics_channels=7 if args.aux_physics_weight > 0.0 else 0,
        monotonic_displacement=not args.allow_nonmonotonic_displacement_output,
        dropout=args.dropout,
    ).to(device)
    init_info = load_initial_checkpoint(model, args.init_checkpoint, device)
    if init_info["loaded"]:
        print(
            f"[Init] Loaded {init_info['path']} "
            f"missing={len(init_info['missing_keys'])} unexpected={len(init_info['unexpected_keys'])}"
        )
    adj = build_parameter_adjacency(device=device, num_nodes=model.num_nodes)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    history: list[dict[str, float]] = []
    best_val = float("inf")
    best_state = None
    best_epoch = 0

    for epoch in range(1, args.epochs + 1):
        train_metrics = run_epoch(
            model,
            train_loader,
            adj,
            device,
            args.aux_physics_weight,
            args.smoothness_weight,
            args.force_monotonic_weight,
            args.displacement_monotonic_weight,
            args.displacement_loss_weight,
            args.force_loss_weight,
            args.displacement_amplitude_weight,
            args.force_conditioned_decoder,
            optimizer,
        )
        with torch.no_grad():
            val_metrics = run_epoch(
                model,
                test_loader,
                adj,
                device,
                args.aux_physics_weight,
                args.smoothness_weight,
                args.force_monotonic_weight,
                args.displacement_monotonic_weight,
                args.displacement_loss_weight,
                args.force_loss_weight,
                args.displacement_amplitude_weight,
                args.force_conditioned_decoder,
            )
        row = {
            "epoch": epoch,
            "train_total": train_metrics["total"],
            "train_curve": train_metrics["curve"],
            "train_physics": train_metrics["physics"],
            "train_smoothness": train_metrics["smoothness"],
            "train_force_monotonic": train_metrics["force_monotonic"],
            "train_displacement_monotonic": train_metrics["displacement_monotonic"],
            "val_total": val_metrics["total"],
            "val_curve": val_metrics["curve"],
            "val_physics": val_metrics["physics"],
            "val_smoothness": val_metrics["smoothness"],
            "val_force_monotonic": val_metrics["force_monotonic"],
            "val_displacement_monotonic": val_metrics["displacement_monotonic"],
        }
        history.append(row)
        if row["val_total"] < best_val:
            best_val = row["val_total"]
            best_state = {key: value.detach().cpu() for key, value in model.state_dict().items()}
            best_epoch = epoch
        print(
            f"[curve_forward] e{epoch} train={row['train_total']:.5f} "
            f"val={row['val_total']:.5f} curve={row['val_curve']:.5f} physics={row['val_physics']:.5f}"
        )

    args.result_dir.mkdir(parents=True, exist_ok=True)
    if best_state is not None:
        model.load_state_dict(best_state)
    pred_scaled, target_scaled = collect_curve_predictions(
        model,
        test_loader,
        adj,
        device,
        args.aux_physics_weight,
        args.force_conditioned_decoder,
    )
    pred_curve = curve_scaler.inverse_transform(pred_scaled)
    target_curve = curve_scaler.inverse_transform(target_scaled)
    denorm_metrics = denormalized_curve_metrics(pred_curve, target_curve)
    denorm_metrics_path = args.result_dir / "denormalized_curve_metrics.json"
    denorm_metrics_path.write_text(json.dumps(denorm_metrics, indent=2), encoding="utf-8")
    plot_paths = plot_typical_curves(
        pred_curve,
        target_curve,
        test_ds.sample_ids,
        args.result_dir / "typical_curves",
        max_samples=args.plot_samples,
    )

    history_path = args.result_dir / "history.csv"
    write_history(history_path, history)
    training_loss_plot = plot_training_history(history, args.result_dir / "training_loss_curves.png")
    metrics = {
        "best_epoch": best_epoch,
        "best_val_total": best_val,
        "final": history[-1],
        "denormalized_curve_metrics": denorm_metrics,
        "training_loss_plot": str(training_loss_plot),
        "typical_curve_plots": [str(path) for path in plot_paths],
        "config": json_ready(vars(args)),
        "metadata": metadata,
        "init_checkpoint": init_info,
    }
    metrics_path = args.result_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    checkpoint_path = args.result_dir / "curve_forward_gnn_transformer_best.pth"
    torch.save(
        {
            "model_state": best_state,
            "best_epoch": best_epoch,
            "best_val_total": best_val,
            "config": vars(args),
            "metadata": metadata,
            "init_checkpoint": init_info,
        },
        checkpoint_path,
    )
    print(f"[Saved] {history_path}")
    print(f"[Saved] {training_loss_plot}")
    print(f"[Saved] {metrics_path}")
    print(f"[Saved] {denorm_metrics_path}")
    for plot_path in plot_paths:
        print(f"[Saved] {plot_path}")
    print(f"[Saved] {checkpoint_path}")


if __name__ == "__main__":
    main()
