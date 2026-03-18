import os
import torch
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from sklearn.metrics import r2_score

# 瀵煎叆妯″瀷瀹氫箟
from GNN_module import GNNForwardNetwork
from CVAE_module import CVAE

# ----------------------------------------------------------------
# 1. 閰嶇疆涓庣幆澧?
# ----------------------------------------------------------------
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 璺緞閰嶇疆 (璇风‘淇濊矾寰勬纭?
TEST_DATA_PATH = os.path.join(SCRIPT_DIR, "dataset used for training", "test.xlsx")
FORWARD_MODEL_PATH = os.path.join(SCRIPT_DIR, "forward_gnn_checkpoints", "forward_gnn_2.pth")
INVERSE_MODEL_PATH = os.path.join(SCRIPT_DIR, "cvae_checkpoints", "cvae_0.pth")

# 銆愭牳蹇冧慨澶嶃€戞洿绋冲仴鐨勭粯鍥鹃鏍艰缃?
try:
    plt.style.use('seaborn-v0_8-whitegrid')  # 鏂扮増 Matplotlib 鍐欐硶
except OSError:
    try:
        plt.style.use('seaborn-whitegrid')  # 鏃х増 Matplotlib 鍐欐硶
    except OSError:
        print("Warning: 'seaborn' style not found, using default style.")
        # 榛樿椋庢牸锛屼笉鍋氭搷浣?

# 璁剧疆瀛椾綋锛岄槻姝腑鏂囨垨鐗规畩绗﹀彿涔辩爜 (鍙€?
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False


# ----------------------------------------------------------------
# 2. 鏁版嵁鍔犺浇宸ュ叿
# ----------------------------------------------------------------
def load_test_data(excel_path):
    print(f"Loading Test Data from {excel_path}...")
    columns = [
        "V1a", "V1v", "V1c", "w",
        "relativeVolume", "relativeArea", "thickness", "poreDiameter", "areaMean",
        "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10",
        "s11", "s12", "s13", "s14", "s15", "s16", "s17", "s18", "s19", "s20"
    ]

    dfs = []
    # 灏濊瘯璇诲彇鎵€鏈夊彲鑳界殑 sheet
    for sheet in ['class1', 'class2', 'class12']:
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet, names=columns)
            dfs.append(df)
        except:
            pass

    if not dfs:
        raise ValueError("No data loaded! Check excel path and sheet names.")

    df_all = pd.concat(dfs, axis=0).reset_index(drop=True)

    # X: Curves (Condition) - 鍚庨潰20鍒?
    X_curve = df_all.iloc[:, 9:].values.astype(np.float32)
    # Y: Params (Ground Truth) - 鍓?鍒?(浠呯敤浜庣粯鍥惧弬鑰冿紝鎺ㄧ悊鏃朵笉鐢?
    y_param = df_all.iloc[:, :9].values.astype(np.float32)

    print(f"Loaded {len(X_curve)} test samples.")
    return X_curve, y_param


# ----------------------------------------------------------------
# 3. 妯″瀷鍔犺浇宸ュ叿
# ----------------------------------------------------------------
def load_models():
    print("Loading Models...")

    # --- 鍔犺浇鍓嶅悜妯″瀷 (楠岃瘉鍣? ---
    # 蹇呴』涓?train_forward_gnn.py 涓殑閰嶇疆涓€鑷?
    forward_net = GNNForwardNetwork(
        units_layer1=512, units_layer2=256, units_layer3=128, units_layer4=64,
        gnn_hidden_dim=256, gnn_heads=8, dropout_rate=0.0
    ).to(device)

    try:
        fwd_checkpoint = torch.load(FORWARD_MODEL_PATH, map_location=device, weights_only=False)
        forward_net.load_state_dict(fwd_checkpoint['model_state_dict'])
        forward_net.eval()
        print(f"Forward model loaded from {FORWARD_MODEL_PATH}")
    except Exception as e:
        print(f"Error loading Forward Model: {e}")
        return None, None, None, None

    # 鑾峰彇璁粌鏃剁殑 Scaler
    scaler_curve = fwd_checkpoint['scaler_y']  # 鍓嶅悜鐨?Y 鏄洸绾?
    scaler_param = fwd_checkpoint['scaler_x']  # 鍓嶅悜鐨?X 鏄弬鏁?

    # --- 鍔犺浇 C-VAE (鐢熸垚鍣? ---
    # 蹇呴』涓?train_inverse_cvae.py 涓殑閰嶇疆涓€鑷?(latent_dim=4, hidden_dim=512)
    cvae_net = CVAE(param_dim=9, curve_points=20, latent_dim=4, hidden_dim=512).to(device)

    try:
        inv_checkpoint = torch.load(INVERSE_MODEL_PATH, map_location=device, weights_only=False)
        cvae_net.load_state_dict(inv_checkpoint['model_state'])
        cvae_net.eval()
        print(f"Inverse model loaded from {INVERSE_MODEL_PATH}")
    except Exception as e:
        print(f"Error loading C-VAE Model: {e}")
        return None, None, None, None

    return forward_net, cvae_net, scaler_curve, scaler_param


