# EXECUTION_STATE — m1m3_marlow_c3d4_20260923

计划文件:`docs/superpowers/plans/2026-09-23-m05-m1m3-marlow-c3d4-validation.md`(checkbox 为跨会话状态载体)
本文件由执行会话追加维护;若会话中断,下个会话以本文件+计划 checkbox 无损接手。

## 会话 1(2026-09-23 01:43 起)

- 01:44 环境核实:M2 验证跑 `m2_marlow_validate` 在跑(standard.exe PID 31352,~1.9GB;SMALauncher PID 26996),solve.log 尾部无 `=== exit`;M2 .sta 至步时 0.359(inc 20,9 迭代,dt 0.009375)。M2 于 01:26 启动,8h 上限即最晚 09:26 终态。
- 01:44 资源:可用物理内存 17.19GB / 总 31.78GB(M2 占用中);F 盘余 3282.7GB;C 盘余 565GB。判定:M2 求解期间 ≥16GB,datacheck 可做;正式求解门(≥20GB)等 M2 终态后复检。
- 01:44 Task 1 预检 PASS(`scripts/precheck_task1.py`,exit 0):
  - M1_BASE 60,000,290B sha256 `da1a87ab6b117ab60f2ee6e663f29e75b71df4cfb1e4e415035b6a3322df2828`
  - M3_BASE 53,944,821B sha256 `cab49958f456669de419b8a70ebf3cfc269a44d747135783cebeea7a017ce8ca`
  - 断言:hyper 卡各恰 1、` -0.0096,` 开头行各恰 1、Uniaxial→Plastic 间数据行各 1202,全过;origin 行精确字节 `b' -0.0096,     0.'`(CRLF 文件)
- 01:45 裁定(Ruling):Task 1 "确认无 standard.exe/pre.exe" 与 M2 在跑并存——按协调指令,M2 是本实验的资源门前置条件,其进程不算违规;本实验自己的启动门在 Task 4/5 起跑时逐一复检(无其他求解进程、内存≥20GB、磁盘≥30GB)。若 M2 在 09:26 后仍无终态,停下写本文件并汇报,不擅自处理 M2。
- 01:48 裁定(Ruling):计划 M1_BASE 字节数"60,000,290"为笔误,实测 60,002,902B(数字换位);M3 与计划一致 53,944,821B。哈希与断言为准,不影响任何结论。
- 01:50 Task 2 PASS(`scripts/make_marlow_variant.py`,exit 0):两变体与基线逐行 diff 恰 2 行且恰为预期替换对(hyper 卡→marlow、origin→(0,0)),CRLF 逐字节保留;`m1/m1_marlow.inp` 60,002,900B sha256 `f8093be2e8d5bb7d3a0062bb779948a8aab69714556d7f566086a22180c94fe2`;`m3/m3_marlow.inp` 53,944,819B sha256 `94b94c4e41c73e4b22831e94850f1fbafb290dfcc7b7138f02dd93221f69ae52`;均入 artifact_index.json。
- 01:50 裁定(Ruling):datacheck 命令在计划模板基础上追加 `memory=4GB` 上限,保护并行中的 M2 求解不被挤占(计划模板未规定 datacheck 内存;该参数不影响模型/步/网格,也不影响 DAT 中的内存需求估计值)。

