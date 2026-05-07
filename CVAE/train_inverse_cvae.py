import os
import argparse
import logging
from pathlib import Path
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

from CVAE_module import CVAE


def setup_device():
    if torch.cuda.is_available():
        device = torch.device('cuda')
        print(f"[Device] Running on CUDA: {torch.cuda.get_device_name(0)}")
    else:
        device = torch.device('cpu')
        print("[Device] Running on CPU")
    return device


DEVICE = setup_device()
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_TRAIN_DATA_PATH = str(REPO_ROOT / "dataset used for training" / "train.xlsx")


def load_inverse_data(excel_path):
    print(f"Loading data: {excel_path}")
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"File not found: {excel_path}")

    columns = [
        "V1a", "V1v", "V1c", "w",
        "relativeVolume", "relativeArea", "thickness", "poreDiameter", "areaMean",
        "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10",
        "s11", "s12", "s13", "s14", "s15", "s16", "s17", "s18", "s19", "s20"
    ]

    try:
        dfs = [pd.read_excel(excel_path, sheet_name=s, names=columns) for s in ['class1', 'class2', 'class12']]
        df_all = pd.concat(dfs, axis=0).reset_index(drop=True)
    except Exception as e:
        raise RuntimeError(f"Error reading Excel: {e}")

    data_cond = df_all.iloc[:, 9:].values.astype(np.float32)
    data_target = df_all.iloc[:, :9].values.astype(np.float32)

    return data_cond, data_target


# 銆愭牳蹇冧慨鏀广€戝紩鍏?Free Bits 鏈哄埗
def loss_function(recon_x, x, mu, logvar, kl_weight, free_bits=1.0):
    # MSE
    MSE = F.mse_loss(recon_x, x, reduction='mean')

    # KLD 璁＄畻
    # sum over dim (latent_dim), mean over batch
    kld_element = -0.5 * (1 + logvar - mu.pow(2) - logvar.exp())
    KLD = torch.mean(torch.sum(kld_element, dim=1))

    # Free Bits: 鍙湁褰?KL 澶т簬闃堝€兼椂鎵嶈绠?Loss
    # 杩欒兘闃叉 KL 琚帇寰楀お浣?(Posterior Collapse)
    KLD_loss = torch.max(KLD, torch.tensor(free_bits).to(DEVICE))

    return MSE + kl_weight * KLD_loss, MSE, KLD


