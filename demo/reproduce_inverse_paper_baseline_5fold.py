import argparse
import glob
import os
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.model_selection import KFold, train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
TRAIN_XLSX = str(REPO_ROOT / "dataset used for training" / "train.xlsx")
TEST_XLSX = str(REPO_ROOT / "dataset used for training" / "test.xlsx")
INVERSE_METRICS_CSV = str(REPO_ROOT / "diffusion" / "inverse_test_results" / "inverse_test_metrics.csv")
CVAE_TOPK_NPZ = str(REPO_ROOT / "diffusion" / "inverse_test_results" / "cvae_topk_candidates.npz")
DIFF_TOPK_NPZ = str(REPO_ROOT / "diffusion" / "inverse_test_results" / "diffusion_topk_candidates.npz")
OUT_DIR = str(SCRIPT_DIR / "comparison_results" / "inverse_paper_baseline_reproduce")


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _find_supp_docx() -> str:
    hits = glob.glob(
        os.path.join(r"C:\Users\48186\Desktop", "**", "smll202500634-sup-0001-suppmat.docx"),
        recursive=True,
    )
    if not hits:
        raise FileNotFoundError("Cannot find smll202500634-sup-0001-suppmat.docx under Desktop.")
    return hits[0]


def _extract_paper_inverse_table_s1_best(docx_path: str) -> float:
    with zipfile.ZipFile(docx_path, "r") as zf:
        xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
    txt = re.sub(r"<[^>]+>", " ", xml)
    txt = re.sub(r"\s+", " ", txt)

    m1 = re.search(r"Table\s*S\s*1", txt, flags=re.IGNORECASE)
    m2 = re.search(r"Table\s*S\s*2", txt, flags=re.IGNORECASE)
    if not m1 or not m2:
        raise RuntimeError("Failed to locate Table S1/S2 in supplementary DOCX.")

    block = txt[m1.start() : m2.start()]
    vals = [float(v) for v in re.findall(r"0\.\d+", block) if float(v) < 0.2]
    if not vals:
        raise RuntimeError("Failed to parse Table S1 scores.")
    return min(vals)


def _load_dataset(xlsx_path: str) -> Tuple[np.ndarray, np.ndarray]:
    cols = [
        "V1a",
        "V1v",
        "V1c",
        "w",
        "relativeVolume",
        "relativeArea",
        "thickness",
        "poreDiameter",
        "areaMean",
        "s1",
        "s2",
        "s3",
        "s4",
        "s5",
        "s6",
        "s7",
        "s8",
        "s9",
        "s10",
        "s11",
        "s12",
        "s13",
        "s14",
        "s15",
        "s16",
        "s17",
        "s18",
        "s19",
        "s20",
    ]
    frames = [
        pd.read_excel(xlsx_path, sheet_name="class1", names=cols),
        pd.read_excel(xlsx_path, sheet_name="class2", names=cols),
        pd.read_excel(xlsx_path, sheet_name="class12", names=cols),
    ]
    df = pd.concat(frames, axis=0).reset_index(drop=True)
    x_curve = df.iloc[:, 9:].to_numpy(dtype=np.float32)  # input curve, shape [N,20]
    y_param = df.iloc[:, :9].to_numpy(dtype=np.float32)  # target params, shape [N,9]
    return x_curve, y_param


class DenseBlock(nn.Module):
    def __init__(self, in_dim: int, out_dim: int, dropout: float):
        super().__init__()
        self.fc = nn.Linear(in_dim, out_dim)
        self.bn = nn.BatchNorm1d(out_dim)
        self.act = nn.ReLU(inplace=True)
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc(x)
        x = self.bn(x)
        x = self.act(x)
        x = self.drop(x)
        return x


class ResidualFCBlock(nn.Module):
    def __init__(self, dim: int, dropout: float):
        super().__init__()
        self.fc1 = nn.Linear(dim, dim)
        self.bn1 = nn.BatchNorm1d(dim)
        self.fc2 = nn.Linear(dim, dim)
        self.bn2 = nn.BatchNorm1d(dim)
        self.act = nn.ReLU(inplace=True)
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        x = self.fc1(x)
        x = self.bn1(x)
        x = self.act(x)
        x = self.drop(x)
        x = self.fc2(x)
        x = self.bn2(x)
        x = x + residual
        x = self.act(x)
        return x


