# Small++ GitHub Synchronization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a verified `small++` branch containing all current TPMS work, a TPMS-only curated file set, and an accurate bilingual-entry README, then push it to `zyql8087/small-`.

**Architecture:** Start from the clean, latest TPMS lineage at `codex/paper-a-gc-graphformer`, replay the approved origami-removal commit, and import only named TPMS files from the other worktrees. Keep generated repowiki, large artifacts, and legacy origami material out of the branch; verify both the scientific code and the final Git object published remotely.

**Tech Stack:** Git/GitHub CLI, PowerShell, Markdown, Python 3 with pytest, MATLAB R2023b

---

## File map

**Create on `small++`:**

- `README.md`: repository entry point for the mechanism-resolved graded-TPMS direction.
- `paper_A_reliable_inverse_design/docs/CURRENT_PAPER_A_PLAN.md`: current authoritative Paper A plan.
- `paper_A_reliable_inverse_design/docs/reports/2026-07-31-advisor-discussion-report.md`: advisor-facing research rationale.
- `paper_A_reliable_inverse_design/docs/superpowers/plans/2026-07-29-m01-v5-contract-hardening.md`: retained M01 implementation history.
- `paper_A_reliable_inverse_design/docs/superpowers/specs/2026-07-31-paper-a-mechanism-resolved-attainability-design.md`: formal current research design.
- `paper_A_reliable_inverse_design/docs/PROJECT_RECORD_AND_LEARNING_GUIDE.md`: project-level evidence and learning guide.
- `paper_A_reliable_inverse_design/docs/README.md`: Paper A documentation index.
- `paper_A_reliable_inverse_design/tools/build_paper_a_framework_docx.py`: framework-document generator retained from the detached worktree.
- `paper_A_reliable_inverse_design/.qoder/README_A2_STATUS.md`: rewritten current status and authority notice.
- `paper_A_reliable_inverse_design/.qoder/academic_skills_config.md`: manually maintained research-skill configuration.
- `docs/superpowers/specs/2026-08-27-small-plus-github-sync-design.md`: approved synchronization design, cherry-picked from the source branch.
- `docs/superpowers/plans/2026-08-27-small-plus-github-sync.md`: this implementation plan, cherry-picked from the source branch.

**Modify on `small++`:**

- `.gitignore`: add a repository-wide `**/.qoder/repowiki/` rule.
- `paper_A_reliable_inverse_design/geometry_compiler_matlab/docs/SIMULATION_EXPERIMENT_MEMORY.md`: link the project record and learning guide.

**Preserve from the base lineage:**

- `paper_A_reliable_inverse_design/geometry_compiler_matlab/`: M01–M04 MATLAB geometry compiler, Gate-0, and tests.
- `paper_A_reliable_inverse_design/gc_graphformer/`: contracts, graph construction, baselines, Graph Transformer, and constrained diffusion interface.
- `paper_A_reliable_inverse_design/tests/`: Python model and contract tests.

### Task 1: Create the isolated integration worktree

**Files:**

- Create worktree: `F:\small++\.worktrees\small-plus-sync`
- Create branch: `small++`

- [ ] **Step 1: Confirm the branch and worktree target are unused**

Run:

```powershell
git branch --list 'small++'
Test-Path -LiteralPath 'F:\small++\.worktrees\small-plus-sync'
```

Expected: no branch output and `False` for the path.

- [ ] **Step 2: Create the worktree from the latest TPMS lineage**

Run:

```powershell
git worktree add -b 'small++' 'F:\small++\.worktrees\small-plus-sync' 'codex/paper-a-gc-graphformer'
```

Expected: Git reports a new branch at commit `fd4176f`.

- [ ] **Step 3: Verify the new branch identity**

Run in `F:\small++\.worktrees\small-plus-sync`:

```powershell
git status --short --branch
git log -1 --oneline
```

Expected: `## small++` and `fd4176f docs: record first GC-GraphFormer algorithm milestone`.

