# M05 M1/M3 Marlow+C3D4 验证实验指导

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 不自动委派、不自动提交 Git。
>
> **用户授权链**:2026-09-23 用户拍板"只要材料参数仿真数据对应就可以采用"(采纳 Marlow);对应性验证已通过(见 `audits/m05_post_round6_20260921/iteration_diagnosis/RESOLUTION_SLOW_SOLVE_20260923.md` 第七节:Marlow 对 1,202 点作者数据最大偏差 1.07%,优于作者 poly2 的 17.76% 一个量级)。本指导据此执行,不再等额外拍板;超出本指导的变更(网格、步长、容差、并行度)仍须停下问用户。

**Goal:** 在 M1、M3 的 C3D4 基线上,唯一变更为超弹形式 poly2→Marlow(材料数据、塑性表、几何、网格、BC、步设置全部不动),各做一次 Abaqus/Standard 求解,回答:**M1/M3 能否越过 poly2 时代窗口内的死亡点(步时 0.108/0.124)并覆盖 0–24% 目标窗口**,同时记录迭代数与墙钟,检验材料修复的普适性。

**背景(为什么这么做):** 根因链已定案——作者 poly2 卡经 Abaqus 拟合被判 UNSTABLE(单轴压缩 <-0.2305、双轴拉伸 >0.14 即失稳),M1/M3 因网格更密、局部更早越界,分别在 2.70%/3.09% 应变死于 minInc 地板(M1 伴 PLASTICITY ALGORITHM DID NOT CONVERGE)。Marlow 为 Abaqus 认证稳定的同数据形式。M2 的 Marlow 验证跑已于 2026-09-23 01:26 启动(`m2_marlow_validate_20260923/`),其结果可作交叉参照,但不阻塞本实验。

**Tech Stack:** Python 3.11/NumPy、Abaqus 2025/Standard、既有曲线导出脚本、PowerShell。

---

## 0. 结论边界与固定设置

本实验只回答:**同一 C3D4 网格上,把 poly2 换成 Marlow 后,M1/M3 能否走完 0–24% 窗口?**

固定不变(与各样本既有基线逐项一致):

- 样本身份:M1 `class1:944`、M3 `class12:665`,40 mm 立方,x 向加载,z 向梯度,条件 `M05-x-std-40mm-tpu-v1`;
- 网格:既有 C3D4 体网格,**不重划、不改单元**;
- 加载:x 驱动面 `u1=-10 mm`(工程压缩 25%),窗口 0–24% 对应步时 0.96;
- 边界:作者公开脚本的六面节点位移 BC,逐字不动;
- 步设置:`*Static, 0.01, 1., 0.001, 1.`、`nlgeom=YES`、`inc=1000`,逐字不动(**不改 minInc、不加增量数**——放宽重跑已证对 poly2 收益为零,Marlow 下如仍踩地板属实验结论而非参数问题);
- 材料:1,202 对 UniaxialTestData(仅原点行 (-0.0096, 0.) 清洗为 (0., 0.))、11 点 Plastic 逐字不动、仅 `*HYPERELASTIC` 卡改 MARLOW;
- 无接触、无稳定化;不同时修改网格密度、输出密度或误差门;
- poly2 基线不重跑,读取既有失败工件(M1/M3 `solver/` 下全部);
- 历史 `s1–s20` 单位仍未确认,一切"接近历史"只作 `s=N` 假设下的诊断,不升级为验收。

资源上限:

- 每样本 datacheck 最多 1 次、正式求解最多 1 次,**失败不自动重试、不改步长**;
- 默认**串行**(M1 完再 M3),单作业 `cpus=4, memory=6GB/进程(总上限 24GB)`;若用户明确要并行,才允许 2+2(`cpus=2, memory=6GB/进程`×2 作业);
- 单次求解最长 8 小时,到点按 Abaqus 正常终止(不用任务管理器强杀),保留全部文件;
- 启动门:可用物理内存 ≥20 GB、F 盘余量 ≥30 GB、无其他 Abaqus 求解进程;M2 验证跑若仍在跑,等待其结束或经用户同意后再启动;
- 磁盘新增每样本 ≤30 GB(ODB 预计 2–3 GB/样本,scratch 另计)。

本轮明确不做:M1/M3 的 C3D10、网格改动、机制标签派生/阈值冻结、基线替换、批量扩展、Git 提交、历史单位裁定。

## 1. 路径和交付物

