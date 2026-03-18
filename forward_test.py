import os
import re
import argparse
import pandas as pd
import numpy as np
import torch
import matplotlib.pyplot as plt
from sklearn.metrics import r2_score

from GNNtransformer_module import TPMSForwardTransformer


device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"[Test] Running on device: {device}")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEST_DATA_PATH = os.path.join(SCRIPT_DIR, "dataset used for training", "test.xlsx")
DEFAULT_TRANSFORMER_MODEL_DIR = os.path.join(SCRIPT_DIR, "forward_transformer_checkpoints")


def load_test_data(excel_path):
    print(f"Loading Test Data from: {excel_path}")
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Test file not found at: {excel_path}")

    columns = [
        "V1a", "V1v", "V1c", "w",
        "relativeVolume", "relativeArea", "thickness", "poreDiameter", "areaMean",
        "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10",
        "s11", "s12", "s13", "s14", "s15", "s16", "s17", "s18", "s19", "s20"
    ]
    input_cols = columns[:9]

    dfs = []
    try:
        for sheet in ['class1', 'class2', 'class12']:
            try:
                df = pd.read_excel(excel_path, sheet_name=sheet, names=columns)
                dfs.append(df)
            except ValueError:
                continue

        if not dfs:
            print("Warning: Specific sheets not found. Reading default sheet...")
            df = pd.read_excel(excel_path, names=columns)
            dfs.append(df)

    except Exception as e:
        print(f"Error reading Excel: {e}")
        return None, None, None

    df_all = pd.concat(dfs, axis=0).reset_index(drop=True)
    X_raw = df_all[input_cols].values.astype(np.float32)
    y_raw = df_all.iloc[:, 9:].values.astype(np.float32)
    return X_raw, y_raw, input_cols


def build_model_from_checkpoint(checkpoint):
    state_dict = checkpoint.get("model_state_dict", {})
    cfg = checkpoint.get("config", {}) or {}

    type_encoding = state_dict.get("type_encoding")
    out_weight = state_dict.get("mlp_head.4.weight")

    inferred_hidden_dim = int(type_encoding.shape[-1]) if type_encoding is not None else 128
    inferred_num_parameters = int(type_encoding.shape[1]) if type_encoding is not None else 9
    inferred_out_dim = int(out_weight.shape[0]) if out_weight is not None else 20

    inferred_num_layers = 3
    layer_indices = []
    for key in state_dict.keys():
        m = re.match(r"transformer\.layers\.(\d+)\.", key)
        if m:
            layer_indices.append(int(m.group(1)))
    if layer_indices:
        inferred_num_layers = max(layer_indices) + 1

    model_cfg = {
        "num_parameters": int(cfg.get("num_parameters", inferred_num_parameters)),
        "hidden_dim": int(cfg.get("hidden_dim", inferred_hidden_dim)),
        "num_heads": int(cfg.get("num_heads", 4)),
        "num_layers": int(cfg.get("num_layers", inferred_num_layers)),
        "out_dim": int(cfg.get("out_dim", inferred_out_dim)),
        "dropout": float(cfg.get("dropout", 0.0)),
    }

    model = TPMSForwardTransformer(**model_cfg).to(device)
    return model, model_cfg


