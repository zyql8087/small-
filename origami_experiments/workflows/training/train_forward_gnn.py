"""Train forward GNN on Origami Sheet data: 8 parameters -> 6 stiffness targets."""

import os
import sys
import copy
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
from origami_experiments.models.origami_forward_gnn import OrigamiGNNForward

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
    print(f"  X shape: {X_raw.shape}, y shape: {y_raw.shape}")

    X_train_raw, X_val_raw, y_train_raw, y_val_raw = train_test_split(
        X_raw, y_raw, test_size=0.2, random_state=42
    )

    scaler_x = StandardScaler()
    X_train = scaler_x.fit_transform(X_train_raw)
    X_val = scaler_x.transform(X_val_raw)

    scaler_y = StandardScaler()
    y_train = scaler_y.fit_transform(y_train_raw)
    y_val = scaler_y.transform(y_val_raw)

    adj_matrix = np.ones((NUM_INPUTS, NUM_INPUTS), dtype=np.float32)
    adj_tensor = torch.tensor(adj_matrix, dtype=torch.float32).to(DEVICE)

    print(f"  Train: {X_train.shape[0]}, Val: {X_val.shape[0]}")
    return X_train, X_val, y_train, y_val, scaler_x, scaler_y, adj_tensor


def plot_training_curves(history, pipeline_idx, save_dir):
    epochs = range(1, len(history["loss"]) + 1)
    plt.figure(figsize=(14, 6))
    plt.subplot(1, 2, 1)
    plt.plot(epochs, history["loss"], "b-", label="Train MSE")
    plt.plot(epochs, history["val_loss"], "r-", label="Val MSE")
    plt.title(f"GNN Forward Pipeline {pipeline_idx} - MSE")
    plt.xlabel("Epochs"); plt.ylabel("MSE")
    plt.legend(); plt.grid(True, linestyle="--", alpha=0.7)

    plt.subplot(1, 2, 2)
    plt.plot(epochs, history["mae"], "b-", label="Train MAE")
    plt.plot(epochs, history["val_mae"], "r-", label="Val MAE")
    plt.title(f"GNN Forward Pipeline {pipeline_idx} - MAE")
    plt.xlabel("Epochs"); plt.ylabel("MAE")
    plt.legend(); plt.grid(True, linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, f"training_curves_gnn_{pipeline_idx}.png"), dpi=300)
    plt.close()


def train_pipeline(args):
    X_train, X_val, y_train, y_val, scaler_x, scaler_y, adj_tensor = load_data(args.data_path)

    train_ds = TensorDataset(torch.tensor(X_train, dtype=torch.float32), torch.tensor(y_train, dtype=torch.float32))
    val_ds = TensorDataset(torch.tensor(X_val, dtype=torch.float32), torch.tensor(y_val, dtype=torch.float32))
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, pin_memory=True)

    save_dir = os.path.join(SCRIPT_DIR, "checkpoints", "forward_gnn")
    os.makedirs(save_dir, exist_ok=True)
    print(f"Checkpoints saved to: {save_dir}")

    for i in range(args.pipelines):
        print(f"\n{'='*20} Training GNN Pipeline {i+1}/{args.pipelines} {'='*20}")

        model = OrigamiGNNForward(
            num_inputs=NUM_INPUTS,
            num_outputs=NUM_OUTPUTS,
            gnn_hidden_dim=256,
            gnn_heads=8,
            units_layer1=512,
            units_layer2=256,
            units_layer3=128,
            units_layer4=64,
            dropout_rate=0.1,
        ).to(DEVICE)

        base_lr = 0.0005
        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=20, min_lr=1e-7
        )
        criterion = nn.MSELoss()
        mae_metric = nn.L1Loss()
        history = {"loss": [], "val_loss": [], "mae": [], "val_mae": []}

        best_val_mae = float("inf")
        best_epoch = -1
        best_model_state = None
        warmup_epochs = 10
        initial_noise = 0.01
        min_noise = 0.002

        for epoch in range(args.epochs):
            if epoch < warmup_epochs:
                warmup_lr = base_lr * (epoch + 1) / warmup_epochs
                for g in optimizer.param_groups:
                    g["lr"] = warmup_lr

            model.train()
            train_loss, train_mae = 0.0, 0.0
            for bx, by in train_loader:
                bx, by = bx.to(DEVICE), by.to(DEVICE)
                if epoch > 0:
                    decay = max(0, 1 - epoch / (args.epochs * 0.9))
                    noise = (initial_noise - min_noise) * decay + min_noise
                    bx = bx + torch.randn_like(bx) * noise

                optimizer.zero_grad()
                out = model(bx, adj_tensor)
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
                    out = model(bx, adj_tensor)
                    val_loss += criterion(out, by).item() * bx.size(0)
                    val_mae += mae_metric(out, by).item() * bx.size(0)
            val_loss /= len(val_ds)
            val_mae /= len(val_ds)

            if epoch >= warmup_epochs:
                scheduler.step(val_loss)

            if val_mae < best_val_mae:
                best_val_mae = val_mae
                best_epoch = epoch + 1
                best_model_state = copy.deepcopy(model.state_dict())

            history["loss"].append(train_loss)
            history["val_loss"].append(val_loss)
            history["mae"].append(train_mae)
            history["val_mae"].append(val_mae)

            if (epoch + 1) % 10 == 0 or epoch == 0:
                lr = optimizer.param_groups[0]["lr"]
                print(f"Epoch {epoch+1}/{args.epochs} | MSE: {train_loss:.6f} | Val: {val_loss:.6f} | MAE: {val_mae:.6f} | Best: {best_val_mae:.6f} | LR: {lr:.2e}")

        model_path = os.path.join(save_dir, f"forward_gnn_{i}.pth")
        if best_model_state is not None:
            torch.save({
                "model_state_dict": best_model_state,
                "scaler_x": scaler_x,
                "scaler_y": scaler_y,
                "input_cols": INPUT_COLS,
                "best_epoch": best_epoch,
                "best_val_mae": best_val_mae,
            }, model_path)
            print(f"Best model saved: {model_path} (MAE: {best_val_mae:.6f}, Epoch: {best_epoch})")

        pd.DataFrame(history).to_excel(os.path.join(save_dir, f"log_forward_gnn_{i}.xlsx"), index=False)
        plot_training_curves(history, i, save_dir)

    print(f"\nAll {args.pipelines} GNN forward pipelines completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_path", type=str, default=str(SCRIPT_DIR / "data" / "origami_train.npz"))
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--batch_size", type=int, default=256)
    parser.add_argument("--pipelines", type=int, default=1)
    args = parser.parse_args()

    torch.manual_seed(42)
    np.random.seed(42)
    train_pipeline(args)