class PaperInverseBaselineMLP(nn.Module):
    # Based on supplementary Table S1 best-ranked 11-layer setting:
    # 11 (D256,R256,D512,R512,D1024,R1024,D2048,R2048,D512,R512,D64)
    def __init__(self, in_dim: int = 20, out_dim: int = 9, dropout: float = 0.1):
        super().__init__()
        config: Sequence[Tuple[str, int]] = [
            ("D", 256),
            ("R", 256),
            ("D", 512),
            ("R", 512),
            ("D", 1024),
            ("R", 1024),
            ("D", 2048),
            ("R", 2048),
            ("D", 512),
            ("R", 512),
            ("D", 64),
        ]

        layers: List[nn.Module] = []
        curr = in_dim
        for typ, units in config:
            if typ == "D":
                layers.append(DenseBlock(curr, units, dropout))
                curr = units
            elif typ == "R":
                if curr != units:
                    layers.append(DenseBlock(curr, units, dropout))
                    curr = units
                layers.append(ResidualFCBlock(units, dropout))
            else:
                raise ValueError(f"Unknown layer type: {typ}")
        self.backbone = nn.Sequential(*layers)
        self.head = nn.Linear(curr, out_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.backbone(x))


@dataclass
class Metrics:
    mse: float
    mae: float
    rmse: float
    nrmse: float
    nrmse_pct: float


def calc_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Metrics:
    diff = y_true - y_pred
    mse = float(np.mean(diff ** 2))
    mae = float(np.mean(np.abs(diff)))
    rmse = float(np.sqrt(mse))
    val_range = max(float(np.max(y_true) - np.min(y_true)), 1e-12)
    nrmse = rmse / val_range
    return Metrics(mse=mse, mae=mae, rmse=rmse, nrmse=nrmse, nrmse_pct=nrmse * 100.0)


def _fit_one_split(
    x_train_raw: np.ndarray,
    y_train_raw: np.ndarray,
    x_val_raw: np.ndarray,
    y_val_raw: np.ndarray,
    epochs: int,
    batch_size: int,
    lr: float,
    weight_decay: float,
    patience: int,
    seed: int,
) -> Tuple[np.ndarray, Dict[str, float]]:
    _set_seed(seed)

    scaler_x = StandardScaler()
    scaler_y = StandardScaler()
    x_train = scaler_x.fit_transform(x_train_raw).astype(np.float32)
    y_train = scaler_y.fit_transform(y_train_raw).astype(np.float32)
    x_val = scaler_x.transform(x_val_raw).astype(np.float32)
    y_val = scaler_y.transform(y_val_raw).astype(np.float32)

    train_ds = TensorDataset(
        torch.tensor(x_train, dtype=torch.float32),
        torch.tensor(y_train, dtype=torch.float32),
    )
    val_ds = TensorDataset(
        torch.tensor(x_val, dtype=torch.float32),
        torch.tensor(y_val, dtype=torch.float32),
    )
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    model = PaperInverseBaselineMLP(dropout=0.1).to(DEVICE)
    optimizer = torch.optim.RMSprop(model.parameters(), lr=lr, weight_decay=weight_decay)
    criterion = nn.MSELoss()

    best_val = float("inf")
    best_state = None
    no_improve = 0

    for epoch in range(epochs):
        model.train()
        for bx, by in train_loader:
            bx = bx.to(DEVICE)
            by = by.to(DEVICE)
            optimizer.zero_grad()
            pred = model(bx)
            loss = criterion(pred, by)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

        model.eval()
        val_loss = 0.0
        count = 0
        with torch.no_grad():
            for bx, by in val_loader:
                bx = bx.to(DEVICE)
                by = by.to(DEVICE)
                pred = model(bx)
                batch_loss = criterion(pred, by).item()
                val_loss += batch_loss * bx.size(0)
                count += bx.size(0)
        val_loss /= max(count, 1)

        if val_loss < best_val:
            best_val = val_loss
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= patience:
                break

    if best_state is None:
        best_state = model.state_dict()
    model.load_state_dict(best_state)
    model.eval()

    x_val_t = torch.tensor(x_val, dtype=torch.float32, device=DEVICE)
    preds_scaled = []
    with torch.no_grad():
        for st in range(0, len(x_val_t), batch_size):
            pred = model(x_val_t[st : st + batch_size]).detach().cpu().numpy()
            preds_scaled.append(pred)
    y_pred_scaled = np.concatenate(preds_scaled, axis=0)
    y_pred_raw = scaler_y.inverse_transform(y_pred_scaled)

    train_log = {
        "best_val_scaled_mse": float(best_val),
        "epochs_ran": epoch + 1,
    }
    return y_pred_raw, train_log


