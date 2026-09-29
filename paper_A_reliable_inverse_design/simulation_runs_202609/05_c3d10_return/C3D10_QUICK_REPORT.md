# M2 C3D10 快速对照 — 状态报告（复审 P1-2/P2-7/P2-13 修订版）

日期：2026-09-22。执行：按 `docs/superpowers/plans/2026-09-21-m05-m2-c3d10-quick-validation.md` 逐任务执行，并按用户 2026-09-22 建议的处理顺序完成最小复现与根因定位；随后按第 8 轮复审（`review_round8_20260922/REVIEW_REPORT.md`）逐条修复。未提交 Git、未自动委派、未启动求解。

## 0. 当前状态（一段话）

**C3D10 对照的 datacheck 致命错误根因已定位：直接触发因素是 CAE `writeInput()` 的节点坐标截断，两个极端病态薄片单元（78890、432458）是使微小扰动被放大为 Jacobian 反号/过小判定的必要脆弱条件。** 用精确坐标重建后，**01:20 版本的精确坐标全模型 C3D10 datacheck 通过（COMPLETED，无错误）**，且**无需对网格做任何改动**——C3D10 与 C3D4 基线为**同一源网格/同一拓扑、存在 CAE 序列化量级坐标差异**。**但当前待求解候选 `solver/m2_c3d10_quick_exact.inp`（01:26 已删 H-Drive，SHA-256 `bb255bcb…`）尚未绑定成功 datacheck（P1-1 未决）**：01:20 成功 datacheck 的输入字节已就地覆盖、哈希未记录、不可恢复。按复审门禁，需用户批准一次「最终输入验证专用 datacheck」（超出计划 2 次上限），或用户另作决定；同时可用内存 <20 GB 未达启动门。**本轮不启动任何求解。**

## 1. 已完成的环节

| 环节 | 状态 |
|---|---|
| Task 1 状态留档/资源门 | ✅ |
| Task 2 C3D10 升级器（TDD 8/8） | ✅ |
| Task 3 网格升级与预检（1,056,313 节点 / 576,628 C3D10，admission passed） | ✅ |
| Task 4 同设置模型构建（材料逐字节一致、u1=-9.6、静态检查通过） | ✅ |
| Task 5a 第一次 datacheck（CAE 写回 INP） | ❌ 致命错误（2 单元体积）→ 触发停止与最小复现 |
| Task 5b 最小复现 + 根因定位 | ✅ 直接触发 = CAE 坐标截断；薄片 = 必要脆弱条件 |
| Task 5c 精确坐标全模型 datacheck（01:20 版本，含 H-Drive） | ✅ **COMPLETED，无错误**（输入哈希未记录、已覆盖） |
| Task 5d 当前候选（01:26 删 H-Drive，`bb255bcb…`） | ⏸ **未绑定成功 datacheck（P1-1 待用户决策）** |
| Task 6 正式求解 | ⛔ 未启动（P1-1 未决 + 内存 <20 GB；硬门禁就绪） |
| Task 7-8 提取/比较 | ⏸ 待求解后执行 |
| Task 9 报告/自复审 | ✅ 本文件 + 第 8 轮复审修复 |

## 2. 根因结论（详见 `minimal_repro/ROOT_CAUSE.md`）

- 两个问题单元（78890、432458）在 C3D4 基线即存在，为近零厚度薄片（最短边 9.4e-6 / 1.96e-5 mm，长宽比 ~29k / ~16.5k）。
- **最小复现**：两单元 + 面邻接环（6 单元）分别做 C3D4/C3D10 datacheck → **均 COMPLETED**；C3D10 全检查点 Jacobian 恒正（det=6V）。→ 精确坐标下单元本身几何有效。
- **定位**：CAE `writeInput()` 写回 INP 时截断节点坐标（角点 ~3e-8 mm、**中点最多 ~9e-7 mm**）；对最短边 ~1e-5 mm 的薄片单元，该扰动使二次 Jacobian 在 Gauss 点反号（78890 在 2 个 Gauss 点 det(J)=-1.47e-8，见 `minimal_repro/findings.json` 机器可读数组）。
- **表述（复审 P2-7）**：CAE 截断是直接触发因素；极端薄片是使扰动被放大的**必要脆弱条件**——不是「非网格缺陷」的二选一排除。
- **比较身份（复审 P2-8）**：C3D10 与既有 C3D4 实际求解 INP 为**同一源网格/同一拓扑，存在 CAE 序列化量级坐标差异**（全局最大 ~1e-6 mm；薄片 78890 角点体积差 4.29%、432458 0.155%），列为局部敏感性限制，**不表述为逐坐标一致**。

