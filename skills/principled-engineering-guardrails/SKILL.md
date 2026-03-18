---
name: principled-engineering-guardrails
description: Enforce strict engineering execution constraints. Use when tasks require first-principles reasoning, clarification before implementation when goals are unclear, mandatory TypeScript standards via the typescript-project-specifications skill, and shortest-path refactor or modification plans with full end-to-end logic validation.
---

# Principled Engineering Guardrails

## Workflow

1. Restate the user's objective and explicit constraints in one concise statement.
2. Judge whether motivation, target outcome, and success criteria are clear.
3. Stop and discuss with the user before implementation when any of these are unclear.
4. Derive the solution from first principles:
   - define the core problem
   - define non-negotiable invariants
   - derive the minimal valid path from input to expected output
5. Reject assumptions that are not grounded in the user's stated requirement.

## TypeScript Rule

1. Load and apply `typescript-project-specifications` before writing any TypeScript.
2. Stop and ask the user how to proceed if that skill is unavailable.
3. Enforce its conventions as a hard requirement, not a suggestion.

## Solution Rule

1. Give only the shortest-path implementation that satisfies the stated requirement.
2. Do not provide compatibility, patch, fallback, downgrade, or hedge plans.
3. Do not over-design or add abstractions beyond what the requirement needs.
4. Do not introduce extra requirements that the user did not ask for.
5. Verify end-to-end logic before finalizing any modification or refactor:
   - assumptions are explicit and minimal
   - each transformation step is necessary
   - affected components are complete and consistent
   - expected behavior is testable from input through output

## Escalation Rule

1. Pause and discuss trade-offs with the user when constraints conflict.
2. Refuse to continue with a plan that cannot pass end-to-end logic validation.
