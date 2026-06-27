"""Generate unified loss curves for final audited taskfit models."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR / "model_audit" / "loss_curves_final"

PLOTS = [
    {
        "name": "forward_resmlp",
        "history": SCRIPT_DIR / "results_taskfit" / "forward_resmlp_history.csv",
        "metrics": ["total", "bending", "axial"],
    },
    {
        "name": "forward_gat_physical_sparse",
        "history": SCRIPT_DIR / "gat_grid_sparse" / "results_h192_d0p12_lr0p0002" / "forward_gat_history.csv",
        "metrics": ["total", "bending", "axial"],
    },
    {
        "name": "forward_transformer",
        "history": SCRIPT_DIR / "tf_grid" / "results_h192_d0p08_lr0p0002" / "forward_transformer_history.csv",
        "metrics": ["total", "bending", "axial"],
    },
    {
        "name": "inverse_resmlp",
        "history": SCRIPT_DIR / "results_taskfit" / "inverse_resmlp_history.csv",
        "metrics": ["total", "class", "param", "closed_loop"],
    },
    {
        "name": "inverse_cvae_physical",
        "history": SCRIPT_DIR / "results_taskfit_round3_physical" / "inverse_cvae_history.csv",
        "metrics": ["total", "class", "param", "kl", "closed_loop"],
    },
    {
        "name": "inverse_diffusion_x0",
        "history": SCRIPT_DIR / "diffusion_x0_round1" / "results" / "inverse_diffusion_history.csv",
        "metrics": ["total", "noise", "x0", "class", "param", "closed_loop", "select"],
    },
    {
        "name": "inverse_classifier",
        "history": SCRIPT_DIR / "split_diff_round1" / "results" / "inverse_classifier_history.csv",
        "metrics": ["total", "pattern_acc", "m_acc", "n_acc"],
    },
    {
        "name": "inverse_cont_diffusion_split_experimental",
        "history": SCRIPT_DIR / "split_diff_x0_round3" / "results" / "inverse_cont_diffusion_history.csv",
        "metrics": ["total", "noise", "x0", "param", "closed_loop", "select"],
    },
]


def add_select_column(df: pd.DataFrame) -> pd.DataFrame:
    if "val_select" not in df.columns:
        return df
    out = df.copy()
    if "train_select" not in out.columns:
        train_parts = [col for col in ["train_x0", "train_class", "train_param", "train_closed_loop"] if col in out.columns]
        if train_parts:
            out["train_select"] = out[train_parts].sum(axis=1)
    return out


def plot_history(name: str, path: Path, metrics: list[str]) -> dict[str, str | float | int]:
    df = add_select_column(pd.read_csv(path))
    available = [
        metric
        for metric in metrics
        if f"train_{metric}" in df.columns or f"val_{metric}" in df.columns
    ]
    if not available:
        raise ValueError(f"No requested metrics found in {path}")

    plt.figure(figsize=(14, max(4, 3.2 * len(available))))
    for idx, metric in enumerate(available, start=1):
        ax = plt.subplot(len(available), 1, idx)
        train_col = f"train_{metric}"
        val_col = f"val_{metric}"
        if train_col in df.columns:
            ax.plot(df["epoch"], df[train_col], label=train_col, linewidth=1.6)
        if val_col in df.columns:
            ax.plot(df["epoch"], df[val_col], label=val_col, linewidth=1.6)
            best_idx = df[val_col].idxmin() if "acc" not in metric else df[val_col].idxmax()
            ax.scatter(df.loc[best_idx, "epoch"], df.loc[best_idx, val_col], s=24, zorder=3)
        ax.set_title(f"{name} {metric}")
        ax.set_xlabel("Epoch")
        ax.set_ylabel(metric)
        ax.grid(True, alpha=0.35)
        ax.legend()
    plt.tight_layout()
    out_path = OUT_DIR / f"{name}_loss.png"
    plt.savefig(out_path, dpi=240)
    plt.close()

    primary = "val_select" if "val_select" in df.columns else "val_total"
    best_idx = df[primary].idxmin()
    return {
        "name": name,
        "history": str(path),
        "curve": str(out_path),
        "primary_metric": primary,
        "best_epoch": int(df.loc[best_idx, "epoch"]),
        "best_value": float(df.loc[best_idx, primary]),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = [plot_history(item["name"], item["history"], item["metrics"]) for item in PLOTS]
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT_DIR / "loss_curve_summary.csv", index=False)
    try:
        summary.to_excel(OUT_DIR / "loss_curve_summary.xlsx", index=False)
    except Exception as exc:  # pragma: no cover - optional Excel engine.
        print(f"[WARN] Could not write xlsx: {exc}")
    print(summary[["name", "primary_metric", "best_epoch", "best_value", "curve"]].to_string(index=False))
    print(f"[Saved] {OUT_DIR}")


if __name__ == "__main__":
    main()
