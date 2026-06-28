# small++ — 折纸（Origami / Miura）力学超材料代理建模与逆向设计

用深度学习给**折纸超材料结构**做「正向性能预测 + 逆向参数设计」的研究项目：

- **正向 (Forward)**：由折纸设计/材料参数预测力学响应（刚度标量，或完整力-位移曲线）。
- **逆向 (Inverse)**：由目标力学响应反推设计参数，并用正向代理模型对候选参数排序 / 做闭环一致性校验。

---

## 1. 项目来历

本项目原是 `F:\TPMS`（TPMS 三周期极小曲面项目）下的折纸扩展实验，于 **2026-06-29 拆分独立**，迁出为 `F:\small++` 并单独建立 git 仓库。

它与 TPMS **共用同一套模型架构家族**（GAT 图网络、参数 Transformer、CVAE、条件扩散、ResNet/ResMLP），只是把这套架构迁移到折纸数据上——TPMS 处理「9 参数 ↔ 20 点应力曲线」，本项目处理「8 参数 ↔ 6 刚度」乃至「8 参数 ↔ 力-位移全曲线」。两者现已是**完全独立的两个仓库**，无代码依赖。

> 项目代号 `small++` 取自目标期刊 *Small*（折纸论文 `smll202500634`）。

---

## 2. 任务与数据定义

折纸天篷（canopy）刚度任务：

| 组 | 列 | 含义 |
| --- | --- | --- |
| **输入参数 (8)** | `pattern, m, n, tcrease, tpanel, W, creaseE, panelE` | `pattern` 1=Miura / 2=TMP；`m∈{24,30,36}`、`n∈{6,9,12}` 为离散类别；其余连续；`creaseE/panelE ∈ [1e9, 5e9] Pa` |
| **输出目标 (6)** | `bendstiff30/60/90, axialstiff30/60/90` | 30%/60%/90% 展开率下的弯曲与轴向刚度，量级 `10²~1.4×10⁶` |

进阶任务（`curve_dataset/`，建设中）：保留每个加载步的**力-位移非线性曲线**（6 工况 × T 步 × [位移, 力]），而非压缩成 6 个刚度标量。

---

## 3. 数据来源（依赖 SWOMPS）

本项目**不自带原始仿真器**，数据来自 `external/` 下的两个上游项目（作者 Yi Zhu & E. T. Filipov）：

- **`external/OrigamiSimulator/`** — **SWOMPS**：MATLAB 写的 bar-and-hinge 多物理折纸仿真器（牛顿-拉夫森、位移控制、电热自折叠、面板接触、热传导）。是所有折纸数据的物理引擎。完整源码需按其 README 自行下载：<https://github.com/zzhuyii/OrigamiSimulator>
- **`external/GenerateOrigamiDataSet/`** — 用 SWOMPS 批量生成的折纸性能数据库。本项目**实际使用其中的 MaterialProperty 版 Origami Sheet 数据**：
  - `Data_Origami_Sheet_MaterialProperty/Miura/MiuraSheetMat.txt`（2000 样本）
  - `Data_Origami_Sheet_MaterialProperty/TMP/TMPSheetMat.txt`（2000 样本）
  - 每行 14 列 = 8 输入 + 6 刚度，逗号分隔，**无表头**。
  - 论文参考：Zhu & Filipov, 2022, *Harnessing Interpretable Machine Learning for Origami Feature Design and Pattern Selection*（arXiv:2204.07235）。

> ⚠️ `external/` 默认被 `.gitignore` 忽略（属第三方、含自带 `.git`、体积大）。克隆本仓库后需把 `external/GenerateOrigamiDataSet` 与 `external/OrigamiSimulator` 重新放回原位，否则 `prepare_data.py` 与曲线仿真无法找到数据/仿真器。

数据流向：

```text
SWOMPS (MATLAB)  →  GenerateOrigamiDataSet/*.txt  →  prepare_data.py  →  data/origami_{train,test}.npz  →  训练/评估
                                                  └→（曲线版）prepare_curve_jobs.py → MATLAB → raw_curves/*.csv → build_curve_dataset_npz.py → *.npz
```