- 01:52 Task 3(M1 datacheck)PASS:`m1/m1_marlow_dc` COMPLETED,0 `***ERROR`,0 `UNSTABLE HYPERELASTIC`(与 poly2 的决定性差异),WARNING 3 条全为畸变类,畸变 120,560/1,066,696=11.31%(与 poly2 基线一致,网格未动);规模 1,066,696 单元/314,708 节点/944,124 变量;内存估计(单进程分解,每进程)min 751MB / I/O 最优 2469MB → 确定性规则选 **cpus=4, memory=6GB**(≤5GB 档)。验收记录已附 `m1/datacheck.log`。
- 01:55 **M2 验证跑到达终态(交叉参照,重要)**:`Abaqus/Analysis exited with errors`——`THE ANALYSIS HAS NOT BEEN COMPLETED`,止于 inc 23 / 步时 **0.362**(9.05% 应变),末 attempt 为 minInc=0.001 地板上的 cutback(1U,9 迭代);摘要:23 增量 / 6 cutback / 181 迭代 / 墙钟 1440s;内存峰值行 MEMORY PEAK=0(msg 口径)。M2 poly2 时代死于 0.968,Marlow 反而死于更早的 0.362——材料失稳消除后死亡点提前且仍在窗口内,与"网格侧病态为待检验假说"的方向一致(本实验无网格干预对照,不能确证控制性)。M2 的判读属 M2 会话职责,本实验只作参照记录。
- 01:55 Task 3(M3 datacheck)PASS:`m3/m3_marlow_dc` COMPLETED,0 ERROR,0 UNSTABLE,畸变 94,156/980,185=9.61%(与 poly2 基线一致);规模 980,185/281,056/843,168;内存估计 min 683MB / I/O 最优 2513MB → **cpus=4, memory=6GB**。记录已附 `m3/datacheck.log`。
- 01:56 Task 4 启动门复检:M2 终态 ✓(01:51 exited with errors);无 standard.exe/pre.exe/SMALauncher 残留 ✓(datacheck 进程已退出);可用物理内存 20.37GB ≥20GB ✓(MemLoad 35%);F 盘余 3282GB ≥30GB ✓;scratch F:\abaqus_scratch 存在 ✓;m1/m3 目录无 .lck 残留 ✓。→ 允许启动 M1 正式求解(唯一一次,不重试)。

- 01:58 Task 4 已启动并核实:M1 正式求解(唯一一次)01:55:51 经 PowerShell Start-Process 脱离启动;`m1_marlow.com` 三项实值核对通过('cpus':4 / 'memory':'6GB' / 'scratch':'F:\abaqus_scratch',无 % 转义问题);pre 35s;standard.exe 01:56:27 起;首增量 inc1 4 迭代收敛至步时 0.0100(poly2 时代同区为 7-10 迭代/增量,4 属健康形态)。`monitor.sh` 已后台运行(60s 采样→monitor.log,8h 上限),终态即通知。
- 02:08 M1 关键检查点:**已越过 poly2 死亡点 0.108**(inc8 于步时 0.113 收敛,10 迭代)。轨迹:inc1-5 各 3-4 迭代健康收敛(dt 长到 0.025,至 0.075);inc6 起 10 迭代/增量 + 周期性 1U cutback(dt 缩到 0.00625→0.0015625),在 0.10-0.116 区间艰难推进。内存最低 15.09GB 可用,求解健康运行。
- 02:14 **M1 正式求解终态(唯一一次,未重试)**:`Abaqus/Analysis exited with errors`(02:13:33);`.sta` 末行 `1 11 2U ... 0.116 0.001000` → `THE ANALYSIS HAS NOT BEEN COMPLETED`;`.msg`:11 增量 / 4 cutback / 77 迭代 / 墙钟 1006s;错误签名 = `TIME INCREMENT REQUIRED IS LESS THAN THE MINIMUM SPECIFIED`(minInc 地板;**无** poly2 时代的 PLASTICITY ALGORITHM DID NOT CONVERGE);分析中 WARNING 仅 2 条(均为 alternate tolerance 接受)。**越过 poly2 死亡点 0.108(至 0.116,+0.008 步时)**,但仍在窗口极早段(2.90% 应变)以 minInc 死亡 → 与预注册失败模式 A 同征(Marlow 仍 minInc 死亡且与 poly2 同区)。M2 参照:poly2 死 0.968 → Marlow 死 0.362;M1:poly2 死 0.108 → Marlow 死 0.116。两样本方向相反但均为 minInc 终局。
- 02:14 Task 5 启动门:M1 进程已退,无 standard.exe/SMALauncher 残留 ✓,可用内存 20.84GB ≥20GB ✓ → 启动 M3(唯一一次)。M3 于 02:16:14 经 Start-Process 启动,`m3_marlow.com` 三项实值核对通过('cpus':4/'memory':'6GB'/'scratch':'F:\abaqus_scratch'),standard.exe 02:16:44 起,monitor.sh 后台运行。
- 02:25 Task 6(M1 部分)完成:
  - 迭代统计(scripts 内联统计,.sta 逐行):14 attempts=10 收敛+4 cutback;总迭代 77(与 .msg 一致);收敛增量 10;末收敛步时 0.116;收敛增量迭代数 [4,4,3,4,4,10,10,10,10,2],均值 6.10,峰值 10。对照 poly2(M1:9 增量/36 迭代/4 cutback,死 0.108)。
  - 曲线导出:`m1/results/curve.csv` 6 帧(0→0.1156 步时),链路=pilot `export_m2_results.py`(abaqus python),M05_DRIVE 默认参数;末帧 RF=-12.373N。
  - 三重对照(`m1/results/comparison.json`,脚本 `scripts/compare_marlow_curves.py`,s=N 诊断口径):
    ① vs 历史 class1:944(sheet class1 row 944):Marlow 比值 1.286@1.25%→1.369@2.5%;poly2 同口径 1.367→1.394(与旧台账 1.37–1.39 吻合=口径复现验证通过);Marlow 略软于 poly2 相对历史。
    ② vs 自身 poly2 已收敛帧(0.625%→2.5%):比值 0.859→0.982,随应变单调收敛。
    ③ 与 M2 Marlow 定性一致:均无材料失稳签名(M1 无 PLASTICITY ALGORITHM 错误),但均 minInc 终局。
