# simulation_runs_202609 — 仿真排查参考包(2026-09-23 → 09-29)

> 本文件夹收录 2026 年 9 月下旬 Paper A 仿真线的**完整排查与修复记录**,供师弟/师兄/导师参考。
> 大文件(ODB/INP/STL,50MB–1.4GB)一律未收录,原件留本地 `audits/` 各实验目录,以报告与哈希索引为准。
> 阅读顺序建议:先读本 README 的时间线,再按需进各子目录。

## 一、时间线与一句话结论

| 日期 | 事件 | 一句话结论 |
|---|---|---|
| 09-23 | 材料排查线 | 作者超弹卡经 Abaqus 拟合官方判 UNSTABLE(单轴压缩 <-0.2305 即失稳);换 Marlow 认证稳定、对数据贴合更好(最大偏差 1.07% vs poly2 的 17.76%),但 **M1/M3 求解仍死在 minInc——材料不是控制性因素**(Codex r1-r3 审核口径) |
| 09-23 | 网格热区治理 | M3 死亡点 0.0637→0.102(+60%),被治理簇残差签名清零;交叉实验(poly2×治理网格 0.122)完成 2×2 析因:软化润滑效应坐实、瓶颈=9195 交界带(非伪影) |
| 09-25→27 | M08 显式 z 向 27 例批次 | 首个配置正确的批次(论文=z 向);3 例全程完成+2 例近全程;**开局坍塌 58%=起步瞬态**(详见 04);发现"沿梯度轴压缩 vs 作者历史 x 向曲线"的比值差异是物理效应(2.3–5.8×) |
| 09-26 | 师弟 C3D10 回传 | 隐式 C3D10 **首次全程走完 24% 窗口**、能量全静;对文献比值中位 1.275 vs C3D4 隐式 1.431——**C3D10 显著更贴近原文** |
| 09-26→29 | 起步瞬态根因与修复 | 根因=STL 3µm 碎三角形→gmsh 继承→质量缩放 65 万倍假质量;网格层修复把瞬态 115.3%→64.3%(部分有效);**论文写明作者用 PDE Toolbox 网格法,碎三角形根本进不了他的网格——根治=复刻该路线(M09 计划)** |
| 09-29 | 方向拍板 | 弃"STL→gmsh"路线;M09=论文完全对齐(PDE 网格+C3D10+Explicit+z 向+周期边界+无质量缩放),师弟执行 |

## 二、关键数字速查

| 对照 | 数值 | 出处 |
|---|---|---|
| 作者超弹卡失稳边界 | 单轴压缩 <-0.2305 / 双轴拉伸 >0.14 | 01/RESOLUTION §一 |
| Marlow vs poly2 对数据贴合 | 最大偏差 1.07% vs 17.76% | 01/RESOLUTION §七 |
| M3 热区治理死亡点 | 0.0637 → 0.102(+60%) | 02/VALIDATION_REPORT |
| C3D10 vs C3D4 对文献比值 | 1.275 vs 1.431(NRMSE 0.265 vs 0.418) | 05/VERIFICATION_NOTE |
| 起步瞬态(修复前后) | ALLKE/ALLIE 峰值 115.3% → 64.3% | 04/FIX_NOTES |
| M08 完成率 | 全程 3/26 + 近全程 2/26(作者基准 25%) | 03/SUMMARY.md |
| 匀质样本 z 向对作者 | m2_1383 晚段比值 1.18(优于隐式 x 向 1.43) | 03/SUMMARY.md §二 |

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
│   └── 2026-09-29-m09-paper-aligned-pde-mesh.md   ← ★当前执行入口(师弟)
└── bigfiles/                        大文件本体(git 直传,共约 520MB)
    ├── MANIFEST.md                         ← 逐文件 sha256/用途/来源(★先读)
    ├── geometry_stl/                       6 个几何 STL(5 设计 + 短边清理版)
    ├── solver_inps/                       6 个显式 z 求解模型 INP(含清洁网格验证模型)
    └── experiment_inps/                    4 个 09-23 实验 INP(Marlow/热区/交叉)
```

**bigfiles 说明**:ODB 结果文件(437MB–1.4GB)超过 GitHub 单文件 100MB 硬限未收录——用上述 INP 重跑即可再生;如需原 ODB,可走 GitHub Release 附件(单文件≤2GB)另行上传(需要时向 zyql 说一声)。

## 四、当前状态与下一步

- **正在执行**:M09(论文完全对齐管线,PDE 网格+C3D10+Explicit+z+周期边界,师弟机),入口=`06_plans/2026-09-29-m09-paper-aligned-pde-mesh.md`;
- **已完成定案**:起步瞬态根因(STL→gmsh 路线特有)、材料卡事实(poly2 UNSTABLE 属实但非控制因素)、C3D10 优于 C3D4(隐式口径);
- **悬置待决**:历史 s1–s20 单位确认(s=N 假设);Marlow 转正与否(随 M09 结果自然解决);z 向 vs 作者 x 向曲线的比值差异归因(起步瞬态修复后重评)。

## 五、复用提示

- 想跑同款显式管线:读 `03/scripts/z_explicit_adapter.py`(显式 z 适配卡与全部断言)与 `m08_solver.py`(调度/截止/优雅终止);
- 想做网格质量体检:读 `01/mesh_quality_analysis.py`(独立 numpy 判据)与 `02/scripts/`(保护性塌缩全套);
- **想避免我们踩过的所有坑**:先读 `04/FIX_NOTES.md` 的失败路线留档,再读 M09 计划 §4 的"C3D10 节点排序映射"与 §5"周期配对"。
