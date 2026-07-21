"""Train inverse ResNet1D on Origami Sheet data: 6 stiffness values -> 8 parameters."""

import os
import sys
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

EXPERIMENT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = EXPERIMENT_ROOT.parent
SCRIPT_DIR = EXPERIMENT_ROOT
sys.path.insert(0, str(REPO_ROOT))
from origami_experiments.models.origami_inverse_resnet import OrigamiResNet1DInverse

INPUT_COLS = ["pattern", "m", "n", "tcrease", "tpanel", "W", "creaseE", "panelE"]
OUTPUT_COLS = ["bendstiff30", "bendstiff60", "bendstiff90", "axialstiff30", "axialstiff60", "axialstiff90"]
NUM_INPUTS = len(INPUT_COLS)
NUM_OUTPUTS = len(OUTPUT_COLS)


def setup_device():
    if torch.cuda.is_available():
        device = torch.device("cuda")
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
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
    curve_raw = y_raw
    param_raw = X_raw

    curve_train, curve_val, param_train, param_val = train_test_split(
        curve_raw, param_raw, test_size=0.2, random_state=42
    )

    scaler_x = StandardScaler()
    curve_train = scaler_x.fit_transform(curve_train)
    curve_val = scaler_x.transform(curve_val)

    scaler_y = StandardScaler()
    param_train = scaler_y.fit_transform(param_train)
    param_val = scaler_y.transform(param_val)

    print(f"  Train: {curve_train.shape[0]}, Val: {curve_val.shape[0]}")
    return curve_train, curve_val, param_train, param_val, scaler_x, scaler_y


def plot_curves(history, pipeline_idx, save_dir):
    epochs = range(1, len(history["loss"]) + 1)
    plt.figure(figsize=(14, 6))
    plt.subplot(1, 2, 1)
    plt.plot(epochs, history["loss"], "b-", label="Train Loss")
    plt.plot(epochs, history["val_loss"], "r-", label="Val Loss")
    plt.title(f"ResNet Inverse Pipeline {pipeline_idx} - SmoothL1")
    plt.xlabel("Epochs"); plt.legend(); plt.grid(True, alpha=0.5)
    plt.subplot(1, 2, 2)
    plt.plot(epochs, history["mae"], "b-", label="Train MAE")
    plt.plot(epochs, history["val_mae"], "r-", label="Val MAE")
    plt.title(f"ResNet Inverse Pipeline {pipeline_idx} - MAE")
    plt.xlabel("Epochs"); plt.legend(); plt.grid(True, alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, f"resnet_curve_{pipeline_idx}.png"))
    plt.close()


def train_pipeline(args):
    curve_train, curve_val, param_train, param_val, scaler_x, scaler_y = load_data(args.data_path)

    train_ds = TensorDataset(torch.tensor(curve_train, dtype=torch.float32), torch.tensor(param_train, dtype=torch.float32))
    val_ds = TensorDataset(torch.tensor(curve_val, dtype=torch.float32), torch.tensor(param_val, dtype=torch.float32))
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, pin_memory=True)

    save_dir = os.path.join(SCRIPT_DIR, "checkpoints", "inverse_resnet")
    os.makedirs(save_dir, exist_ok=True)
    print(f"Checkpoints saved to: {save_dir}")

    for i in range(args.pipelines):
        print(f"\n{'='*20} Training ResNet Inverse Pipeline {i+1}/{args.pipelines} {'='*20}")

        model = OrigamiResNet1DInverse(dropout_rate=0.2, num_outputs=NUM_INPUTS).to(DEVICE)

        base_lr = 0.001
        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=1e-5)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.6, patience=40, min_lr=1e-6
        )
        criterion = nn.SmoothL1Loss()
        mae_metric = nn.L1Loss()

        history = {"loss": [], "val_loss": [], "mae": [], "val_mae": []}
        best_val_loss = float("inf")

        initial_noise = 0.003
        noise_floor = 0.0005
        noise_decay_end = int(args.epochs * 0.85)
        warmup_epochs = 20

        for epoch in range(args.epochs):
            if epoch < warmup_epochs:
                for g in optimizer.param_groups:
                    g["lr"] = base_lr * (epoch + 1) / warmup_epochs

            model.train()
            train_loss, train_mae = 0.0, 0.0
            for bx, by in train_loader:
                bx, by = bx.to(DEVICE), by.to(DEVICE)
                if epoch < noise_decay_end:
                    noise = max(noise_floor, initial_noise * (1 - epoch / noise_decay_end))
                    bx = bx + torch.randn_like(bx) * noise

                optimizer.zero_grad()
                out = model(bx)
                loss = criterion(out, by)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=0.5)
                optimizer.step()
                train_loss += loss.item() * bx.size(0)
                train_mae += mae_metric(out, by).item() * bx.size(0)

            train_loss /= len(train_ds)
            train_mae /= len(train_ds)

            model.eval()
            val_loss, val_mae = 0.0, 0.0
            with torch.no_grad():
                for bx, by in val_loader:
                    bx, by = bx.to(DEVICE), by.to(DEVICE)
                    out = model(bx)
                    val_loss += criterion(out, by).item() * bx.size(0)
                    val_mae += mae_metric(out, by).item() * bx.size(0)
            val_loss /= len(val_ds)
            val_mae /= len(val_ds)

            scheduler.step(val_loss)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save({
                    "model_state": model.state_dict(),
                    "scaler_x": scaler_x,
                    "scaler_y": scaler_y,
                }, os.path.join(save_dir, f"inverse_resnet_{i}.pth"))

            history["loss"].append(train_loss)
            history["val_loss"].append(val_loss)
            history["mae"].append(train_mae)
            history["val_mae"].append(val_mae)

            if (epoch + 1) % 10 == 0:
                lr = optimizer.param_groups[0]["lr"]
                print(f"Epoch {epoch+1} | Loss: {train_loss:.5f} | Val: {val_loss:.5f} | Best: {best_val_loss:.5f} | LR: {lr:.2e}")

        pd.DataFrame(history).to_excel(os.path.join(save_dir, f"log_resnet_{i}.xlsx"), index=False)
        plot_curves(history, i, save_dir)

    print(f"\nAll {args.pipelines} ResNet inverse pipelines completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_path", type=str, default=str(SCRIPT_DIR / "data" / "origami_train.npz"))
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--batch_size", type=int, default=2048)
    parser.add_argument("--pipelines", type=int, default=1)
    args = parser.parse_args()

    torch.manual_seed(42)
    train_pipeline(args)