def evaluate_pipeline(pipeline_idx, model_dir, test_data_path):
    model_path = os.path.join(model_dir, f'forward_transformer_{pipeline_idx}.pth')
    if not os.path.exists(model_path):
        print(f"[Skip] Pipeline {pipeline_idx} checkpoint not found at {model_path}")
        return None

    print(f"\n>>> Evaluating Pipeline {pipeline_idx}...")

    try:
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    except Exception as e:
        print(f"Error loading checkpoint: {e}")
        return None

    scaler_x = checkpoint['scaler_x']
    scaler_y = checkpoint['scaler_y']

    X_test_raw, y_test_raw, _ = load_test_data(test_data_path)
    if X_test_raw is None:
        return None

    X_test_scaled = scaler_x.transform(X_test_raw)
    X_tensor = torch.tensor(X_test_scaled, dtype=torch.float32).to(device)

    model, model_cfg = build_model_from_checkpoint(checkpoint)
    print(f"Using model config: {model_cfg}")

    try:
        model.load_state_dict(checkpoint['model_state_dict'])
    except RuntimeError as e:
        print(f"Model architecture mismatch! Error: {e}")
        return None

    model.eval()

    batch_size = 512
    num_samples = len(X_test_raw)
    y_pred_all = []

    with torch.no_grad():
        for i in range(0, num_samples, batch_size):
            batch_x = X_tensor[i:i + batch_size]
            outputs = model(batch_x)
            y_pred_all.append(outputs.cpu().numpy())

    y_pred_scaled = np.concatenate(y_pred_all, axis=0)
    y_pred_raw = scaler_y.inverse_transform(y_pred_scaled)

    mse = np.mean((y_test_raw - y_pred_raw) ** 2)
    mae = np.mean(np.abs(y_test_raw - y_pred_raw))
    r2 = r2_score(y_test_raw, y_pred_raw)

    data_range = np.max(y_test_raw) - np.min(y_test_raw)
    rmse = np.sqrt(mse)
    nrmse = (rmse / data_range) * 100 if data_range != 0 else 0.0

    print(f"Pipeline {pipeline_idx} Evaluation Results:")
    print(f"  MSE  : {mse:.4f}")
    print(f"  MAE  : {mae:.4f}")
    print(f"  R2   : {r2:.4f}")
    print(f"  NRMSE: {nrmse:.2f}%")

    return {
        'pipeline': pipeline_idx,
        'y_true': y_test_raw,
        'y_pred': y_pred_raw,
        'nrmse': nrmse,
        'mae': mae,
        'r2': r2,
    }


def main(args):
    best_nrmse = float('inf')
    best_result = None

    print(f"Target Test File: {args.test_data_path}")
    print(f"Model Directory: {args.model_dir}")

    all_results = []
    for i in range(6):
        res = evaluate_pipeline(i, args.model_dir, args.test_data_path)
        if res:
            all_results.append(res)
            if res['nrmse'] < best_nrmse:
                best_nrmse = res['nrmse']
                best_result = res

    if not all_results:
        print("Error: No valid models found or evaluated.")
        return

    print("\n" + "=" * 60)
    print("Summary (all valid pipelines):")
    for r in all_results:
        print(f"  Pipeline {r['pipeline']}: NRMSE={r['nrmse']:.2f}% | MAE={r['mae']:.4f} | R2={r['r2']:.4f}")

    print("\n" + "=" * 60)
    print(f"Best Performing Model: Pipeline {best_result['pipeline']}")
    print(f"Final Test NRMSE: {best_result['nrmse']:.2f}%")
    print(f"Final Test MAE  : {best_result['mae']:.4f}")
    print(f"Final Test R2   : {best_result['r2']:.4f}")
    print("=" * 60)

    y_true = best_result['y_true']
    y_pred = best_result['y_pred']

    indices = np.random.choice(len(y_true), 4, replace=False)

    plt.figure(figsize=(12, 10))
    for idx, sample_idx in enumerate(indices):
        plt.subplot(2, 2, idx + 1)

        true_curve = np.concatenate(([0], y_true[sample_idx]))
        pred_curve = np.concatenate(([0], y_pred[sample_idx]))
        x_axis = np.linspace(0, 25, 21)

        plt.plot(x_axis, true_curve, 'k-', linewidth=2, label='Ground Truth (FEA)')
        plt.plot(x_axis, pred_curve, 'r--', linewidth=2, marker='o', markersize=4, label='Prediction (Transformer)')

        plt.title(f'Test Sample {sample_idx}')
        plt.xlabel('Strain (%)')
        plt.ylabel('Stress (kPa)')
        plt.legend()
        plt.grid(True, linestyle=':', alpha=0.6)

    plt.tight_layout()
    save_path = os.path.join(args.model_dir, 'test_result_visualization_transformer.png')
    plt.savefig(save_path, dpi=300)
    print(f"Visualization plot saved to: {save_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--test_data_path', type=str, default=DEFAULT_TEST_DATA_PATH,
                        help='Path to the test excel file')
    parser.add_argument('--model_dir', type=str, default=DEFAULT_TRANSFORMER_MODEL_DIR,
                        help='Directory containing trained .pth models')
    args = parser.parse_args()

    main(args)