### Task 2: Replay the approved cleanup and workflow documents

**Files:**

- Delete through commit replay: legacy `origami_experiments/`, `demo_data/`, `output/`, and `evidence/` content.
- Modify through commit replay: `.gitignore`, `README.md`.
- Create through commit replay: synchronization design and implementation plan.

- [ ] **Step 1: Replay the TPMS-only cleanup**

Run:

```powershell
git cherry-pick db0d239
```

Expected: cherry-pick succeeds or stops only on `README.md`/`.gitignore`; any conflict is resolved by retaining TPMS content and deletions of origami material.

- [ ] **Step 2: Replay the approved design**

Run:

```powershell
git cherry-pick 2bc7ead
```

Expected: one new design-document commit.

- [ ] **Step 3: Replay this implementation plan from the source branch tip**

Run:

```powershell
git cherry-pick paper-a/matlab-gyroid-m03-continuous-csg-design
```

Expected: one new plan-document commit, with no unrelated untracked files.

- [ ] **Step 4: Prove the milestone history is retained**

Run:

```powershell
git merge-base --is-ancestor be24186 HEAD
git merge-base --is-ancestor d2e45e6 HEAD
git merge-base --is-ancestor fd4176f HEAD
```

Expected: every command exits `0`.

### Task 3: Import only the approved cross-worktree TPMS material

**Files:**

- Create the ten named TPMS documents/configuration/tool files in the file map.
- Modify `paper_A_reliable_inverse_design/geometry_compiler_matlab/docs/SIMULATION_EXPERIMENT_MEMORY.md`.
- Modify `.gitignore`.

- [ ] **Step 1: Copy the six authoritative files from the current workspace**

Copy these exact sources into the same relative paths under `F:\small++\.worktrees\small-plus-sync`:

```text
F:\small++\paper_A_reliable_inverse_design\.qoder\README_A2_STATUS.md
F:\small++\paper_A_reliable_inverse_design\.qoder\academic_skills_config.md
F:\small++\paper_A_reliable_inverse_design\docs\CURRENT_PAPER_A_PLAN.md
F:\small++\paper_A_reliable_inverse_design\docs\reports\2026-07-31-advisor-discussion-report.md
F:\small++\paper_A_reliable_inverse_design\docs\superpowers\plans\2026-07-29-m01-v5-contract-hardening.md
F:\small++\paper_A_reliable_inverse_design\docs\superpowers\specs\2026-07-31-paper-a-mechanism-resolved-attainability-design.md
```

Expected: only the named files are copied; `F:\small++\.qoder\repowiki` and `paper_A_reliable_inverse_design\.qoder\repowiki` are not copied.

- [ ] **Step 2: Copy the detached-worktree tool**

Source:

```text
C:\Users\48186\.codex\worktrees\76f1\small++\paper_A_reliable_inverse_design\tools\build_paper_a_framework_docx.py
```

Destination:

```text
F:\small++\.worktrees\small-plus-sync\paper_A_reliable_inverse_design\tools\build_paper_a_framework_docx.py
```

Expected: the Python tool exists at the destination and no `.qoder/repowiki` material is transferred.

- [ ] **Step 3: Copy the M04 documentation updates**

Copy these exact sources into the same relative paths in the integration worktree:

```text
F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\docs\PROJECT_RECORD_AND_LEARNING_GUIDE.md
F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\docs\README.md
F:\small++\.worktrees\m03-continuous-csg-impl\paper_A_reliable_inverse_design\geometry_compiler_matlab\docs\SIMULATION_EXPERIMENT_MEMORY.md
```

Expected: the memory file gains the link to `PROJECT_RECORD_AND_LEARNING_GUIDE.md` and otherwise matches the latest tracked M04 version.

- [ ] **Step 4: Add the generated-wiki exclusion**

Append this rule in the “Scratch and generated workspace state” section of `.gitignore`:

```gitignore
**/.qoder/repowiki/
```

