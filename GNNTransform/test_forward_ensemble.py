import argparse
import os
import shutil
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import r2_score

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
GAT_DIR = REPO_ROOT / "GAT"
if str(GAT_DIR) not in sys.path:
    sys.path.insert(0, str(GAT_DIR))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from GAT_module import GNNForwardNetwork
from GNNtransformer_module import TPMSForwardTransformer


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[Test] Running on device: {DEVICE}")
DEFAULT_TEST_DATA_PATH = str(REPO_ROOT / "dataset used for training" / "test.xlsx")
DEFAULT_GAT_CHECKPOINT = str(REPO_ROOT / "GAT" / "forward_gnn_checkpoints" / "forward_gnn_0.pth")
DEFAULT_TRANSFORMER_CHECKPOINT = ""
DEFAULT_TRANSFORMER_CHECKPOINT_DIR = str(SCRIPT_DIR / "forward_transformer_checkpoints")
DEFAULT_TRANSFORMER_ENSEMBLE_INDICES = "0,1,2,3,4"
DEFAULT_SAVE_DIR = str(SCRIPT_DIR / "forward_test_results")


def load_test_data(excel_path):
    print(f"Loading test data from: {excel_path}")
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Test file not found: {excel_path}")

    columns = [
        "V1a", "V1v", "V1c", "w",
        "relativeVolume", "relativeArea", "thickness", "poreDiameter", "areaMean",
        "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10",
        "s11", "s12", "s13", "s14", "s15", "s16", "s17", "s18", "s19", "s20",
    ]

    frames = []
    frame_names = []
    for sheet_name in ("class1", "class2", "class12"):
        try:
            frames.append(pd.read_excel(excel_path, sheet_name=sheet_name, names=columns))
            frame_names.append(sheet_name)
        except ValueError:
            continue

    if not frames:
        frames.append(pd.read_excel(excel_path, names=columns))
        frame_names.append("all")

    df_all = pd.concat(frames, axis=0).reset_index(drop=True)
    x_raw = df_all.iloc[:, :9].values.astype(np.float32)
    y_raw = df_all.iloc[:, 9:].values.astype(np.float32)
    class_slices = []
    start = 0
    for name, frame in zip(frame_names, frames):
        end = start + len(frame)
        class_slices.append((name, start, end))
        start = end

    print(f"Loaded {len(df_all)} samples. X={x_raw.shape}, y={y_raw.shape}")
    for name, start, end in class_slices:
        print(f"  - {name}: {end - start} samples [{start}, {end})")
    return x_raw, y_raw, class_slices


def calculate_metrics(y_true, y_pred):
    mse = float(np.mean((y_true - y_pred) ** 2))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    data_range = max(float(np.max(y_true) - np.min(y_true)), 1e-12)
    nrmse_pct = float(np.sqrt(mse) / data_range * 100.0)
    return {
        "mse": mse,
        "mae": mae,
        "r2": r2,
        "nrmse_pct": nrmse_pct,
    }


def parse_index_list(raw_indices):
    if raw_indices is None:
        return []
    tokens = [token.strip() for token in str(raw_indices).split(",")]
    result = []
    for token in tokens:
        if not token:
            continue
        result.append(int(token))
    return result


def resolve_transformer_checkpoints(args):
    if args.transformer_checkpoint:
        if not os.path.exists(args.transformer_checkpoint):
            raise FileNotFoundError(
                f"Transformer checkpoint not found: {args.transformer_checkpoint}"
            )
        return [args.transformer_checkpoint]

    if args.transformer_ensemble_size > 0:
        target_indices = list(range(args.transformer_ensemble_size))
    else:
        target_indices = parse_index_list(args.transformer_ensemble_indices)
        if not target_indices:
            target_indices = [0]

    checkpoint_paths = []
    for idx in target_indices:
        path = os.path.join(
            args.transformer_checkpoint_dir,
            f"forward_transformer_{idx}.pth",
        )
        if os.path.exists(path):
            checkpoint_paths.append(path)
        else:
            print(f"[Warn] Transformer checkpoint missing, skipped: {path}")

    if not checkpoint_paths:
        raise FileNotFoundError(
            "No valid transformer checkpoints found for ensemble."
        )
    return checkpoint_paths