- 02:25 M3 求解中:02:16:44 standard.exe 起,inc3 步时 0.025(3 迭代),健康段与 M1 同形态。

- 02:52 Task 6(M3 部分)完成:M3 统计——13 attempts=7 收敛+6 cutback;总迭代 111(与 .msg 一致);收敛增量 7;末收敛步时 0.0637;收敛增量迭代数 [4,4,3,10,10,16,10] 均值 8.14 峰值 16;曲线 4 帧至 0.0637(RF -17.993N);对照(`m3/results/comparison.json`):vs 历史 1.643@1.25%(poly2 同口径 1.701–1.714,与旧台账吻合),vs poly2 0.902→0.966。
- 02:55 **M3 正式求解终态(唯一一次,未重试)**:`Abaqus/Analysis exited with errors`(02:38:38);.sta 末 `1 8 2U ... 0.0637 0.001000` → NOT COMPLETED;.msg:8 增量/6 cutback/111 迭代/墙钟 1299s;错误=minInc 地板,无 PLASTICITY 错误;3 条 alternate-tolerance 接受。**未到 poly2 死亡点 0.124 即死(0.0637)** → M3 单列:minInc 失败且终点明显提前(0.124→0.0637),预注册失败模式 A 的位置条件("与 poly2 同区")未能确认,不做事后扩展分类。
- 02:58 Task 7 完成:`VALIDATION_REPORT.md` 已写(预注册判据:主判据 M1/M3 双 FAIL;越点 M1 PASS/M3 FAIL;均值迭代双 FAIL;M1 与 A 定性相容("同区"未量化)、M3 单列;建议下一步开网格质量线,网格病态为待检验假说);`batch_ledger.csv` 追加 2 行(校验 6 行×9 列);`artifact_index.json` 冻结 58 个新工件哈希;`N/` 全程未写。
- 02:58 **实验全部完成,无遗留进程**。终局判定:poly2→Marlow 消除材料失稳签名(datacheck 0 UNSTABLE、无 PLASTICITY 错误),但 M1/M3(及 M2 参照)仍 minInc 死亡且位置随网格移动——本次 Marlow 替换不足以使现有配置覆盖目标窗口;网格侧病态列为待检验假说(固定网格单改材料的设计无网格干预对照,不能证明其独立充分性或控制性)。下一步(需用户拍板):网格质量线(局部退化单元治理)另立计划;Marlow 是否转正待三份验证齐备后用户裁定。

