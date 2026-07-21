"""Summarize and plot diffusion tuning histories."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


EXPERIMENT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = EXPERIMENT_ROOT

RUNS = [
    (
        "epsilon_round3_best",
        SCRIPT_DIR
        / "diffusion_grid_round3"
        / "results_h512_lr3e4_x0p4_loop0p5_temp0p12"
        / "inverse_diffusion_history.csv",
    ),
    ("split_base", SCRIPT_DIR / "split_diff_round1" / "results" / "inverse_cont_diffusion_history.csv"),
    (
        "split_teacher",
        SCRIPT_DIR / "split_diff_teacher_round2" / "results" / "inverse_cont_diffusion_history.csv",
    ),
    ("mixed_x0_round1", SCRIPT_DIR / "diffusion_x0_round1" / "results" / "inverse_diffusion_history.csv"),
    ("mixed_x0_round2", SCRIPT_DIR / "diffusion_x0_round2" / "results" / "inverse_diffusion_history.csv"),
    ("mixed_x0_round3", SCRIPT_DIR / "diffusion_x0_round3" / "results" / "inverse_diffusion_history.csv"),
]


def main() -> None:
    out_dir = SCRIPT_DIR / "diffusion_x0_round1" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = []
    frames = {}
    for name, path in RUNS:
        df = pd.read_csv(path)
        frames[name] = df
        row = df.loc[df["val_select"].idxmin()]
        summary.append(
            {
                "run": name,
                "best_epoch": int(row["epoch"]),
                "best_val_select": float(row["val_select"]),
                "val_total": float(row["val_total"]),
                "val_noise": float(row["val_noise"]),
                "val_x0": float(row["val_x0"]),
                "val_class": float(row.get("val_class", 0.0)),
                "val_param": float(row["val_param"]),
                "val_closed_loop": float(row["val_closed_loop"]),
            }
        )

    summary_df = pd.DataFrame(summary).sort_values("best_val_select")
    summary_df.to_csv(out_dir / "diffusion_iteration_summary.csv", index=False)
    try:
        summary_df.to_excel(out_dir / "diffusion_iteration_summary.xlsx", index=False)
    except Exception as exc:  # pragma: no cover - optional Excel engine.
        print(f"[WARN] Could not write xlsx: {exc}")

    metrics = ["val_select", "val_x0", "val_param", "val_closed_loop"]
    plt.figure(figsize=(14, 11))
    for idx, metric in enumerate(metrics, start=1):
        ax = plt.subplot(2, 2, idx)
        for name, df in frames.items():
            ax.plot(df["epoch"], df[metric], label=name, linewidth=1.6)
        ax.set_title(metric)
        ax.set_xlabel("Epoch")
        ax.set_ylabel(metric)
        ax.grid(True, alpha=0.35)
        if idx == 1:
            ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(out_dir / "diffusion_iteration_loss_compare.png", dpi=240)
    plt.close()

    print(summary_df.to_string(index=False))
    print(f"[Saved] {out_dir / 'diffusion_iteration_summary.csv'}")
    print(f"[Saved] {out_dir / 'diffusion_iteration_loss_compare.png'}")


if __name__ == "__main__":
    main()