## 3. 残余风险与预注册失败规则（复审 P2-13）

- **畸变单元风险量化**：61,976 / 576,628 = **10.748%** 的单元被 Abaqus 判为畸变（警告级）。这不是可忽略的边缘比例：畸变→局部病态刚度/误差；与超弹性材料不稳定警告叠加，增大非线性不收敛风险。
- **收敛背景事实**：相邻 M1、M3 分别在步时 0.108、0.124 因所需增量小于 `minInc` 失败；M2 C3D4 基线在步时 ~0.968 未完成完整步（仅覆盖 24.2%）。→ C3D10 正式求解失败概率不可忽略。
- **C3D10 完成门（复审 P1②，与 C3D4 基线不同）**：本求解终值 u1=-9.6 mm 已对应 24%，因此**最后接受步时必须达到 1.0**（允许明确浮点容差 `t_last >= 1.0 - 1e-6`），**且实际驱动面位移覆盖 `|U1|/40 >= 0.24`（即 |U1| >= 9.6 mm）**，两者同时满足才算覆盖 24% 目标窗口。`0.96` 只适用于 C3D4 基线从 25% 行程截取 24% 时的折算，**不适用于本 C3D10 求解**（步时 0.96 仅约 23.04%，会把未达标的求解误判为可比较）。
- **预注册失败规则（禁止外推与自动重试）**：若出现以下任一情形，比较判定一律记为**「无法判断」**，且**不得把部分曲线外推到 24%**、**不得自动放宽步长或重试**：
  1. 未满足上述 C3D10 完成门（最后接受步时 < 1.0−1e-6 或 `|U1|/40 < 0.24`）；
  2. 出现 Abaqus 明确报出的**负 Jacobian / 过度畸变**（`ErrElem...` 或等效求解级错误）——作为硬失败；
  3. 因 `minInc` 失败而终止。
- **「薄片附近异常能量集中」（复审 P2⑨）**：因求解前无法预先定义计算区域/变量/阈值，**降为诊断项而非硬失败门**。求解后如观测到单元 78890/432458 及其一环的 `SENER`/局部内能占比或异常倍数显著偏离整体，仅作诊断记录与因果讨论，不作为「无法判断」的独立触发条件。
- 即便结果改善，也只能说明「二阶单元/离散是重要候选因素」，不能证明作者实际 INP 一定使用该网格，也不能把相关性写成唯一原因。

## 4. datacheck 绑定状态（复审 P1-2，两个版本分别记录）

| 版本 | 时间 | 输入 SHA-256 | datacheck |
|---|---|---|---|
| 精确坐标（含 H-Drive） | 01:20–01:22 | **未记录**（输入字节已就地覆盖，不可恢复；重建哈希 `204eebe6…` 未经验证） | ✅ COMPLETED，无 ERROR |
| 当前待求解候选（删 H-Drive） | 01:26:57 | `bb255bcb9d210d227e4e56d9f0d70d774615c22d2802c10cf21ab1f9dca7a920` | ⏸ **NOT_BOUND**（P1-1 未决） |

- 当前候选的静态检查已通过（H-Drive 缺失、RF 场输出存在、能量 history 存在、u1=-9.6、仅材料 tpu-wenext）——见 `solver/solver_inp_static_check.json`。
- 「history 请求 19,884>10,000 警告已消失」目前是输入文本推断，不是当前候选的求解器证据；需最终 datacheck 证实。

## 5. 求解阻塞与启动条件