- [ ] **Step 5: Rewrite the stale Qoder status notice**

Replace `paper_A_reliable_inverse_design/.qoder/README_A2_STATUS.md` with:

```markdown
# Paper A Qoder Status Notice

`.qoder/repowiki/` is generated and intentionally excluded from version control. It may contain obsolete model-first terminology and must not be used as scientific evidence.

Current authoritative sources:

1. `../docs/CURRENT_PAPER_A_PLAN.md`
2. `../docs/superpowers/specs/2026-07-31-paper-a-mechanism-resolved-attainability-design.md`
3. `../docs/reports/2026-07-31-advisor-discussion-report.md`
4. `../docs/PROJECT_RECORD_AND_LEARNING_GUIDE.md`

The current Paper A direction is mechanism-resolved empirical attainability for inverse design of graded TPMS. Graph Transformer and Diffusion are supporting tools, not the scientific claim by themselves.
```

- [ ] **Step 6: Inspect and commit the curated import**

Run:

```powershell
git status --short
git diff --check
git add -- .gitignore paper_A_reliable_inverse_design
git diff --cached --name-status
git commit -m "docs: consolidate current TPMS research record"
```

Expected: the staged list contains only named TPMS files and no path containing `repowiki`, `origami_experiments`, `demo_data`, `output`, or `evidence`.

### Task 4: Rewrite the repository README

**Files:**

- Modify: `README.md`

- [ ] **Step 1: Replace the obsolete origami README with the approved TPMS narrative**

The README must contain these exact sections and evidence boundaries:

```markdown
# Small++: Mechanism-Resolved Inverse Design of Graded TPMS

> Small++ develops evidence-gated inverse design for graded triply periodic minimal surface structures, connecting target stress–strain responses to realizable geometries and distinguishable local collapse mechanisms.

Small++ 面向渐变三周期极小曲面（TPMS）的可信逆向设计。当前主线不是单纯比较神经网络误差，而是在预先声明的几何、材料、制造和加载域内研究：目标响应是否有证据支持、哪些不同局部塌缩路径可以实现近似响应，以及何时应接受候选、延迟裁决或拒绝过度自信的输出。

## 核心研究问题

- 目标应力–应变曲线在声明的渐变 TPMS 设计域与有限搜索预算内是否存在已验证候选？
- 曲线相近的候选是否可能具有可区分的首塌区域、塌缩顺序或局部化路径？
- 哪些候选靠近模式转换边界，并对厚度、材料、摩擦或加载偏心等扰动更敏感？
- 几何硬约束、前向验证和不确定性门控能否提高 Diffusion 候选的联合成功率？

## 技术路线

1. 确定性渐变 Gyroid/TPMS 几何编译与制造约束检查；
2. Abaqus 曲线、局部场、接触与塌缩事件数据；
3. Graph Transformer/基线模型联合预测全局曲线和局部机制；
4. Conditional Diffusion 提议多个满足方法约束的候选；
5. 几何筛选、前向复核、不确定性排序和 accept/defer/no-feasible-design-found 门控；
6. 密封数值裁决与小规模重复打印压缩实验。

## 当前已实现

- M01–M03：编译器契约、渐变 Gyroid 场、有限连续 CSG、表面网格验证和二进制 STL；
- M04：Legacy/Physical 双描述符接口、Gate-0 冻结与溯源约束；
- Paper A 模型层：曲线/参数契约、编译器感知图、前向基线、GC-GraphFormer 和方法约束 Diffusion 接口；
- MATLAB 与 Python 单元测试覆盖上述核心接口。

真实 discovery、30-case confirmation、正式 Abaqus 主数据、3D 打印与压缩实验尚未完成，因此当前仓库不声称已完成论文级物理验证。

## 仓库结构

- `paper_A_reliable_inverse_design/geometry_compiler_matlab/`：M01–M04 几何与描述符编译器；
- `paper_A_reliable_inverse_design/gc_graphformer/`：图构建、基线、GC-GraphFormer 和 Diffusion 约束接口；
- `paper_A_reliable_inverse_design/tests/`：Python 合约与模型测试；
- `paper_A_reliable_inverse_design/docs/`：研究计划、规格、实施记录与报告；
- `.qoder/skills/executing-research-experiments/`：实验交付与证据审计工作流。

## 快速验证

```powershell
python -m pytest paper_A_reliable_inverse_design/tests -q
matlab -batch "cd('paper_A_reliable_inverse_design/geometry_compiler_matlab'); run_tests"
```

完整研究入口见 `paper_A_reliable_inverse_design/docs/CURRENT_PAPER_A_PLAN.md`；M03 用法见 `paper_A_reliable_inverse_design/geometry_compiler_matlab/docs/M03_USAGE.md`；M04 与仿真实验接手信息见 `paper_A_reliable_inverse_design/geometry_compiler_matlab/docs/SIMULATION_EXPERIMENT_MEMORY.md`。

## 数据与证据约定

- 不提交模型权重、打包数据集、原始 Abaqus 输出、日志、缓存和其他可再生产物；
- `.qoder/repowiki/` 为自动生成资料，不作为权威研究记录；
- “可实现”仅指预注册设计域、容差和有限预算下的经验可实现性；
- `no feasible design found within the declared domain and budget` 不等于证明物理上绝对不可实现；
- Graph Transformer 与 Diffusion 是解决研究问题的工具，不作为脱离证据链的创新声明。

## 路线图

1. 完成 Small 历史几何与 FE 复现 Gate 0；
2. 冻结局部事件、扰动场景和数据契约；
3. 生成名义与局部场 Abaqus 数据，开展机制发现；
4. 训练并比较前向验证器，完成多候选逆向门控；
5. 执行密封目标和配对扰动裁决；
6. 锁定打印设计并开展重复压缩与侧面视频验证。

## 关键文档

- `paper_A_reliable_inverse_design/docs/superpowers/specs/2026-07-31-paper-a-mechanism-resolved-attainability-design.md`
- `paper_A_reliable_inverse_design/docs/reports/2026-07-31-advisor-discussion-report.md`
- `paper_A_reliable_inverse_design/docs/PROJECT_RECORD_AND_LEARNING_GUIDE.md`
- `paper_A_reliable_inverse_design/docs/superpowers/reports/2026-08-06-paper-a-gc-graphformer-milestone.md`
```

- [ ] **Step 2: Verify every README path exists**

Run `Test-Path` for each path listed in “快速验证” and “关键文档”.

Expected: every result is `True`.

- [ ] **Step 3: Check terminology and commit**

Run:

```powershell
rg -n -i "折纸|origami|miura|证明.*不可实现|覆盖全部 TPMS|已完成.*物理验证" README.md
git diff --check
git add -- README.md
git commit -m "docs: reframe small++ around reliable TPMS inverse design"
```

Expected: the terminology scan has no match; `git diff --check` exits `0`; the commit changes only `README.md`.

### Task 5: Verify the curated branch contents

**Files:**

- Verify all tracked files; make no content changes unless a check fails.

- [ ] **Step 1: Scan for excluded paths and artifacts**

Run:

```powershell
git ls-files | rg -n -i "(^|/)(origami_experiments|demo_data|output|evidence)(/|$)|(^|/)\.qoder/repowiki/|\.(pth|pt|ckpt|npz|joblib|pkl)$|(^|/)raw_curves(_[^/]*)?/"
```

Expected: no output and ripgrep exit `1`.

- [ ] **Step 2: Verify required TPMS paths**

Run `Test-Path` for:

```text
paper_A_reliable_inverse_design/geometry_compiler_matlab/run_tests.m
paper_A_reliable_inverse_design/gc_graphformer/model.py
paper_A_reliable_inverse_design/gc_graphformer/diffusion_interface.py
paper_A_reliable_inverse_design/tests/test_model.py
paper_A_reliable_inverse_design/docs/CURRENT_PAPER_A_PLAN.md
paper_A_reliable_inverse_design/docs/PROJECT_RECORD_AND_LEARNING_GUIDE.md
paper_A_reliable_inverse_design/tools/build_paper_a_framework_docx.py
```

Expected: every result is `True`.

- [ ] **Step 3: Verify branch history and patch hygiene**

Run:

```powershell
git merge-base --is-ancestor be24186 HEAD
git merge-base --is-ancestor d2e45e6 HEAD
git merge-base --is-ancestor fd4176f HEAD
git diff --check codex/paper-a-gc-graphformer..HEAD
git status --short --branch
```

Expected: the ancestry and diff checks exit `0`; status reports `## small++` with a clean worktree.

### Task 6: Run the project verification suites

**Files:**

- Test: `paper_A_reliable_inverse_design/tests/*.py`
- Test: `paper_A_reliable_inverse_design/geometry_compiler_matlab/tests/*.m`
- Test: `.qoder/skills/executing-research-experiments/tests/test-validate-delivery.ps1`

- [ ] **Step 1: Run the Python TPMS tests**

Run from the integration worktree:

```powershell
& 'F:\Anaconda\envs\GMM\python.exe' -m pytest paper_A_reliable_inverse_design\tests -q
```

Expected: pytest exits `0` with no failed tests.

- [ ] **Step 2: Run the MATLAB geometry compiler tests**

Run:

```powershell
& 'F:\MATLAB\R2023b\bin\matlab.exe' -batch "cd('F:/small++/.worktrees/small-plus-sync/paper_A_reliable_inverse_design/geometry_compiler_matlab'); run_tests"
```

Expected: MATLAB exits `0` and reports all tests passed.

- [ ] **Step 3: Run the research-delivery validator tests**

Run:

```powershell
& '.\.qoder\skills\executing-research-experiments\tests\test-validate-delivery.ps1'
```

Expected: PowerShell exits `0` and all valid/invalid fixture expectations pass.

### Task 7: Configure GitHub and publish `small++`

**Files:**

- Modify local Git remote configuration only; no repository content changes.

- [ ] **Step 1: Add the confirmed target remote**

Run from the integration worktree:

```powershell
git remote add origin 'https://github.com/zyql8087/small-.git'
git remote -v
```

Expected: fetch and push URLs both point to `https://github.com/zyql8087/small-.git`.

- [ ] **Step 2: Confirm authentication before the write**

Run:

```powershell
gh auth status
```

Expected: account `zyql8087` is active with a valid token. If the token is invalid, run `gh auth login -h github.com` interactively and repeat the status check.

- [ ] **Step 3: Push without rewriting remote history**

Run:

```powershell
git push -u origin 'small++'
```

Expected: a new remote branch is created; no `--force` option is used.

- [ ] **Step 4: Verify the remote object equals local HEAD**

Run:

```powershell
$localCommit = git rev-parse HEAD
$remoteLine = git ls-remote --heads origin 'refs/heads/small++'
$remoteCommit = ($remoteLine -split "`t")[0]
if ($localCommit -ne $remoteCommit) { throw "Remote branch does not match local HEAD" }
Write-Output "Verified small++ at $localCommit"
```

Expected: the command prints `Verified small++ at` followed by the 40-character local commit SHA and exits `0`.

### Task 8: Final evidence review

**Files:**

- No file changes.

- [ ] **Step 1: Capture the final branch summary**

Run:

```powershell
git status --short --branch
git log -8 --oneline --decorate
git remote -v
```

Expected: clean `small++` branch tracking `origin/small++`, with the README and curated TPMS commits at the tip.

- [ ] **Step 2: Report verified results and any environmental limitations**

Report the exact Python, MATLAB, workflow-test, exclusion-scan, and remote-hash outcomes. Do not describe a skipped or failed check as passing.