def run_5fold_cv(
    x_raw: np.ndarray,
    y_raw: np.ndarray,
    epochs: int,
    batch_size: int,
    lr: float,
    weight_decay: float,
    patience: int,
    seed: int,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    kf = KFold(n_splits=5, shuffle=True, random_state=seed)
    fold_rows = []
    all_pred = np.zeros_like(y_raw, dtype=np.float32)

    for fold_id, (tr_idx, va_idx) in enumerate(kf.split(x_raw), start=1):
        y_pred_val, train_log = _fit_one_split(
            x_train_raw=x_raw[tr_idx],
            y_train_raw=y_raw[tr_idx],
            x_val_raw=x_raw[va_idx],
            y_val_raw=y_raw[va_idx],
            epochs=epochs,
            batch_size=batch_size,
            lr=lr,
            weight_decay=weight_decay,
            patience=patience,
            seed=seed + fold_id,
        )
        all_pred[va_idx] = y_pred_val
        m = calc_metrics(y_raw[va_idx], y_pred_val)
        fold_rows.append(
            {
                "fold": fold_id,
                "samples": int(len(va_idx)),
                "mse": m.mse,
                "mae": m.mae,
                "rmse": m.rmse,
                "nrmse": m.nrmse,
                "nrmse_pct": m.nrmse_pct,
                **train_log,
            }
        )
        print(
            f"[5-fold] Fold {fold_id}/5 | n={len(va_idx)} | "
            f"RMSE={m.rmse:.6f}, NRMSE={m.nrmse:.6f} ({m.nrmse_pct:.3f}%) | "
            f"epochs={train_log['epochs_ran']}"
        )

    fold_df = pd.DataFrame(fold_rows)
    overall = calc_metrics(y_raw, all_pred)
    summary_df = pd.DataFrame(
        [
            {
                "model": "paper_inverse_baseline_mlp_5fold_oof",
                "mse": overall.mse,
                "mae": overall.mae,
                "rmse": overall.rmse,
                "nrmse": overall.nrmse,
                "nrmse_pct": overall.nrmse_pct,
                "fold_rmse_mean": float(fold_df["rmse"].mean()),
                "fold_rmse_std": float(fold_df["rmse"].std(ddof=0)),
                "fold_nrmse_mean": float(fold_df["nrmse"].mean()),
                "fold_nrmse_std": float(fold_df["nrmse"].std(ddof=0)),
                "fold_nrmse_pct_mean": float(fold_df["nrmse_pct"].mean()),
                "fold_nrmse_pct_std": float(fold_df["nrmse_pct"].std(ddof=0)),
            }
        ]
    )
    return fold_df, summary_df


def train_trainset_eval_testset(
    x_train_raw: np.ndarray,
    y_train_raw: np.ndarray,
    x_test_raw: np.ndarray,
    y_test_raw: np.ndarray,
    epochs: int,
    batch_size: int,
    lr: float,
    weight_decay: float,
    patience: int,
    seed: int,
) -> pd.DataFrame:
    x_tr, x_va, y_tr, y_va = train_test_split(
        x_train_raw, y_train_raw, test_size=0.1, random_state=seed
    )
    y_pred_val, train_log = _fit_one_split(
        x_train_raw=x_tr,
        y_train_raw=y_tr,
        x_val_raw=x_va,
        y_val_raw=y_va,
        epochs=epochs,
        batch_size=batch_size,
        lr=lr,
        weight_decay=weight_decay,
        patience=patience,
        seed=seed + 99,
    )
    _ = y_pred_val  # validation prediction not used in final report

    # Retrain on full train-set with test-set only for final evaluation:
    scaler_x = StandardScaler()
    scaler_y = StandardScaler()
    x_train = scaler_x.fit_transform(x_train_raw).astype(np.float32)
    y_train = scaler_y.fit_transform(y_train_raw).astype(np.float32)
    x_test = scaler_x.transform(x_test_raw).astype(np.float32)

    train_ds = TensorDataset(
        torch.tensor(x_train, dtype=torch.float32),
        torch.tensor(y_train, dtype=torch.float32),
    )
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

    model = PaperInverseBaselineMLP(dropout=0.1).to(DEVICE)
    optimizer = torch.optim.RMSprop(model.parameters(), lr=lr, weight_decay=weight_decay)
    criterion = nn.MSELoss()
    best_state = None
    best_loss = float("inf")
    no_improve = 0

    _set_seed(seed + 123)
    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0
        count = 0
        for bx, by in train_loader:
            bx = bx.to(DEVICE)
            by = by.to(DEVICE)
            optimizer.zero_grad()
            pred = model(bx)
            loss = criterion(pred, by)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            epoch_loss += loss.item() * bx.size(0)
            count += bx.size(0)
        epoch_loss /= max(count, 1)

        if epoch_loss < best_loss:
            best_loss = epoch_loss
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()

    x_test_t = torch.tensor(x_test, dtype=torch.float32, device=DEVICE)
    preds_scaled = []
    with torch.no_grad():
        for st in range(0, len(x_test_t), batch_size):
            pred = model(x_test_t[st : st + batch_size]).detach().cpu().numpy()
            preds_scaled.append(pred)
    y_pred_test = scaler_y.inverse_transform(np.concatenate(preds_scaled, axis=0))
    m = calc_metrics(y_test_raw, y_pred_test)
    print(
        f"[Train->Test] Baseline | RMSE={m.rmse:.6f}, NRMSE={m.nrmse:.6f} ({m.nrmse_pct:.3f}%) "
        f"| best_train_scaled_mse={best_loss:.6f}"
    )
    return pd.DataFrame(
        [
            {
                "model": "paper_inverse_baseline_mlp",
                "mse": m.mse,
                "mae": m.mae,
                "rmse": m.rmse,
                "nrmse": m.nrmse,
                "nrmse_pct": m.nrmse_pct,
                "best_train_scaled_mse": float(best_loss),
                "epochs_ran": int(epoch + 1),
                "val_probe_best_scaled_mse": float(train_log["best_val_scaled_mse"]),
                "val_probe_epochs": int(train_log["epochs_ran"]),
            }
        ]
    )


def build_strict_comparison(
    baseline_test_df: pd.DataFrame,
    cvae_npz: str,
    diffusion_npz: str,
    y_test_true: np.ndarray,
    paper_table_s1_best: float,
) -> pd.DataFrame:
    cvae_top1 = np.load(cvae_npz)["topk_params"][:, 0, :]
    diff_top1 = np.load(diffusion_npz)["topk_params"][:, 0, :]

    cvae_m = calc_metrics(y_test_true, cvae_top1)
    diff_m = calc_metrics(y_test_true, diff_top1)
    base_row = baseline_test_df.iloc[0]
    base_m = Metrics(
        mse=float(base_row["mse"]),
        mae=float(base_row["mae"]),
        rmse=float(base_row["rmse"]),
        nrmse=float(base_row["nrmse"]),
        nrmse_pct=float(base_row["nrmse_pct"]),
    )

    rows = [
        {
            "model": "paper_tableS1_best_reported",
            "score_type": "paper_mean_test_score",
            "rmse": np.nan,
            "nrmse": paper_table_s1_best,
            "nrmse_pct": paper_table_s1_best * 100.0,
            "improve_vs_baseline_test_nrmse_pct": np.nan,
            "improve_vs_paper_reported_nrmse_pct": 0.0,
        },
        {
            "model": "paper_inverse_baseline_mlp",
            "score_type": "test_top1_params",
            "rmse": base_m.rmse,
            "nrmse": base_m.nrmse,
            "nrmse_pct": base_m.nrmse_pct,
            "improve_vs_baseline_test_nrmse_pct": 0.0,
            "improve_vs_paper_reported_nrmse_pct": (paper_table_s1_best - base_m.nrmse)
            / max(abs(paper_table_s1_best), 1e-12)
            * 100.0,
        },
        {
            "model": "cvae_top1",
            "score_type": "test_top1_params",
            "rmse": cvae_m.rmse,
            "nrmse": cvae_m.nrmse,
            "nrmse_pct": cvae_m.nrmse_pct,
            "improve_vs_baseline_test_nrmse_pct": (base_m.nrmse - cvae_m.nrmse)
            / max(abs(base_m.nrmse), 1e-12)
            * 100.0,
            "improve_vs_paper_reported_nrmse_pct": (paper_table_s1_best - cvae_m.nrmse)
            / max(abs(paper_table_s1_best), 1e-12)
            * 100.0,
        },
        {
            "model": "diffusion_top1",
            "score_type": "test_top1_params",
            "rmse": diff_m.rmse,
            "nrmse": diff_m.nrmse,
            "nrmse_pct": diff_m.nrmse_pct,
            "improve_vs_baseline_test_nrmse_pct": (base_m.nrmse - diff_m.nrmse)
            / max(abs(base_m.nrmse), 1e-12)
            * 100.0,
            "improve_vs_paper_reported_nrmse_pct": (paper_table_s1_best - diff_m.nrmse)
            / max(abs(paper_table_s1_best), 1e-12)
            * 100.0,
        },
    ]
    return pd.DataFrame(rows)


def plot_results(
    fold_df: pd.DataFrame,
    baseline_test_df: pd.DataFrame,
    strict_df: pd.DataFrame,
    fig_path: str,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.6))

    # Left: 5-fold reproducibility for paper baseline
    ax = axes[0]
    x = np.arange(len(fold_df), dtype=int)
    bars = ax.bar(x, fold_df["nrmse"], color="#4c78a8", alpha=0.9, label="Fold NRMSE")
    ax.errorbar(
        [len(fold_df) + 0.5],
        [fold_df["nrmse"].mean()],
        yerr=[fold_df["nrmse"].std(ddof=0)],
        fmt="o",
        color="#f58518",
        capsize=5,
        label="Mean卤Std",
    )
    ax.set_xticks(list(x) + [len(fold_df) + 0.5])
    ax.set_xticklabels([f"Fold{i}" for i in range(1, len(fold_df) + 1)] + ["Mean"])
    ax.set_title("Paper Inverse Baseline Reproduction (5-fold, same score)")
    ax.set_ylabel("NRMSE (ratio, lower better)")
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)
    for b, v in zip(bars, fold_df["nrmse"].tolist()):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{v:.4f}", ha="center", va="bottom", fontsize=8)
    ax.legend(fontsize=8)

    # Right: strict test comparison under same metric definition
    ax = axes[1]
    comp = strict_df[strict_df["score_type"] == "test_top1_params"].copy()
    labels = comp["model"].tolist()
    vals = comp["nrmse"].tolist()
    bars = ax.bar(labels, vals, color=["#888888", "#5f9e6e", "#3b82f6"])
    ax.set_title("Strict Comparable Test Metrics (Top1 Params, same RMSE/NRMSE)")
    ax.set_ylabel("NRMSE (ratio, lower better)")
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)
    for i, (b, v) in enumerate(zip(bars, vals)):
        if i == 0:
            txt = f"{v:.4f}\nbaseline"
        else:
            impr = float(comp.iloc[i]["improve_vs_baseline_test_nrmse_pct"])
            txt = f"{v:.4f}\n{impr:+.1f}% vs baseline"
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), txt, ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    fig.savefig(fig_path, dpi=300)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=180)
    parser.add_argument("--batch_size", type=int, default=512)
    parser.add_argument("--lr", type=float, default=8e-4)
    parser.add_argument("--weight_decay", type=float, default=1e-5)
    parser.add_argument("--patience", type=int, default=25)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    _set_seed(args.seed)

    print(f"[Device] {DEVICE}")
    print(f"[Config] epochs={args.epochs}, batch_size={args.batch_size}, lr={args.lr}, wd={args.weight_decay}")

    supp_docx = _find_supp_docx()
    paper_s1_best = _extract_paper_inverse_table_s1_best(supp_docx)
    print(f"[Paper] Table S1 best mean test score = {paper_s1_best:.6f}")

    x_train_raw, y_train_raw = _load_dataset(TRAIN_XLSX)
    x_test_raw, y_test_raw = _load_dataset(TEST_XLSX)

    fold_df, cv_summary_df = run_5fold_cv(
        x_raw=x_train_raw,
        y_raw=y_train_raw,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        weight_decay=args.weight_decay,
        patience=args.patience,
        seed=args.seed,
    )
    fold_csv = os.path.join(OUT_DIR, "inverse_paper_baseline_5fold_folds.csv")
    summary_csv = os.path.join(OUT_DIR, "inverse_paper_baseline_5fold_summary.csv")
    fold_df.to_csv(fold_csv, index=False)
    cv_summary_df.to_csv(summary_csv, index=False)

    baseline_test_df = train_trainset_eval_testset(
        x_train_raw=x_train_raw,
        y_train_raw=y_train_raw,
        x_test_raw=x_test_raw,
        y_test_raw=y_test_raw,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        weight_decay=args.weight_decay,
        patience=args.patience,
        seed=args.seed,
    )
    baseline_test_csv = os.path.join(OUT_DIR, "inverse_paper_baseline_test_metrics.csv")
    baseline_test_df.to_csv(baseline_test_csv, index=False)

    strict_df = build_strict_comparison(
        baseline_test_df=baseline_test_df,
        cvae_npz=CVAE_TOPK_NPZ,
        diffusion_npz=DIFF_TOPK_NPZ,
        y_test_true=y_test_raw,
        paper_table_s1_best=paper_s1_best,
    )
    strict_csv = os.path.join(OUT_DIR, "inverse_strict_comparable_metrics.csv")
    strict_df.to_csv(strict_csv, index=False)

    fig_path = os.path.join(OUT_DIR, "inverse_strict_comparable_plot.png")
    plot_results(fold_df=fold_df, baseline_test_df=baseline_test_df, strict_df=strict_df, fig_path=fig_path)

    meta = pd.DataFrame(
        [
            {
                "supp_docx_path": supp_docx,
                "paper_table_s1_best": paper_s1_best,
                "train_samples": len(x_train_raw),
                "test_samples": len(x_test_raw),
                "epochs": args.epochs,
                "batch_size": args.batch_size,
                "lr": args.lr,
                "weight_decay": args.weight_decay,
                "patience": args.patience,
            }
        ]
    )
    meta_csv = os.path.join(OUT_DIR, "meta.csv")
    meta.to_csv(meta_csv, index=False)

    print(f"[Saved] {fold_csv}")
    print(f"[Saved] {summary_csv}")
    print(f"[Saved] {baseline_test_csv}")
    print(f"[Saved] {strict_csv}")
    print(f"[Saved] {fig_path}")
    print(f"[Saved] {meta_csv}")

    print("\n[5-fold summary]")
    print(cv_summary_df.to_string(index=False))
    print("\n[Test strict comparison]")
    print(strict_df.to_string(index=False))


if __name__ == "__main__":
    main()