- **阻塞 1（P1-1）**：当前候选 `bb255bcb…` 未绑定成功 datacheck；最终输入验证 datacheck 超出计划 2 次上限，**须用户明确批准**（或用户另作决定）。01:20 输入哈希已不可恢复，「恢复同哈希输入」路径不可靠。
- **阻塞 2**：可用物理内存 <20 GB（复审时 19.53 GB）未达启动门。
- **启动条件（由硬门禁强制，见下）**：`solver/gate_state.json.run_allowed=true`（仅最终 datacheck 绑定该哈希且用户批准后置真）+ 无其他求解进程 + 可用内存 ≥20 GB + F 盘 ≥25 GB + 输入哈希等于绑定哈希；job 名独立 `m2_c3d10_quick_exact_solve`（不覆盖 datacheck 证据），CPU 4、内存 ≤70%、最长 8 小时、失败不重试。门禁链为 **fail-closed**：`check_solve_gates.ps1`（纯检查）+ `run_solve_exact.ps1`（编排），生产模式遇到任何测试环境变量即 exit 19 拒绝，`-CheckOnly` 实测 exit 11 = run_allowed=false；监控已接入启动链（见第 9 节）。

## 6. 证据索引（均在 `audits/m05_post_round6_20260921/m2_c3d10_quick_20260921/`）

- 报告与配置：`C3D10_QUICK_REPORT.md`（本文件）、`SETTINGS_DELTA.md`、`PREFLIGHT_REPORT.md`、`artifact_index.json`（含 final_candidate 索引）、`review_round8_20260922/REVIEW_REPORT.md`
- 网格：`scripts/upgrade_c3d4_to_c3d10.py`、`tests/`（8/8 通过）、`mesh/upgrade_report.json`、`mesh/mesh_admission.json`、`mesh/m2_class2_1383_volume_mesh_c3d10.inp`
- 模型：`solver/build_m2_c3d10_quick.py`、`solver/m2_c3d10_quick_exact.inp`（当前候选，`bb255bcb…`）、`solver/m2_c3d10_quick_exact_rb.inp`（重建含 H-Drive 版）、`solver/solver_inp_static_check.json`、`scripts/rebuild_exact_solver_inp.py`
- 根因证据：`minimal_repro/ROOT_CAUSE.md`、`minimal_repro/findings.json`（富化：CAE Jacobian 数组/坐标差/哈希）、`minimal_repro/mesh_c3d4.dat`、`minimal_repro/mesh_c3d10.dat`（均 COMPLETED）、`scripts/enrich_findings.py`
- datacheck：`solver/m2_c3d10_quick_exact.dat`（01:20 COMPLETED）、`solver/datacheck_findings.json`（failed/final 两记录）、`logs/datacheck_exact_run.log`
- 门禁：`solver/gate_state.json`（run_allowed=false）、`solver/run_solve_exact.ps1`（硬门禁 + 独立 job 名）

## 7. 执行停止点（当前）

按复审第 5 节门禁与用户指示：**本轮不启动任何求解**。P1-1（最终输入验证 datacheck / 恢复同哈希输入）与「M3 完成后是否自动启动求解」均待用户决策；决策后再推进 Task 6-8。

## 8. 第 9 轮复审修复记录（2026-09-22，不调用 Abaqus）——【历史记录】

> **本节为第 9 轮修复的历史记录，其中「10/10 PASS」「ABAQUS_MOCK_CMD」「监控五类终态 mock 测试 6/6」等表述已被第 10/11 节取代，请以第 10/11 节为准。** 第 11 轮将监控升级为受监督的状态机（waiting→running→terminal + 启动超时）、TestMode 收紧为结构上 no-Abaqus、门禁测试扩至 20/20、监控测试扩至 14/14（见第 11 节）。

