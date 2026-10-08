# simulation_runs_202609 — 仿真排查参考包(2026-09-23 → 09-29)

> 本文件夹收录 2026 年 9 月下旬 Paper A 仿真线的**完整排查与修复记录**,供师弟/师兄/导师参考。
> 报告与 CSV 收录在各实验目录；部分历史 INP/STL 已归档于远端 `bigfiles/`，ODB 保留本地 `audits/` 及桌面交接包。文件身份以实际清单为准。
> 阅读顺序建议:先读本 README 的时间线,再按需进各子目录。

## 当前实验设置（2026-10-08 用户确认，先读这里）

**此后仿真实验统一采用 M09。M08 及更早版本只作历史记录，不作为后续实验设置。仿真实现、求解与排障已全量交师弟。**

- [当前参数与遗留事项](CURRENT_SIMULATION_SETTINGS.md)：M09 基线、M08 历史差异、六个 ODB 身份和验收限制。
- [M09 参数登记](../simulation/abaqus/current_config.json)：Explicit、z 渐变、z 加载、25%、PDE 网格、计划 C3D10 二阶四面体、x/y 周期边界、默认无质量缩放。
- [历史与来源记录](solver_settings_record.json)：M08 实际卡、状态和 ODB 包清单；仅作记录，不是后续建模配置。
- M09 参数选择已确定，执行与结果验收仍须师弟返回证据。本次未找到 M09 验收回传，不声称已经跑通或正在运行。
- 桌面 ODB 包属于 M08，前三个用于 M09 对照；不能将 M09 参数反填到 M08 的既有 ODB。

## 一、时间线与一句话结论

| 日期 | 事件 | 一句话结论 |
|---|---|---|
| 09-23 | 材料排查线 | 作者超弹卡在探针中出现 UNSTABLE;Marlow 对所测单轴数据更贴合，但没有解决 M1/M3 完整窗口求解，不能据此完全排除材料因素 |
| 09-23 | 网格热区治理 | M3 局部治理与 2×2 交叉实验显示材料/网格效应存在交互，四种组合均失败；早期“软化润滑效应坐实”等解释不作为已证实结论 |
| 09-25→27 | M08 显式 z 向 27 例批次 | 3 例覆盖完整 25%、2 例有部分曲线；全程准静态门未通过。与历史曲线的 2.3–5.8 倍差异受方向、边界和动力污染等共同影响，归因未闭合 |
| 09-26 | 师弟 C3D10 回传 | 单个 M2 隐式 C3D10 结果覆盖 24% 窗口；在 s=N 工作假设下比值中位 1.275 vs C3D4 的 1.431；不外推到全域或 Explicit 二阶单元 |
| 09-26→29 | 起步瞬态排查与修复 | STL 微小边／gmsh 极小单元／质量缩放是重点证据链；清洁网格峰值 115.3%→64.3%，仍未通过能量门。PDE 能否消除问题须由 M09 验证 |
| 09-29 | M09 方向确定 | 转向 PDE 网格、计划 C3D10、Explicit、z 加载、目标 x/y 周期边界、默认无质量缩放；工程细节与验收尚待验证 |
| 10-08 | 后续设置统一 | 用户明确：此后只采用 M09；M08 及以前只用于记录。旧 x/Standard 配置归档，当前参数入口切换为 M09 登记 |

## 二、关键数字速查

| 对照 | 数值 | 出处 |
|---|---|---|
| 作者超弹卡失稳边界 | 单轴压缩 <-0.2305 / 双轴拉伸 >0.14 | 01/RESOLUTION §一 |
| Marlow vs poly2 对数据贴合 | 最大偏差 1.07% vs 17.76% | 01/RESOLUTION §七 |
| M3 热区治理死亡点 | 0.0637 → 0.102(+60%) | 02/VALIDATION_REPORT |
| C3D10 vs C3D4 对文献比值 | 1.275 vs 1.431(NRMSE 0.265 vs 0.418) | 05/VERIFICATION_NOTE |
| 起步瞬态(修复前后) | ALLKE/ALLIE 峰值 115.3% → 64.3% | 04/FIX_NOTES |
| M08 完整覆盖／部分覆盖 | 完整 3/26 + 部分 2/26；完整三例能量门均失败；作者经验约25%的分母未明确 | 03/summary_data.json |
| m2_1383 历史曲线对照 | 晚段比值约1.18；c0=c1=c2 但 w 非零，不据此认定完全匀质或 x/z 等价 | 03/SUMMARY.md §二、选样清单 |

## 三、目录索引

