import os
import torch
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import r2_score
from tqdm import tqdm  # 杩涘害鏉?

# 瀵煎叆妯″瀷瀹氫箟
from GNN_module import GNNForwardNetwork
from CVAE_module import CVAE

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Running on: {device}")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------
# 閰嶇疆璺緞
# ----------------------------------------------------------------
TEST_DATA_PATH = os.path.join(SCRIPT_DIR, "dataset used for training", "test.xlsx")
FORWARD_MODEL_PATH = os.path.join(SCRIPT_DIR, "forward_gnn_checkpoints", "forward_gnn_2.pth")
INVERSE_MODEL_PATH = os.path.join(SCRIPT_DIR, "cvae_checkpoints", "cvae_0.pth")


# ----------------------------------------------------------------
# 1. 鍔犺浇鏁版嵁
# ----------------------------------------------------------------
def load_test_data(excel_path):
    print(f"Loading Test Data...")
    columns = [
        "V1a", "V1v", "V1c", "w",
        "relativeVolume", "relativeArea", "thickness", "poreDiameter", "areaMean",
        "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10",
        "s11", "s12", "s13", "s14", "s15", "s16", "s17", "s18", "s19", "s20"
    ]

    dfs = []
    for sheet in ['class1', 'class2', 'class12']:
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet, names=columns)
            dfs.append(df)
        except:
            pass

    df_all = pd.concat(dfs, axis=0).reset_index(drop=True)

    # X: Curves (Condition)
    X_curve = df_all.iloc[:, 9:].values.astype(np.float32)
    # Y: Params (Ground Truth - 浠呯敤浜庣粯鍥惧弬鑰?
    y_param = df_all.iloc[:, :9].values.astype(np.float32)

    return X_curve, y_param


# ----------------------------------------------------------------
# 2. 鍔犺浇妯″瀷
# ----------------------------------------------------------------
def load_models():
    print("Loading Models...")
    # 鍔犺浇鍓嶅悜妯″瀷
    forward_net = GNNForwardNetwork(
        units_layer1=512, units_layer2=256, units_layer3=128, units_layer4=64,
        gnn_hidden_dim=256, gnn_heads=8, dropout_rate=0.0
    ).to(device)

    fwd_checkpoint = torch.load(FORWARD_MODEL_PATH, map_location=device, weights_only=False)
    forward_net.load_state_dict(fwd_checkpoint['model_state_dict'])
    forward_net.eval()

    # 鑾峰彇 Scaler
    scaler_curve = fwd_checkpoint['scaler_y']
    scaler_param = fwd_checkpoint['scaler_x']

    # 鍔犺浇 C-VAE
    cvae_net = CVAE(param_dim=9, curve_points=20, latent_dim=3, hidden_dim=256).to(device)
    inv_checkpoint = torch.load(INVERSE_MODEL_PATH, map_location=device, weights_only=False)
    cvae_net.load_state_dict(inv_checkpoint['model_state'])
    cvae_net.eval()

    return forward_net, cvae_net, scaler_curve, scaler_param