| 别名 | 路径 |
|---|---|
| P | `F:/small++/paper_A_reliable_inverse_design` |
| N | `P/audits/m05_small_mechanism_pilot_20260919` |
| M1_BASE | `N/cases/m1_class1_944/solver/m1_small_repro.inp`(60,000,290 字节,1,066,696 C3D4) |
| M3_BASE | `N/cases/m3_class12_665/solver/m3_small_repro.inp`(53,944,821 字节,980,185 C3D4) |
| D | `P/audits/m05_post_round6_20260921/m1m3_marlow_c3d4_20260923/` |
| REF | `P/audits/m05_post_round6_20260921/iteration_diagnosis/RESOLUTION_SLOW_SOLVE_20260923.md`(根因与对应性证据) |
| M2_REF | `P/audits/m05_post_round6_20260921/m2_marlow_validate_20260923/`(M2 Marlow 验证跑,交叉参照) |

新建:

- `D/m1/m1_marlow.inp`、`D/m3/m3_marlow.inp`(变体 INP,各自 sha256 记录进 `D/artifact_index.json`);
- `D/scripts/make_marlow_variant.py`(带断言的变体生成器,规格见任务 2);
- `D/{m1,m3}/datacheck.log`、`{sample}.dat`(datacheck 版);
- `D/{m1,m3}/solve.log`、`monitor.log`、`.sta/.msg/.dat/.odb`(正式求解全工件);
- `D/{m1,m3}/results/curve.csv`(复用既有导出脚本链);
- `D/VALIDATION_REPORT.md`、`D/artifact_index.json`(工件哈希台账);
- `P/audits/m05_post_round6_20260921/batch_ledger.csv` 追加两行(M1/M3 各一行)。

## 2. 任务清单

### Task 1 预检

- [x] 确认无 `standard.exe/pre.exe` 进程;可用内存 ≥20 GB;F 盘余量 ≥30 GB;(预检 01:44 实况:M2 验证跑 standard.exe PID 31352 在跑=预期例外,本实验启动门在 Task 4 起跑时复检;当时可用内存 17.19GB<20GB,故正式求解必须等 M2 终态;F 盘余 3282GB 达标)
- [x] 记录 M1_BASE/M3_BASE 的 SHA-256 与字节数入 `artifact_index.json`;(M1 60,000,290B sha256 da1a87ab6b117ab60f2ee6e663f29e75b71df4cfb1e4e415035b6a3322df2828;M3 53,944,821B sha256 cab49958f456669de419b8a70ebf3cfc269a44d747135783cebeea7a017ce8ca)
- [x] 断言两个基线 INP 各含**恰好 1 处** `*Hyperelastic, n=2, test data input, poisson=0.47` 与**恰好 1 处**以 ` -0.0096,` 开头的数据行(防止改错行);
- [x] 从基线 INP 数出 `*Uniaxial Test Data` 与 `*Plastic` 之间的数据行数,断言 =1202。

### Task 2 生成 Marlow 变体 INP

- [x] `make_marlow_variant.py`:对每个基线做**且仅做**两处替换——
  1. `*Hyperelastic, n=2, test data input, poisson=0.47` → `*Hyperelastic, marlow, test data input, poisson=0.47`
  2. 原点行 ` -0.0096,     0.` → ` 0.,     0.`(作者曲线数字化噪声;Marlow 形式硬性要求原点 (0,0));
- [x] 脚本内置断言:替换计数各=1,否则非零退出;输出与基线做逐行 diff,**必须恰好 2 行差异**,多一行都算失败;(实测:两样本 diff 恰 2 行且恰为预期替换对,CRLF 逐字节保留,M1 60,002,902→60,002,900B、M3 53,944,821→53,944,819B)
- [x] 写出 `m1_marlow.inp`/`m3_marlow.inp` 并记录 SHA-256。(m1: f8093be2e8d5bb7d3a0062bb779948a8aab69714556d7f566086a22180c94fe2;m3: 94b94c4e41c73e4b22831e94850f1fbafb290dfcc7b7138f02dd93221f69ae52)

### Task 3 datacheck(每样本 1 次)

- [x] `abaqus.bat job=<sample>_marlow_dc input=<sample>_marlow.inp datacheck interactive`;
- [x] 验收:**COMPLETED、DAT 无 `***ERROR`、无 `UNSTABLE HYPERELASTIC`**(这是与 poly2 的决定性差异;畸变单元 WARNING 仍在,属预期,记录数量即可);(M1:COMPLETED/0 ERROR/0 UNSTABLE/畸变 120,560=11.31%;M3:COMPLETED/0 ERROR/0 UNSTABLE/畸变 94,156=9.61%,均与 poly2 基线网格数字一致)
- [x] 从 DAT 记录 `NUMBER OF ELEMENTS/NODES`、`TOTAL NUMBER OF VARIABLES`、直接法 `MINIMUM MEMORY REQUIRED / MEMORY TO MINIMIZE I/O`;(M1:1,066,696/314,708/944,124 变量,751MB/2469MB;M3:980,185/281,056/843,168 变量,683MB/2513MB)
- [x] **配置选择规则(确定性)**:若每进程 I/O 最优内存 ≤5 GB → `cpus=4, memory=6GB`;若 >5 GB → `cpus=2, memory=12GB`(总上限同为 24GB,速度约慢 1.3–1.5×)。选择与依据写入日志。(两样本 I/O 最优均 ≤5GB(2469/2513MB)→ 均选 cpus=4, memory=6GB,与 M2 实测稳定配置一致;依据已写入各自 datacheck.log)