```
simulation_runs_202609/
├── README.md                        ← 本文件
├── 01_material_marlow_line/         材料排查:失稳判定、Marlow 认证、M1/M3 验证(结论:材料非控制因素)
│   ├── RESOLUTION_SLOW_SOLVE_20260923.md   ← 根因链+对应性验证总报告(含单元素探针方法)
│   ├── DIAGNOSIS.md                        ← 离线定位报告(节点 97943 局部病态)
│   ├── material_stability_check.py / fit_full_curve.py / stable_refit.py / mesh_quality_analysis.py
│   └── m1m3_marlow_VALIDATION_REPORT.md / EXECUTION_STATE.md
├── 02_hotzone_mesh_treatment/       网格热区治理(6µm 重合节点簇塌缩)+ 2×2 交叉实验
│   ├── VALIDATION_REPORT.md               ← 含 §七 交叉实验析因表
│   ├── m3_hotzone_elements.csv             ← 病态口袋清单(11 单元/15 节点)
│   └── scripts/                           ← 口袋圈定/保护性塌缩/定位脚本
├── 03_explicit_z27_batch/            M08 批次(显式 z 向 27 例,09-25→27)
│   ├── SUMMARY.md                         ← 批次总账+作者对比+批量就绪评估(★先读这个)
│   ├── EXECUTION_STATE.md / batch_ledger.csv / selection_manifest_m08.csv / summary_data.json
│   ├── figures/ + 两个样本展示图(png)
│   ├── scripts/                           ← 全套管线(适配器/调度/提取/汇总/作图)
│   └── curves/                            ← 5 个有效样本的曲线+能量 CSV
├── 04_startup_transient_fix/        起步瞬态根因与修复(09-26→29)
│   ├── FIX_NOTES.md                       ← 修复链总结(★根因三层/失败路线留档/能量门对照/论文答案)
│   ├── scripts/                           ← STL 塌缩/两遍法/datacheck 迭代脚本
│   └── cleaned_case/                      ← 清洁网格验证跑的曲线+能量+提取脚本
├── 05_c3d10_return/                  师弟 C3D10 隐式全程回传(09-26)+ 独立复算
│   ├── VERIFICATION_NOTE.md               ← 三格对照(C3D4隐/C3D10隐/C3D4显)+ 复算方法
│   ├── result.md / curve.csv / energies.csv / solve_status.json
│   └── C3D10_QUICK_REPORT.md              ← C3D10 datacheck 根因(CAE 坐标截断)历史报告
├── 06_plans/                        四份实验计划(按时间序)
│   ├── 2026-09-23-m05-m1m3-marlow-c3d4-validation.md
│   ├── 2026-09-23-m05-m3-hotzone-mesh-quality-draft.md
│   ├── 2026-09-25-m08-explicit-z27.md
│   └── 2026-09-29-m09-paper-aligned-pde-mesh.md   ← M09 原计划及执行更正
└── bigfiles/                        远端已有的历史 INP/STL 归档（本次保留）
    ├── MANIFEST.md                         ← 文件身份、来源与用途
    ├── geometry_stl/                       6 个几何 STL（含 M09 两例几何输入）
    ├── solver_inps/                        6 个 M08 显式求解 INP，仅作历史记录
    └── experiment_inps/                    4 个材料／网格排查 INP，仅作历史记录
```

**大文件边界**：本次 PR 保留远端已归档的 INP/STL，不上传 ODB。几何可在保留身份链的前提下作为 M09 输入；历史 M08 求解 INP 的网格、边界和质量缩放设置不作为后续实验设置。

## 四、当前状态与下一步

- **后续唯一实验设置**：M09，入口=[当前设置](CURRENT_SIMULATION_SETTINGS.md)与[原计划及更正](06_plans/2026-09-29-m09-paper-aligned-pde-mesh.md)。参数已选定，本次未找到回传证据，不写“正在执行”。
- **历史证据**：M08 加载完成与能量门失败分别保留；清洁网格仅部分改善；单例隐式 C3D10 对照不能代替 M09 验证。
- **待回传**：M09 两例网格／单元／边界／完整曲线／能量证据；历史 s1–s20 单位与曲线差异归因仍待核实。当前材料沿用作者原卡，Marlow 只作排查记录。

## 五、复用提示

- 查阅历史显式管线:读 `03/scripts/z_explicit_adapter.py`(M08 卡与断言)与 `m08_solver.py`(历史调度)；这些脚本不作为后续 M09 的默认设置或执行入口；
- 想做网格质量体检:读 `01/mesh_quality_analysis.py`(独立 numpy 判据)与 `02/scripts/`(保护性塌缩全套);
- **想避免我们踩过的所有坑**:先读 `04/FIX_NOTES.md` 的失败路线留档,再读 M09 计划 §4 的"C3D10 节点排序映射"与 §5"周期配对"。
