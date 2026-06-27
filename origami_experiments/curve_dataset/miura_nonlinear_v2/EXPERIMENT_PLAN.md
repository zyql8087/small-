# Miura Nonlinear V2 全量仿真实验计划书

## 1. 实验目标

对 2000 个 Miura 折纸设计样本执行带物理量的大载荷非线性力-位移仿真，生成完整数据集用于机器学习模型训练。

## 2. 数据概况

| 项目 | 值 |
|------|-----|
| 总样本数 | 2000 |
| 每样本工况数 | 6 (bending×3 + axial×3) |
| 每工况载荷步数 | 80 |
| 每样本输出行数 | 480 (6×80) |
| 总输出行数 | 960,000 |
| CSV 列数 | 21 |

### 2.1 输入参数空间

| 参数 | 范围 | 说明 |
|------|------|------|
| pattern | 1 (固定) | Miura pattern |
| m | {24, 30, 36} | 3 档，共 692/670/638 个样本 |
| n | {6, 9, 12} | 3 档 |
| tcrease | [0.0005, 0.001] | 折痕厚度，连续均匀 |
| tpanel | [0.001, 0.006] | 面板厚度，连续均匀 |
| W | [0.001, 0.004] | 折痕宽度，连续均匀 |
| creaseE | [1.0e9, 5.0e9] | 折痕弹性模量，连续均匀 |
| panelE | [1.0e9, 5.0e9] | 面板弹性模量，连续均匀 |

### 2.2 (m, n) 组合分布

| m\n | 6 | 9 | 12 |
|-----|---|---|----|
| 24 | 213 | 243 | 236 |
| 30 | 241 | 225 | 204 |
| 36 | 217 | 217 | 204 |

### 2.3 输出 CSV 列

```
sample_id, curve_id, load_case, deployment, response_axis, step,
force, displacement, signed_force, signed_displacement, converged,
strain_energy_total, strain_energy_crease, strain_energy_panel,
max_bar_stress, max_bar_strain, max_crease_moment, max_crease_rotation,
final_load, reference_stiffness, target_linear_displacement
```

## 3. 仿真配置

| 参数 | 值 | 说明 |
|------|-----|------|
| FinalLoadMode | stiffness_scaled | 根据线性刚度自适应载荷 |
| TargetLinearDisplacement | 0.015 | 目标线性位移 (m) |
| MaxFinalLoad | 10000 | 载荷上限 (N) |
| CurvePoints | 80 | 每工况载荷步数 |
| RequireMiuraOnly | true | 仅 Miura pattern |
| RequirePhysics | true | 要求物理量字段完整 |
| NR tol | 1e-7 | Newton-Raphson 收敛容差 |

## 4. 预期输出

### 4.1 目录结构

```
miura_nonlinear_v2/
├── raw_curves/          ← 2000 个 CSV (miura_00001.csv ~ miura_002000.csv)
├── logs/                ← 批处理日志
├── smoke_results/       ← 审计报告 + 图表 + 烟雾训练结果
├── data/                ← 最终 NPZ 打包输出
│   ├── origami_curve_train.npz
│   ├── origami_curve_test.npz
│   ├── scaler_x.pkl
│   ├── scaler_y.pkl
│   ├── train_samples.csv
│   ├── test_samples.csv
│   └── metadata.json
└── failures.log         ← 失败记录 (预期为空)
```

### 4.2 NPZ 打包内容

| 键 | 形状 | 说明 |
|----|------|------|
| X | (N, 8) | 标准化后的输入参数 |
| y | (N, 480) | 标准化后的位移曲线 (6×80 展平) |
| X_raw | (N, 8) | 原始输入参数 |
| y_raw | (N, 6, 80) | 原始位移 |
| force_raw | (N, 6, 80) | 原始力 |
| curve_raw | (N, 6, 80, 2) | [displacement, force] |
| physics_raw | (N, 6, 80, 7) | 7 个物理量 |
| converged | (N, 6, 80) | 收敛标记 |

## 5. 执行步骤

### 5.1 环境检查

```powershell
# 确认 MATLAB 可执行
Test-Path "F:\Polyspace\R2020b\bin\matlab.exe"

# 确认参数表存在
Test-Path "F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\jobs_miura\parameters.csv"

# 确认 OrigamiSimulator 存在
Test-Path "F:\small++\external\OrigamiSimulator"

# 确认 Python 环境
F:\Anaconda\envs\GMM\python.exe --version
```

### 5.2 全量仿真

分 4 批执行，每批 500 个样本，便于中间检查和故障恢复：

```powershell
# 批次 1: 样本 1-500
powershell -NoProfile -ExecutionPolicy Bypass -File `
  F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\scripts\run_swomps_miura_nonlinear_batch.ps1 `
  -StartIndex 1 -EndIndex 500 -CurvePoints 80 `
  -TargetLinearDisplacement 0.015 -MaxFinalLoad 10000

# 批次 2: 样本 501-1000
powershell -NoProfile -ExecutionPolicy Bypass -File `
  F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\scripts\run_swomps_miura_nonlinear_batch.ps1 `
  -StartIndex 501 -EndIndex 1000 -CurvePoints 80 `
  -TargetLinearDisplacement 0.015 -MaxFinalLoad 10000

# 批次 3: 样本 1001-1500
powershell -NoProfile -ExecutionPolicy Bypass -File `
  F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\scripts\run_swomps_miura_nonlinear_batch.ps1 `
  -StartIndex 1001 -EndIndex 1500 -CurvePoints 80 `
  -TargetLinearDisplacement 0.015 -MaxFinalLoad 10000

