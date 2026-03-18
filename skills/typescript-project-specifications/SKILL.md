---
name: typescript-project-specifications
description: Define mandatory TypeScript project specifications for coding, refactor, and review tasks in TypeScript or TSX files, including project typing settings, type-safety boundaries, module conventions, and end-to-end change validation. Use when creating, modifying, or reviewing TypeScript code, or when proposing TypeScript implementation plans.
---

# Typescript Project Specifications

## Workflow

1. Restate the requested outcome and explicit constraints before coding.
2. Stop and ask for clarification if goal, scope, or success criteria are unclear.
3. Inspect existing repository conventions and follow them when they are stricter than this skill.
4. Implement the shortest path that satisfies the requirement without compatibility patches.
5. Validate the full affected path before finalizing.

## Project Baseline

1. Keep `tsconfig` strictness enabled for touched projects.
2. Keep `strict` enabled.
3. Keep `noUncheckedIndexedAccess` enabled.
4. Keep `exactOptionalPropertyTypes` enabled.
5. Keep `noImplicitOverride` enabled.
6. Do not weaken compiler checks to make code compile.

## Typing Rules

1. Model domain data with explicit interfaces or type aliases before implementation.
2. Type all exported functions and public class methods explicitly.
3. Avoid `any`; use `unknown` plus narrowing at boundaries.
4. Narrow union types with discriminants or explicit guards.
5. Validate external input at boundaries before mapping into domain types.
6. Reuse existing project utilities and shared types before creating new ones.

## Implementation Rules

1. Keep each function focused on one behavior.
2. Separate pure transformation logic from IO and side effects.
3. Propagate errors with actionable messages; do not swallow exceptions silently.
4. Remove dead code and obsolete branches in the same change.
5. Avoid adding abstractions unless they are required by current scope.

## Refactor and Plan Rules

1. Do not propose fallback, downgrade, or compatibility-layer solutions.
2. Do not propose requirements outside the user request.
3. Keep architecture changes minimal and directly tied to the target behavior.
4. Validate end-to-end logic from input to output before presenting a plan.

## Validation Checklist

1. Run TypeScript checks for impacted packages or apps.
2. Run lint checks for touched files when lint is configured.
3. Run relevant tests for affected modules and behavior paths.
4. Confirm no type regressions in nearby call sites.
5. Report what was validated and what was not run.
