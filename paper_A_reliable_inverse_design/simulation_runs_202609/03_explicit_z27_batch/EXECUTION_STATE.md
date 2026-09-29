# M08 execution state — 27-case explicit z batch
# plan: docs/superpowers/plans/2026-09-25-m08-explicit-z27.md
# (appended every ~15 min; newest entry at bottom)

## 2026-09-25 (session start)

- Environment verified: F:\SIMULIA\Commands\abaqus.bat (Abaqus 2025), F:/Anaconda/python.exe
  (gmsh 4.15.2 present), MATLAB F:\MATLAB\R2023b\bin\matlab.exe, F:\abaqus_scratch exists,
  32GB RAM (~21GB free at start), F: 3262GB free.
- gate0 fixture sha256 verified: a67890d0b115de28... (36 rows, 12/12/12). OK.
- selection_manifest_m08.csv written (27 rows): 12 zload12-selected + 15 supplements
  (rv-quantile rule over remaining 8 rows per class; rule text in manifest selection_reason;
  supplement picks verified by hand against fixture rv list).
- Ruling: gen_build_model.py output gets a 2-line text patch adding part-level node sets
  M05_ZDRIVE / M05_ZFIX (same bounding boxes as A_ZPOS/A_ZNEG) — required because ODB probe
  on m06_m1_1145.odb confirmed assembly sets (A_*) do NOT appear on inst.nodeSets, and the
  audited extract_odb.py hard-requires instance node sets. Part sets are extraction handles,
  not BCs; BCs still reference assembly sets A_*. Recorded in per-case build_patch.diff.
- Ruling: no extra history outputs beyond plan section 0-C (no fix-set RF3) — adapter patch
  surface strictly = step block / amplitude / BC block / output cards. Equilibrium evidence
  in Explicit = energy balance (ETOTAL vs ALLIE/ALLKE/ALLAE/ALLPD), documented in SUMMARY.

## 2026-09-25 23:25

- Adapter debugged against real CAE output (datacheck round-trip on m1_class1_1424):
  3 keyword fixes, each found by datacheck, recorded in adapter docstring:
  1) inc= not allowed on *Step for Explicit -> removed;
  2) *Fixed Mass Scaling requires TYPE with DT -> TYPE=BELOW MIN
     (only elements below dt target get scaled; ELEMENT BY ELEMENT / SEMI AUTOMATIC
     are not legal strings - datacheck errors preserved in datacheck dir);
  3) *Output,history forbids number interval in Explicit -> time interval=0.005 s
     (=T/20, same 20-interval semantics); *Restart,frequency card removed.
- m1_class1_1424 datacheck gate PASS (0 ***ERROR; 4 baseline warnings incl.
  HYPERELASTIC MATERIAL IS UNSTABLE; 83863 distorted elements = same count as M06).
- Workers launched (background, logs in scripts/): matlab_compile (18 geoms),
  mesh_worker (18 meshes), prep_dc_worker (build+adapt+check+datacheck all),
  solver_scheduler (2 concurrent, cpus=4 memory=6GB double=both, 16GB free-mem gate).
- First solve m08_m1_1424 launched 23:24 (pid 33600).

## 2026-09-25 23:55 — batch state + stop-rule ruling

- First solve m08_m1_1424 died at increment ~154 (step time 1.504e-4, i.e. 0.15% of T):
  ***ERROR: ratio of deformation speed to wave speed exceeds 1.0000; stable dt collapsed
  1e-6 -> 1e-14 (local element collapse). Same death for m1_class1_763.
- Counterexample in flight: m2_class2_1383 (M05-pilot mesh) alive at increment 13687,
  step time 13.5%, stable dt ~9.8e-7, PERCENT CHNG MASS 3.0e+03 (3000% = x31 mass,
  plan gate <1% MASSIVELY VIOLATED — recorded per case, parameter frozen by plan).
- Ruling (discipline 4 implementation): stop rule = 3 consecutive same-signature deaths
  AND no live run AND no healthy result ("系统性故障" = nothing works). A live/
  healthy counterexample defeats systematics; batch continues with per-case recording.
  If truly systematic, the stop still fires the moment no run is alive.
