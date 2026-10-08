# Paper A 仿真实验接手 Memory

## 2026-10-08 当前入口：Explicit、z 渐变、z 加载、25%

- 仿真实现、求解和排障已全量交由师弟。**M09 是此后实验唯一基线，M08 及更早版本只作历史记录，不作为后续仿真设置。** 当前统一记录见 `F:/small++/paper_A_reliable_inverse_design/simulation_runs_202609/CURRENT_SIMULATION_SETTINGS.md`，其优先于下方旧“当前”段落。
- 已跑 M08 ODB：C3D4、z 向加载 U3=-10mm/40mm、T=0.1s、SMOOTH STEP、固定质量缩放 dt=1e-6、六面法向约束（非严格周期边界）、作者 Polynomial n=2＋塑性材料。
- M09 当前参数：PDE 网格（归一化 HMax=0.05、HGrad=1.2）、计划 C3D10 二阶单元、x-y 周期边界、默认无质量缩放、T=0.1s、SMOOTH STEP、作者原 TPU 材料卡、double=both。参数已选定；本次未找到验收回传，不宣称执行已通过，不自动回退旧设置。
- M08 有 3 例完成 25%，但全程准静态门均失败；清洁网格修复仍未过门。部分曲线覆盖、完整加载、能量有效性与机制标签准入分别记账。
- 后处理沿 z：RF3、U3、z 分区；应变从实际位移计算。M08 场输出未请求 LE，不能假定已有 LE33。
- `simulation/abaqus/current_config.json` 已登记 M09；旧 x 向 Standard 配置归档为 `script_first_config_20260924.json`，历史生成器只读归档。以下保留旧实验决策及状态，不作为当前求解设置。

## 2026-09-25 最新参考口径：以论文仿真实验结果为主

- 用户要求以论文仿真实验结果为主。正文/补充材料作为设置与结果对比的主要依据，公开脚本冲突项单列；下方“脚本优先”作为历史决策保留。
- 用户补充作者实际成功率约25%，按用户提供的经验信息记录，分母及成功定义未明确。正文第8页的15000组参数→9000个进入FEA→8008个有输出→5111个筛后保留是另一统计链，不能混用为同一成功率。
- 本次仅核对设置、更新参考口径。当前活动文件仍为x向Standard；最新12样本方案为z向Standard、六面位移约束变体，尚非论文Explicit/周期边界实现。本条不表示模型已切换或求解已启动。

## 2026-09-24 最新试验安排：12个z向加载样本方案

用户要求先沿z加载试算，并设计M1/M2/M3共12个样本。方案已生成，三类各4个，按3+3+6推进；沿用脚本材料与Standard，以六面边界轴交换形成z向25%压缩变体，C3D4暂用。方案入口：`F:/small++/paper_A_reliable_inverse_design/docs/superpowers/plans/2026-09-24-zload-12/EXPERIMENT_PLAN.md`，同目录含真实参数清单与planned_config.json。

这是当前拟执行的z向试点；下方“脚本优先”仍作为材料/求解器依据，x向配置保留为参考。现有build_current_model.py仅支持x向，执行方必须实现z专用适配并核对RF3/U3/LE33、节点集和z分区。此次完成方案设计，尚未生成z向INP或启动求解。旧x向数据只做注明配置差异的探索性对照。


## 2026-09-24 最新裁定：以 Small 作者公开脚本为主