# 批次 4: 样本 1501-2000
powershell -NoProfile -ExecutionPolicy Bypass -File `
  F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\scripts\run_swomps_miura_nonlinear_batch.ps1 `
  -StartIndex 1501 -EndIndex 2000 -CurvePoints 80 `
  -TargetLinearDisplacement 0.015 -MaxFinalLoad 10000
```

> **注意**：脚本支持断点续跑。已存在的 CSV 会被 `[SKIP]` 跳过。如果某批中断，重新运行相同命令即可从断点继续。

### 5.3 中间审计（每批完成后）

```powershell
# 审计前 500 个样本
F:\Anaconda\envs\GMM\python.exe `
  F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\scripts\audit_curve_batch.py `
  --job-dir F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\jobs_miura `
  --curves-dir F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\raw_curves `
  --output-dir F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\smoke_results `
  --curve-points 80 `
  --expected-samples 500 `
  --audit-mode nonlinear `
  --min-mean-secant-change-ratio 0.08 `
  --min-max-secant-change-ratio 0.25 `
  --min-mean-linearity-error 0.08

# 审计前 1000 个样本 (累加)
# ... --expected-samples 1000

# 审计前 1500 个样本
# ... --expected-samples 1500

# 审计全部 2000 个样本
# ... --expected-samples 2000
```

**审计关注指标**：

| 指标 | 阈值 | 含义 |
|------|------|------|
| issues_count | = 0 | 无结构性问题 |
| rel_stiff_error.mean | < 0.3 | 割线刚度与线性刚度的平均偏差 |
| secant_change_ratio.mean | > 0.08 | 平均非线性程度 |
| max_linearity_error.mean | > 0.08 | 平均线性偏离程度 |
| failures.log | 为空 | 无仿真失败 |

### 5.4 绘图抽查（每批完成后）

```powershell
# 抽查 3 个样本的力-位移曲线
F:\Anaconda\envs\GMM\python.exe `
  F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\scripts\plot_miura_nonlinear_curves.py `
  --job-dir F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\jobs_miura `
  --curves-dir F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\raw_curves `
  --output-dir F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\smoke_results `
  --max-samples 5
```

**目视检查**：
- 曲线是否光滑（无震荡）
- 非线性曲线是否明显偏离线性参考线
- 不同 deployment 下曲线形态是否合理

### 5.5 全量打包

```powershell
F:\Anaconda\envs\GMM\python.exe `
  F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\scripts\build_curve_dataset_npz.py `
  --job-dir F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\jobs_miura `
  --curves-dir F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\raw_curves `
  --output-dir F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\data `
  --split group_pattern_mn `
  --test-size 0.2 `
  --seed 42 `
  --curve-points 80 `
  --allow-partial
```

**划分策略选择**：

| 策略 | 命令参数 | 适用场景 |
|------|---------|---------|
| 随机划分 | `--split random` | 基线实验 |
| 按几何分组 | `--split group_pattern_mn` | **推荐**，确保测试集覆盖所有 (m,n) 组合 |
| W 外推 | `--split extrapolate_high_W` | 测试泛化到未见折痕宽度 |

### 5.6 烟雾训练验证

```powershell
F:\Anaconda\envs\GMM\python.exe `
  F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\scripts\smoke_train_curve_dataset.py `
  --data-dir F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\data `
  --result-dir F:\small++\origami_experiments\curve_dataset\miura_nonlinear_v2\smoke_results `
  --epochs 300 `
  --batch-size 16 `
  --hidden-dim 256 `
  --lr 1e-3 `
  --seed 42
```

**验收标准**：

| 指标 | 预期 | 说明 |
|------|------|------|
| forward train_mse_reduction_ratio | > 0.5 | 正向模型有效学习 |
| forward test_mse | < train_mse × 2 | 无严重过拟合 |
| inverse train_mse_reduction_ratio | > 0.3 | 逆向模型有效学习 |

## 6. 故障处理

### 6.1 单样本失败

- `[FAIL]` 消息会打印到控制台，详情写入 `failures.log`
- 失败样本不阻塞后续样本
- 打包时使用 `--allow-partial` 跳过失败样本

### 6.2 批次中断

- 直接重新运行相同命令，已存在的 CSV 自动跳过
- 检查 `failures.log` 确认无持续性错误

### 6.3 物理量缺失

- `RequirePhysics=true` 时，SWOMPS 历史属性缺失或含 NaN 会立即报错
- 如遇 SWOMPS 版本不兼容，可临时设 `RequirePhysics=false` 降级运行

### 6.4 大结构仿真缓慢

- m=36, n=12 的样本节点数最多，仿真时间最长
- 如个别样本超时，可记录其 sample_id 后单独补跑

## 7. 预期时间估算

| m 值 | 节点数 (约) | 每样本约 | 样本数 | 小计 |
|------|------------|---------|--------|------|
| 24 | ~600 | 2-3 min | 692 | 23-35 hr |
| 30 | ~900 | 4-6 min | 670 | 45-67 hr |
| 36 | ~1300 | 8-12 min | 638 | 85-128 hr |
| **合计** | | | **2000** | **150-230 hr** |

> 以上为单 MATLAB 进程估算。如使用 `parfor` 并行或在多台机器上分批运行可显著缩短。

## 8. 质量检查清单

- [ ] 环境检查通过
- [ ] 批次 1 (1-500) 完成，审计 0 issues
- [ ] 批次 2 (501-1000) 完成，审计 0 issues
- [ ] 批次 3 (1001-1500) 完成，审计 0 issues
- [ ] 批次 4 (1501-2000) 完成，审计 0 issues
- [ ] 全量审计通过 (2000 samples, 0 issues)
- [ ] 力-位移曲线目视抽查正常
- [ ] NPZ 打包完成 (group_pattern_mn 划分)
- [ ] 烟雾训练指标达标
- [ ] failures.log 为空
- [ ] data/ 目录包含完整输出文件
