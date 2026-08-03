# Work Buddy Skill Installation Record

Date: 2026-08-03
Project root: `F:\small++`
Skill: `executing-research-experiments`

## Installation

The project Skill was copied from:

```text
F:\small++\.qoder\skills\executing-research-experiments
```

to Work Buddy's detected installed-skill root:

```text
C:\Users\48186\.workbuddy\skills\executing-research-experiments
```

The sibling `C:\Users\48186\.workbuddy-ai\skills` directory contains only its migration marker and is not the active installed-skill root. The existing Work Buddy skill directories are under `.workbuddy\skills` and contain `SKILL.md` entry points.

## File-level verification

The source and target inventories were compared recursively after copying:

| Check | Result |
|---|---:|
| Source files | 25 |
| Target files | 25 |
| Missing target files | 0 |
| Unexpected target files | 0 |
| SHA-256 mismatches | 0 |
| Target `SKILL.md` SHA-256 | `DDCFE2B2C457D9ED719F917A158834D50560EDE76EE4FC778B861FDEBC8C0993` |

The target includes the entry point, seven routed references, four templates, the delivery validator, fixtures, and validator tests.

## Runtime loading boundary

No Work Buddy CLI executable was discoverable through `Get-Command`, and the desktop process was not running during verification. Therefore this record certifies installation and content integrity only. The remaining runtime check is to launch/restart Work Buddy, refresh its Skill registry if the UI exposes that action, and confirm that `executing-research-experiments` is listed or invoked by a matching prompt. A filesystem copy must not be reported as a runtime-load pass.
