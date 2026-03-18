import os
import torch
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm

from GNN_module import GNNForwardNetwork
from CVAE_module import CVAE

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

TEST_DATA_PATH = os.path.join(SCRIPT_DIR, "dataset used for training", "test.xlsx")
FORWARD_MODEL_PATH = os.path.join(SCRIPT_DIR, "forward_gnn_checkpoints", "forward_gnn_2.pth")
INVERSE_MODEL_PATH = os.path.join(SCRIPT_DIR, "cvae_checkpoints", "cvae_0.pth")


def load_data_and_models():
    # ... (鍔犺浇鏁版嵁鍜屾ā鍨嬬殑浠ｇ爜涓庝箣鍓嶄竴鑷达紝鐪佺暐浠ヨ妭鐪佺瘒骞? ...
    # 璇风洿鎺ュ鐢?verify_inverse_design_final.py 涓殑 load_test_data 鍜?load_models 鍑芥暟
    # 姝ゅ鍋囪宸插畾涔?
    from verify_inverse_design_final import load_test_data, load_models
    return load_test_data(TEST_DATA_PATH), load_models()


def solve_hard_samples():
    (curves_raw, true_params), (forward_net, cvae_net, scaler_curve, scaler_param) = load_data_and_models()

    # 1. 鍏堢敤 N=50 蹇€熺瓫閫夊嚭闅炬牱鏈?(Hard Samples)
    print("Scanning for hard samples (N=50)...")
    curves_scaled = scaler_curve.transform(curves_raw)
    curves_tensor = torch.tensor(curves_scaled).to(device)
    adj = torch.ones((9, 9), dtype=torch.float32).to(device)

    errors = []
    with torch.no_grad():
        for i in tqdm(range(len(curves_raw))):
            target = curves_tensor[i].unsqueeze(0).repeat(50, 1)
            z = torch.randn(50, 4).to(device)
            gen_params = cvae_net.inference(target, z=z)

            batch_adj = adj.unsqueeze(0).repeat(50, 1, 1)
            pred_curves = forward_net(gen_params, batch_adj)

            # 璁＄畻鏈€灏忚宸?
            diff = pred_curves - target
            mse = torch.mean(diff ** 2, dim=1).min().item()
            errors.append(mse)

    errors = np.array(errors)
    # 瀹氫箟闅炬牱鏈細璇樊鏈€澶х殑 Top 5%
    hard_threshold = np.percentile(errors, 95)
    hard_indices = np.where(errors >= hard_threshold)[0]

    print(f"\nFound {len(hard_indices)} hard samples (MSE > {hard_threshold:.5f})")
    print(f"Example indices: {hard_indices[:10]}...")

    # 2. 瀵归毦鏍锋湰杩涜鈥滄毚鍔涙敾鍧氣€?(N=2000)
    print("\nAttacking hard samples with N=2000 sampling...")
    improved_errors = []

    plt.figure(figsize=(15, 10))
    plot_count = 0

    with torch.no_grad():
        for idx in tqdm(hard_indices):
            target_raw = curves_raw[idx]
            target = curves_tensor[idx].unsqueeze(0).repeat(2000, 1)  # 2000娆￠噰鏍?

            z = torch.randn(2000, 4).to(device)
            gen_params = cvae_net.inference(target, z=z)

            batch_adj = adj.unsqueeze(0).repeat(2000, 1, 1)
            pred_curves = forward_net(gen_params, batch_adj)

            # 浼橀€?
            diff = pred_curves - target
            mse_scores = torch.mean(diff ** 2, dim=1)
            best_idx = torch.argmin(mse_scores).item()
            best_mse = mse_scores[best_idx].item()

            improved_errors.append(best_mse)

            # 缁樺浘 (鍙敾鍓?涓?
            if plot_count < 9:
                best_c_scaled = pred_curves[best_idx].cpu().numpy().reshape(1, -1)
                best_curve = scaler_curve.inverse_transform(best_c_scaled).flatten()

                plt.subplot(3, 3, plot_count + 1)
                x_axis = np.linspace(0, 25, 21)
                # 琛?
                t_plot = np.concatenate(([0], target_raw))
                p_plot = np.concatenate(([0], best_curve))

                plt.plot(x_axis, t_plot, 'k-', linewidth=2, label='Target')
                plt.plot(x_axis, p_plot, 'r--', linewidth=2, label=f'Pred (N=2000)')
                plt.title(f'Hard Sample {idx}\nOld MSE: {errors[idx]:.4f} -> New: {best_mse:.4f}')
                plt.legend()
                plt.grid(True, linestyle=':')
                plot_count += 1

    plt.tight_layout()
    plt.savefig('hard_sample_attack.png')

    # 缁熻鎻愬崌
    avg_old = np.mean(errors[hard_indices])
    avg_new = np.mean(improved_errors)
    print(f"\n{'=' * 30}")
    print(f"Optimization Result for Hard Samples:")
    print(f"Avg MSE (N=50)  : {avg_old:.5f}")
    print(f"Avg MSE (N=2000): {avg_new:.5f}")
    print(f"Improvement     : {(avg_old - avg_new) / avg_old * 100:.2f}%")
    print(f"{'=' * 30}")


if __name__ == '__main__':
    solve_hard_samples()