# ----------------------------------------------------------------
# 3. 鏍稿績閫昏緫锛氶噰鏍?-> 浼橀€?
# ----------------------------------------------------------------
def evaluate_design_with_sampling(num_samples=50):  # 姣忎釜鐩爣鐢熸垚 50 涓€欓€?
    curves_raw, true_params = load_test_data(TEST_DATA_PATH)
    forward_model, cvae_model, scaler_curve, scaler_param = load_models()

    # 鍑嗗鍏ㄨ繛鎺ラ偦鎺ョ煩闃?(鐢ㄤ簬鍓嶅悜楠岃瘉)
    adj = torch.ones((9, 9), dtype=torch.float32).to(device)

    # 棰勫鐞嗚緭鍏ユ洸绾?
    curves_scaled = scaler_curve.transform(curves_raw)
    curves_tensor = torch.tensor(curves_scaled).to(device)

    num_test = len(curves_raw)
    best_pred_curves = []
    best_gen_params = []

    print(f"\nStarting Optimization: Generating {num_samples} candidates per target...")

    with torch.no_grad():
        for i in tqdm(range(num_test)):
            # 1. 鍙栧嚭褰撳墠鐩爣鏇茬嚎
            target_curve_tensor = curves_tensor[i].unsqueeze(0)  # (1, 20)

            # 2. 澶嶅埗 N 浠斤紝鐢ㄤ簬骞惰鐢熸垚 N 涓€欓€?
            target_repeated = target_curve_tensor.repeat(num_samples, 1)  # (N, 20)

            # 3. C-VAE 閲囨牱鐢熸垚
            # 閲囨牱 N 涓笉鍚岀殑闅忔満鍣０ z
            z = torch.randn(num_samples, 3).to(device)
            gen_params_scaled = cvae_model.inference(target_repeated, z=z)  # (N, 9)

            # 4. 鍓嶅悜妯″瀷蹇€熻瘎浼?(Proxy Evaluation)
            # 鎵╁睍 adj 浠ュ尮閰?batch
            batch_adj = adj.unsqueeze(0).repeat(num_samples, 1, 1)
            pred_curves_scaled = forward_model(gen_params_scaled, batch_adj)  # (N, 20)

            # 5. 璁＄畻璇樊骞朵紭閫?
            # 鍦?Scaled 绌洪棿璁＄畻 MSE 鍗冲彲锛屾棤闇€鍙嶅綊涓€鍖栵紝閫熷害鏇村揩
            diff = pred_curves_scaled - target_repeated
            mse_scores = torch.mean(diff ** 2, dim=1)  # (N, )

            # 鎵惧埌鏈€灏忚宸殑绱㈠紩
            best_idx = torch.argmin(mse_scores).item()

            # 6. 璁板綍鏈€浣崇粨鏋?(鍙嶅綊涓€鍖?
            best_p_scaled = gen_params_scaled[best_idx].cpu().numpy().reshape(1, -1)
            best_c_scaled = pred_curves_scaled[best_idx].cpu().numpy().reshape(1, -1)

            best_gen_params.append(scaler_param.inverse_transform(best_p_scaled))
            best_pred_curves.append(scaler_curve.inverse_transform(best_c_scaled))

    # 鎷兼帴鎵€鏈夌粨鏋?
    final_pred_curves = np.concatenate(best_pred_curves, axis=0)
    final_gen_params = np.concatenate(best_gen_params, axis=0)

    # ----------------------------------------------------------------
    # 4. 鏈€缁堣瘎浼?
    # ----------------------------------------------------------------
    # 璁＄畻鍏ㄥ眬鎸囨爣
    mse = np.mean((curves_raw - final_pred_curves) ** 2)
    mae = np.mean(np.abs(curves_raw - final_pred_curves))

    data_range = np.max(curves_raw) - np.min(curves_raw)
    nrmse = (np.sqrt(mse) / data_range) * 100

    print(f"\n{'=' * 40}")
    print(f"INVERSE DESIGN EVALUATION (Sampling N={num_samples})")
    print(f"{'=' * 40}")
    print(f"Design NRMSE: {nrmse:.2f}%")
    print(f"Design MAE  : {mae:.4f} kPa")
    print(f"Paper Baseline: 2.49%")
    print(f"{'=' * 40}")

    if nrmse < 2.49:
        print(">>> SUCCESS: SOTA Performance Achieved! <<<")

    # 缁樺浘
    plot_results(curves_raw, final_pred_curves, final_gen_params, true_params)


def plot_results(target_curves, designed_curves, gen_params, true_params):
    indices = np.random.choice(len(target_curves), 4, replace=False)

    plt.figure(figsize=(15, 10))
    for i, idx in enumerate(indices):
        plt.subplot(2, 2, i + 1)

        t_curve = np.concatenate(([0], target_curves[idx]))
        d_curve = np.concatenate(([0], designed_curves[idx]))
        x_axis = np.linspace(0, 25, 21)

        plt.plot(x_axis, t_curve, 'k-', linewidth=2.5, label='Target')
        plt.plot(x_axis, d_curve, 'r--', linewidth=2, marker='o', markersize=4, label='Best Design')

        plt.title(f'Test Sample {idx}')
        plt.xlabel('Strain (%)')
        plt.ylabel('Stress (kPa)')
        plt.legend()
        plt.grid(True, linestyle=':', alpha=0.6)

    plt.tight_layout()
    plt.savefig('inverse_design_final_result.png')
    print("Saved final plot to inverse_design_final_result.png")


if __name__ == '__main__':
    # 鎮ㄥ彲浠ュ皾璇?N=10, N=50, N=100锛岄€氬父 N=50 灏辫兘杈惧埌寰堝ソ鐨勬晥鏋?
    evaluate_design_with_sampling(num_samples=100)