### Task 4 启动 M1 正式求解

- [x] 写 `D/m1/run_solve.bat`:`cd /d <D/m1>` 后 `F:\SIMULIA\Commands\abaqus.bat job=m1_marlow input=m1_marlow.inp <选定配置> scratch=F:\abaqus_scratch interactive >> solve.log 2>&1`;(选定配置=cpus=4 memory=6GB,依据 Task 3 确定性规则)
- [x] **批处理转义教训(必读)**:bat 参数里**禁止出现 `%`**——`memory=20%` 的 `%` 会被解释器吞掉(M2 验证跑 attempt1 实测传入 `memory='20\abaqus_scratch'`),必须用绝对值如 `memory=6GB`,或写 `%%` 转义;启动前用 `.com` 文件核对 `'memory'/'cpus'/'scratch'` 三项实值;(01:56 核对 `m1_marlow.com`:'cpus':4、'memory':'6GB'、'scratch':'F:\abaqus_scratch' 三项实值与预期一致)
- [x] PowerShell `Start-Process -FilePath <bat> -WindowStyle Hidden` 脱离会话启动(不用 bash 前台挂长跑);(01:55:51 启动;pre 01:55:52→01:56:27;standard.exe 01:56:27 起)
- [x] 监控:60 s 采样 `.sta` 末行写 `monitor.log`,8 h 硬上限;记录启动时刻、首增量时刻。(monitor.sh 后台运行;首增量 inc1 于 01:57:50 前 4 迭代收敛至步时 0.0100)

### Task 5 M3 正式求解

- [x] M1 到终态(COMPLETED/NOT COMPLETED/8h 终止)并释放资源后,按 Task 3/4 同规格启动 M3;(M1 终态 02:13:33=exited with errors;M3 02:16:14 启动,.com 核对 'cpus':4/'memory':'6GB'/'scratch':'F:\abaqus_scratch' 通过,standard.exe 02:16:44 起,monitor.sh 后台运行)
- [x] 若用户中途明确要求并行,才允许 2+2 配置同时启动,其余不变。(条件未触发:用户全程未要求并行,保持串行 M1→M3)

### Task 6 终态判读与曲线提取

- [x] 终态证据:`solve.log` 的 `COMPLETED`/`exited with` 行、`.sta` 末行、`.msg` 末段,三者归档;(M1 02:13:33/M3 02:38:38 均 `Abaqus/Analysis exited with errors`;.sta 末行 minInc cutback+NOT COMPLETED;.msg ANALYSIS SUMMARY+JOB TIME 已归档于报告第二节)
- [x] 迭代统计:从 `.sta` 统计 attempt 行数、总迭代数、失败尝试数、cutback 数,与同样本 poly2 基线(M1:9 增量/36 迭代/4 cutback;M3:39 增量/349 迭代/5 cutback)并列成表;(M1:11 增量/77 迭代/4 cutback/均值 6.10;M3:8 增量/111 迭代/6 cutback/均值 8.14;表见 VALIDATION_REPORT.md 第二、四节)
- [x] 曲线:复用既有导出脚本链得 `results/curve.csv`(位移-反力,40 帧);失败未完成时同样导出已完成部分并注明步时;(M1 6 帧至 0.1156/M3 4 帧至 0.0637,pilot export_m2_results.py 原链复用)
- [x] 对照(全部标注 `s=N` 假设):① 对自身历史曲线 `class1:944`/`class12:665` 的 `s1–s20`(比值+光滑性,与 batch_ledger 旧口径一致:M1 1.37–1.39×、M3 1.70–1.71×);② 对自身 poly2 失败点之前已收敛帧;③ 与 M2 Marlow 验证跑的定性一致性(是否同样不再出现 7–10 迭代/增量的局部劫持)。(comparison.json 双样本;poly2 旧口径复现吻合校验通过;③ 劫持未消失且起点随网格移动,见报告第五节)

### Task 7 报告与台账