def predict_with_gat(checkpoint_path, x_raw, batch_size):
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"GAT checkpoint not found: {checkpoint_path}")

    checkpoint = torch.load(checkpoint_path, map_location=DEVICE, weights_only=False)
    scaler_x = checkpoint["scaler_x"]
    scaler_y = checkpoint["scaler_y"]

    x_scaled = scaler_x.transform(x_raw).astype(np.float32)
    x_tensor = torch.tensor(x_scaled, dtype=torch.float32, device=DEVICE)

    model = GNNForwardNetwork(
        units_layer1=512,
        units_layer2=256,
        units_layer3=128,
        units_layer4=64,
        gnn_hidden_dim=256,
        gnn_heads=8,
        dropout_rate=0.0,
    ).to(DEVICE)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    adj = torch.ones((9, 9), dtype=torch.float32, device=DEVICE)
    outputs = []
    with torch.no_grad():
        for start in range(0, len(x_tensor), batch_size):
            batch_x = x_tensor[start:start + batch_size]
            batch_adj = adj.unsqueeze(0).repeat(batch_x.size(0), 1, 1)
            outputs.append(model(batch_x, batch_adj).detach().cpu().numpy())
    y_scaled = np.concatenate(outputs, axis=0)
    return scaler_y.inverse_transform(y_scaled)


def predict_with_transformer_single(checkpoint_path, x_raw, batch_size):
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Transformer checkpoint not found: {checkpoint_path}")

    checkpoint = torch.load(checkpoint_path, map_location=DEVICE, weights_only=False)
    scaler_x = checkpoint["scaler_x"]
    scaler_y = checkpoint["scaler_y"]
    config = checkpoint.get("config", {})

    x_scaled = scaler_x.transform(x_raw).astype(np.float32)
    x_tensor = torch.tensor(x_scaled, dtype=torch.float32, device=DEVICE)

    model = TPMSForwardTransformer(
        num_parameters=9,
        hidden_dim=config.get("hidden_dim", 256),
        num_heads=config.get("num_heads", 8),
        num_layers=config.get("num_layers", 4),
        out_dim=20,
        dropout=config.get("dropout", 0.10),
    ).to(DEVICE)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    outputs = []
    with torch.no_grad():
        for start in range(0, len(x_tensor), batch_size):
            batch_x = x_tensor[start:start + batch_size]
            outputs.append(model(batch_x).detach().cpu().numpy())
    y_scaled = np.concatenate(outputs, axis=0)
    return scaler_y.inverse_transform(y_scaled)


def predict_with_transformer_ensemble(checkpoint_paths, x_raw, batch_size):
    raw_predictions = []
    for checkpoint_path in checkpoint_paths:
        raw_predictions.append(
            predict_with_transformer_single(checkpoint_path, x_raw, batch_size)
        )
    return np.mean(np.stack(raw_predictions, axis=0), axis=0)


def _safe_middle_index(sorted_indices):
    return sorted_indices[len(sorted_indices) // 2]


def build_stratified_plot_items(
    y_true,
    y_gat,
    y_transformer,
    class_slices,
    random_seed,
    fixed_samples_per_class,
):
    mse_gat = np.mean((y_true - y_gat) ** 2, axis=1)
    mse_tr = np.mean((y_true - y_transformer) ** 2, axis=1)
    delta = mse_gat - mse_tr  # > 0: Transformer better; < 0: GAT better

    grouped_items = []
    for class_order, (class_name, start, end) in enumerate(class_slices):
        class_indices = np.arange(start, end, dtype=int)
        if class_indices.size == 0:
            continue

        rng = np.random.default_rng(random_seed + class_order)
        num_fixed = min(fixed_samples_per_class, class_indices.size)
        fixed_selected = rng.choice(class_indices, size=num_fixed, replace=False)

        class_delta = delta[class_indices]
        sort_local = np.argsort(class_delta)
        best_idx = int(class_indices[int(sort_local[-1])])
        worst_idx = int(class_indices[int(sort_local[0])])
        median_idx = int(class_indices[int(_safe_middle_index(sort_local))])

        selected = []
        selected_set = set()

        for rank, idx in enumerate(fixed_selected, start=1):
            idx = int(idx)
            if idx not in selected_set:
                selected.append((idx, f"fixed-{rank}"))
                selected_set.add(idx)

        for idx, tag in (
            (best_idx, "best-tr"),
            (worst_idx, "worst-tr"),
            (median_idx, "median"),
        ):
            if idx not in selected_set:
                selected.append((idx, tag))
                selected_set.add(idx)

        grouped_items.append(
            {
                "class_name": class_name,
                "start": start,
                "end": end,
                "items": selected,
            }
        )
    return grouped_items


def plot_comparison_stratified(
    y_true,
    y_gat,
    y_transformer,
    class_slices,
    save_path,
    random_seed,
    fixed_samples_per_class,
):
    grouped_items = build_stratified_plot_items(
        y_true=y_true,
        y_gat=y_gat,
        y_transformer=y_transformer,
        class_slices=class_slices,
        random_seed=random_seed,
        fixed_samples_per_class=fixed_samples_per_class,
    )
    if not grouped_items:
        raise ValueError("No class items to plot.")

    rows = len(grouped_items)
    cols = max(len(group["items"]) for group in grouped_items)
    fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 3.8 * rows))
    axes = np.array(axes).reshape(rows, cols)
    x_axis = np.arange(1, y_true.shape[1] + 1)

    for row_idx, group in enumerate(grouped_items):
        class_name = group["class_name"]
        items = group["items"]
        for col_idx in range(cols):
            ax = axes[row_idx, col_idx]
            if col_idx >= len(items):
                ax.axis("off")
                continue

            sample_idx, tag = items[col_idx]
            target = y_true[sample_idx]
            pred_gat = y_gat[sample_idx]
            pred_tr = y_transformer[sample_idx]

            mse_gat = float(np.mean((target - pred_gat) ** 2))
            mse_tr = float(np.mean((target - pred_tr) ** 2))
            diff = mse_gat - mse_tr

            ax.plot(x_axis, target, "k-", linewidth=2.0, label="Target")
            ax.plot(x_axis, pred_gat, "r--", linewidth=1.7, label="GAT")
            ax.plot(x_axis, pred_tr, "b-.", linewidth=1.7, label="Transformer")
            ax.set_title(
                f"{class_name} | {tag} | id={sample_idx}\n"
                f"MSE GAT={mse_gat:.3f}, TR={mse_tr:.3f}, dMSE={diff:.3f}"
            )
            ax.set_xlabel("Point")
            ax.set_ylabel("Stress")
            ax.grid(True, linestyle=":", alpha=0.6)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(save_path, dpi=300)
    plt.close(fig)