---

## 4. 目录结构

```text
F:\small++\
├── README.md                       # ← 本文件
├── .gitignore
├── origami_experiments/            # 折纸 ML 实验主体
│   ├── prepare_data.py             # external/*.txt → data/origami_{train,test}.npz (+ scaler_*.pkl)
│   ├── prepare_validation_splits.py# 论文式划分：random / group_pattern_mn / extrapolate_high_W
│   ├── modules/                    # 5 种架构的折纸版 + taskfit 版 + 曲线版
│   ├── train_forward_gnn.py        # 正向 GAT (8→6)
│   ├── train_forward_transformer.py# 正向 Transformer (8→6)
│   ├── train_inverse_resnet.py     # 逆向 ResNet1D (6→8)
│   ├── train_inverse_cvae.py       # 逆向 CVAE (6→8)
│   ├── train_inverse_diffusion.py  # 逆向扩散 (6→8)
│   ├── train_taskfit.py            # 【推荐】任务适配训练：离散变量分类化 + 闭环一致性
│   ├── evaluate_all.py             # 基础 5 模型统一评估
│   ├── evaluate_taskfit.py         # taskfit 评估（含逐参数 R²、闭环刚度还原）
│   ├── evaluate_all_final_models.py# 最终模型综合评估
│   ├── data/                       # 生成的 .npz + scaler（.npz 默认被 gitignore）
│   ├── checkpoints*/  results*/  *_grid/  *_round*/  split_diff_*/   # 各轮训练/调参产物
│   ├── curve_dataset/              # 力-位移全曲线数据集管线（见其 README / EXPERIMENT_PLAN）
│   │   └── miura_nonlinear_v2/     # 2000 样本 × 6 工况 × 80 步 + 物理量 的全量计划
│   └── 实验总结报告.md             # 第一版（朴素连续回归）实验中文报告 + 结果
├── external/                       # 第三方上游（gitignore）：SWOMPS + 数据生成器
├── output/                         # 论文产物：Miura 文档、图、PDF（含 small++.docx）
└── evidence/                       # 运行截图与日志（历史记录，含旧 F:\TPMS 路径）
```

---

## 5. 环境与依赖

推荐 Python 3.10/3.11 + CUDA（CPU 也能跑，训练慢）。原训练环境为 `F:\Anaconda\envs\GMM`。

**核心依赖**（与 TPMS 一致，外加 `joblib`）：

```text
numpy  pandas  scikit-learn  matplotlib  torch>=2.2  torch-geometric>=2.5
networkx  tqdm  openpyxl  joblib
```

```powershell
# 示例（按本机 CUDA/Python 版本选择匹配的 torch / torch-geometric 轮子）
pip install numpy pandas scikit-learn matplotlib torch torch-geometric networkx tqdm openpyxl joblib
```

**可选**（仅出报告/PPT 时需要）：`python-pptx`（`generate_ppt.py`）、`reportlab`（`curve_dataset/generate_curve_dataset_report_pdf.py`）、`python-docx`（实验报告 docx）。

**数据生成**（仅重新生成曲线数据集时需要）：MATLAB + 下载好的 SWOMPS（`external/OrigamiSimulator`）。

---

## 6. 如何跑

> 所有脚本用 `Path(__file__)` 解析相对路径，可在任意工作目录下用完整脚本路径调用；以下命令以 `F:\small++` 为根。

### 管线 A：刚度任务（8→6，主线、完整可复现）