- 04:2x **Codex r1 复审返修完成(协调者转交,审核原文=`P/coordination_review/codex_review_r1.md`,该目录未改动)**。结论:数据/哈希/台账/判据核验全对,不通过原因是分类与结论表述越界。三点全部采纳:① P0 因果收窄——VALIDATION_REPORT §一/§三/§五③/§六/§七 的"网格病态单独足以/控制性因素"改为「本次 Marlow 替换不足以使现有配置覆盖目标窗口」+ 网格病态=待检验假说(无网格干预对照);② P0 M3 单列——撤回"A 更强形态",改为「minInc 失败且终点明显提前(−48.6%),预注册 A 位置条件未能确认」,M1 保留 A 但披露"同区"未量化;③ P1 内存——撤回"内存峰值远低于24GB",改为「本轮未见内存/系统终止;实际峰值未可靠量化」(.msg MEMORY PEAK=0 不可作证据),§八-5 资源外推同步收窄。修正落点:VALIDATION_REPORT.md 六节、本文件 4 处、计划文档补记一节;台账 r1 时仅做了中文关键词检索,漏检 notes 中的英文越界措辞;Codex r2 指出后已修正(见下方 r2 条目)。coordination_review/ 只读未动;预注册判据原文未改。
CODEX_R1_FIXES_DONE

- 06:5x **Codex r2 复审返修完成(审核原文=`P/coordination_review/codex_review_r2.md`,该目录未改动)**。结论:报告主体返修到位、判据未改、58/58 哈希匹配;剩三处收尾,全部采纳:① **P0 台账 notes**:第 5/6 行(M1/M3)的英文旧裁定(`material form not controlling` / `failure mode A stronger form` / `mesh-side pathology controlling`)与收窄后报告冲突——r1 时我只做了中文关键词检索故漏检。已按"保留原始数值、状态、证据字段,verdict 子句显式标注 supersedes 并改为收窄结论(M3 单列、A 位置条件未确认、网格病态=待检验假说)"修正,CSV 6 行×9 列完整性校验通过;② **P1 报告 §六**:"材料失稳清除后"改为「本轮未再出现上述材料相关警告/错误签名,但仍发生收敛失败」;③ **P2 报告 §八-5**:"6%/1.6%进程"改为工程应变口径「2.89%/1.59%,占 24% 目标窗口的 12.04%/6.63%」(由末收敛步时 0.115625/0.063671872 换算)。同步纠正两处"台账无越界措辞"的不实记载:本文件 r1 条目与计划文档 §5 补记。coordination_review/ 只读未动;预注册判据原文未改。
CODEX_R2_FIXES_DONE

- 09:5x **协调循环终局确认(本会话核验 STATE.md)**:Codex r3 复审=**通过**(无新增 P0/P1/P2,r2 三项+两处连带纠正全部确认闭环,58/58 哈希独立复算 MATCH);state=DONE、round=3(终),协调自动化已删除。循环遗留待用户拍板:①网格质量线立项;②Marlow 是否转正(三份验证已齐)。**离线诊断新增(只读,获批前允许项)**:`scripts/locate_m3_hotzone.py` 定位 M3 劫持热区——主残差节点 8095/12312/13910(占 88% 提及),后两者共享 quality=0.00028 薄片单元,坐标 (19.9,10.3,-19.5) 贴 x=+20 加载面/z=-20 边界;12312 与 poly2 时代主残差节点为同一节点→同簇网格病态跨本构劫持收敛(网格假说的坐标级证据)。**网格质量线实验指导草案已写**:`docs/superpowers/plans/2026-09-23-m05-m3-hotzone-mesh-quality-draft.md`(仅计划,执行待用户批准;Task 1 离线诊断为获批前唯一可推进项)。