- MASS GATE note for report: fixed mass scaling dt=1e-06 (frozen) yields x31-x47 model
  mass on these meshes (PERCENT CHNG MASS column, .sta) — per-case record, no rerun.

## 2026-09-26 00:30 — batch running; incidents recorded

- m2_class2_1383 alive at ~24% step time (inc 25431), m3_class12_26 alive at ~12%
  (inc 12201); both progressing, stable dt ~1e-6 as designed, mass +3000%/+1665%
  (frozen dt=1e-06 scaling; gate violation recorded per case, no rerun).
- INCIDENT 1 (resolved): three scheduler instances ran concurrently 23:38-00:14
  (a kill command failed silently: bash expanded $_ inside the PS filter). Duplicate
  launches of 1383/26 at 00:10 aborted on the existing .lck (no run corrupted; their
  solve.log redirects were truncated - evidence intact in .log/.sta/.msg/.odb).
  Fix: all schedulers killed; single-instance lockfile (scripts/scheduler.lock) added;
  one scheduler restarted, adopted both in-flight jobs via lck scan.
- INCIDENT 2 (resolved): MATLAB compile driver died on m3_class12_759 during the
  0.6GB-free memory crunch; m03_response valid=False, no STL. Marked prep_failed
  (not retried, discipline 1/4). Driver now try/catch per case; relaunch compiles
  the 6 unattempted cases (1128, 1580, 1571, 1310, 1651, 1685).
- Orchestration memory guards added (solve priority, plan section 5): CAE build 6GB,
  datacheck 7GB, gmsh mesh 6GB, independent verify 14GB (verifier peak ~12GB, M06
  evidence). Workers/guards active.
- Pipeline counters: compile 11/18 (+1 failed 759), mesh+verify 2/18, datacheck
  PASS 11, solve finalized: 1424/763 solver_error (deformation-speed signature).

## 2026-09-26 02:00

- 1383 at 53.0% step time (wall 112 min), 26 at 39.0% (wall 106 min). Both alive;
  ETOTAL ~ -1e-5 N·mm (energy balance essentially closed); KE rising ~1.2 N·mm.
- Mesh pipeline: 45/871/138 verified+dc-passed; 1145 meshed, verifying. MATLAB: all
  17 geometries done (759 prep-failed). dc_pass=14. Memory guards regulating:
  verifier/prep run in gaps between solve memory footprints.

## 2026-09-26 06:45 — FIRST FULL EXPLICIT COMPLETION

- m2_class2_1383 COMPLETED T=0.1s (U3=-10.0, 25% strain, 21 frames, wall 395 min):
  judgment=completed_quasi_static_FAILED per plan gate (max ALLKE/ALLIE=98.8%,
  occurring at t=0.00055s early transient; ALLAE=0.0; ALLPD peak ratio 18.8%;
  ALLKE peak 1.19 vs ALLIE peak 89.1 N·mm -> late-time ratio ~1.3%, reported as
  diagnostic only, verdict unchanged). RF3 sum at 25% = -13.28 N, sigma -0.0083 MPa.
- m3_class12_26 alive at 62%, stable dt dropped to 1.7558e-7 (element distortion
  during deformation; fixed step-start scaling cannot prevent this) -> ETA ~19:00,
  will exceed the plan's 8h wall cap. Ruling: no force-termination of a progressing
  run (destructive, no retry allowed); over-8h recorded at termination, per
  zload-12 "不为赶报告强制终止" precedent.
- 26 is a reuse-mesh M3 design; 1383 a reuse-mesh M2 design; the two early deaths
  (1424/763) reuse-mesh M1 designs — deformation-speed fatality is design/mesh-
  local, not systematic (stop rule unaffected).

## 2026-09-26 08:35

- Preproc fully decided: 26/27 dc-pass (0 datacheck errors), 1 prep-failed (759).
- Solves: 5 finalized (3 early deaths with deformation-speed signature:
  1424/763/944 + m2_45; 1 full completion 1383 = completed_quasi_static_FAILED);
  2 long-runners: m3_26 at 73% (over the 8h wall cap at 07:46 — ruling recorded,
  left running), m3_61 at 48% (slowing, dt ~1.7e-7). 20 cases queued behind them.
