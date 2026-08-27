# Paper A 仿真实验接手 Memory

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

- 项目进展与整体研究逻辑：`paper_A_reliable_inverse_design/docs/PROJECT_RECORD_AND_LEARNING_GUIDE.md`
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
