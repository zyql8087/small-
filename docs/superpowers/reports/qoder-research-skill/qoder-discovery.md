# Qoder Skill Discovery and Trigger Verification

Date: 2026-08-03
Project root under test: `F:\small++\.worktrees\qoder-research-skill`
Skill path: `.qoder/skills/executing-research-experiments/SKILL.md`

## Filesystem and metadata checks

Status: passed.

- The Skill entry point exists at the declared project path.
- The frontmatter name is `executing-research-experiments`.
- Seven routed references exist under `references/`.
- Templates, validator, and tests are present.
- The project `.gitattributes` assigns LF to the Skill tree.

## Qoder executable check

Status: partial.

Observed command:

```powershell
qoder.cmd --help
```

Observed CLI version from the command output: `1.20.1` with build `4ee322f78fe8606b0bcb6dd6991c61463b3112de`. The separate `qoder.cmd chat --help` output identified a different bundled version string (`1.106.3`), so the active UI/CLI version identity is not treated as fully resolved.

The CLI exposes `chat`, but it does not expose a non-interactive `/skills reload` or loaded-reference report. A `qoder.cmd --status` probe returned process diagnostics and did not return a usable Skill-discovery result before the bounded command timeout.

## Manual reload check

Status: blocked pending interactive Qoder UI evidence.

Required interactive procedure:

```text
/skills reload
/skills
```

Record the Qoder UI version, project root, command output, and whether `executing-research-experiments` appears. No filesystem-only observation is substituted for this check.

## Manual trigger check

Status: blocked pending interactive Qoder UI evidence.

Required prompt:

```text
/executing-research-experiments Review the next MATLAB geometry milestone without editing files.
```

Expected evidence is a transcript showing that the Skill reads `matlab-geometry.md` and `review-and-git.md`, begins with specification/context discovery, and does not claim completion.

## Automatic trigger checks

Status: blocked pending fresh interactive Qoder sessions.

Run each prompt in a fresh session and record loaded Skill/reference files:

```text
Prepare an Abaqus mesh-convergence experiment task and acceptance checklist.
Audit this TPMS train/test split for leakage before Graph Transformer training.
Review whether these repeated compression tests support the simulation claim.
```

Expected routing is respectively Abaqus + review, dataset/ML + review, and physical-experiment + review. A missing transcript, screenshot, or UI report remains `blocked`, not `passed`.

## Conclusion

Filesystem, frontmatter, routing, validator, and test evidence are independently verifiable. Qoder's interactive reload, manual trigger, and automatic trigger behavior cannot be certified from the available non-interactive CLI output and therefore remain explicitly blocked. This limitation does not establish a Skill failure; it establishes that the required UI evidence is still missing.