def main(args):
    os.makedirs(args.save_dir, exist_ok=True)

    x_raw, y_true, class_slices = load_test_data(args.test_data_path)
    y_pred_gat = predict_with_gat(args.gat_checkpoint, x_raw, args.batch_size)
    transformer_ckpts = resolve_transformer_checkpoints(args)
    print(f"[Ensemble] Using {len(transformer_ckpts)} transformer checkpoints:")
    for ckpt in transformer_ckpts:
        print(f"  - {ckpt}")
    y_pred_transformer = predict_with_transformer_ensemble(
        transformer_ckpts, x_raw, args.batch_size
    )

    gat_metrics = calculate_metrics(y_true, y_pred_gat)
    tr_metrics = calculate_metrics(y_true, y_pred_transformer)
    transformer_model_name = f"transformer_ens_{len(transformer_ckpts)}"

    summary_df = pd.DataFrame(
        [
            {"model": "gat", **gat_metrics},
            {"model": transformer_model_name, **tr_metrics},
        ]
    )
    summary_csv = os.path.join(args.save_dir, "forward_test_metrics.csv")
    summary_df.to_csv(summary_csv, index=False)

    figure_path = os.path.join(args.save_dir, "forward_test_comparison_stratified.png")
    plot_comparison_stratified(
        y_true=y_true,
        y_gat=y_pred_gat,
        y_transformer=y_pred_transformer,
        class_slices=class_slices,
        save_path=figure_path,
        random_seed=args.random_seed,
        fixed_samples_per_class=args.fixed_samples_per_class,
    )
    legacy_figure_path = os.path.join(args.save_dir, "forward_test_comparison.png")
    if figure_path != legacy_figure_path:
        shutil.copyfile(figure_path, legacy_figure_path)

    print("\n==================== Forward Test Summary ====================")
    print(summary_df.to_string(index=False))
    print(f"[Saved] Metrics: {summary_csv}")
    print(f"[Saved] Figure:  {figure_path}")
    print(f"[Saved] Figure:  {legacy_figure_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test_data_path", type=str, default=DEFAULT_TEST_DATA_PATH)
    parser.add_argument("--gat_checkpoint", type=str, default=DEFAULT_GAT_CHECKPOINT)
    parser.add_argument("--transformer_checkpoint", type=str, default=DEFAULT_TRANSFORMER_CHECKPOINT)
    parser.add_argument("--transformer_checkpoint_dir", type=str, default=DEFAULT_TRANSFORMER_CHECKPOINT_DIR)
    parser.add_argument("--transformer_ensemble_indices", type=str, default=DEFAULT_TRANSFORMER_ENSEMBLE_INDICES)
    parser.add_argument("--transformer_ensemble_size", type=int, default=0)
    parser.add_argument("--save_dir", type=str, default=DEFAULT_SAVE_DIR)
    parser.add_argument("--batch_size", type=int, default=1024)
    parser.add_argument("--random_seed", type=int, default=42)
    parser.add_argument("--fixed_samples_per_class", type=int, default=2)
    cli_args = parser.parse_args()
    main(cli_args)



