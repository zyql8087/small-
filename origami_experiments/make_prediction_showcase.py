"""Create presentation-ready plots for strong test-set predictions."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

from evaluate_all_final_models import (
    DEVICE,
    eval_inverse_diffusion,
    instantiate_forward_resmlp,
    instantiate_forward_transformer,
    instantiate_inverse_diffusion,
    inverse_x_transform,
    load_portable,
    load_test_raw,
    predict_forward,
)
from train_taskfit import CAT_VALUES, INPUT_COLS, OUTPUT_COLS, load_train_val


SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR / "results_final_model_test" / "prediction_showcase"
MODEL_DIR = SCRIPT_DIR / "best_models_taskfit"


def load_model(name: str, factory):
    ckpt = load_portable(name)
    model = factory(ckpt.get("config", {}), ckpt.get("diffusion_config", {}))
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    return model, ckpt


def relative_error_percent(true: np.ndarray, pred: np.ndarray) -> np.ndarray:
    return np.abs(pred - true) / np.maximum(np.abs(true), 1e-12) * 100.0


def design_summary(x: np.ndarray) -> str:
    parts = []
    for idx, col in enumerate(INPUT_COLS):
        if col in ("pattern", "m", "n"):
            parts.append(f"{col}={x[idx]:.0f}")
        elif col in ("creaseE", "panelE"):
            parts.append(f"{col}={x[idx]:.2e}")
        else:
            parts.append(f"{col}={x[idx]:.4g}")
    return " | ".join(parts)


def plot_stiffness_case(
    case_id: int,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    title: str,
    subtitle: str,
    out_path: Path,
) -> None:
    x = np.arange(len(OUTPUT_COLS))
    rel = relative_error_percent(y_true, y_pred)
    overall = float(np.mean(rel))

    plt.figure(figsize=(12, 6.8))
    ax1 = plt.subplot(2, 1, 1)
    ax1.plot(x, y_true, marker="o", linewidth=2.2, label="True stiffness")
    ax1.plot(x, y_pred, marker="s", linewidth=2.2, label="Predicted stiffness")
    ax1.set_xticks(x)
    ax1.set_xticklabels(OUTPUT_COLS, rotation=18, ha="right")
    ax1.set_ylabel("Stiffness")
    ax1.set_title(f"{title} | sample #{case_id} | mean rel. error {overall:.2f}%")
    ax1.text(0.0, 0.98, subtitle, transform=ax1.transAxes, va="top", ha="left", fontsize=9)
    ax1.grid(True, alpha=0.35)
    ax1.legend()

    ax2 = plt.subplot(2, 1, 2)
    bars = ax2.bar(x, rel, color="#5DA5DA")
    ax2.set_xticks(x)
    ax2.set_xticklabels(OUTPUT_COLS, rotation=18, ha="right")
    ax2.set_ylabel("Relative error (%)")
    ax2.set_title("Per-stiffness relative error")
    ax2.grid(axis="y", alpha=0.35)
    for bar, value in zip(bars, rel):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.2f}%", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    plt.savefig(out_path, dpi=260)
    plt.close()


def plot_inverse_design_case(
    case_id: int,
    y_true: np.ndarray,
    y_loop: np.ndarray,
    x_true: np.ndarray,
    x_pred: np.ndarray,
    out_path: Path,
) -> None:
    x = np.arange(len(OUTPUT_COLS))
    rel = relative_error_percent(y_true, y_loop)
    overall = float(np.mean(rel))
    param_df = pd.DataFrame(
        {
            "Parameter": INPUT_COLS,
            "True": x_true,
            "Predicted": x_pred,
        }
    )

    fig = plt.figure(figsize=(13, 8))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1.0])
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(x, y_true, marker="o", linewidth=2.2, label="Target stiffness")
    ax1.plot(x, y_loop, marker="s", linewidth=2.2, label="Closed-loop stiffness")
    ax1.set_xticks(x)
    ax1.set_xticklabels(OUTPUT_COLS, rotation=18, ha="right")
    ax1.set_ylabel("Stiffness")
    ax1.set_title(f"Inverse Diffusion x0 | sample #{case_id} | closed-loop mean rel. error {overall:.2f}%")
    ax1.grid(True, alpha=0.35)
    ax1.legend()

    ax2 = fig.add_subplot(gs[1, 0])
    bars = ax2.bar(x, rel, color="#60BD68")
    ax2.set_xticks(x)
    ax2.set_xticklabels(OUTPUT_COLS, rotation=18, ha="right")
    ax2.set_ylabel("Relative error (%)")
    ax2.set_title("Closed-loop relative error")
    ax2.grid(axis="y", alpha=0.35)
    for bar, value in zip(bars, rel):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.2f}%", ha="center", va="bottom", fontsize=8)

    ax3 = fig.add_subplot(gs[1, 1])
    ax3.axis("off")
    table = ax3.table(
        cellText=[
            [
                param,
                f"{true_val:.4g}" if param not in ("pattern", "m", "n") else f"{true_val:.0f}",
                f"{pred_val:.4g}" if param not in ("pattern", "m", "n") else f"{pred_val:.0f}",
            ]
            for param, true_val, pred_val in param_df.itertuples(index=False, name=None)
        ],
        colLabels=["Parameter", "True", "Predicted"],
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1.0, 1.3)
    ax3.set_title("Design parameters")

    plt.tight_layout()
    plt.savefig(out_path, dpi=260)
    plt.close()


def main() -> None:
    np.random.seed(42)
    torch.manual_seed(42)
    if DEVICE.type == "cuda":
        torch.cuda.manual_seed_all(42)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    _, _, prep = load_train_val(str(SCRIPT_DIR / "data" / "origami_train.npz"))
    x_test, y_test = load_test_raw(SCRIPT_DIR / "data" / "origami_test.npz")

    forward_resmlp, _ = load_model("forward_resmlp", lambda config, _dc: instantiate_forward_resmlp(config))
    forward_transformer, _ = load_model("forward_transformer", lambda config, _dc: instantiate_forward_transformer(config))
    inverse_diffusion, diffusion_ckpt = load_model("inverse_diffusion_x0", instantiate_inverse_diffusion)

    y_resmlp = predict_forward(forward_resmlp, prep, x_test, "resmlp")
    y_transformer = predict_forward(forward_transformer, prep, x_test, "transformer")
    x_inv = eval_inverse_diffusion(inverse_diffusion, diffusion_ckpt, prep, forward_transformer, y_test, samples=50)
    y_inv_loop = predict_forward(forward_transformer, prep, x_inv, "transformer")

    resmlp_err = relative_error_percent(y_test, y_resmlp).mean(axis=1)
    transformer_err = relative_error_percent(y_test, y_transformer).mean(axis=1)
    inverse_err = relative_error_percent(y_test, y_inv_loop).mean(axis=1)

    rows = []
    for rank, idx in enumerate(np.argsort(resmlp_err)[:3], start=1):
        out = OUT_DIR / f"forward_resmlp_good_case_{rank}_sample_{idx}.png"
        plot_stiffness_case(
            int(idx),
            y_test[idx],
            y_resmlp[idx],
            "Forward ResMLP prediction",
            design_summary(x_test[idx]),
            out,
        )
        rows.append({"Figure": str(out), "Task": "forward_resmlp", "Sample": int(idx), "MeanRelError%": float(resmlp_err[idx])})

    for rank, idx in enumerate(np.argsort(transformer_err)[:3], start=1):
        out = OUT_DIR / f"forward_transformer_good_case_{rank}_sample_{idx}.png"
        plot_stiffness_case(
            int(idx),
            y_test[idx],
            y_transformer[idx],
            "Forward Transformer prediction",
            design_summary(x_test[idx]),
            out,
        )
        rows.append({"Figure": str(out), "Task": "forward_transformer", "Sample": int(idx), "MeanRelError%": float(transformer_err[idx])})

    for rank, idx in enumerate(np.argsort(inverse_err)[:4], start=1):
        out = OUT_DIR / f"inverse_diffusion_good_case_{rank}_sample_{idx}.png"
        plot_inverse_design_case(
            int(idx),
            y_test[idx],
            y_inv_loop[idx],
            x_test[idx],
            x_inv[idx],
            out,
        )
        rows.append({"Figure": str(out), "Task": "inverse_diffusion_x0", "Sample": int(idx), "MeanRelError%": float(inverse_err[idx])})

    summary = pd.DataFrame(rows).sort_values(["Task", "MeanRelError%"])
    summary.to_csv(OUT_DIR / "prediction_showcase_summary.csv", index=False)
    try:
        summary.to_excel(OUT_DIR / "prediction_showcase_summary.xlsx", index=False)
    except Exception as exc:
        print(f"[WARN] Could not write xlsx: {exc}")
    print(summary.to_string(index=False))
    print(f"[Saved] {OUT_DIR}")


if __name__ == "__main__":
    main()
