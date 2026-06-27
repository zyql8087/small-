"""Evaluate all 5 trained models on origami test set and produce summary metrics."""

import os
import sys
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.metrics import r2_score

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from modules.origami_forward_gnn import OrigamiGNNForward
from modules.origami_forward_transformer import OrigamiForwardTransformer
from modules.origami_inverse_resnet import OrigamiResNet1DInverse
from modules.origami_inverse_cvae import OrigamiCVAE
from modules.origami_inverse_diffusion import OrigamiConditionalDenoisingMLP

INPUT_COLS = ["pattern", "m", "n", "tcrease", "tpanel", "W", "creaseE", "panelE"]
OUTPUT_COLS = ["bendstiff30", "bendstiff60", "bendstiff90", "axialstiff30", "axialstiff60", "axialstiff90"]
NUM_INPUTS = len(INPUT_COLS)
NUM_OUTPUTS = len(OUTPUT_COLS)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[Device] {DEVICE}")


def load_test_data(npz_path):
    data = np.load(npz_path)
    X_raw = data["X_raw"].astype(np.float32)
    y_raw = data["y_raw"].astype(np.float32)
    pattern = X_raw[:, 0]
    return X_raw, y_raw, pattern


def load_and_inverse_transform(ckpt_path, scaler_x_key, scaler_y_key):
    ckpt = torch.load(ckpt_path, map_location=DEVICE, weights_only=False)
    return ckpt[scaler_x_key], ckpt[scaler_y_key]


def metrics(target, pred):
    target, pred = np.asarray(target, dtype=np.float64), np.asarray(pred, dtype=np.float64)
    mae = float(np.mean(np.abs(target - pred)))
    rmse = float(np.sqrt(np.mean((target - pred) ** 2)))
    r2 = float(r2_score(target.reshape(-1), pred.reshape(-1)))
    value_range = max(float(np.max(target) - np.min(target)), 1e-12)
    nrmse_pct = float(rmse / value_range * 100.0)
    return {"MAE": mae, "RMSE": rmse, "R2": r2, "NRMSE%": nrmse_pct}


# ---- Forward Models ----

def eval_forward_gnn(X_raw, y_raw, pattern):
    path = os.path.join(SCRIPT_DIR, "checkpoints", "forward_gnn", "forward_gnn_0.pth")
    ckpt = torch.load(path, map_location=DEVICE, weights_only=False)
    scaler_x, scaler_y = ckpt["scaler_x"], ckpt["scaler_y"]
    adj = torch.ones((NUM_INPUTS, NUM_INPUTS), dtype=torch.float32, device=DEVICE)

    model = OrigamiGNNForward(
        num_inputs=NUM_INPUTS, num_outputs=NUM_OUTPUTS,
        gnn_hidden_dim=256, gnn_heads=8,
        units_layer1=512, units_layer2=256, units_layer3=128, units_layer4=64,
        dropout_rate=0.0,
    ).to(DEVICE)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    X_scaled = scaler_x.transform(X_raw)
    X_t = torch.tensor(X_scaled, dtype=torch.float32, device=DEVICE)
    with torch.no_grad():
        out = model(X_t, adj.unsqueeze(0).repeat(X_t.size(0), 1, 1))
    y_pred_scaled = out.cpu().numpy()
    y_pred = scaler_y.inverse_transform(y_pred_scaled)

    return compute_all_metrics(y_raw, y_pred, pattern, "Forward GNN")


def eval_forward_transformer(X_raw, y_raw, pattern):
    path = os.path.join(SCRIPT_DIR, "checkpoints", "forward_transformer", "forward_transformer_0.pth")
    ckpt = torch.load(path, map_location=DEVICE, weights_only=False)
    scaler_x, scaler_y = ckpt["scaler_x"], ckpt["scaler_y"]
    cfg = ckpt.get("config", {})

    model = OrigamiForwardTransformer(
        num_parameters=NUM_INPUTS,
        hidden_dim=cfg.get("hidden_dim", 256),
        num_heads=cfg.get("num_heads", 8),
        num_layers=cfg.get("num_layers", 4),
        out_dim=NUM_OUTPUTS,
        dropout=0.0,
    ).to(DEVICE)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    X_scaled = scaler_x.transform(X_raw)
    X_t = torch.tensor(X_scaled, dtype=torch.float32, device=DEVICE)
    with torch.no_grad():
        out = model(X_t)
    y_pred_scaled = out.cpu().numpy()
    y_pred = scaler_y.inverse_transform(y_pred_scaled)

    return compute_all_metrics(y_raw, y_pred, pattern, "Forward Transformer")