- Deaths so far are all M1/M2-class; long-runners both M3-class.

## 2026-09-26 11:00

- Long-runners: m3_26 81.3% (wall >10h, ruling: left running), m3_61 65.2%.
  Both M3-class; slowing as dt degrades with distortion (dt ~1.5e-7).
- 20 cases queued; batch continues until queue drains.

## 2026-09-26 13:00 — BATCH PAUSED (user instruction via coordinator, 2026-09-26 ~12:40)

Pause executed:
- solver_scheduler / prep_dc_worker / mesh_worker processes KILLED; no new solves,
  no compile/mesh/datacheck activity (preproc was already fully decided:
  26 dc-pass, 1 prep-failed 759, mesh 26/27).
- Two in-flight solves left to finish naturally (explicit has no restart; killing
  = full rerun, forbidden):
  * m3_class12_26: ~88.6% of T at pause (inc 325737, wall 13h, over 8h cap per
    recorded ruling); lck present.
  * m3_class12_61: ~76.0% of T at pause (inc 212132, wall ~6h); lck present.
- Executor (this session) stays resident, monitors the two lcks, and on each
  termination runs extraction + ledger rebuild manually, then IDLES.
- Remaining queue at pause: 19 cases —
  M1 x6: m1_class1_1145, m1_class1_138, m1_class1_283, m1_class1_466,
         m1_class1_1128, m1_class1_1310
  M2 x7: m2_class2_833, m2_class2_871, m2_class2_1145, m2_class2_1267,
         m2_class2_1489, m2_class2_1580, m2_class2_1651
  M3 x6: m3_class12_74, m3_class12_540, m3_class12_1571, m3_class12_1685,
         m3_class12_1390, m3_class12_665
- RESUME entry point (exact, run in git-bash):
    cd F:/small++/paper_A_reliable_inverse_design/audits/m08_explicit_z27_20260925
    (F:/Anaconda/python.exe scripts/m08_solver.py > scripts/solver_scheduler.log 2>&1 &)
  The scheduler adopts any in-flight lck, skips solved cases, and launches in
  queue_order with unchanged config (cpus=4 memory=6GB double=both, 16GB free-mem
  gate, 2 concurrent). No parameter or plan change; paused state = nothing running
  except the two named jobs until they terminate.


## 2026-09-26 13:3x — 更正(协调侧核实)

- 此前 12:56 监控判定的 m3_26/m3_61 "STA TERMINAL" 为**误报**:Explicit 的 .sta 原地重写,文件尾部残留旧文本("THE ANALYSIS HAS COMPLETED SUCCESSFULLY"),grep/tail 命中了残影。
- 实时核实(13:28):m3_26 步时 0.08996(89.96%,增量 335,978,dt=1.36e-7)仍在推进;m3_61 同样在跑。两例未完成,**暂停策略不变**(不杀、自然跑完、队列不启动)。
- **教训:Explicit .sta 的完成判定必须取最后一条增量行的步时(≥0.1),禁止 grep 文本模式——残影文本会假阳性。**

## 2026-09-26 14:30 (paused, monitoring)

- m3_class12_26: 92.5% of T, wall 14.3h. dt ~1.35e-7. ETA ~18:00-19:00.
- m3_class12_61: 79.8% of T, wall 7.3h, but stable dt collapsed 1.37e-7 -> 6.95e-9
  (second local element collapse in slow motion). Progress 0.006%/10 min ->
  remaining 20% ≈ 100 h at current dt (dt may degrade further). Effectively
  dead-in-motion; left running per pause instruction (禁止终止). RESUME will need
  a decision: adopt as in-flight (blocks a concurrency slot for days) or record
  as practical-termination. Flagged for coordinator.

## 2026-09-26 16:50 (paused) — both in-flight jobs terminated