# ----------------------------------------------------------------
# 4. 缁樺浘鍑芥暟 (瀹屾暣鐗?
# ----------------------------------------------------------------
def plot_results(target_curves, designed_curves, gen_params, true_params):
    print("Plotting results...")
    # 闅忔満鎶藉彇 9 涓牱鏈繘琛屽睍绀?(3x3 缃戞牸)
    num_plots = 9
    indices = np.random.choice(len(target_curves), num_plots, replace=False)

    fig, axes = plt.subplots(3, 3, figsize=(18, 12))
    fig.suptitle('Inverse Design Validation: Target vs Designed Curves', fontsize=16)

    # 搴斿彉杞?(0% - 25%)
    x_axis = np.linspace(0, 25, 21)

    # 鏁版嵁鑼冨洿鐢ㄤ簬璁＄畻鍗曚釜鏍锋湰鐨?NRMSE
    data_range = np.max(target_curves) - np.min(target_curves)

    for i, idx in enumerate(indices):
        row = i // 3
        col = i % 3
        ax = axes[row, col]

        # 鏋勯€犳洸绾?(琛ヤ笂鍘熺偣 0,0)
        t_curve = np.concatenate(([0], target_curves[idx]))
        d_curve = np.concatenate(([0], designed_curves[idx]))

        # 璁＄畻璇ユ牱鏈殑璇樊
        mse = np.mean((t_curve - d_curve) ** 2)
        nrmse = (np.sqrt(mse) / data_range) * 100

        # 缁樺浘
        ax.plot(x_axis, t_curve, 'k-', linewidth=2.5, label='Target (Goal)')
        ax.plot(x_axis, d_curve, 'r--', linewidth=2, marker='o', markersize=4, label='Designed (AI)')

        # 鏍囨敞淇℃伅
        ax.set_title(f'Sample {idx} | NRMSE: {nrmse:.2f}%', fontsize=12)
        ax.set_xlabel('Strain (%)')
        ax.set_ylabel('Stress (kPa)')
        ax.grid(True, linestyle=':', alpha=0.6)
        if i == 0: ax.legend()  # 鍙湪绗竴涓浘鏄剧ず鍥句緥

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])  # 璋冩暣甯冨眬鐣欏嚭鏍囬绌洪棿

    save_path = 'inverse_design_final_result.png'
    plt.savefig(save_path, dpi=300)
    print(f"Visualization saved to: {os.path.abspath(save_path)}")