# ---- Inverse Models ----

def eval_inverse_resnet(X_raw, y_raw, pattern):
    path = os.path.join(SCRIPT_DIR, "checkpoints", "inverse_resnet", "inverse_resnet_0.pth")
    ckpt = torch.load(path, map_location=DEVICE, weights_only=False)
    scaler_x, scaler_y = ckpt["scaler_x"], ckpt["scaler_y"]

    model = OrigamiResNet1DInverse(dropout_rate=0.0, num_outputs=NUM_INPUTS).to(DEVICE)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    curve_scaled = scaler_x.transform(y_raw)
    curve_t = torch.tensor(curve_scaled, dtype=torch.float32, device=DEVICE)
    with torch.no_grad():
        out = model(curve_t)
    param_pred_scaled = out.cpu().numpy()
    param_pred = scaler_y.inverse_transform(param_pred_scaled)

    return compute_all_metrics(X_raw, param_pred, pattern, "Inverse ResNet")


def eval_inverse_cvae(X_raw, y_raw, pattern):
    path = os.path.join(SCRIPT_DIR, "checkpoints", "inverse_cvae", "cvae_0.pth")
    ckpt = torch.load(path, map_location=DEVICE, weights_only=False)
    scaler_curve, scaler_param = ckpt["scaler_curve"], ckpt["scaler_param"]

    model = OrigamiCVAE(param_dim=NUM_INPUTS, curve_points=NUM_OUTPUTS, latent_dim=4, hidden_dim=512).to(DEVICE)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    curve_scaled = scaler_curve.transform(y_raw)
    curve_t = torch.tensor(curve_scaled, dtype=torch.float32, device=DEVICE)

    with torch.no_grad():
        preds = []
        for _ in range(50):
            z = torch.randn(curve_t.size(0), 4, device=DEVICE)
            param_scaled = model.inference(curve_t, z=z)
            preds.append(scaler_param.inverse_transform(param_scaled.cpu().numpy()))
    param_pred = np.mean(np.stack(preds, axis=0), axis=0)

    return compute_all_metrics(X_raw, param_pred, pattern, "Inverse CVAE")


def eval_inverse_diffusion(X_raw, y_raw, pattern):
    path = os.path.join(SCRIPT_DIR, "checkpoints", "inverse_diffusion", "inverse_diffusion_0.pth")
    ckpt = torch.load(path, map_location=DEVICE, weights_only=False)
    scaler_curve, scaler_param = ckpt["scaler_curve"], ckpt["scaler_param"]
    diff_cfg = ckpt["diffusion_config"]

    model = OrigamiConditionalDenoisingMLP(
        param_dim=NUM_INPUTS, curve_dim=NUM_OUTPUTS,
        time_emb_dim=64, cond_emb_dim=128, hidden_dim=512,
    ).to(DEVICE)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    # Build schedule
    betas = torch.linspace(diff_cfg["beta_start"], diff_cfg["beta_end"], diff_cfg["timesteps"],
                           dtype=torch.float32, device=DEVICE)
    alphas = 1.0 - betas
    alpha_cumprod = torch.cumprod(alphas, dim=0)
    sqrt_ac = torch.sqrt(alpha_cumprod)
    sqrt_1m_ac = torch.sqrt(1.0 - alpha_cumprod)

    curve_scaled = scaler_curve.transform(y_raw)
    curve_t = torch.tensor(curve_scaled, dtype=torch.float32, device=DEVICE)

    # DDIM sampling with 50 steps
    inference_steps = 50
    step_ids = np.linspace(diff_cfg["timesteps"] - 1, 0, inference_steps, dtype=np.int64)
    step_ids = sorted(set(step_ids.tolist()), reverse=True)
    if step_ids[-1] != 0:
        step_ids.append(0)

    with torch.no_grad():
        preds = []
        for _ in range(10):
            x_t = torch.randn(curve_t.size(0), NUM_INPUTS, device=DEVICE, dtype=torch.float32)
            for i, t_val in enumerate(step_ids):
                t_batch = torch.full((x_t.size(0),), t_val, device=DEVICE, dtype=torch.long)
                eps_pred = model(x_t, t_batch.float(), curve_t).float()
                ac_t = alpha_cumprod[t_val].view(-1, 1)
                sqrt_1m_ac_t = sqrt_1m_ac[t_val].view(-1, 1)
                sqrt_ac_t = sqrt_ac[t_val].view(-1, 1)
                x0_pred = (x_t - sqrt_1m_ac_t * eps_pred) / sqrt_ac_t.clamp(min=1e-6)

                if i == len(step_ids) - 1:
                    x_t = x0_pred
                else:
                    next_t = step_ids[i + 1]
                    ac_next = alpha_cumprod[next_t].view(-1, 1)
                    eps = eps_pred
                    sigma = 0.0  # DDIM eta=0
                    direction = torch.sqrt((1.0 - ac_next).clamp(min=0.0)) * eps
                    x_t = torch.sqrt(ac_next) * x0_pred + direction

            preds.append(scaler_param.inverse_transform(x_t.cpu().numpy()))
    param_pred = np.mean(np.stack(preds, axis=0), axis=0)

    return compute_all_metrics(X_raw, param_pred, pattern, "Inverse Diffusion")


