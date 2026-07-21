"""Train task-adapted Origami models without touching legacy checkpoints/results.

Stages:
1. forward_resmlp: 8 design/material parameters -> 6 log-stiffness values.
2. inverse_resmlp: 6 log-stiffness values -> discrete + continuous design parameters.
3. forward_gat: task-adapted GAT forward surrogate.
4. inverse_cvae: CVAE inverse model with closed-loop stiffness consistency.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

EXPERIMENT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = EXPERIMENT_ROOT.parent
SCRIPT_DIR = EXPERIMENT_ROOT
sys.path.insert(0, str(REPO_ROOT))

from origami_experiments.models.origami_taskfit_models import (  # noqa: E402
    OrigamiForwardGATTaskfit,
    OrigamiForwardResMLP,
    OrigamiForwardTransformerTaskfit,
    OrigamiInverseCVAEHeaded,
    OrigamiInverseDiscreteClassifier,
    OrigamiInverseDiffusionTaskfit,
    OrigamiInverseResMLP,
)

INPUT_COLS = ["pattern", "m", "n", "tcrease", "tpanel", "W", "creaseE", "panelE"]
OUTPUT_COLS = ["bendstiff30", "bendstiff60", "bendstiff90", "axialstiff30", "axialstiff60", "axialstiff90"]
CAT_COLS = ["pattern", "m", "n"]
CONT_COLS = ["tcrease", "tpanel", "W", "creaseE", "panelE"]
CAT_VALUES = {
    "pattern": np.array([1.0, 2.0], dtype=np.float32),
    "m": np.array([24.0, 30.0, 36.0], dtype=np.float32),
    "n": np.array([6.0, 9.0, 12.0], dtype=np.float32),
}
NODE_INDEX = {
    "pattern": 0,
    "m": 1,
    "n": 2,
    "tcrease": 3,
    "tpanel": 4,
    "W": 5,
    "creaseE": 6,
    "panelE": 7,
}


def setup_device() -> torch.device:
    if hasattr(torch, "set_float32_matmul_precision"):
        torch.set_float32_matmul_precision("high")
    if torch.cuda.is_available():
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
        device = torch.device("cuda")
        print(f"[Device] CUDA: {torch.cuda.get_device_name(0)}")
    else:
        device = torch.device("cpu")
        print("[Device] CPU")
    return device


DEVICE = setup_device()


def make_dirs(args: argparse.Namespace) -> None:
    for path in [args.checkpoint_dir, args.result_dir, args.curve_dir]:
        Path(path).mkdir(parents=True, exist_ok=True)


def category_ids(values: np.ndarray, allowed: np.ndarray) -> np.ndarray:
    ids = np.zeros(values.shape[0], dtype=np.int64)
    for idx, val in enumerate(allowed):
        ids[np.isclose(values, val)] = idx
    return ids


class TaskfitPreprocessor:
    def __init__(self) -> None:
        self.cont_scaler = StandardScaler()
        self.curve_scaler = StandardScaler()

    def fit(self, x_raw: np.ndarray, y_raw: np.ndarray) -> None:
        self.cont_scaler.fit(self._continuous_log(x_raw))
        self.curve_scaler.fit(self._curve_log(y_raw))

    @staticmethod
    def _continuous_log(x_raw: np.ndarray) -> np.ndarray:
        return np.log10(np.clip(x_raw[:, 3:8].astype(np.float64), 1e-12, None))

    @staticmethod
    def _curve_log(y_raw: np.ndarray) -> np.ndarray:
        return np.log10(np.clip(y_raw.astype(np.float64), 1e-12, None))

    def transform_x(self, x_raw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        cat = np.stack(
            [
                category_ids(x_raw[:, 0], CAT_VALUES["pattern"]),
                category_ids(x_raw[:, 1], CAT_VALUES["m"]),
                category_ids(x_raw[:, 2], CAT_VALUES["n"]),
            ],
            axis=1,
        )
        cont = self.cont_scaler.transform(self._continuous_log(x_raw)).astype(np.float32)
        return cat.astype(np.int64), cont

    def transform_y(self, y_raw: np.ndarray) -> np.ndarray:
        return self.curve_scaler.transform(self._curve_log(y_raw)).astype(np.float32)


def load_train_val(npz_path: str) -> tuple[tuple[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray], TaskfitPreprocessor]:
    print(f"[Data] Loading train-only data from {npz_path}")
    data = np.load(npz_path)
    x_raw = data["X_raw"].astype(np.float32)
    y_raw = data["y_raw"].astype(np.float32)
    x_train, x_val, y_train, y_val = train_test_split(
        x_raw, y_raw, test_size=0.2, random_state=42, stratify=x_raw[:, 0]
    )
    prep = TaskfitPreprocessor()
    prep.fit(x_train, y_train)
    print(f"[Data] train={len(x_train)} val={len(x_val)}")
    return (x_train, y_train), (x_val, y_val), prep


def make_forward_loaders(
    train_raw: tuple[np.ndarray, np.ndarray],
    val_raw: tuple[np.ndarray, np.ndarray],
    prep: TaskfitPreprocessor,
    batch_size: int,
) -> tuple[DataLoader, DataLoader]:
    x_train, y_train = train_raw
    x_val, y_val = val_raw
    train_cat, train_cont = prep.transform_x(x_train)
    val_cat, val_cont = prep.transform_x(x_val)
    train_curve = prep.transform_y(y_train)
    val_curve = prep.transform_y(y_val)
    train_ds = TensorDataset(
        torch.tensor(train_cat, dtype=torch.long),
        torch.tensor(train_cont, dtype=torch.float32),
        torch.tensor(train_curve, dtype=torch.float32),
    )
    val_ds = TensorDataset(
        torch.tensor(val_cat, dtype=torch.long),
        torch.tensor(val_cont, dtype=torch.float32),
        torch.tensor(val_curve, dtype=torch.float32),
    )
    return (
        DataLoader(train_ds, batch_size=batch_size, shuffle=True, pin_memory=DEVICE.type == "cuda"),
        DataLoader(val_ds, batch_size=batch_size, shuffle=False, pin_memory=DEVICE.type == "cuda"),
    )


def make_inverse_loaders(
    train_raw: tuple[np.ndarray, np.ndarray],
    val_raw: tuple[np.ndarray, np.ndarray],
    prep: TaskfitPreprocessor,
    batch_size: int,
) -> tuple[DataLoader, DataLoader]:
    x_train, y_train = train_raw
    x_val, y_val = val_raw
    train_cat, train_cont = prep.transform_x(x_train)
    val_cat, val_cont = prep.transform_x(x_val)
    train_curve = prep.transform_y(y_train)
    val_curve = prep.transform_y(y_val)
    train_ds = TensorDataset(
        torch.tensor(train_curve, dtype=torch.float32),
        torch.tensor(train_cat, dtype=torch.long),
        torch.tensor(train_cont, dtype=torch.float32),
    )
    val_ds = TensorDataset(
        torch.tensor(val_curve, dtype=torch.float32),
        torch.tensor(val_cat, dtype=torch.long),
        torch.tensor(val_cont, dtype=torch.float32),
    )
    return (
        DataLoader(train_ds, batch_size=batch_size, shuffle=True, pin_memory=DEVICE.type == "cuda"),
        DataLoader(val_ds, batch_size=batch_size, shuffle=False, pin_memory=DEVICE.type == "cuda"),
    )


def output_probabilities(outputs: dict[str, torch.Tensor]) -> list[torch.Tensor]:
    return [
        F.softmax(outputs["pattern"], dim=1),
        F.softmax(outputs["m"], dim=1),
        F.softmax(outputs["n"], dim=1),
    ]


def cat_ids_to_probs(cat_ids: torch.Tensor) -> list[torch.Tensor]:
    return [
        F.one_hot(cat_ids[:, 0], num_classes=2).float(),
        F.one_hot(cat_ids[:, 1], num_classes=3).float(),
        F.one_hot(cat_ids[:, 2], num_classes=3).float(),
    ]


def cat_probs_to_condition(probs: list[torch.Tensor]) -> torch.Tensor:
    return torch.cat(probs, dim=1)


def blend_cat_probs(
    teacher_probs: list[torch.Tensor],
    predicted_probs: list[torch.Tensor],
    teacher_ratio: float,
) -> list[torch.Tensor]:
    if teacher_ratio <= 0.0:
        return predicted_probs
    if teacher_ratio >= 1.0:
        return teacher_probs
    return [
        teacher_ratio * teacher + (1.0 - teacher_ratio) * predicted
        for teacher, predicted in zip(teacher_probs, predicted_probs)
    ]


def scheduled_teacher_ratio(epoch: int, hold_epochs: int, decay_epochs: int) -> float:
    if hold_epochs <= 0 and decay_epochs <= 0:
        return 0.0
    if epoch <= hold_epochs:
        return 1.0
    if decay_epochs <= 0:
        return 0.0
    progress = min(1.0, (epoch - hold_epochs) / decay_epochs)
    return 1.0 - progress


def cat_target_centers(device: torch.device) -> list[torch.Tensor]:
    return [
        torch.linspace(-1.0, 1.0, steps=2, device=device),
        torch.linspace(-1.0, 1.0, steps=3, device=device),
        torch.linspace(-1.0, 1.0, steps=3, device=device),
    ]


def cat_ids_to_target(cat_ids: torch.Tensor) -> torch.Tensor:
    parts = []
    for i, centers in enumerate(cat_target_centers(cat_ids.device)):
        parts.append(centers.index_select(0, cat_ids[:, i]).unsqueeze(1))
    return torch.cat(parts, dim=1)


def target_to_cat_probs(target: torch.Tensor, temperature: float = 0.08) -> list[torch.Tensor]:
    probs = []
    for i, centers in enumerate(cat_target_centers(target.device)):
        logits = -((target[:, i : i + 1] - centers.view(1, -1)) ** 2) / temperature
        probs.append(F.softmax(logits, dim=1))
    return probs


def target_to_class_loss(target: torch.Tensor, cat_ids: torch.Tensor, temperature: float = 0.08) -> torch.Tensor:
    losses = []
    for i, centers in enumerate(cat_target_centers(target.device)):
        logits = -((target[:, i : i + 1] - centers.view(1, -1)) ** 2) / temperature
        losses.append(F.cross_entropy(logits, cat_ids[:, i]))
    return sum(losses) / len(losses)


def class_loss(outputs: dict[str, torch.Tensor], cat_ids: torch.Tensor) -> torch.Tensor:
    return (
        F.cross_entropy(outputs["pattern"], cat_ids[:, 0])
        + F.cross_entropy(outputs["m"], cat_ids[:, 1])
        + F.cross_entropy(outputs["n"], cat_ids[:, 2])
    ) / 3.0


def build_adjacency(graph_type: str, device: torch.device) -> torch.Tensor:
    """Build an 8-node graph over pattern/m/n/tcrease/tpanel/W/creaseE/panelE."""
    n = len(INPUT_COLS)
    adj = torch.eye(n, dtype=torch.float32)

    def connect(*names: str) -> None:
        ids = [NODE_INDEX[name] for name in names]
        for i in ids:
            for j in ids:
                adj[i, j] = 1.0

    def edge(a: str, b: str) -> None:
        i, j = NODE_INDEX[a], NODE_INDEX[b]
        adj[i, j] = 1.0
        adj[j, i] = 1.0

    if graph_type == "full":
        adj[:] = 1.0
    elif graph_type == "physical":
        # Local groups.
        connect("pattern", "m", "n")
        connect("tcrease", "tpanel", "W")
        connect("creaseE", "panelE")

        # Mechanically motivated cross-group couplings.
        edge("pattern", "tcrease")
        edge("pattern", "tpanel")
        edge("pattern", "W")
        edge("m", "W")
        edge("n", "W")
        edge("tcrease", "creaseE")
        edge("tpanel", "panelE")
        edge("W", "tpanel")
        edge("W", "panelE")
        edge("tcrease", "tpanel")
    elif graph_type == "physical_sparse":
        connect("pattern", "m", "n")
        edge("m", "W")
        edge("n", "W")
        edge("tcrease", "creaseE")
        edge("tpanel", "panelE")
        edge("pattern", "tcrease")
        edge("pattern", "tpanel")
    else:
        raise ValueError(f"Unknown graph_type: {graph_type}")
    return adj.to(device)


def save_checkpoint(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, path)
    print(f"[Saved] {path}")


def save_history(history: list[dict[str, float]], name: str, args: argparse.Namespace) -> Path:
    df = pd.DataFrame(history)
    csv_path = Path(args.result_dir) / f"{name}_history.csv"
    xlsx_path = Path(args.result_dir) / f"{name}_history.xlsx"
    df.to_csv(csv_path, index=False)
    try:
        df.to_excel(xlsx_path, index=False)
    except Exception as exc:  # pragma: no cover - depends on optional Excel engine.
        print(f"[WARN] Could not write {xlsx_path.name}: {exc}")
    return csv_path


def plot_history(history: list[dict[str, float]], name: str, metrics: list[str], args: argparse.Namespace) -> None:
    df = pd.DataFrame(history)
    plt.figure(figsize=(14, 4 * len(metrics)))
    for idx, metric in enumerate(metrics, start=1):
        plt.subplot(len(metrics), 1, idx)
        train_col = f"train_{metric}"
        val_col = f"val_{metric}"
        if train_col in df:
            plt.plot(df["epoch"], df[train_col], label=train_col)
        if val_col in df:
            plt.plot(df["epoch"], df[val_col], label=val_col)
        plt.xlabel("Epoch")
        plt.ylabel(metric)
        plt.title(f"{name} {metric}")
        plt.grid(True, alpha=0.4)
        plt.legend()
    plt.tight_layout()
    out_path = Path(args.curve_dir) / f"{name}_loss.png"
    plt.savefig(out_path, dpi=240)
    plt.close()
    print(f"[Saved] {out_path}")


def freeze(model: torch.nn.Module) -> torch.nn.Module:
    model.eval()
    for param in model.parameters():
        param.requires_grad_(False)
    return model


def train_forward_resmlp(train_raw, val_raw, prep, args) -> Path:
    train_loader, val_loader = make_forward_loaders(train_raw, val_raw, prep, args.batch_size_forward)
    model = OrigamiForwardResMLP(hidden_dim=args.forward_hidden, dropout=args.forward_dropout).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.forward_lr, weight_decay=args.forward_weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=25, min_lr=1e-7)
    best_state = None
    best_val = float("inf")
    best_epoch = -1
    history = []

    for epoch in range(1, args.epochs_forward_resmlp + 1):
        row = {"epoch": epoch}
        for mode, loader in [("train", train_loader), ("val", val_loader)]:
            model.train(mode == "train")
            totals = {"total": 0.0, "bending": 0.0, "axial": 0.0}
            n_total = 0
            for cat, cont, curve in loader:
                cat, cont, curve = cat.to(DEVICE), cont.to(DEVICE), curve.to(DEVICE)
                with torch.set_grad_enabled(mode == "train"):
                    pred = model(cat, cont)
                    bending = F.mse_loss(pred[:, :3], curve[:, :3])
                    axial = F.mse_loss(pred[:, 3:], curve[:, 3:])
                    total = bending + axial
                    if mode == "train":
                        optimizer.zero_grad(set_to_none=True)
                        total.backward()
                        torch.nn.utils.clip_grad_norm_(model.parameters(), 0.8)
                        optimizer.step()
                bs = cat.size(0)
                n_total += bs
                totals["total"] += total.detach().item() * bs
                totals["bending"] += bending.detach().item() * bs
                totals["axial"] += axial.detach().item() * bs
            for key, val in totals.items():
                row[f"{mode}_{key}"] = val / n_total

        scheduler.step(row["val_total"])
        if row["val_total"] < best_val:
            best_val = row["val_total"]
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
        history.append(row)
        if epoch == 1 or epoch % args.log_every == 0:
            print(f"[forward_resmlp] e{epoch} train={row['train_total']:.5f} val={row['val_total']:.5f}")
        if args.forward_resmlp_patience > 0 and epoch - best_epoch >= args.forward_resmlp_patience:
            print(f"[forward_resmlp] early stop at epoch {epoch}; best epoch {best_epoch}")
            break

    ckpt_path = Path(args.checkpoint_dir) / "forward_resmlp" / "forward_resmlp_best.pth"
    save_checkpoint(
        ckpt_path,
        {
            "model_state": best_state,
            "best_val_total": best_val,
            "best_epoch": best_epoch,
            "preprocessor": prep,
            "config": vars(args),
            "input_cols": INPUT_COLS,
            "output_cols": OUTPUT_COLS,
        },
    )
    save_history(history, "forward_resmlp", args)
    plot_history(history, "forward_resmlp", ["total", "bending", "axial"], args)
    return ckpt_path


def train_inverse_resmlp(train_raw, val_raw, prep, surrogate_path: Path, args) -> Path:
    ckpt = torch.load(surrogate_path, map_location=DEVICE, weights_only=False)
    surrogate = OrigamiForwardResMLP(hidden_dim=args.forward_hidden, dropout=args.forward_dropout).to(DEVICE)
    surrogate.load_state_dict(ckpt["model_state"])
    freeze(surrogate)

    train_loader, val_loader = make_inverse_loaders(train_raw, val_raw, prep, args.batch_size_inverse)
    model = OrigamiInverseResMLP(hidden_dim=args.inverse_hidden, dropout=args.inverse_dropout).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.inverse_lr, weight_decay=args.inverse_weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.6, patience=35, min_lr=1e-7)
    best_state = None
    best_val = float("inf")
    best_epoch = -1
    history = []

    for epoch in range(1, args.epochs_inverse_resmlp + 1):
        row = {"epoch": epoch}
        loop_w = args.closed_loop_weight * min(1.0, epoch / max(1, args.closed_loop_warmup))
        for mode, loader in [("train", train_loader), ("val", val_loader)]:
            model.train(mode == "train")
            totals = {"total": 0.0, "class": 0.0, "param": 0.0, "closed_loop": 0.0}
            n_total = 0
            for curve, cat, cont in loader:
                curve, cat, cont = curve.to(DEVICE), cat.to(DEVICE), cont.to(DEVICE)
                with torch.set_grad_enabled(mode == "train"):
                    out = model(curve)
                    c_loss = class_loss(out, cat)
                    p_loss = F.smooth_l1_loss(out["cont"], cont)
                    pred_curve = surrogate.forward_from_probs(output_probabilities(out), out["cont"])
                    cl_loss = F.mse_loss(pred_curve, curve)
                    total = args.class_loss_weight * c_loss + args.param_loss_weight * p_loss + loop_w * cl_loss
                    if mode == "train":
                        optimizer.zero_grad(set_to_none=True)
                        total.backward()
                        torch.nn.utils.clip_grad_norm_(model.parameters(), 0.8)
                        optimizer.step()
                bs = curve.size(0)
                n_total += bs
                totals["total"] += total.detach().item() * bs
                totals["class"] += c_loss.detach().item() * bs
                totals["param"] += p_loss.detach().item() * bs
                totals["closed_loop"] += cl_loss.detach().item() * bs
            for key, val in totals.items():
                row[f"{mode}_{key}"] = val / n_total

        scheduler.step(row["val_total"])
        if row["val_total"] < best_val:
            best_val = row["val_total"]
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
        history.append(row)
        if epoch == 1 or epoch % args.log_every == 0:
            print(
                f"[inverse_resmlp] e{epoch} train={row['train_total']:.5f} "
                f"val={row['val_total']:.5f} loop={row['val_closed_loop']:.5f}"
            )
        if args.inverse_resmlp_patience > 0 and epoch - best_epoch >= args.inverse_resmlp_patience:
            print(f"[inverse_resmlp] early stop at epoch {epoch}; best epoch {best_epoch}")
            break

    ckpt_path = Path(args.checkpoint_dir) / "inverse_resmlp" / "inverse_resmlp_best.pth"
    save_checkpoint(
        ckpt_path,
        {
            "model_state": best_state,
            "best_val_total": best_val,
            "best_epoch": best_epoch,
            "preprocessor": prep,
            "surrogate": str(surrogate_path),
            "config": vars(args),
            "input_cols": INPUT_COLS,
            "output_cols": OUTPUT_COLS,
        },
    )
    save_history(history, "inverse_resmlp", args)
    plot_history(history, "inverse_resmlp", ["total", "class", "param", "closed_loop"], args)
    return ckpt_path


def train_forward_gat(train_raw, val_raw, prep, args) -> Path:
    train_loader, val_loader = make_forward_loaders(train_raw, val_raw, prep, args.batch_size_forward)
    model = OrigamiForwardGATTaskfit(
        hidden_dim=args.gat_hidden,
        heads=args.gat_heads,
        mlp_dim=args.gat_mlp_dim,
        dropout=args.gat_dropout,
    ).to(DEVICE)
    adj = build_adjacency(args.gat_graph, DEVICE)
    print(f"[forward_gat] graph={args.gat_graph} edges={int(adj.sum().item())}/{adj.numel()}")
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.forward_lr, weight_decay=args.forward_weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=25, min_lr=1e-7)
    best_state = None
    best_val = float("inf")
    best_epoch = -1
    history = []

    for epoch in range(1, args.epochs_forward_gat + 1):
        row = {"epoch": epoch}
        for mode, loader in [("train", train_loader), ("val", val_loader)]:
            model.train(mode == "train")
            totals = {"total": 0.0, "bending": 0.0, "axial": 0.0}
            n_total = 0
            for cat, cont, curve in loader:
                cat, cont, curve = cat.to(DEVICE), cont.to(DEVICE), curve.to(DEVICE)
                with torch.set_grad_enabled(mode == "train"):
                    pred = model(cat, cont, adj)
                    bending = F.mse_loss(pred[:, :3], curve[:, :3])
                    axial = F.mse_loss(pred[:, 3:], curve[:, 3:])
                    total = bending + axial
                    if mode == "train":
                        optimizer.zero_grad(set_to_none=True)
                        total.backward()
                        torch.nn.utils.clip_grad_norm_(model.parameters(), 0.8)
                        optimizer.step()
                bs = cat.size(0)
                n_total += bs
                totals["total"] += total.detach().item() * bs
                totals["bending"] += bending.detach().item() * bs
                totals["axial"] += axial.detach().item() * bs
            for key, val in totals.items():
                row[f"{mode}_{key}"] = val / n_total
        scheduler.step(row["val_total"])
        if row["val_total"] < best_val:
            best_val = row["val_total"]
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
        history.append(row)
        if epoch == 1 or epoch % args.log_every == 0:
            print(f"[forward_gat] e{epoch} train={row['train_total']:.5f} val={row['val_total']:.5f}")
        if args.forward_gat_patience > 0 and epoch - best_epoch >= args.forward_gat_patience:
            print(f"[forward_gat] early stop at epoch {epoch}; best epoch {best_epoch}")
            break

    ckpt_path = Path(args.checkpoint_dir) / "forward_gat" / "forward_gat_best.pth"
    save_checkpoint(
        ckpt_path,
        {
            "model_state": best_state,
            "best_val_total": best_val,
            "best_epoch": best_epoch,
            "preprocessor": prep,
            "config": vars(args),
            "input_cols": INPUT_COLS,
            "output_cols": OUTPUT_COLS,
        },
    )
    save_history(history, "forward_gat", args)
    plot_history(history, "forward_gat", ["total", "bending", "axial"], args)
    return ckpt_path


def train_forward_transformer(train_raw, val_raw, prep, args) -> Path:
    train_loader, val_loader = make_forward_loaders(train_raw, val_raw, prep, args.batch_size_forward)
    model = OrigamiForwardTransformerTaskfit(
        hidden_dim=args.transformer_hidden,
        num_heads=args.transformer_heads,
        num_layers=args.transformer_layers,
        dropout=args.transformer_dropout,
    ).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.transformer_lr, weight_decay=args.forward_weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=25, min_lr=1e-7)
    best_state = None
    best_val = float("inf")
    best_epoch = -1
    history = []

    for epoch in range(1, args.epochs_forward_transformer + 1):
        row = {"epoch": epoch}
        for mode, loader in [("train", train_loader), ("val", val_loader)]:
            model.train(mode == "train")
            totals = {"total": 0.0, "bending": 0.0, "axial": 0.0}
            n_total = 0
            for cat, cont, curve in loader:
                cat, cont, curve = cat.to(DEVICE), cont.to(DEVICE), curve.to(DEVICE)
                with torch.set_grad_enabled(mode == "train"):
                    pred = model(cat, cont)
                    bending = F.mse_loss(pred[:, :3], curve[:, :3])
                    axial = F.mse_loss(pred[:, 3:], curve[:, 3:])
                    total = bending + axial
                    if mode == "train":
                        optimizer.zero_grad(set_to_none=True)
                        total.backward()
                        torch.nn.utils.clip_grad_norm_(model.parameters(), 0.8)
                        optimizer.step()
                bs = cat.size(0)
                n_total += bs
                totals["total"] += total.detach().item() * bs
                totals["bending"] += bending.detach().item() * bs
                totals["axial"] += axial.detach().item() * bs
            for key, val in totals.items():
                row[f"{mode}_{key}"] = val / n_total
        scheduler.step(row["val_total"])
        if row["val_total"] < best_val:
            best_val = row["val_total"]
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
        history.append(row)
        if epoch == 1 or epoch % args.log_every == 0:
            print(f"[forward_transformer] e{epoch} train={row['train_total']:.5f} val={row['val_total']:.5f}")
        if args.forward_transformer_patience > 0 and epoch - best_epoch >= args.forward_transformer_patience:
            print(f"[forward_transformer] early stop at epoch {epoch}; best epoch {best_epoch}")
            break

    ckpt_path = Path(args.checkpoint_dir) / "forward_transformer" / "forward_transformer_best.pth"
    save_checkpoint(
        ckpt_path,
        {
            "model_state": best_state,
            "best_val_total": best_val,
            "best_epoch": best_epoch,
            "preprocessor": prep,
            "config": vars(args),
            "input_cols": INPUT_COLS,
            "output_cols": OUTPUT_COLS,
        },
    )
    save_history(history, "forward_transformer", args)
    plot_history(history, "forward_transformer", ["total", "bending", "axial"], args)
    return ckpt_path


def cvae_kl(mu: torch.Tensor, logvar: torch.Tensor, free_bits: float) -> tuple[torch.Tensor, torch.Tensor]:
    raw = torch.mean(torch.sum(-0.5 * (1 + logvar - mu.pow(2) - logvar.exp()), dim=1))
    return torch.maximum(raw, torch.tensor(free_bits, dtype=raw.dtype, device=raw.device)), raw


def build_diffusion_schedule(num_steps: int, beta_start: float, beta_end: float, device: torch.device) -> dict[str, torch.Tensor]:
    betas = torch.linspace(beta_start, beta_end, num_steps, dtype=torch.float32, device=device)
    alphas = 1.0 - betas
    alpha_cumprod = torch.cumprod(alphas, dim=0)
    return {
        "alpha_cumprod": alpha_cumprod,
        "sqrt_alpha_cumprod": torch.sqrt(alpha_cumprod),
        "sqrt_one_minus_alpha_cumprod": torch.sqrt(1.0 - alpha_cumprod),
    }


def extract_timesteps(values: torch.Tensor, timesteps: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    return values.gather(0, timesteps).view(timesteps.size(0), *([1] * (target.dim() - 1)))


def q_sample(x0: torch.Tensor, timesteps: torch.Tensor, noise: torch.Tensor, schedule: dict[str, torch.Tensor]) -> torch.Tensor:
    sqrt_ac = extract_timesteps(schedule["sqrt_alpha_cumprod"], timesteps, x0)
    sqrt_1m_ac = extract_timesteps(schedule["sqrt_one_minus_alpha_cumprod"], timesteps, x0)
    return sqrt_ac * x0 + sqrt_1m_ac * noise


def predict_x0(x_t: torch.Tensor, timesteps: torch.Tensor, eps_pred: torch.Tensor, schedule: dict[str, torch.Tensor]) -> torch.Tensor:
    sqrt_ac = extract_timesteps(schedule["sqrt_alpha_cumprod"], timesteps, x_t)
    sqrt_1m_ac = extract_timesteps(schedule["sqrt_one_minus_alpha_cumprod"], timesteps, x_t)
    return (x_t - sqrt_1m_ac * eps_pred) / sqrt_ac.clamp(min=1e-6)


def predict_noise(
    x_t: torch.Tensor,
    timesteps: torch.Tensor,
    x0_pred: torch.Tensor,
    schedule: dict[str, torch.Tensor],
) -> torch.Tensor:
    sqrt_ac = extract_timesteps(schedule["sqrt_alpha_cumprod"], timesteps, x_t)
    sqrt_1m_ac = extract_timesteps(schedule["sqrt_one_minus_alpha_cumprod"], timesteps, x_t)
    return (x_t - sqrt_ac * x0_pred) / sqrt_1m_ac.clamp(min=1e-6)


def diffusion_predictions(
    model_output: torch.Tensor,
    x_t: torch.Tensor,
    timesteps: torch.Tensor,
    schedule: dict[str, torch.Tensor],
    prediction_type: str,
) -> tuple[torch.Tensor, torch.Tensor]:
    if prediction_type == "epsilon":
        eps_pred = model_output
        x0_pred = predict_x0(x_t, timesteps, eps_pred, schedule)
    elif prediction_type == "x0":
        x0_pred = model_output
        eps_pred = predict_noise(x_t, timesteps, x0_pred, schedule)
    else:
        raise ValueError(f"Unsupported diffusion_prediction_type: {prediction_type}")
    return eps_pred, x0_pred


def make_diffusion_target(cat: torch.Tensor, cont: torch.Tensor) -> torch.Tensor:
    return torch.cat([cat_ids_to_target(cat), cont], dim=1)


def diffusion_target_losses(
    x0_pred: torch.Tensor,
    cat: torch.Tensor,
    cont: torch.Tensor,
    surrogate: OrigamiForwardTransformerTaskfit,
    curve: torch.Tensor,
    category_temperature: float,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    cls = target_to_class_loss(x0_pred[:, :3], cat, temperature=category_temperature)
    param = F.smooth_l1_loss(x0_pred[:, 3:], cont)
    pred_curve = surrogate.forward_from_probs(
        target_to_cat_probs(x0_pred[:, :3], temperature=category_temperature),
        x0_pred[:, 3:],
    )
    loop = F.mse_loss(pred_curve, curve)
    return cls, param, loop


def train_inverse_diffusion(train_raw, val_raw, prep, surrogate_path: Path, args) -> Path:
    ckpt = torch.load(surrogate_path, map_location=DEVICE, weights_only=False)
    surrogate = OrigamiForwardTransformerTaskfit(
        hidden_dim=args.transformer_hidden,
        num_heads=args.transformer_heads,
        num_layers=args.transformer_layers,
        dropout=args.transformer_dropout,
    ).to(DEVICE)
    surrogate.load_state_dict(ckpt["model_state"])
    freeze(surrogate)

    train_loader, val_loader = make_inverse_loaders(train_raw, val_raw, prep, args.batch_size_diffusion)
    model = OrigamiInverseDiffusionTaskfit(
        time_dim=args.diffusion_time_dim,
        cond_dim=args.diffusion_cond_dim,
        hidden_dim=args.diffusion_hidden,
        dropout=args.diffusion_dropout,
    ).to(DEVICE)
    schedule = build_diffusion_schedule(args.diffusion_steps, args.diffusion_beta_start, args.diffusion_beta_end, DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.diffusion_lr, weight_decay=args.inverse_weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs_inverse_diffusion, eta_min=1e-7)
    best_state = None
    best_val = float("inf")
    best_epoch = -1
    history = []

    for epoch in range(1, args.epochs_inverse_diffusion + 1):
        row = {"epoch": epoch}
        x0_w = args.diffusion_x0_weight * min(1.0, epoch / max(1, args.diffusion_x0_warmup))
        loop_w = args.closed_loop_weight * min(1.0, epoch / max(1, args.closed_loop_warmup))
        for mode, loader in [("train", train_loader), ("val", val_loader)]:
            model.train(mode == "train")
            totals = {"total": 0.0, "noise": 0.0, "x0": 0.0, "class": 0.0, "param": 0.0, "closed_loop": 0.0}
            n_total = 0
            for curve, cat, cont in loader:
                curve, cat, cont = curve.to(DEVICE), cat.to(DEVICE), cont.to(DEVICE)
                x0 = make_diffusion_target(cat, cont)
                t = torch.randint(0, args.diffusion_steps, (x0.size(0),), dtype=torch.long, device=DEVICE)
                noise = torch.randn_like(x0)
                x_t = q_sample(x0, t, noise, schedule)
                with torch.set_grad_enabled(mode == "train"):
                    model_output = model(x_t, t.float(), curve)
                    eps_pred, x0_pred = diffusion_predictions(
                        model_output,
                        x_t,
                        t,
                        schedule,
                        args.diffusion_prediction_type,
                    )
                    noise_loss = F.mse_loss(eps_pred, noise)
                    x0_loss = F.mse_loss(x0_pred, x0)
                    cls_loss, param_loss, loop_loss = diffusion_target_losses(
                        x0_pred, cat, cont, surrogate, curve, args.diffusion_category_temperature
                    )
                    total = (
                        args.diffusion_noise_weight * noise_loss
                        + x0_w * x0_loss
                        + args.class_loss_weight * cls_loss
                        + args.param_loss_weight * param_loss
                        + loop_w * loop_loss
                    )
                    if mode == "train":
                        optimizer.zero_grad(set_to_none=True)
                        total.backward()
                        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                        optimizer.step()
                bs = curve.size(0)
                n_total += bs
                totals["total"] += total.detach().item() * bs
                totals["noise"] += noise_loss.detach().item() * bs
                totals["x0"] += x0_loss.detach().item() * bs
                totals["class"] += cls_loss.detach().item() * bs
                totals["param"] += param_loss.detach().item() * bs
                totals["closed_loop"] += loop_loss.detach().item() * bs
            for key, val in totals.items():
                row[f"{mode}_{key}"] = val / n_total
        scheduler.step()

        select_val = row["val_x0"] + row["val_class"] + row["val_param"] + row["val_closed_loop"]
        row["val_select"] = select_val
        if select_val < best_val:
            best_val = select_val
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
        history.append(row)
        if epoch == 1 or epoch % args.log_every == 0:
            print(
                f"[inverse_diffusion] e{epoch} train={row['train_total']:.5f} val={row['val_total']:.5f} "
                f"select={row['val_select']:.5f} noise={row['val_noise']:.5f} x0={row['val_x0']:.5f} "
                f"loop={row['val_closed_loop']:.5f}"
            )
        if args.inverse_diffusion_patience > 0 and epoch - best_epoch >= args.inverse_diffusion_patience:
            print(f"[inverse_diffusion] early stop at epoch {epoch}; best epoch {best_epoch}")
            break

    ckpt_path = Path(args.checkpoint_dir) / "inverse_diffusion" / "inverse_diffusion_best.pth"
    save_checkpoint(
        ckpt_path,
        {
            "model_state": best_state,
            "best_val_select": best_val,
            "best_epoch": best_epoch,
            "preprocessor": prep,
            "surrogate": str(surrogate_path),
            "config": vars(args),
            "diffusion_config": {
                "steps": args.diffusion_steps,
                "beta_start": args.diffusion_beta_start,
                "beta_end": args.diffusion_beta_end,
                "prediction_type": args.diffusion_prediction_type,
                "noise_weight": args.diffusion_noise_weight,
            },
            "input_cols": INPUT_COLS,
            "output_cols": OUTPUT_COLS,
        },
    )
    save_history(history, "inverse_diffusion", args)
    plot_history(history, "inverse_diffusion", ["total", "noise", "x0", "class", "param", "closed_loop"], args)
    return ckpt_path


def train_inverse_classifier(train_raw, val_raw, prep, args) -> Path:
    train_loader, val_loader = make_inverse_loaders(train_raw, val_raw, prep, args.batch_size_inverse)
    model = OrigamiInverseDiscreteClassifier(
        hidden_dim=args.inverse_classifier_hidden,
        dropout=args.inverse_classifier_dropout,
    ).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.inverse_classifier_lr, weight_decay=args.inverse_weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.6, patience=30, min_lr=1e-7)
    best_state = None
    best_val = float("inf")
    best_epoch = -1
    history = []

    for epoch in range(1, args.epochs_inverse_classifier + 1):
        row = {"epoch": epoch}
        for mode, loader in [("train", train_loader), ("val", val_loader)]:
            model.train(mode == "train")
            totals = {"total": 0.0, "pattern_acc": 0.0, "m_acc": 0.0, "n_acc": 0.0}
            n_total = 0
            for curve, cat, _cont in loader:
                curve, cat = curve.to(DEVICE), cat.to(DEVICE)
                with torch.set_grad_enabled(mode == "train"):
                    out = model(curve)
                    total = class_loss(out, cat)
                    if mode == "train":
                        optimizer.zero_grad(set_to_none=True)
                        total.backward()
                        torch.nn.utils.clip_grad_norm_(model.parameters(), 0.8)
                        optimizer.step()
                bs = curve.size(0)
                n_total += bs
                totals["total"] += total.detach().item() * bs
                totals["pattern_acc"] += (out["pattern"].argmax(dim=1) == cat[:, 0]).float().sum().item()
                totals["m_acc"] += (out["m"].argmax(dim=1) == cat[:, 1]).float().sum().item()
                totals["n_acc"] += (out["n"].argmax(dim=1) == cat[:, 2]).float().sum().item()
            row[f"{mode}_total"] = totals["total"] / n_total
            row[f"{mode}_pattern_acc"] = totals["pattern_acc"] / n_total
            row[f"{mode}_m_acc"] = totals["m_acc"] / n_total
            row[f"{mode}_n_acc"] = totals["n_acc"] / n_total
        scheduler.step(row["val_total"])
        if row["val_total"] < best_val:
            best_val = row["val_total"]
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
        history.append(row)
        if epoch == 1 or epoch % args.log_every == 0:
            print(
                f"[inverse_classifier] e{epoch} train={row['train_total']:.5f} val={row['val_total']:.5f} "
                f"acc=({row['val_pattern_acc']:.3f},{row['val_m_acc']:.3f},{row['val_n_acc']:.3f})"
            )
        if args.inverse_classifier_patience > 0 and epoch - best_epoch >= args.inverse_classifier_patience:
            print(f"[inverse_classifier] early stop at epoch {epoch}; best epoch {best_epoch}")
            break

    ckpt_path = Path(args.checkpoint_dir) / "inverse_classifier" / "inverse_classifier_best.pth"
    save_checkpoint(
        ckpt_path,
        {
            "model_state": best_state,
            "best_val_total": best_val,
            "best_epoch": best_epoch,
            "preprocessor": prep,
            "config": vars(args),
            "input_cols": INPUT_COLS,
            "output_cols": OUTPUT_COLS,
        },
    )
    save_history(history, "inverse_classifier", args)
    plot_history(history, "inverse_classifier", ["total", "pattern_acc", "m_acc", "n_acc"], args)
    return ckpt_path


def train_inverse_cont_diffusion(train_raw, val_raw, prep, surrogate_path: Path, classifier_path: Path, args) -> Path:
    transformer_ckpt = torch.load(surrogate_path, map_location=DEVICE, weights_only=False)
    surrogate = OrigamiForwardTransformerTaskfit(
        hidden_dim=args.transformer_hidden,
        num_heads=args.transformer_heads,
        num_layers=args.transformer_layers,
        dropout=args.transformer_dropout,
    ).to(DEVICE)
    surrogate.load_state_dict(transformer_ckpt["model_state"])
    freeze(surrogate)

    classifier_ckpt = torch.load(classifier_path, map_location=DEVICE, weights_only=False)
    classifier = OrigamiInverseDiscreteClassifier(
        hidden_dim=args.inverse_classifier_hidden,
        dropout=args.inverse_classifier_dropout,
    ).to(DEVICE)
    classifier.load_state_dict(classifier_ckpt["model_state"])
    freeze(classifier)

    train_loader, val_loader = make_inverse_loaders(train_raw, val_raw, prep, args.batch_size_diffusion)
    model = OrigamiInverseDiffusionTaskfit(
        target_dim=5,
        cond_extra_dim=8,
        time_dim=args.diffusion_time_dim,
        cond_dim=args.diffusion_cond_dim,
        hidden_dim=args.diffusion_hidden,
        dropout=args.diffusion_dropout,
    ).to(DEVICE)
    schedule = build_diffusion_schedule(args.diffusion_steps, args.diffusion_beta_start, args.diffusion_beta_end, DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.diffusion_lr, weight_decay=args.inverse_weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs_inverse_cont_diffusion, eta_min=1e-7)
    best_state = None
    best_val = float("inf")
    best_epoch = -1
    history = []

    for epoch in range(1, args.epochs_inverse_cont_diffusion + 1):
        row = {"epoch": epoch}
        x0_w = args.diffusion_x0_weight * min(1.0, epoch / max(1, args.diffusion_x0_warmup))
        loop_w = args.closed_loop_weight * min(1.0, epoch / max(1, args.closed_loop_warmup))
        train_teacher_ratio = scheduled_teacher_ratio(
            epoch,
            args.split_loop_teacher_epochs,
            args.split_loop_teacher_decay_epochs,
        )
        row["train_teacher_ratio"] = train_teacher_ratio
        for mode, loader in [("train", train_loader), ("val", val_loader)]:
            model.train(mode == "train")
            totals = {"total": 0.0, "noise": 0.0, "x0": 0.0, "param": 0.0, "closed_loop": 0.0}
            n_total = 0
            for curve, cat, cont in loader:
                curve, cat, cont = curve.to(DEVICE), cat.to(DEVICE), cont.to(DEVICE)
                x0 = cont
                t = torch.randint(0, args.diffusion_steps, (x0.size(0),), dtype=torch.long, device=DEVICE)
                noise = torch.randn_like(x0)
                x_t = q_sample(x0, t, noise, schedule)
                with torch.set_grad_enabled(mode == "train"):
                    cls_out = classifier(curve)
                    predicted_probs = output_probabilities(cls_out)
                    teacher_probs = cat_ids_to_probs(cat)
                    teacher_ratio = train_teacher_ratio if mode == "train" else 0.0
                    cond_probs = blend_cat_probs(teacher_probs, predicted_probs, teacher_ratio)
                    model_output = model(x_t, t.float(), curve, cat_probs_to_condition(cond_probs))
                    eps_pred, x0_pred = diffusion_predictions(
                        model_output,
                        x_t,
                        t,
                        schedule,
                        args.diffusion_prediction_type,
                    )
                    noise_loss = F.mse_loss(eps_pred, noise)
                    x0_loss = F.mse_loss(x0_pred, x0)
                    param_loss = F.smooth_l1_loss(x0_pred, cont)
                    pred_curve = surrogate.forward_from_probs(cond_probs, x0_pred)
                    loop_loss = F.mse_loss(pred_curve, curve)
                    total = (
                        args.diffusion_noise_weight * noise_loss
                        + x0_w * x0_loss
                        + args.param_loss_weight * param_loss
                        + loop_w * loop_loss
                    )
                    if mode == "train":
                        optimizer.zero_grad(set_to_none=True)
                        total.backward()
                        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                        optimizer.step()
                bs = curve.size(0)
                n_total += bs
                totals["total"] += total.detach().item() * bs
                totals["noise"] += noise_loss.detach().item() * bs
                totals["x0"] += x0_loss.detach().item() * bs
                totals["param"] += param_loss.detach().item() * bs
                totals["closed_loop"] += loop_loss.detach().item() * bs
            for key, val in totals.items():
                row[f"{mode}_{key}"] = val / n_total
        scheduler.step()
        row["val_select"] = row["val_x0"] + row["val_param"] + row["val_closed_loop"]
        if row["val_select"] < best_val:
            best_val = row["val_select"]
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
        history.append(row)
        if epoch == 1 or epoch % args.log_every == 0:
            print(
                f"[inverse_cont_diffusion] e{epoch} train={row['train_total']:.5f} val={row['val_total']:.5f} "
                f"select={row['val_select']:.5f} noise={row['val_noise']:.5f} x0={row['val_x0']:.5f} "
                f"loop={row['val_closed_loop']:.5f} teacher={train_teacher_ratio:.2f}"
            )
        if args.inverse_cont_diffusion_patience > 0 and epoch - best_epoch >= args.inverse_cont_diffusion_patience:
            print(f"[inverse_cont_diffusion] early stop at epoch {epoch}; best epoch {best_epoch}")
            break

    ckpt_path = Path(args.checkpoint_dir) / "inverse_cont_diffusion" / "inverse_cont_diffusion_best.pth"
    save_checkpoint(
        ckpt_path,
        {
            "model_state": best_state,
            "best_val_select": best_val,
            "best_epoch": best_epoch,
            "preprocessor": prep,
            "surrogate": str(surrogate_path),
            "classifier": str(classifier_path),
            "config": vars(args),
            "diffusion_config": {
                "steps": args.diffusion_steps,
                "beta_start": args.diffusion_beta_start,
                "beta_end": args.diffusion_beta_end,
                "target_dim": 5,
                "cond_extra_dim": 8,
                "prediction_type": args.diffusion_prediction_type,
                "noise_weight": args.diffusion_noise_weight,
            },
            "input_cols": INPUT_COLS,
            "output_cols": OUTPUT_COLS,
        },
    )
    save_history(history, "inverse_cont_diffusion", args)
    plot_history(history, "inverse_cont_diffusion", ["total", "noise", "x0", "param", "closed_loop"], args)
    return ckpt_path


def train_inverse_cvae(train_raw, val_raw, prep, surrogate_path: Path, args) -> Path:
    ckpt = torch.load(surrogate_path, map_location=DEVICE, weights_only=False)
    surrogate = OrigamiForwardGATTaskfit(
        hidden_dim=args.gat_hidden,
        heads=args.gat_heads,
        mlp_dim=args.gat_mlp_dim,
        dropout=args.gat_dropout,
    ).to(DEVICE)
    surrogate.load_state_dict(ckpt["model_state"])
    freeze(surrogate)
    adj = build_adjacency(args.gat_graph, DEVICE)

    train_loader, val_loader = make_inverse_loaders(train_raw, val_raw, prep, args.batch_size_inverse)
    model = OrigamiInverseCVAEHeaded(latent_dim=args.cvae_latent_dim, hidden_dim=args.cvae_hidden).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.cvae_lr, weight_decay=args.inverse_weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs_inverse_cvae, eta_min=1e-7)
    best_state = None
    best_val = float("inf")
    best_epoch = -1
    history = []

    for epoch in range(1, args.epochs_inverse_cvae + 1):
        row = {"epoch": epoch}
        kl_weight = args.cvae_kl_weight * min(1.0, epoch / max(1, args.cvae_kl_warmup))
        loop_w = args.closed_loop_weight * min(1.0, epoch / max(1, args.closed_loop_warmup))
        for mode, loader in [("train", train_loader), ("val", val_loader)]:
            model.train(mode == "train")
            totals = {"total": 0.0, "class": 0.0, "param": 0.0, "kl": 0.0, "closed_loop": 0.0}
            n_total = 0
            for curve, cat, cont in loader:
                curve, cat, cont = curve.to(DEVICE), cat.to(DEVICE), cont.to(DEVICE)
                with torch.set_grad_enabled(mode == "train"):
                    out, mu, logvar = model(curve, cat, cont)
                    c_loss = class_loss(out, cat)
                    p_loss = F.mse_loss(out["cont"], cont)
                    kl_loss, raw_kl = cvae_kl(mu, logvar, args.cvae_free_bits)
                    pred_curve = surrogate.forward_from_probs(output_probabilities(out), out["cont"], adj)
                    cl_loss = F.mse_loss(pred_curve, curve)
                    total = (
                        args.class_loss_weight * c_loss
                        + args.param_loss_weight * p_loss
                        + kl_weight * kl_loss
                        + loop_w * cl_loss
                    )
                    if mode == "train":
                        optimizer.zero_grad(set_to_none=True)
                        total.backward()
                        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                        optimizer.step()
                bs = curve.size(0)
                n_total += bs
                totals["total"] += total.detach().item() * bs
                totals["class"] += c_loss.detach().item() * bs
                totals["param"] += p_loss.detach().item() * bs
                totals["kl"] += raw_kl.detach().item() * bs
                totals["closed_loop"] += cl_loss.detach().item() * bs
            for key, val in totals.items():
                row[f"{mode}_{key}"] = val / n_total
        scheduler.step()
        if args.cvae_select_metric == "task":
            select_val = row["val_class"] + row["val_param"] + row["val_closed_loop"]
        elif args.cvae_select_metric == "closed_loop":
            select_val = row["val_closed_loop"]
        else:
            select_val = row["val_total"]
        row["val_select"] = select_val

        if select_val < best_val:
            best_val = select_val
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
        history.append(row)
        if epoch == 1 or epoch % args.log_every == 0:
            print(
                f"[inverse_cvae] e{epoch} train={row['train_total']:.5f} "
                f"val={row['val_total']:.5f} select={row['val_select']:.5f} "
                f"kl={row['val_kl']:.5f} loop={row['val_closed_loop']:.5f}"
            )
        if args.inverse_cvae_patience > 0 and epoch - best_epoch >= args.inverse_cvae_patience:
            print(f"[inverse_cvae] early stop at epoch {epoch}; best epoch {best_epoch}")
            break

    ckpt_path = Path(args.checkpoint_dir) / "inverse_cvae" / "inverse_cvae_best.pth"
    save_checkpoint(
        ckpt_path,
        {
            "model_state": best_state,
            "best_val_select": best_val,
            "select_metric": args.cvae_select_metric,
            "best_epoch": best_epoch,
            "preprocessor": prep,
            "surrogate": str(surrogate_path),
            "config": vars(args),
            "input_cols": INPUT_COLS,
            "output_cols": OUTPUT_COLS,
        },
    )
    save_history(history, "inverse_cvae", args)
    plot_history(history, "inverse_cvae", ["total", "class", "param", "kl", "closed_loop"], args)
    return ckpt_path


def write_recommendations(args: argparse.Namespace) -> None:
    recommendations = []
    for csv_path in sorted(Path(args.result_dir).glob("*_history.csv")):
        df = pd.read_csv(csv_path)
        name = csv_path.stem.replace("_history", "")
        if "train_total" not in df or "val_total" not in df or len(df) < 3:
            continue
        train_last = float(df["train_total"].iloc[-1])
        val_last = float(df["val_total"].iloc[-1])
        val_best = float(df["val_total"].min())
        val_first = float(df["val_total"].iloc[0])
        gap = val_last - train_last
        if val_last > val_best * 1.15 and gap > 0.05:
            msg = "val loss has drifted above the best point; increase dropout/weight decay or add early stopping."
        elif val_last > val_first * 0.8:
            msg = "train/val loss are still high or slow to improve; try higher hidden_dim/lr or lower dropout."
        elif len(df) >= 8 and df["val_total"].tail(min(8, len(df))).std() > max(0.02, 0.15 * val_best):
            msg = "val loss is oscillating; lower lr, increase batch size, or tighten gradient clipping."
        else:
            msg = "loss trend is acceptable for the first pass; keep current hyperparameters for the next full run."
        recommendations.append(f"- `{name}`: {msg}")

        if "val_closed_loop" in df and float(df["val_closed_loop"].iloc[-1]) > float(df["val_closed_loop"].iloc[0]) * 0.9:
            recommendations.append(f"- `{name}` closed-loop: raise `closed_loop_weight` to 1.0 or extend warmup.")
        if "val_kl" in df:
            kl_last = float(df["val_kl"].iloc[-1])
            if kl_last < 0.05:
                recommendations.append(f"- `{name}` KL: KL is near zero; reduce KL weight or increase free bits.")
            elif "val_param" in df and kl_last > 5.0 and float(df["val_param"].iloc[-1]) > float(df["val_param"].iloc[0]) * 0.8:
                recommendations.append(f"- `{name}` KL: KL is large while reconstruction is weak; lengthen KL warmup.")

    out_path = Path(args.result_dir) / "hyperparameter_recommendations.md"
    out_path.write_text(
        "# Taskfit Hyperparameter Recommendations\n\n"
        + ("\n".join(recommendations) if recommendations else "No completed histories were found.\n"),
        encoding="utf-8",
    )
    print(f"[Saved] {out_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_path", type=str, default=str(SCRIPT_DIR / "data" / "origami_train.npz"))
    parser.add_argument("--checkpoint_dir", type=str, default=str(SCRIPT_DIR / "checkpoints_taskfit"))
    parser.add_argument("--result_dir", type=str, default=str(SCRIPT_DIR / "results_taskfit"))
    parser.add_argument("--curve_dir", type=str, default=str(SCRIPT_DIR / "results_taskfit" / "loss_curves"))
    parser.add_argument(
        "--stages",
        nargs="+",
        default=["forward_resmlp", "inverse_resmlp", "forward_gat", "inverse_cvae"],
        choices=[
            "forward_resmlp",
            "inverse_resmlp",
            "forward_gat",
            "inverse_cvae",
            "forward_transformer",
            "inverse_diffusion",
            "inverse_classifier",
            "inverse_cont_diffusion",
        ],
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--log_every", type=int, default=10)

    parser.add_argument("--epochs_forward_resmlp", type=int, default=500)
    parser.add_argument("--epochs_inverse_resmlp", type=int, default=500)
    parser.add_argument("--epochs_forward_gat", type=int, default=500)
    parser.add_argument("--epochs_forward_transformer", type=int, default=500)
    parser.add_argument("--epochs_inverse_cvae", type=int, default=400)
    parser.add_argument("--epochs_inverse_diffusion", type=int, default=600)
    parser.add_argument("--epochs_inverse_classifier", type=int, default=300)
    parser.add_argument("--epochs_inverse_cont_diffusion", type=int, default=700)
    parser.add_argument("--batch_size_forward", type=int, default=256)
    parser.add_argument("--batch_size_inverse", type=int, default=256)
    parser.add_argument("--batch_size_diffusion", type=int, default=512)

    parser.add_argument("--forward_hidden", type=int, default=256)
    parser.add_argument("--gat_hidden", type=int, default=256)
    parser.add_argument("--gat_heads", type=int, default=8)
    parser.add_argument("--gat_mlp_dim", type=int, default=256)
    parser.add_argument("--gat_graph", type=str, default="full", choices=["full", "physical", "physical_sparse"])
    parser.add_argument("--transformer_hidden", type=int, default=192)
    parser.add_argument("--transformer_heads", type=int, default=4)
    parser.add_argument("--transformer_layers", type=int, default=3)
    parser.add_argument("--inverse_hidden", type=int, default=256)
    parser.add_argument("--inverse_classifier_hidden", type=int, default=256)
    parser.add_argument("--cvae_hidden", type=int, default=512)
    parser.add_argument("--cvae_latent_dim", type=int, default=8)
    parser.add_argument("--forward_dropout", type=float, default=0.1)
    parser.add_argument("--gat_dropout", type=float, default=0.1)
    parser.add_argument("--transformer_dropout", type=float, default=0.12)
    parser.add_argument("--inverse_dropout", type=float, default=0.2)
    parser.add_argument("--inverse_classifier_dropout", type=float, default=0.1)
    parser.add_argument("--forward_lr", type=float, default=5e-4)
    parser.add_argument("--transformer_lr", type=float, default=2e-4)
    parser.add_argument("--inverse_lr", type=float, default=5e-4)
    parser.add_argument("--inverse_classifier_lr", type=float, default=5e-4)
    parser.add_argument("--cvae_lr", type=float, default=5e-4)
    parser.add_argument("--diffusion_lr", type=float, default=3e-4)
    parser.add_argument("--forward_weight_decay", type=float, default=1e-4)
    parser.add_argument("--inverse_weight_decay", type=float, default=1e-5)

    parser.add_argument("--class_loss_weight", type=float, default=0.5)
    parser.add_argument("--param_loss_weight", type=float, default=1.0)
    parser.add_argument("--closed_loop_weight", type=float, default=0.5)
    parser.add_argument("--closed_loop_warmup", type=int, default=50)
    parser.add_argument("--cvae_kl_weight", type=float, default=0.002)
    parser.add_argument("--cvae_kl_warmup", type=int, default=120)
    parser.add_argument("--cvae_free_bits", type=float, default=1.0)
    parser.add_argument("--cvae_select_metric", type=str, default="total", choices=["total", "task", "closed_loop"])
    parser.add_argument("--diffusion_steps", type=int, default=200)
    parser.add_argument("--diffusion_beta_start", type=float, default=1e-4)
    parser.add_argument("--diffusion_beta_end", type=float, default=0.02)
    parser.add_argument("--diffusion_time_dim", type=int, default=64)
    parser.add_argument("--diffusion_cond_dim", type=int, default=128)
    parser.add_argument("--diffusion_hidden", type=int, default=512)
    parser.add_argument("--diffusion_dropout", type=float, default=0.1)
    parser.add_argument("--diffusion_x0_weight", type=float, default=0.3)
    parser.add_argument("--diffusion_x0_warmup", type=int, default=200)
    parser.add_argument("--diffusion_prediction_type", type=str, default="epsilon", choices=["epsilon", "x0"])
    parser.add_argument("--diffusion_noise_weight", type=float, default=1.0)
    parser.add_argument("--diffusion_category_temperature", type=float, default=0.08)
    parser.add_argument("--split_loop_teacher_epochs", type=int, default=0)
    parser.add_argument("--split_loop_teacher_decay_epochs", type=int, default=0)
    parser.add_argument("--forward_resmlp_patience", type=int, default=0)
    parser.add_argument("--forward_gat_patience", type=int, default=0)
    parser.add_argument("--forward_transformer_patience", type=int, default=0)
    parser.add_argument("--inverse_resmlp_patience", type=int, default=0)
    parser.add_argument("--inverse_cvae_patience", type=int, default=0)
    parser.add_argument("--inverse_diffusion_patience", type=int, default=160)
    parser.add_argument("--inverse_classifier_patience", type=int, default=80)
    parser.add_argument("--inverse_cont_diffusion_patience", type=int, default=160)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if DEVICE.type == "cuda":
        torch.cuda.manual_seed_all(args.seed)
    make_dirs(args)
    (train_raw, val_raw, prep) = (*load_train_val(args.data_path),)
    config_path = Path(args.result_dir) / "taskfit_config.json"
    config_path.write_text(json.dumps(vars(args), indent=2, ensure_ascii=False), encoding="utf-8")

    forward_resmlp_path = Path(args.checkpoint_dir) / "forward_resmlp" / "forward_resmlp_best.pth"
    forward_gat_path = Path(args.checkpoint_dir) / "forward_gat" / "forward_gat_best.pth"
    forward_transformer_path = Path(args.checkpoint_dir) / "forward_transformer" / "forward_transformer_best.pth"
    inverse_classifier_path = Path(args.checkpoint_dir) / "inverse_classifier" / "inverse_classifier_best.pth"

    if "forward_resmlp" in args.stages:
        forward_resmlp_path = train_forward_resmlp(train_raw, val_raw, prep, args)
    if "inverse_resmlp" in args.stages:
        if not forward_resmlp_path.exists():
            raise FileNotFoundError(f"Missing forward ResMLP surrogate: {forward_resmlp_path}")
        train_inverse_resmlp(train_raw, val_raw, prep, forward_resmlp_path, args)
    if "forward_gat" in args.stages:
        forward_gat_path = train_forward_gat(train_raw, val_raw, prep, args)
    if "inverse_cvae" in args.stages:
        if not forward_gat_path.exists():
            raise FileNotFoundError(f"Missing forward GAT surrogate: {forward_gat_path}")
        train_inverse_cvae(train_raw, val_raw, prep, forward_gat_path, args)
    if "forward_transformer" in args.stages:
        forward_transformer_path = train_forward_transformer(train_raw, val_raw, prep, args)
    if "inverse_diffusion" in args.stages:
        if not forward_transformer_path.exists():
            raise FileNotFoundError(f"Missing forward Transformer surrogate: {forward_transformer_path}")
        train_inverse_diffusion(train_raw, val_raw, prep, forward_transformer_path, args)
    if "inverse_classifier" in args.stages:
        inverse_classifier_path = train_inverse_classifier(train_raw, val_raw, prep, args)
    if "inverse_cont_diffusion" in args.stages:
        if not forward_transformer_path.exists():
            raise FileNotFoundError(f"Missing forward Transformer surrogate: {forward_transformer_path}")
        if not inverse_classifier_path.exists():
            raise FileNotFoundError(f"Missing inverse classifier: {inverse_classifier_path}")
        train_inverse_cont_diffusion(train_raw, val_raw, prep, forward_transformer_path, inverse_classifier_path, args)

    write_recommendations(args)
    print("[DONE] Taskfit training pipeline complete.")


if __name__ == "__main__":
    main()