- **门禁原始值比较**：`solver/check_solve_gates.ps1` 用未舍入原始 double 比较内存/磁盘，仅日志舍入显示；新增缺失输入(15)/空哈希(17)/缺 run_allowed(18)/非法 JSON(16) 非零退出路径。
- **门禁可测性与日志留档**：门禁拆为纯检查 `check_solve_gates.ps1` + `run_solve_exact.ps1`（支持 `-CheckOnly`、`ABAQUS_MOCK_CMD`、`exit $solveExit`）。`solver/test_gates.ps1` 用 mock 覆盖 5 类失败路径 + 非法 JSON + 缺失输入 + 成功路径（mock exit 0/5）+ 真实门禁拒绝，全部 10/10 PASS，日志存于 `logs/gate_tests/`；真实门禁 `-CheckOnly` 实测 exit 11，证据在 `logs/gate_state.log` 与 `logs/solve_run.log`。
- **C3D10 完成门（P1②）**：最后接受步时 `>= 1.0 - 1e-6` **且** `|U1|/40 >= 0.24`（u1=-9.6 即 24%）；0.96 仅用于 C3D4 截取 24%。**「薄片附近异常能量集中」降为诊断项**（P2⑨），不作为硬失败门。
- **静态检查结构化（P1③）**：`scripts/check_solver_inp.py` 改块级解析（field interval=40 + Node RF,U + Element LE,S,SENER；history interval=20 + Energy 7 变量；H-Drive 缺失），正负例测试 5 项通过；结果记录 `input_sha256/size/mtime/check_time`（P2④，当前 `bb255bcb…`）。
- **重建断言（P2⑤）**：`scripts/rebuild_exact_solver_inp.py` 断言 `_rb` 去掉 H-Drive 后与磁盘候选逐字节一致，不一致非零退出（实测 OK）。
- **哈希冻结（P2⑥）**：`artifact_index.json` 冻结 17 个最终候选工件（含 launcher/checker/enrich/两份核心 JSON/monitor/finalcheck runner 等）。
- **监控（P2⑧，第 10 轮已接入启动链）**：`solver/monitor_solve.ps1` 2–5 分钟采样 `.sta`/内存/磁盘，8 小时上限与资源停止门触发 `abaqus terminate`；由 `run_solve_exact.ps1` 在 Abaqus 前启动、`finally` 回收；以 `.lck` 消失判定作业结束并退出，在 `$SolverDir` 内 terminate 并传播退出码；五类终态（正常/失败/8h/低内存/低磁盘）mock 测试 6/6 通过（见第 9 节）。
- **最终 datacheck 预备（复审第 5/6 节）**：`solver/run_finalcheck_datacheck.ps1` 已准备未执行，独立 job 名 `m2_c3d10_quick_exact_finalcheck`（不覆盖 01:20 证据），受 `gate_state.json.finalcheck.approved=false` 门控（实测拒绝 exit 10）。
- **节点数（P2⑪）**：`SETTINGS_DELTA.md` 改为「170,385 角点 + 885,928 共享中点 = 1,056,313 节点」。
- **状态保持**：`gate_state.run_allowed=false` 不因静态检查通过或内存偶尔超 20 GB 而置真。

## 9. 第 10 轮复审修复记录（2026-09-22，不调用 Abaqus；`review_round10_20260922/REVIEW_REPORT.md`）

- **P1① 生产路径 fail-closed**：`check_solve_gates.ps1`、`run_solve_exact.ps1`、`run_finalcheck_datacheck.ps1` 生产模式（无 `-TestMode`）遇到任何 `GATE_TEST_*`/`ABAQUS_MOCK_CMD`/`MOCK_EXIT` 即 **exit 19 拒绝**；测试钩子仅在 `-TestMode` 下生效，且 `-TestMode` 拒绝读取生产授权文件 `gate_state.json`（exit 20）与生产输入。已实测：`production_refuses_test_env`→19、`testmode_refuses_prod_gate`→20。
- **P1② 输入绑定统一（check A / run B 关闭）**：`run_solve_exact.ps1` 与 `run_finalcheck_datacheck.ps1` 用 `Resolve-Path` 规范化一次，同一路径同时用于存在性、哈希校验与 `abaqus ... input=` 调用；`mock_abaqus.ps1` 断言 job/输入路径非空、文件存在并记录输入哈希，测试 `mock_input_binding` 验证传给执行命令的就是被哈希校验的候选（PASS）。
- **P1③ 监控接入启动链**：`run_solve_exact.ps1` 在 Abaqus 前启动 `monitor_solve.ps1`（Start-Process）并在 `finally` 回收；监控以 `<job>.lck` 消失判定作业结束并退出 0（不会等满 8 小时再对已结束作业 terminate），在 `$SolverDir` 内 terminate 并传播退出码；五类终态 mock 测试 6/6 通过（正常完成/求解失败/8h/低内存/低磁盘）。
- **P2④ mock 参数与绑定断言**：`mock_abaqus.ps1` 参数由保留名 `$input` 改为 `[Alias('input')]$InputFile`（此前 10 条调用记录的 `input=` 全为空），空值/文件缺失即 mock 失败（exit 90/91）。
- **P2⑤ 测试摘要冻结**：`test_gates.ps1`（13 项）与 `test_monitor.ps1`（6 项）每次写入独立时间戳目录 `logs/gate_tests/run_<ts>/summary.json`（无 BOM），记录各 case 期望/实际码、输入哈希、脚本哈希与总退出码；最新摘要 `run_20260922_090659`（gate 13/13）与 `run_20260922_090702`（monitor 6/6）已冻结入 artifact index。
- **P2⑥ 表述与证据同步**：门禁/监控表述已改为与上述 fail-closed、输入绑定、监控接线一致的证据状态（见第 5 节与本节）；artifact index 已按最终哈希重冻结。
- **状态保持**：`gate_state.run_allowed=false`、`finalcheck.approved=false`；当前候选 `bb255bcb…` 仍未绑定成功 datacheck（P1-1 待用户批准）。