- [x] `VALIDATION_REPORT.md`:预注册成功判据逐条判定(见下)、迭代/墙钟表、三重对照、与根因链的印证或矛盾、遗留问题;(已写:主判据双 FAIL,M1 越点 PASS/M3 FAIL,失败模式 A 双确认,建议网格质量线)
- [x] `batch_ledger.csv` 追加 M1/M3 两行(格式沿用现有列);`artifact_index.json` 冻结全部新工件哈希;(两行已追加,CSV 校验 6 行×9 列;58 个新工件 sha256 已冻结)
- [x] **不替换基线**:`N/` 下 poly2 工件原样不动;是否把 Marlow 转正为新基线由用户在看到 M2+M1+M3 三份验证结果后另行拍板。(全程未写 `N/`,本实验仅读)

## 3. 预注册成功判据(写报告前不许改)

- **主要判据(每样本独立)**:步时达到 ≥0.96(24% 窗口覆盖)或步时 1.0 COMPLETED,且终止原因**不是** minInc 地板;
- **次要判据**:越过各自 poly2 死亡点(0.108/0.124);平均迭代数/增量 ≤5(M2 poly2 时代为 7–10);墙钟记录在案;
- **失败模式 A**(Marlow 仍 minInc 死亡且位置与 poly2 同区):结论=材料形式不是 M1/M3 的控制性因素,升级到网格质量线(局部退化单元治理),**不得**当场改网格重跑;
- **失败模式 B**(内存/系统终止):记录 DAT 内存需求与实际峰值,按配置规则降档后**经用户同意**再试一次;
- 曲线比较只做诊断口径(`s=N` 假设),无论结果如何不写"更接近历史/验证通过历史"这类验收措辞。

## 4. 预期与预算(诚实区间,不承诺)

- 规模:M1/M3 约 100 万/98 万 C3D4,约为 M2 的 1.7–1.85 倍;按 M2 实测 4 进程 ~4.3 s/迭代折算,**单次迭代约 7–10 s**;
- 时长:若 Marlow 使增量回到健康形态(2–4 迭代/增量、dt 可长大到 0.025),估计 **1.5–3 h/样本**;若末段仍需小步长,可能显著更长——这本身就是实验要测的量,不是失败;
- 磁盘:每样本 ODB 2–3 GB + scratch,预留 30 GB;
- 风险:两样本 9.6–11.3% 畸变单元仍在,Marlow 只消除材料侧失稳,网格侧病态(薄片、退化簇)可能仍拖慢末段——若出现,属失败模式 A 的证据,如实记录。

---

## 5. 第 1 轮 Codex 复审返修补记(2026-09-23,不改动上方预注册判据)

Codex r1 审核结论:数据/哈希/台账/判据核验全部正确,**不通过原因是分类与结论表述越界**。三点处置(全部采纳,原文见 `P/coordination_review/codex_review_r1.md`,该目录只读):

- **P0 因果收窄**:报告/执行状态中"网格侧病态单独足以/是控制性因素"的表述已收窄为——**本实验能支持的结论仅是"本次 Marlow 替换不足以使现有配置覆盖目标窗口"**;网格侧病态降为**待检验假说**(固定网格、单改材料卡的设计无网格干预对照,不能证明其独立充分性,也不能排除材料与其他因素的交互);升级网格质量线保留为下一步建议,其判定需局部热区治理前后的受控对照。
- **P0 M3 单列**:撤回"失败模式 A 更强形态"的事后扩展。M1 与 A 定性相容(0.108→0.116,但计划未定义"同区"的量化范围,如实披露);M3 单列为"minInc 失败且终点明显提前(0.124→0.0637,−48.6%),预注册 A 的位置条件未能确认"。第 3 节预注册判据原文保持不变。
- **P1 内存表述**:撤回"内存峰值远低于 24GB"——两份 `.msg` 的 `MEMORY PEAK (GB)` 字段为 0,不可作峰值证据;改为"本轮未见内存/系统终止;实际峰值未可靠量化";第八节由早期失败推断"资源充足"的表述同步收窄,后续网格变更实验须重新预检资源(含峰值观测手段)。

修正落点:`m1m3_marlow_c3d4_20260923/VALIDATION_REPORT.md`(§一/§三/§五③/§六/§七/§八-5)、`EXECUTION_STATE.md`(4 处 + 返修日志);台账数据行数值/状态/证据字段经 Codex 核验一致;但 r2 复审指出 notes 中的英文旧裁定(material form not controlling / failure mode A stronger form / mesh-side pathology controlling)与收窄后报告冲突,已在 r2 返修中以"supersedes"方式修正,原始数值与证据字段未动。24/24 checkbox 已勾。追加标记:`CODEX_R1_FIXES_DONE`(见 EXECUTION_STATE.md)。
