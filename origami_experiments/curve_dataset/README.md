# Origami force-displacement curve dataset

这个目录用于构造新的数据集：

```text
原始 8 个参数 -> 多工况力-位移响应曲线
```

核心思路参考 GraphMetaMat：物理上做完整加载响应，进入机器学习数据集时保存为固定长度的离散曲线数组。这里不再把 30%/60%/90% 展开状态下的轴向/弯曲响应压缩成 6 个刚度标量，而是保留每个加载步的力和位移。

## 数据定义

输入参数仍保持原始数据集的 8 列：

```text
pattern, m, n, tcrease, tpanel, W, creaseE, panelE
```

每个样本输出 6 条曲线：

| curve_id | load_case | deployment | response_axis |
|---:|---|---:|---|
| 0 | bending | 0.3 | z |
| 1 | bending | 0.6 | z |
| 2 | bending | 0.9 | z |
| 3 | axial | 0.3 | x |
| 4 | axial | 0.6 | x |
| 5 | axial | 0.9 | x |

默认每条曲线采样 30 个加载步，所以一个样本的曲线响应为：

```text
force_raw:        [N, 6, 30]
y_raw:            [N, 6, 30]      # displacement magnitude
curve_raw:        [N, 6, 30, 2]   # [displacement, force]
y:                [N, 180]        # 标准化后的模型目标，按 [condition, step] 展平
```

注意：SWOMPS 原脚本使用的是 NR 力加载。这里的曲线是“逐步增加外力，记录平均位移”的力-位移曲线；力是加载控制量，位移是结构响应。相比原来的刚度标量，它保留了完整非线性加载路径信息。若后续要完全复刻 GraphMetaMat 的位移控制压缩逻辑，需要把 MATLAB 控制器替换为位移边界/压缩板接触仿真。

## 运行流程

1. 生成参数表和仿真任务表：

```powershell
python F:\small++\origami_experiments\curve_dataset\prepare_curve_jobs.py --curve-points 30
```

输出：

```text
F:\small++\origami_experiments\curve_dataset\jobs\parameters.csv
F:\small++\origami_experiments\curve_dataset\jobs\simulation_jobs.csv
F:\small++\origami_experiments\curve_dataset\jobs\condition_schema.csv
F:\small++\origami_experiments\curve_dataset\jobs\dataset_spec.json
```

小规模试跑可以先用：

```powershell
python F:\small++\origami_experiments\curve_dataset\prepare_curve_jobs.py --sample-count 20 --curve-points 30
```

2. 在 MATLAB 中运行 SWOMPS 曲线导出。

先确保 `OrigamiSimulator` / SWOMPS 已经下载，并且里面能找到：

```text
OrigamiSolver
ControllerNRLoading
GenerateMiuraSheet
GenerateTMPSheet
```

然后在 MATLAB 中执行：

```matlab
addpath("F:\small++\origami_experiments\curve_dataset\matlab")

GenerateOrigamiForceDisplacementCurves( ...
    "F:\small++\origami_experiments\curve_dataset\jobs\parameters.csv", ...
    "F:\small++\origami_experiments\curve_dataset\raw_curves", ...
    "SimulatorRoot", "D:\path\to\OrigamiSimulator", ...
    "CurvePoints", 30, ...
    "StartIndex", 1, ...
    "EndIndex", 20)
```

每个样本会生成一个 CSV：

```text
F:\small++\origami_experiments\curve_dataset\raw_curves\miura_00001.csv
```

CSV 字段：

```text
sample_id, curve_id, load_case, deployment, response_axis, step,
force, displacement, signed_force, signed_displacement, converged
```

3. 打包为模型可读的 `.npz`：

```powershell
python F:\small++\origami_experiments\curve_dataset\build_curve_dataset_npz.py --allow-partial
```

输出：

```text
F:\small++\origami_experiments\curve_dataset\data\origami_curve_train.npz
F:\small++\origami_experiments\curve_dataset\data\origami_curve_test.npz
F:\small++\origami_experiments\curve_dataset\data\scaler_x.pkl
F:\small++\origami_experiments\curve_dataset\data\scaler_y.pkl
```

## 推荐实验设置

第一轮不要直接全量跑 4000 个样本。建议：

1. 先跑 `20` 个样本，确认曲线无 NaN、无不收敛、曲线形状合理。
2. 再跑 `200-500` 个样本，训练一个 forward Transformer/MLP 验证可学习性。
3. 最后扩大到全量，并保留 `group_pattern_mn` 或 `extrapolate_high_W` 作为更像论文的泛化测试。

打包时可切换 split：

```powershell
python F:\small++\origami_experiments\curve_dataset\build_curve_dataset_npz.py --allow-partial --split group_pattern_mn
python F:\small++\origami_experiments\curve_dataset\build_curve_dataset_npz.py --allow-partial --split extrapolate_high_W
```