- 老师经用户明确要求“以脚本为主，改 memory 和现在的参数配置，尽量还原脚本”。本条取代此前同日“论文优先”的决定。
- 当前活动配置：`F:/small++/paper_A_reliable_inverse_design/simulation/abaqus/current_config.json`；新建模入口 `simulation/abaqus/build_current_model.py`。
- 新作业：Standard StaticStep / NLGEOM，x 向 -10 mm（40 mm 跨度、25%）；initialInc=0.01、minInc=0.001、maxNumInc=1000；六面位移约束按脚本，不称严格 PBC；原 Polynomial n=2 试验数据拟合+塑性，不换 Marlow/显式。场与历史输出各 20 区间。
- 几何梯度仍沿 z，加载沿 x；其与论文描述不一致作为已知差异保留，不再以论文覆盖脚本。
- 25% 为完整求解目标；原 0–24% 机制分析窗口保留为独立字段，覆盖窗口不等于正常完成 25%。新链路按 x / RF1 / U1 / LE11 处理。
- C3D4 仅暂用，正式网格仍待 C3D10 对照，不能声称原作者实际单元已确认。本机资源单独设置，不复制作者硬件配置。
- 本次已更新活动参数与可生成建模脚本的入口；不启动求解、不覆盖已生成 INP/ODB，不改变运行中任务。M05/M06 旧配置与审核记录保持原身份。后续新任务使用活动入口，不再套用 M06 的 -9.6 mm 补丁。
- 交接：`docs/handoffs/2026-09-24-script-first-alignment.md`。以下相冲突段落仅为历史记录。


## 已被替代：2026-09-24 早先论文优先决策

用户明确要求“都按照论文公开的配置进行对齐”。正文/补充材料优先于冲突的公开脚本：新论文对齐基线应为梯度沿 z、沿 z 压缩、目标 25%、Explicit、正文所述上下端约束及 x/y 周期边界。旧 x 向 Standard 与 24% 试点保持原身份和证据，不回改。

当前只完成决策记录与差异交接，尚未生成或验证新的 Explicit 模型，不能声称已经配置对齐。单元尚待 C3D10 对照，未公开的加载时间/幅值/质量缩放/周期配对实现等不能伪称作者原值。参考 `F:/small++/paper_A_reliable_inverse_design/docs/handoffs/2026-09-24-paper-first-alignment.md`。下方 2026-09-21 内容为历史路线，不再作为新论文对齐批次的默认方向。

## 2026-09-21 当前实验决策：参考 Small 重建数据集并增加机制标签

来源：用户提供导师沟通截图，并明确确认“那就按老师要求的来”“更新到实验 memory 里”。这是方向决策，不是仿真完成声明。

### 目标与对照口径

- 参照 Small 公开方法重建统一、可信、可复现的新数据集，在同一次仿真结果上增加变形机制标签；不再以逐点复现作者旧曲线为推进前提。
- 不再等待作者原始 INP/CAE。使用本项目几何和网格，沿用已核对的作者材料输入及当前试点加载设置；无法核实的设置和本项目特有处理如实记录，不宣称完全一致。
- 此前已核对材料输入一致，不等于其在所有变形状态下的稳定性已验证。
- 历史曲线保留作对照，原 NRMSE 10% 门不再单独阻塞新数据集建设。不得删除旧门、旧失败结论或手改证据；执行前版本化修订模型说明和验收规则。
- 本次只调整 M05 历史力学曲线对照用途，不放宽 M03/M04 几何、描述符、身份或证据完整性门。
- 既有约 31%–47% 力比偏差仍待解释，不直接认定为“小误差”或归因于某一种单元；其比较依赖历史 s 单位和应变轴假设，确认前不能作最终复现误差结论。

### 统一加载目标与机制标签

- 下一轮以工程压缩应变 24% 为统一试点目标；40 mm 加载跨度对应压缩位移 9.6 mm。先 M2，再检查少量不同结构，稳定后再决定扩批。
- 24% 是下一轮目标，不代表全样本已能达到。不得各样本以不同终点冒充同一曲线标签；未达目标者单独记录失败/缺失。
- 旧数据 20 个曲线点对应 0–20% 还是 0–25%、s 列单位，仍未确认；不得把新目标 24% 赋给旧数据横坐标。
- 机制标签只针对共同的 0–24% 区间；未出现的机制标为“该区间内未观察到”，不推断更大应变下不会发生。

### 质量底线和旧证据