def train_pipeline(args):
    X_raw, y_raw = load_inverse_data(args.data_path)
    X_train, X_val, y_train, y_val = train_test_split(X_raw, y_raw, test_size=0.2, random_state=42)

    scaler_curve = StandardScaler()
    X_train = scaler_curve.fit_transform(X_train)
    X_val = scaler_curve.transform(X_val)

    scaler_param = StandardScaler()
    y_train = scaler_param.fit_transform(y_train)
    y_val = scaler_param.transform(y_val)

    train_loader = DataLoader(
        TensorDataset(torch.tensor(X_train), torch.tensor(y_train)),
        batch_size=args.batch_size,
        shuffle=True,
    )
    val_loader = DataLoader(
        TensorDataset(torch.tensor(X_val), torch.tensor(y_val)),
        batch_size=args.batch_size,
        shuffle=False,
    )

    save_dir = os.path.join(SCRIPT_DIR, "cvae_checkpoints")
    os.makedirs(save_dir, exist_ok=True)

    for i in range(args.pipelines):
        print(f"\n{'=' * 20} Training C-VAE Pipeline {i + 1}/{args.pipelines} {'=' * 20}")

        # latent_dim=4
        model = CVAE(param_dim=9, curve_points=20, latent_dim=4, hidden_dim=512).to(DEVICE)

        optimizer = torch.optim.AdamW(model.parameters(), lr=0.0005, weight_decay=1e-5)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-7)

        history = {'loss': [], 'mse': [], 'kld': [], 'val_mse': []}
        best_val_mse = float('inf')

        # 銆愮瓥鐣ヨ皟鏁淬€?
        target_kl_weight = 0.002  # 闄嶄綆鏉冮噸锛岀粰 z 鍛煎惛绌洪棿
        target_free_bits = 1.0  # 鍏佽 1.0 nat 鐨勮嚜鐢变俊鎭噺
        initial_cond_drop = 0.5  # 鍒濆寮?Dropout

        for epoch in range(args.epochs):
            model.train()
            train_loss = 0;
            train_mse = 0;
            train_kld = 0

            # KL Warmup (绾挎€у鍔?
            if epoch < args.epochs * 0.3:
                kl_weight = target_kl_weight * (epoch / (args.epochs * 0.3))
            else:
                kl_weight = target_kl_weight

            # Condition Dropout: 鏈€缁堜繚鐣?0.1 鐨勫簳鍣紝涓嶉檷鍒?0
            decay_factor = max(0, (1 - epoch / (args.epochs * 0.8)))
            cond_drop = (initial_cond_drop - 0.1) * decay_factor + 0.1

            for curve, param in train_loader:
                curve, param = curve.to(DEVICE), param.to(DEVICE)
                optimizer.zero_grad()

                recon_param, mu, logvar = model(param, curve, condition_dropout_prob=cond_drop)

                # 浣跨敤 Free Bits Loss
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

            # Validation
            model.eval()
            val_mse = 0
            with torch.no_grad():
                for curve, param in val_loader:
                    curve, param = curve.to(DEVICE), param.to(DEVICE)
                    recon_param, mu, logvar = model(param, curve, condition_dropout_prob=0.0)
                    # 楠岃瘉鏃跺彧鐪?MSE
                    _, mse, _ = loss_function(recon_param, param, mu, logvar, kl_weight, free_bits=0.0)
                    val_mse += mse.item()

            val_mse /= len(val_loader)
            scheduler.step()

            if val_mse < best_val_mse:
                best_val_mse = val_mse
                torch.save({
                    'model_state': model.state_dict(),
                    'scaler_curve': scaler_curve,
                    'scaler_param': scaler_param
                }, os.path.join(save_dir, f'cvae_{i}.pth'))

            history['loss'].append(train_loss)
            history['mse'].append(train_mse)
            history['kld'].append(train_kld)
            history['val_mse'].append(val_mse)

            if (epoch + 1) % 20 == 0:
                print(
                    f"Epoch {epoch + 1} | MSE: {train_mse:.5f} | Val: {val_mse:.5f} | KLD: {train_kld:.2f} | Drop: {cond_drop:.2f}")

        # 缁樺浘
        plt.figure()
        # 鍙岃酱缁樺浘锛氬乏杞?MSE锛屽彸杞?KLD
        fig, ax1 = plt.subplots()
        ax1.plot(history['mse'], 'b-', label='Train MSE')
        ax1.plot(history['val_mse'], 'r-', label='Val MSE')
        ax1.set_xlabel('Epochs')
        ax1.set_ylabel('MSE', color='b')

        ax2 = ax1.twinx()
        ax2.plot(history['kld'], 'g--', label='KLD')
        ax2.set_ylabel('KL Divergence', color='g')

        plt.title(f'C-VAE Pipeline {i}')
        plt.savefig(os.path.join(save_dir, f'cvae_curve_{i}.png'))
        plt.close()

        pd.DataFrame(history).to_excel(os.path.join(save_dir, f'log_cvae_{i}.xlsx'), index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path', type=str, default=DEFAULT_TRAIN_DATA_PATH)
    parser.add_argument('--epochs', type=int, default=400)
    parser.add_argument('--batch_size', type=int, default=256)
    parser.add_argument('--pipelines', type=int, default=1)
    args = parser.parse_args()

    torch.manual_seed(42)
    train_pipeline(args)



