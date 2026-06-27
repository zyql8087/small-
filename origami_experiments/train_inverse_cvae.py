"""Train inverse CVAE on Origami Sheet data: 6 stiffness values -> 8 parameters."""

import os
import sys
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from modules.origami_inverse_cvae import OrigamiCVAE

INPUT_COLS = ["pattern", "m", "n", "tcrease", "tpanel", "W", "creaseE", "panelE"]
OUTPUT_COLS = ["bendstiff30", "bendstiff60", "bendstiff90", "axialstiff30", "axialstiff60", "axialstiff90"]
NUM_INPUTS = len(INPUT_COLS)
NUM_OUTPUTS = len(OUTPUT_COLS)


def setup_device():
    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(f"[Device] Running on CUDA: {torch.cuda.get_device_name(0)}")
    else:
        device = torch.device("cpu")
        print("[Device] Running on CPU")
    return device


DEVICE = setup_device()


def load_data(npz_path):
    print(f"Loading data from: {npz_path}")
    data = np.load(npz_path)
    X_raw = data["X_raw"]
    y_raw = data["y_raw"]

    # Inverse: curve=stiffness (6) -> target=params (8)
    curve_raw = y_raw  # stiffness values
    param_raw = X_raw  # design parameters

    curve_train, curve_val, param_train, param_val = train_test_split(
        curve_raw, param_raw, test_size=0.2, random_state=42
    )

    scaler_curve = StandardScaler()
    curve_train = scaler_curve.fit_transform(curve_train)
    curve_val = scaler_curve.transform(curve_val)

    scaler_param = StandardScaler()
    param_train = scaler_param.fit_transform(param_train)
    param_val = scaler_param.transform(param_val)

    print(f"  Train: {curve_train.shape[0]}, Val: {curve_val.shape[0]}")
    return curve_train, curve_val, param_train, param_val, scaler_curve, scaler_param


def loss_function(recon_x, x, mu, logvar, kl_weight, free_bits=1.0):
    MSE = F.mse_loss(recon_x, x, reduction="mean")
    kld_element = -0.5 * (1 + logvar - mu.pow(2) - logvar.exp())
    KLD = torch.mean(torch.sum(kld_element, dim=1))
    KLD_loss = torch.max(KLD, torch.tensor(free_bits).to(DEVICE))
    return MSE + kl_weight * KLD_loss, MSE, KLD


def train_pipeline(args):
    curve_train, curve_val, param_train, param_val, scaler_curve, scaler_param = load_data(args.data_path)

    train_loader = DataLoader(
        TensorDataset(torch.tensor(curve_train), torch.tensor(param_train)),
        batch_size=args.batch_size, shuffle=True,
    )
    val_loader = DataLoader(
        TensorDataset(torch.tensor(curve_val), torch.tensor(param_val)),
        batch_size=args.batch_size, shuffle=False,
    )

    save_dir = os.path.join(SCRIPT_DIR, "checkpoints", "inverse_cvae")
    os.makedirs(save_dir, exist_ok=True)

    for i in range(args.pipelines):
        print(f"\n{'='*20} Training CVAE Pipeline {i+1}/{args.pipelines} {'='*20}")

        model = OrigamiCVAE(
            param_dim=NUM_INPUTS, curve_points=NUM_OUTPUTS, latent_dim=4, hidden_dim=512
        ).to(DEVICE)

        optimizer = torch.optim.AdamW(model.parameters(), lr=0.0005, weight_decay=1e-5)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-7)

        history = {"loss": [], "mse": [], "kld": [], "val_mse": []}
        best_val_mse = float("inf")

        target_kl_weight = 0.002
        target_free_bits = 1.0
        initial_cond_drop = 0.5

        for epoch in range(args.epochs):
            model.train()
            train_loss, train_mse, train_kld = 0.0, 0.0, 0.0

            if epoch < args.epochs * 0.3:
                kl_weight = target_kl_weight * (epoch / (args.epochs * 0.3))
            else:
                kl_weight = target_kl_weight

            decay_factor = max(0, (1 - epoch / (args.epochs * 0.8)))
            cond_drop = (initial_cond_drop - 0.1) * decay_factor + 0.1

            for curve, param in train_loader:
                curve, param = curve.to(DEVICE), param.to(DEVICE)
                optimizer.zero_grad()
                recon_param, mu, logvar = model(param, curve, condition_dropout_prob=cond_drop)
                loss, mse, kld = loss_function(recon_param, param, mu, logvar, kl_weight, free_bits=target_free_bits)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                train_loss += loss.item()
                train_mse += mse.item()
                train_kld += kld.item()

            train_loss /= len(train_loader)
            train_mse /= len(train_loader)
            train_kld /= len(train_loader)

            model.eval()
            val_mse = 0.0
            with torch.no_grad():
                for curve, param in val_loader:
                    curve, param = curve.to(DEVICE), param.to(DEVICE)
                    recon_param, mu, logvar = model(param, curve, condition_dropout_prob=0.0)
                    _, mse, _ = loss_function(recon_param, param, mu, logvar, kl_weight, free_bits=0.0)
                    val_mse += mse.item()
            val_mse /= len(val_loader)
            scheduler.step()

            if val_mse < best_val_mse:
                best_val_mse = val_mse
                torch.save({
                    "model_state": model.state_dict(),
                    "scaler_curve": scaler_curve,
                    "scaler_param": scaler_param,
                }, os.path.join(save_dir, f"cvae_{i}.pth"))

            history["loss"].append(train_loss)
            history["mse"].append(train_mse)
            history["kld"].append(train_kld)
            history["val_mse"].append(val_mse)

            if (epoch + 1) % 20 == 0:
                print(f"Epoch {epoch+1} | MSE: {train_mse:.5f} | Val: {val_mse:.5f} | KLD: {train_kld:.2f} | Drop: {cond_drop:.2f}")

        fig, ax1 = plt.subplots()
        ax1.plot(history["mse"], "b-", label="Train MSE")
        ax1.plot(history["val_mse"], "r-", label="Val MSE")
        ax1.set_xlabel("Epochs"); ax1.set_ylabel("MSE")
        ax2 = ax1.twinx()
        ax2.plot(history["kld"], "g--", label="KLD")
        ax2.set_ylabel("KL Divergence")
        plt.title(f"CVAE Pipeline {i}")
        plt.savefig(os.path.join(save_dir, f"cvae_curve_{i}.png"))
        plt.close()

        pd.DataFrame(history).to_excel(os.path.join(save_dir, f"log_cvae_{i}.xlsx"), index=False)

    print(f"\nAll {args.pipelines} CVAE pipelines completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_path", type=str, default=str(SCRIPT_DIR / "data" / "origami_train.npz"))
    parser.add_argument("--epochs", type=int, default=400)
    parser.add_argument("--batch_size", type=int, default=256)
    parser.add_argument("--pipelines", type=int, default=1)
    args = parser.parse_args()

    torch.manual_seed(42)
    train_pipeline(args)