## 10. 第 11 轮复审修复记录（2026-09-22，不调用 Abaqus；`review_round11_20260922/REVIEW_REPORT.md`）

- **P1① 监控升级为受监督的硬边界**：`monitor_solve.ps1` 改为 `waiting_for_start → running → terminal` 状态机——只有观察到 `.lck` 后才允许以消失判定「作业结束」；`StartupTimeoutSec` 内从未启动则 fail-closed（exit 2），不再把「尚未启动」误判为「已结束」。`run_solve_exact.ps1` 生产模式硬绑定唯一 monitor 路径并校验 `gate_state.monitor_sha256`（缺失/空/不匹配/不存在 → exit 19，绝不求解）；启动器轮询监督 Abaqus 与 monitor，monitor 在 solve 结束前非零退出 → fail-closed 正常 terminate 并合并退出码（monitor 失败优先）。新增测试：monitor 缺失(19)、从未启动(2)、monitor 崩溃(launcher→7)、terminate 非零(7)。
- **P1② TestMode 结构上 no-Abaqus**：`run_solve_exact.ps1` 与 `run_finalcheck_datacheck.ps1` 的 `-TestMode` 现要求显式 `-MockAbaqus` + `-MockTerminate` + 临时 `-SolverDir`（缺一 → exit 21）；finalcheck 增加对称 `-MockAbaqus`/`-CheckOnly`；生产模式拒绝所有 mock 参数（exit 19）。测试证明 TestMode 下不产生 `m2_c3d10_quick_exact_solve/finalcheck.*` 工件（`no_abaqus_artifacts_from_tests` PASS）。**（第 11 轮起该表述已加固：TestMode 只接受冻结哈希 mock、显式拒绝真实 `abaqus.bat` 与任意其他可执行文件——见第 11 节 `launcher_testmode_rejects_real_abaqus`/`finalcheck_testmode_rejects_real_abaqus` 均 exit 22。）**
- **P2③ terminate mock 修正**：`mock_terminate.ps1` 显式解析 `terminate` 动词与 `job=<name>`（不匹配 → exit 92）；`test_monitor.ps1` 按目标 job 精确断言（8h/mem/disk/term7 各 1 次，norm/fail/never 0 次），并新增 terminate 非零(7) 传播用例。
- **P2④ accepted run 冻结**：`artifact_index.json` 改用明确的 `accepted_run`，不再用会随时间失真的 `latest`；`generated_utc` 明确为 UTC 并注明 run_id 为本地时区。**（第 11 轮按第 12 轮复审更新为 gate `run_20260922_131018` 27/27、monitor `run_20260922_131056` 14/14，并记录 `generated_local` 与 `utc_offset=+08:00`，见第 11 节。）**
- **P2⑤ 文档口径**：本节与第 8 节历史标记使监控/门禁能力描述与实现一致（受监督状态机 + fail-closed 编排），不再超证据。
- **P2⑥ 监控日志可审计**：`monitor_solve.ps1` 显式 `-LogFile`；`test_monitor.ps1` 每 case 独立日志并写入 run 目录，summary 记录各 case 日志哈希 + mock terminate 日志哈希，随 accepted run 一起冻结。
- **状态保持**：`gate_state.run_allowed=false`、`finalcheck.approved=false`；当前候选 `bb255bcb…` 仍未绑定成功 datacheck（P1-1 待用户批准）。门禁测试 20/20、监控测试 14/14、Python 13/13 全绿，全部不调用 Abaqus。**（第 11 轮门禁/启动器扩至 27/27，见第 11 节。）**