- 正常完成预定加载、材料/网格问题不影响可信度、场输出完整且机制标签与同次运行对应，仍是必要验收条件；仅收敛不等于全部质量验收通过。
- 旧 M2 目标为 25%，约 24.2% 处终止，保持 solver_failed/不可入监督集状态。已收敛部分可用于诊断，不裁剪窗口或修改状态把旧运行变成通过。
- 新 24% 目标需按修订身份和规则单独验证，不覆盖旧日志、ODB、checkpoint、曲线或审核报告。
- 材料稳定性警告、网格畸变及局部大应变的必要核查保留；降低终点不自动关闭问题，也不证明已有确定因果关系。
- 4% 删除预算及主承载路径规则保持冻结口径；它们是本项目规则，不标成作者设置。

### 下一步及授权边界

1. 同步执行方案、模型说明及验收规则，记录 25% → 24% 和历史误差门用途变化。本次只更新 memory，尚未完成上述执行文件修订。
2. 保留第 6 轮 C1–C3 无需求解随修：计数字段、strict_instance 主入口接线、热点因果表述收窄。实际是否完成须查代码和证据，不由本记录推定。
3. 确认单例求解授权、资源和尝试预算后，验证 M2 的 24% 工况；通过必要质量检查后，再安排小批结构验证。
4. 方向确认和 memory 更新不自动授权批量求解、额外重试、C3D10 升级、材料改动、降低收敛标准或 Git 提交。材料 MODEL=YES/小规模评估、C3D10 对照与资源预算仍须单独授权；历史单位及四次启动预算记账仍待确认。

### 接手入口