- m3_class12_26: THE ANALYSIS HAS COMPLETED SUCCESSFULLY (full T=0.1 = 25% strain,
  21 frames, wall 60180 s = 16.7 h; 2nd full completion). lck gone 16:42.
- m3_class12_61: ***ERROR: Process terminated by external request (SIGTERM or
  SIGINT received) at step time 8.004e-2 = 80.04% (wall ~9.6 h, dt had collapsed
  to 2.3e-9 -> effectively stalled). NOT terminated by this session (session
  killed only scheduler/worker pythons at 12:55, verified). Initiator unknown
  (user/system action on this machine). Recorded as external termination; ODB
  holds frames up to 80.04%; extracted as-is, no relaunch (no-retry discipline).
- Extraction + ledger rebuild for both follow; then session idles (queue 19
  frozen) until RESUME.


## 2026-09-26 16:5x — m3_61 practical-termination executed (user-approved option A)

- 协调侧执行:确认 4 个 explicit_dp PID 属 m08_m3_61(命令行核对)→ `abaqus job=m08_m3_61 terminate` 优雅终止(SIGTERM 由 sta 记录,非强杀)→ 进程清零;
- 数据保全超预期:history 刷盘到步时 0.080,**曲线提取覆盖 eps 23.55%**(RF3=-13.19N)≈ 24% 窗口的 98%;ODB 场帧到 0.075;
- results/(curve.csv/energies/npz)已由 m08_extract_case.py 产出;并发槽位已释放;m3_26 未受影响(终止时仍在 99.6% 收尾,自然结束);
- 队列恢复(今晚,待用户信号)时 m3_61 不再占槽;其 author 曲线对比(class12:61)留待 SUMMARY 统一计算。

## 2026-09-26 17:10 (paused) — both terminations processed, session IDLE

- Extraction + ledger done for both: m3_class12_26 = completed_quasi_static_FAILED
  (full 25%, 21 frames; wall 60180 s); m3_class12_61 = solver_error
  (externally terminated at 80.04%; ODB/npz/curve archived to 80.04%).
- batch_ledger.csv rebuilt: 27 rows. selection_manifest solver_status updated.
- artifact_index.json regenerated (post-extraction snapshot).
- PAUSED STATE: queue 19 frozen, no processes running (verified: no scheduler/
  worker/abaqus python/explicit_dp). Session idles until RESUME instruction.
  Resume entry point documented at 13:00 entry above.

## 2026-09-26 17:30 (paused) — m3_61 records corrected per coordinator alignment

- Correction: m3_61's SIGTERM was issued by the coordinator via
  `abaqus job=m08_m3_61 terminate`, user-approved 2026-09-26 ~16:4x (option A:
  practical-termination; dt collapsed to 2.3e-9, remaining 20% needed ~100h).
  NOT "unknown initiator" as previously recorded here.
- m3_61 judgment/manifest now = practical_terminated; stale .lck already absent
  (verified 0 lck files); scheduler adoption logic additionally skips any case
  with manifest solver_status == practical_terminated (belt and braces: solved()
  already prevents relaunch).
- Curve coverage correction: m3_61 curve covers eps 23.552% (98% of the 24%
  window), final RF3 sum -13.194 N — richer than the 80.04% step-time figure;
  this is the口径 for SUMMARY.
- Cross-check: m3_26 independent extraction by coordinator matches ours
  (25% full curve, RF3 sum -76.76 N).
- Still pending: possible "全域薄片清理" amendment with RESUME (awaiting user).
  Session idle.

## 2026-09-27 00:45 — RESUMED (user-approved, coordinator 00:3x)

- Deadline logic implemented in m08_solver.py: hard stop 2026-09-27 12:00
  (terminate all in-flight via `abaqus job=<job> terminate`, finalize with
  judgment=deadline_terminated, exit); projection gate after 10:00 (skip M2/M3
  whose class-median projection exceeds 12:00; M1 always eligible). Class
  medians from decided cases: M1 ~2 min, M2 ~198 min, M3 ~798 min.
- m3_class12_61 stays practical_terminated (adoption + launch both exclude it).
- Scheduler restarted; original meshes (no cleanup amendment in this window).