```powershell
# 1) 制备数据：读取 external/*.txt → data/origami_{train,test}.npz + scaler_*.pkl
python origami_experiments\prepare_data.py

# 2) 训练 —— 方式 ① 推荐：taskfit（离散变量分类化 + log 刚度 + 闭环一致性）
#    默认依次训练 forward_resmlp → inverse_resmlp → forward_gat → inverse_cvae
python origami_experiments\train_taskfit.py
#    可选更多 stage / 图结构：
python origami_experiments\train_taskfit.py --stages forward_gat inverse_cvae --gat_graph physical_sparse

#    训练 —— 方式 ② 基础五件套（朴素连续回归，对照用）
python origami_experiments\train_forward_gnn.py
python origami_experiments\train_forward_transformer.py
python origami_experiments\train_inverse_resnet.py
python origami_experiments\train_inverse_cvae.py
python origami_experiments\train_inverse_diffusion.py

# 3) 评估
python origami_experiments\evaluate_taskfit.py      # taskfit：逐参数 R² + 闭环刚度还原（参数见 --help）
python origami_experiments\evaluate_all.py          # 基础五件套统一评估

# 4) （可选）论文式更严格划分：未见 (m,n) 结构族 / W 外推
python origami_experiments\prepare_validation_splits.py --split group_pattern_mn
```

默认产物：`origami_experiments/data/`（npz+scaler）、`checkpoints_taskfit/`（权重）、`results_taskfit/`（指标与曲线）。

### 管线 B：力-位移全曲线任务（建设中，需 MATLAB + SWOMPS）

```powershell
# 1) 生成参数表与仿真任务表
python origami_experiments\curve_dataset\prepare_curve_jobs.py --sample-count 20 --curve-points 30

# 2) 在 MATLAB 中运行 SWOMPS 曲线导出（详见 curve_dataset/README.md）
#    需先下载 OrigamiSimulator 并放到 external/ 下

# 3) 打包为 .npz
python origami_experiments\curve_dataset\build_curve_dataset_npz.py --allow-partial

# 4) 烟雾训练验证
python origami_experiments\curve_dataset\smoke_train_curve_dataset.py
```

全量非线性 v2 计划（2000 样本、6 工况、80 步、含物理量）见
`origami_experiments/curve_dataset/miura_nonlinear_v2/EXPERIMENT_PLAN.md`。

---

## 7. 主要结果（摘要）

**正向**：GAT / Transformer / ResMLP 均能近乎完美预测刚度，**R² > 0.999、NRMSE < 0.4%**。

**逆向**（taskfit 版，测试集 N=800）：

| 指标 | Inverse ResMLP | Inverse CVAE (best-of-50) |
| --- | --- | --- |
| pattern 准确率 | 1.000 | 1.000 |
| n 准确率 | 0.999 | 0.994 |
| m 准确率 | 0.908 | 0.839 |
| 连续参数整体 R² | 0.886 | 0.822 |
| **闭环刚度 R²** | 0.9948 | **0.9990（NRMSE 0.35%）** |

核心结论：逆问题存在**一对多**（不同几何×材料组合产生几乎相同刚度），单参数难以唯一反推；但把离散变量当分类、并以「逆→正」**闭环刚度还原**为目标后，逆向设计在闭环意义上接近完美。详见 `origami_experiments/实验总结报告.md`。

---

## 8. git 与 .gitignore 说明

`F:\small++` 为独立 git 仓库。`.gitignore` 忽略大体积 / 可再生产物：

- 模型权重 `*.pth`（约 1.3 GB，全部忽略）、打包数据 `*.npz`、`raw_curves/`
- `__pycache__/`、日志、IDE/OS 文件
- **`external/`**（第三方上游，含自带 `.git`）

如需把 `external/GenerateOrigamiDataSet` 纳入本仓库版本管理，删除 `.gitignore` 中的 `external/` 行并移除其嵌套 `.git` 后再 `git add`。

---

## 9. 参考

- SWOMPS 仿真器：<https://github.com/zzhuyii/OrigamiSimulator>（新版 Sim-FAST：<https://github.com/zzhuyii/Sim-FAST>）
- 折纸数据集：<https://github.com/zzhuyii/GenerateOrigamiDataSet>
- 论文：Y. Zhu, E. T. Filipov, 2022, *Harnessing Interpretable Machine Learning for Origami Feature Design and Pattern Selection*, arXiv:2204.07235
- 架构与逆向设计思想详见母项目 `F:\TPMS`（核心 TPMS 管线）。