- M05 证据：`F:\small++\paper_A_reliable_inverse_design\audits\m05_small_mechanism_pilot_20260919\`，重点读 RESULTS_M2.md、REPAIR_SUMMARY_ROUND5.md、SETTINGS_COMPARISON.md。
- 第 6 轮复审：`F:\small++\paper_A_reliable_inverse_design\audits\m05_pilot_review_round6_20260921\REVIEW_REPORT.md`；通过范围限本轮修复与当前单实例 M2 诊断链路。
- 既有计划：`F:\small++\paper_A_reliable_inverse_design\docs\superpowers\plans\2026-09-21-m05-post-round6-next-steps.md`；旧加载目标/历史曲线硬门如有冲突，按本次用户决定修订后执行，不静默套用旧口径。
- 作者资料位置见 `F:\small++\paper_A_reliable_inverse_design\MEMORY.md`。

---

## 以下为 2026-08-06 的 M04 历史接手快照（不是当前进度）

以下状态、路径、版本和停止条件按当时语境保留。不得据此误认 M05 未开始或覆盖后续成果；当前方向先读上方决策，具体实现状态查现行报告。

> 最后更新：2026-08-06（Asia/Shanghai）
> 用途：让新的 Agent 在不依赖原对话的情况下继续 M04 仿真实验。
> 若本文与版本化规格或实施计划冲突，以规格、计划和当前 Git 内容为准。

## 1. 当前接手点

- 项目：Paper A，渐变 Gyroid/TPMS 几何编译、双描述符校准和 Abaqus Gate-0 前处理。
- 工作树：`F:\small++\.worktrees\m03-continuous-csg-impl`
- 分支：`paper-a/matlab-gyroid-m04-descriptors-interface`
- 当前功能提交：`d30ff3d`，`feat(gate0): preregister and freeze legacy calibration`
- M03 基线提交：`be24186`
- M01、M02、M03 已完成；M04 Task 1–6 已完成；应从 **M04 Task 7** 接手。
- 最近一次完整验证：MATLAB 全项目 `227/227` 通过，Gate-0 `15/15` 通过，Code Analyzer `0` 问题。
- 尚未运行真实 release calibration、30-case confirmation 或 Abaqus。

权威文档：

- 设计规格：`paper_A_reliable_inverse_design/docs/superpowers/specs/2026-08-05-m04-dual-descriptors-abaqus-interface-design.md`
- 实施计划：`paper_A_reliable_inverse_design/docs/superpowers/plans/2026-08-05-m04-dual-descriptors-gate0-implementation.md`
- M03 使用说明：`paper_A_reliable_inverse_design/geometry_compiler_matlab/docs/M03_USAGE.md`

## 2. 科学与工程边界

M04 明确分离两个描述符空间，禁止混用：

1. `legacy_small`：复现 Small 原始数据和 TPMS-Designer 的历史算法，用于旧数据对齐、6-case discovery 和 30-case confirmation。
2. `physical_m04`：基于 M03 有限试样、cell-centred interior mask 和水密表面网格的物理描述符，用于后续工程数据和 Abaqus 接口。

`legacy_small` 的历史一致性不代表它是最合理的有限试样物理定义；`physical_m04` 也不能直接替换 Small 归档标签。论文中应把两者解释为“历史复现空间”和“有限试样物理空间”。

本阶段 Abaqus 边界只能生成并离线验证交换包，必须保持 `solver_ready=false`。M04 不允许：

- 启动 Abaqus 或导入 `abaqus` 模块；
- 生成求解器体网格或正式 `.inp`；
- 调用 `job.submit()`；
- 声称已完成力学、可制造性、3D 打印或压缩实验验证。

正式 Abaqus 导入、体网格和求解属于后续 M05；3D 打印与重复压缩实验尚未开始。

## 3. 环境与外部输入

- MATLAB：R2023b
- 可执行文件：`F:\MATLAB\R2023b\bin\matlab.exe`
- 必需工具箱：Image Processing Toolbox
- MATLAB 项目目录：
  `F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab`
- Small 原始测试工作簿（只读，不提交）：
  `F:\demo_TPMS\xiedian\Inverse-design-of-graded-TPMS-main\Inverse-design-of-graded-TPMS-main\dataset used for training\test.xlsx`
- Small 原项目备份：
  `F:\demo_TPMS\xiedian\Inverse-design-of-graded-TPMS-main`
- Small 论文：
  `C:\Users\48186\Desktop\文献\逆向设计优化\Small - 2025 - Zong - Machine‐Learning‐Powered  Rapid  Accurate  and Multi‐Target Mechanical Metamaterials Inverse Design.pdf`
- 补充材料：
  `C:\Users\48186\Desktop\文献\逆向设计优化\smll202500634-sup-0001-suppmat.pdf`

如果 MATLAB R2023b 出现 `ddux_logging` access violation，使用工作树内临时偏好目录，不要修改用户全局 MATLAB 配置：

```powershell
$pref='F:\small++\.worktrees\m03-continuous-csg-impl\.matlab_pref_r2023b'
New-Item -ItemType Directory -Force -Path $pref | Out-Null
$env:MATLAB_PREFDIR=$pref
```

验证结束后确认该路径仍在工作树内，再删除临时目录；不得提交它。

## 4. M01–M03 已完成能力

### M01：编译器契约

- 版本化配置、参数域、M1/M2/M3 活跃变量和边界规则。
- M2 使用正交 L2 等值投影；M1 固定 `w=0`；M3 四变量均活跃。
- 配置、描述符定义、参数域清单和输出均带 SHA-256 provenance。

### M02：渐变 Gyroid 连续场

- M1 分段线性阈值；M2/M3 使用 `gamma(z)=1.5+z/w`。
- 已验证阈值结点、连续性、投影、单位和确定性。
- 生产公式不得改成乘以 `w`、倒数重参数化或未经批准的平滑形式。

### M03：有限边界、水密 STL

- 权威几何为连续 sheet-Gyroid 与硬矩形盒的 CSG 交集。
- 使用 cell-centred 网格、等值面提取、闭合二流形检查、自交检测和二进制 STL 验证。
- 不允许补洞、平滑、焊接、形态学闭运算或删除不合格组件来“修复”生产几何。
- M03 `valid=true` 只证明请求、几何、网格和文件完整性，不证明描述符、Abaqus 或实验有效性。

## 5. M04 Task 1–6 已完成内容

关键提交按顺序为：

- `5588061`：激活双描述符 v2 契约并保留 v1 历史定义。
- `2a493c3`：实现 `legacy_small` 采样与五个历史描述符。
- `27bf787`：实现有限试样 `physical_m04` 描述符。
- `e2428f3`：集成 fail-closed M04 双描述符编译器。
- `085dd14`：认证真实 Small 工作簿并冻结确定性 6+30 选择。
- `ff3facd`：修复选择 provenance 和 M04 错误映射。
- `d30ff3d`：实现 discovery 密度/尺度校准和不可变冻结契约。

主要入口与实现：

- `run_geometry_compiler.m`：M03 几何编译入口。
- `run_descriptor_compiler.m`：认证 M03 产物后计算双描述符。
- `gate0/prepare_small_gate0_selection.m`：审计真实工作簿并生成 6+30 清单。
- `gate0/calibrate_legacy_scale.m`：在 discovery 集上选择密度并计算单一全局尺度。
- `gate0/freeze_legacy_calibration.m`：原子发布不可覆盖的校准冻结文件。
- `gate0/verify_legacy_calibration_freeze.m`：读取时重新推导并验证冻结内容。
- `tests/fixtures/small_gate0_rows.json`：已提交的紧凑 6+30 选择证据。

## 6. 已冻结标识和校准规则

- 源工作簿 SHA-256：
  `b4544b09c2688af8bc7aeeca5140a5d4c1cfc1c5b262709c9618c030d90fa561`
- 6+30 选择 SHA-256：
  `b953901b85178d5a54f9009e14b39af227b39e81e921aed52767c36585abe6c1`
- 编译器版本：`matlab-gyroid-0.3.0`
- 参数域清单 SHA-256：
  `671e0c081f8d50e1060a1cfdb4e10d70b662319582f2922231400ba56dd7bd2a`
- v2 描述符定义 SHA-256：
  `9e31513211e50a5251a91cecd303947939db023c1713ea3900c5920dbf98003d`
- TPMS-Designer source-of-record commit：
  `a5f7d59b59f5c00e0f50c0bc3675f38f553454eb`
- 样本组成：M1/M2/M3 每种方法 2 个 discovery、10 个 confirmation，共 6+30。
- 候选采样密度顺序固定为：
  `[20,24,30,32,40,48,60,64,80,96]`
- 密度筛选只使用六个 discovery 样本的 `relativeVolume` 和 `relativeArea`。
- 两个描述符必须分别满足 median `<=0.02`、确定性 p95 `<=0.05`。
- 合格密度按 pooled median、pooled p95、较低密度依次排序。
- 相对误差绝对容差固定为 `1e-12`。

单位参考长度下的三组尺度估计必须严格使用：

```matlab
estimates = [archivedThickness./computedThickness, ...
             archivedPore./computedPore, ...
             sqrt(archivedArea./computedArea)];