def compute_all_metrics(target, pred, pattern, model_name):
    results = []
    # Overall
    m = metrics(target, pred)
    m["Model"] = model_name
    m["Group"] = "All"
    m["N"] = len(target)
    results.append(m)

    # By pattern
    for p_val, p_name in [(1.0, "Miura"), (2.0, "TMP")]:
        mask = np.isclose(pattern, p_val)
        if mask.sum() > 0:
            m = metrics(target[mask], pred[mask])
            m["Model"] = model_name
            m["Group"] = p_name
            m["N"] = int(mask.sum())
            results.append(m)

    # Per-output metrics
    target_cols = OUTPUT_COLS if target.shape[1] == NUM_OUTPUTS else INPUT_COLS
    for col_idx, col_name in enumerate(target_cols):
        m = metrics(target[:, col_idx], pred[:, col_idx])
        m["Model"] = model_name
        m["Group"] = f"  {col_name}"
        m["N"] = len(target)
        results.append(m)

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test_path", type=str, default=str(SCRIPT_DIR / "data" / "origami_test.npz"))
    parser.add_argument("--save_dir", type=str, default=str(SCRIPT_DIR / "results"))
    args = parser.parse_args()

    X_raw, y_raw, pattern = load_test_data(args.test_path)
    print(f"Test set: {len(X_raw)} samples (Miura={int(np.sum(np.isclose(pattern, 1.0)))}, TMP={int(np.sum(np.isclose(pattern, 2.0)))})")

    os.makedirs(args.save_dir, exist_ok=True)

    all_rows = []

    print("\n--- Forward GNN ---")
    rows = eval_forward_gnn(X_raw, y_raw, pattern)
    all_rows.extend(rows)
    print(f"  Overall MAE={rows[0]['MAE']:.4f} RMSE={rows[0]['RMSE']:.4f} R2={rows[0]['R2']:.4f}")

    print("\n--- Forward Transformer ---")
    rows = eval_forward_transformer(X_raw, y_raw, pattern)
    all_rows.extend(rows)
    print(f"  Overall MAE={rows[0]['MAE']:.4f} RMSE={rows[0]['RMSE']:.4f} R2={rows[0]['R2']:.4f}")

    print("\n--- Inverse ResNet ---")
    rows = eval_inverse_resnet(X_raw, y_raw, pattern)
    all_rows.extend(rows)
    print(f"  Overall MAE={rows[0]['MAE']:.4f} RMSE={rows[0]['RMSE']:.4f} R2={rows[0]['R2']:.4f}")

    print("\n--- Inverse CVAE ---")
    rows = eval_inverse_cvae(X_raw, y_raw, pattern)
    all_rows.extend(rows)
    print(f"  Overall MAE={rows[0]['MAE']:.4f} RMSE={rows[0]['RMSE']:.4f} R2={rows[0]['R2']:.4f}")

    print("\n--- Inverse Diffusion ---")
    rows = eval_inverse_diffusion(X_raw, y_raw, pattern)
    all_rows.extend(rows)
    print(f"  Overall MAE={rows[0]['MAE']:.4f} RMSE={rows[0]['RMSE']:.4f} R2={rows[0]['R2']:.4f}")

    df = pd.DataFrame(all_rows)
    summary_path = os.path.join(args.save_dir, "summary.csv")
    df.to_csv(summary_path, index=False)
    print(f"\nSummary saved to: {summary_path}")

    # Print overview table
    overview = df[df["Group"].isin(["All", "Miura", "TMP"])].copy()
    print("\n==================== OVERVIEW ====================")
    print(overview.to_string(index=False))


if __name__ == "__main__":
    main()
