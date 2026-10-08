# 项目 Memory

## 2026-10-08 当前仿真方向与交接（取代下方旧“当前”设置）

- 用户确认：仿真已全量交由师弟；**M09 是此后实验唯一基线，M08 及更早设置仅用于历史记录**。采用 Abaqus/Explicit **显式**求解、几何 z 向渐变、z 向加载，完整压缩目标 25%。
- 当前参数与遗留事项入口：`simulation_runs_202609/CURRENT_SIMULATION_SETTINGS.md`；机器可读记录：同目录 `solver_settings_record.json`。前者区分已跑 M08 与待验证 M09，后者仅为记录，不是可直接执行的建模配置。
- 截图所示桌面 `M08_ODB结果包_20260929` 是 M08 结果：C3D4、六面法向位移约束（非严格 PBC）、T=0.1s、SMOOTH STEP、U3=-10mm/40mm、固定质量缩放 dt=1e-6。原材料为作者 Polynomial n=2＋塑性，未转为 Marlow。
- M08 原批次 3 例完成 25%，均未通过全程准静态能量门；清洁网格 m3_26 仍未通过。m3_61 与 m3_540 分别只覆盖 23.552% 与 17.064%。完成加载、曲线可提取、准静态通过和机制监督准入必须分开。
- M09 选定 PDE 网格（归一化 HMax=0.05，HGrad=1.2）、计划 C3D10 二阶四面体、Explicit z 加载和 x/y 周期边界，默认不加质量缩放；T=0.1s、SMOOTH STEP、double=both、作者原 TPU 数据卡。单元支持性、节点排序、网格尺度、周期相容性和能量门仍待师弟实际验证；参数选择已定，不称已完成或正在运行，不自动回退 M08。
- `simulation/abaqus/current_config.json` 已改为 M09 声明式参数登记；旧 x/Standard 参数归档为 `script_first_config_20260924.json`，旧 `build_current_model.py` 只读该历史文件。尚未实现可消费 M09 配置的已验收建模器。旧 24% 窗口与 x 向结果保留原身份。
- 本次只整理记录与 PR，不提交新仿真、不改写已有 INP/ODB/曲线或历史失败状态。以下按日期保留的是历史决策快照。

## 2026-09-25 最新参考口径：以论文仿真实验结果为主

- 用户明确要求“要参考论文里的仿真实验结果为主”，并补充作者实际成功率约25%。后续设置与结果对比以正文及补充材料为主要依据；公开脚本冲突项单列，不再将脚本优先视为当前比较口径。
- 约25%是用户补充的实际经验信息，分母及成功定义尚未明确，不能标成论文报告值。正文第8页记载15000组参数、选9000个进入FEA、8008个有输出、筛后5111个；按这条链计算，筛后/初始为34.1%，筛后/进入FEA为56.8%，有输出/进入FEA为89.0%，分别记录。
- 本次请求是设置对比。现存current_config.json仍为x向Standard脚本配置，最新12样本方案为z向Standard/六面位移约束变体；尚不能称论文Explicit/PBC已实现。本条更新参考口径，不改写历史结果，也不表示已修改求解配置或启动新仿真。

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

- 用户明确要求“都按照论文公开的配置进行对齐”。后续论文对齐批次以正文和补充材料明确描述为准；公开脚本仅补充不冲突的信息。
- 论文明确项：z 向压缩、25% 位移加载、Abaqus/Explicit、底面固定、顶面只允许 z 向位移、x/y 方向周期边界。梯度保持沿 z，加载与梯度平行。实现细节仍须核验，不能把旧六面零位移约束称为严格周期边界。
- 当前 M05/M06 是公开脚本参考的 x 向 Standard 路线（M06 实际 24%），保留为历史诊断，不改写为论文对齐结果。该最新决策取代后续新批次继续沿用 x 向 Standard 的建议。
- 本次已记录方向与配置依据，尚未完成 Explicit 输入生成或启动论文对齐求解。单元等待 C3D10 对照，不能凭论文未明确的信息提前确定；加载时间、幅值、质量缩放、周期配对等缺失细节须明确记录工程选择。
- 详细交接见 `docs/handoffs/2026-09-24-paper-first-alignment.md`。下方 2026-09-21 决策为历史阶段记录。

## 当前实验方向（2026-09-21 用户确认）

实验决策入口：`F:\small++\paper_A_reliable_inverse_design\simulation\matlab\geometry_compiler_matlab\docs\SIMULATION_EXPERIMENT_MEMORY.md`，优先读顶部“2026-09-21 当前实验决策”；后面的早期 M04 内容仅为历史快照。

- 参考 Small 重建新数据集并增加同次仿真的机制标签，不以逐点复现旧曲线为前提，不再等待作者 INP/CAE。
- 下一轮统一 24% 压缩试点（40 mm 跨度压缩 9.6 mm），先 M2、再少量结构，验证后扩批。
- 历史曲线作对照，原 NRMSE 10% 门不再单独阻塞新数据集建设；保留旧偏差和失败证据，不将未确认单位/应变轴下的比较当最终结论。
- 正常完成、材料/网格可信度和场数据完整性检查保留；旧 25% 目标运行在约 24.2% 终止的失败状态不改写。
- 本次仅更新记忆；执行方案/模型说明/验收规则仍需同步，求解与预算另行确认，不自动授权批量作业或材料/单元变更。

## Small 作者公开资料的本地位置

更新日期：2026-09-21。来源：用户明确指定，并已核对目录存在。

- 用户指定的资料目录：`F:\Inverse-design-of-graded-TPMS-main`
- 当前解压后的实际仓库根目录：`F:\Inverse-design-of-graded-TPMS-main\Inverse-design-of-graded-TPMS-main`
- Abaqus 脚本：`F:\Inverse-design-of-graded-TPMS-main\Inverse-design-of-graded-TPMS-main\FEA-abaqus.py`
- 训练/测试数据目录：`F:\Inverse-design-of-graded-TPMS-main\Inverse-design-of-graded-TPMS-main\dataset used for training`
- 原始结果整理脚本：`F:\Inverse-design-of-graded-TPMS-main\Inverse-design-of-graded-TPMS-main\extract dataset from rawdata.m`
- 逆向设计代码目录：`F:\Inverse-design-of-graded-TPMS-main\Inverse-design-of-graded-TPMS-main\Inverse design code by python`

后续查阅作者公开数据和代码时，优先检查上述用户指定目录；不要再默认只在旧 `F:\demo_TPMS\xiedian\...` 路径寻找。

项目 `audits` 中的作者仓库副本仍是此前复审使用的历史证据，保留原样。新目录与审计副本是否逐字一致尚未核验；涉及已冻结数据身份或复现差异时应先比较对应文件摘要，不自动替换历史输入、摘要或冻结记录。

此记录只确认资料位置，不代表公开资料包含完整几何生成代码或全部原始 INP/CAE/ODB 文件，也不构成执行脚本或启动求解的授权。