# ----------------------------------------------------------------
# 5. 涓婚€昏緫锛氶噰鏍?-> 浼橀€?-> 璇勪及 -> 缁樺浘
# ----------------------------------------------------------------
def evaluate_design_with_diversity(num_samples=50):
    # 1. 鍑嗗
    curves_raw, true_params = load_test_data(TEST_DATA_PATH)
    forward_model, cvae_model, scaler_curve, scaler_param = load_models()

    if forward_model is None: return

    # 鍑嗗鍏ㄨ繛鎺ュ浘 (鐢ㄤ簬鍓嶅悜楠岃瘉)
    adj = torch.ones((9, 9), dtype=torch.float32).to(device)

    # 棰勫鐞嗘洸绾?(Condition)
    # 娉ㄦ剰锛欳-VAE 鍜?Forward 搴旇浣跨敤鐩稿悓鐨?Scaler
    curves_scaled = scaler_curve.transform(curves_raw)
    curves_tensor = torch.tensor(curves_scaled).to(device)

    num_test = len(curves_raw)
    best_pred_curves = []  # 瀛樺偍浼橀€夊悗鐨勯娴嬫洸绾?
    best_gen_params = []  # 瀛樺偍浼橀€夊悗鐨勭粨鏋勫弬鏁?
    diversity_scores = []  # 瀛樺偍澶氭牱鎬у垎鏁?

    print(f"\nStarting Optimization: Generating {num_samples} candidates per target...")

    # 2. 寰幆澶勭悊姣忎釜娴嬭瘯鏍锋湰
    with torch.no_grad():
        for i in tqdm(range(num_test)):
            # A. 澶嶅埗鐩爣 N 浠?
            target_curve_tensor = curves_tensor[i].unsqueeze(0)  # (1, 20)
            target_repeated = target_curve_tensor.repeat(num_samples, 1)  # (N, 20)

            # B. C-VAE 閲囨牱鐢熸垚 N 涓€欓€夌粨鏋?
            # 閲囨牱 N 涓笉鍚岀殑闅忔満鍣０ z
            z = torch.randn(num_samples, 4).to(device)  # latent_dim=4
            gen_params_scaled = cvae_model.inference(target_repeated, z=z)  # (N, 9)

            # --- 璁＄畻澶氭牱鎬?(Diversity) ---
            # 璁＄畻鐢熸垚鐨?N 涓弬鏁扮殑鏍囧噯宸潎鍊?
            # 濡傛灉妯″瀷鍧嶅锛宻td 浼氳秼杩戜簬 0
            diversity = torch.mean(torch.std(gen_params_scaled, dim=0)).item()
            diversity_scores.append(diversity)

            # C. 鍓嶅悜妯″瀷蹇€熻瘎浼?(Proxy Evaluation)
            # 鎵╁睍 adj 浠ュ尮閰?batch
            batch_adj = adj.unsqueeze(0).repeat(num_samples, 1, 1)
            pred_curves_scaled = forward_model(gen_params_scaled, batch_adj)  # (N, 20)

            # D. 浼橀€?(Ranking)
            # 璁＄畻 N 涓€欓€夋洸绾夸笌鐩爣鏇茬嚎鐨?MSE
            diff = pred_curves_scaled - target_repeated
            mse_scores = torch.mean(diff ** 2, dim=1)  # (N, )

            # 鎵惧埌璇樊鏈€灏忕殑閭ｄ釜绱㈠紩
            best_idx = torch.argmin(mse_scores).item()

            # E. 璁板綍鏈€浣崇粨鏋?(鍙嶅綊涓€鍖?
            # 鍙栧嚭鏈€浣崇殑鍙傛暟鍜屾洸绾?
            best_p_scaled = gen_params_scaled[best_idx].cpu().numpy().reshape(1, -1)
            best_c_scaled = pred_curves_scaled[best_idx].cpu().numpy().reshape(1, -1)

            best_gen_params.append(scaler_param.inverse_transform(best_p_scaled))
            best_pred_curves.append(scaler_curve.inverse_transform(best_c_scaled))

    # 鎷兼帴鎵€鏈夋渶浣崇粨鏋?
    final_pred_curves = np.concatenate(best_pred_curves, axis=0)
    final_gen_params = np.concatenate(best_gen_params, axis=0)

    # ----------------------------------------------------------------
    # 6. 鏈€缁堟寚鏍囪绠?
    # ----------------------------------------------------------------
    mse = np.mean((curves_raw - final_pred_curves) ** 2)
    mae = np.mean(np.abs(curves_raw - final_pred_curves))

    # NRMSE 璁＄畻
    data_range = np.max(curves_raw) - np.min(curves_raw)
    rmse = np.sqrt(mse)
    nrmse = (rmse / data_range) * 100

    avg_diversity = np.mean(diversity_scores)

    print(f"\n{'=' * 40}")
    print(f"FINAL EVALUATION REPORT (Sampling N={num_samples})")
    print(f"{'=' * 40}")
    print(f"Design NRMSE : {nrmse:.2f}%  (Target: < 2.49%)")
    print(f"Design MAE   : {mae:.4f} kPa")
    print(f"Diversity    : {avg_diversity:.4f} (Higher is better, >0.01 is good)")
    print(f"{'=' * 40}")

    if nrmse < 2.49:
        print(">>> SUCCESS: Model outperforms the paper baseline! <<<")
    else:
        print(">>> Result is close. Try increasing num_samples (e.g., 100). <<<")

    # 7. 缁樺浘
    plot_results(curves_raw, final_pred_curves, final_gen_params, true_params)


if __name__ == '__main__':
    evaluate_design_with_diversity(num_samples=5000)  #
    # 浣跨敤 5000 娆￠噰鏍