frozenLength = median(estimates,'all');
relativeDeviation = abs(estimates-frozenLength)./frozenLength;
```

18 个尺度估计必须全部为正且有限；总体 median deviation `<=0.02`，确定性 p95 `<=0.05`，三个尺度组的中位数相对全局尺度偏差均 `<=0.02`。不满足时返回 `M04_SCALE_NOT_IDENTIFIED`，禁止产生冻结文件。

## 7. 本轮审查发现并修复的问题

后续 Agent 不应撤销以下防护：

- 选择摘要现已绑定原始参数和五个归档目标，不再只绑定行号。
- `effective_parameters` 必须由原始参数和当前约束重新推导后逐字段比较。
- 工作簿 SHA 与唯一 6+30 选择 SHA 均被精确钉扎；“内部自洽但来源错误”的清单会被拒绝。
- schema、compiler、descriptor definition、profile 和 TPMS-Designer commit 均被锁定。
- 冻结摘要只排除 `freeze_sha256`；额外未签名字段会被拒绝。
- 读取器会重新计算密度资格、排序、三组尺度、统计量、discovery/confirmation 身份和选中密度结果。
- MATLAB JSON 把 `1x3` 向量读成 `3x1` 时只允许向量方向等价；`6x3` 尺度矩阵仍严格检查形状。
- `DescriptorContractMismatch` 已有独立失败码映射，不再误报成 profile 无效。
- 理论上恰好落在阈值处的数值只使用机器精度级比较余量，不改变科学阈值。

## 8. 尚未完成，禁止误报为已完成

### M04 Task 7：未开始

需要实现 30-case confirmation 的断点续算和终态报告：

- 新建 `gate0/summarize_descriptor_errors.m`；
- 新建 `gate0/run_small_descriptor_gate0.m`；
- 扩展 `tests/TestDescriptorGate0.m`；
- 覆盖全通过、阈值失败、非有限输出、非确定性、中断恢复、检查点篡改、freeze 变更和禁止 override；
- confirmation 参数、密度、尺度、公式和阈值一律不可根据结果调优。

### M04 Task 8–9：未开始

- MATLAB Abaqus Gate-0 五文件交换包契约；
- 普通 Python 离线预检；
- 源码守卫证明没有 Abaqus 提交行为。

### M04 Task 10：未开始

- 尚未执行真实的 6 discovery × 10 density 计算；当前没有真实选定密度和真实全局尺度。
- 尚未生成正式 calibration freeze。
- 尚未运行 untouched 30-case confirmation。
- 尚未生成 M04 QA report、使用说明或三种方法的代表性离线 Abaqus 包。

## 9. 下一 Agent 的推荐执行顺序

1. 进入上述工作树，确认分支和 `git status --short`；不得覆盖用户已有改动。
2. 完整阅读 M04 规格、实施计划 Task 7，以及本 Memory。
3. 按 TDD 执行 Task 7：先添加失败测试并确认 RED，再做最小实现。
4. checkpoint 身份至少绑定 freeze SHA、selection digest、输入、计算描述符 SHA 和 canonical JSON SHA。
5. 每个 confirmation case 必须独立计算两次并比较 canonical descriptor text；不一致立即停止。
6. 失败时不得跳过样本、推进 case index 或删除失败证据。
7. Task 7 代码完成后先跑 Gate-0 测试，再跑全部测试和 Code Analyzer，最后逐文件审查后提交。
8. Task 7 通过后才进入 Task 8；Task 8–9 仍然不得运行 Abaqus。
9. 真实 release 数据只在 Task 10 产生，并且必须先重新审计外部 `test.xlsx`。

常用验证命令：

```powershell
$project='F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab'
$pref='F:\small++\.worktrees\m03-continuous-csg-impl\.matlab_pref_r2023b'
New-Item -ItemType Directory -Force -Path $pref | Out-Null
$env:MATLAB_PREFDIR=$pref
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('$($project -replace '\\','/')'); r=runtests('tests/TestDescriptorGate0.m'); assertSuccess(r)"
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('$($project -replace '\\','/')'); run_tests"
```

完整回归此前约需 7–8 分钟；不要用 60 秒外层超时杀掉 MATLAB 后把超时误报为测试失败。

## 10. 接手时必须维持的停止条件

出现下列任一情况立即停止 release 流程并保存证据：

- 外部工作簿 hash、sheet 顺序、表头或选定行认证失败；
- 无候选密度满足 discovery 阈值；
- 三组尺度不能形成一个合格的全局尺度；
- freeze、checkpoint、M03/M04 artifact 或 STL hash 不一致；
- 任一 confirmation case 非确定、非有限或超过阈值；
- 用户要求正式 Abaqus 求解但 Task 8–10/M05 前置门禁尚未通过。

不得为了“跑通”而修改候选密度集合、全局尺度公式、6+30 划分、阈值、描述符定义或失败样本。