## 11. 第 12 轮复审修复记录（2026-09-22，不调用 Abaqus；`review_round12_20260922/REVIEW_REPORT.md`）

- **P1① 监督任意提前退出 + 终止超时**：`run_solve_exact.ps1` 把 **monitor 在 solve 完成前的任何退出**都作为监督事件——exit 0 先给 solve 短 grace（`-MonGraceSec`），仍存活则再次正常 terminate；若 solve 在 `-TermWaitSec` 内仍不退出则强制停止并记录**专用监督失败码 90**（超时后不再读取未退出进程的 `.ExitCode`）。新增三类 launcher 测试：`launcher_monitor_early0`（0 提前退出→terminate→有界完成，exit 0）、`launcher_terminate0_solve_hangs`（terminate 返 0 但 solve 挂起→90）、`launcher_terminate7_solve_hangs`（terminate 返 7 且 solve 挂起→90）。
- **P1② TestMode mock 身份硬绑定**：新建 `solver/test_mock_allowlist.json`（冻结 `mock_abaqus.ps1`/`mock_terminate.ps1`/`mock_monitor_crash.ps1`/`mock_monitor_early0.ps1`/生产 `monitor_solve.ps1` 哈希）；`run_solve_exact.ps1` 与 `run_finalcheck_datacheck.ps1` 的 TestMode **只接受白名单内冻结哈希的 mock**，显式拒绝真实 `abaqus.bat` 与任意其他可执行文件（exit 22）；`-SolverDir`（solve）与 `-WorkDir`（finalcheck）必须已存在、为目录、位于 `$env:TEMP` 临时根下且非生产目录。新增测试：`launcher_testmode_rejects_real_abaqus`/`finalcheck_testmode_rejects_real_abaqus`（传真实 `abaqus.bat`→22）、`launcher_testmode_rejects_arbitrary_mock`（任意可执行→22）、`launcher_testmode_rejects_bad_solverdir`（非临时目录→22）。「结构上 no-Abaqus」现由 mock 身份校验保证，而非仅靠产物缺失推断。
- **P2③ artifact_index 哈希修正**：重算 24 项 `final_candidate` 工件（含新增 `test_mock_allowlist.json`、`mock_monitor_early0.ps1`），逐项与磁盘/ accepted 摘要脚本哈希核对后重冻结；`test_monitor.ps1` 哈希已更新为当前实际值。
- **P2④ 时间戳修正**：`generated_utc` 由 `datetime.utcnow()` 生成（`2026-09-22T05:12:12Z`），并记录 `generated_local`（`13:12:12`）与 `utc_offset`（`+08:00`，经 `time.timezone` 计算）。
- **P2⑤ accepted run 统一**：主报告与 PREFLIGHT 统一引用 gate `run_20260922_131018`（27/27）与 monitor `run_20260922_131056`（14/14）；`no-Abaqus` 表述按 P1② 加固为「TestMode 只接受冻结哈希 mock、真实 abaqus.bat 与任意可执行文件一律拒绝」。
- **P2⑥ run-scoped 日志片段**：`test_monitor.ps1` 将本轮 terminate 行写入 accepted run 目录 `mock_terminate_segment.log` 并单独哈希；`test_gates.ps1` 快照 `solve_run.log`/`finalcheck_run.log`/`solve_monitor_test.log` 基线并保存 run-scoped 片段与哈希入 summary。
- **状态保持**：`gate_state.run_allowed=false`、`finalcheck.approved=false`；当前候选 `bb255bcb…` 仍未绑定成功 datacheck（P1-1 待用户批准）。门禁/启动器测试 **27/27**、监控测试 **14/14**、Python **13/13**，全部不调用 Abaqus。
