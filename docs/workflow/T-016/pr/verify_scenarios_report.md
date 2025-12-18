# T-016 — Scenarios Verification Report

Source checklist: `docs/workflow/T-016/pr/scenarios.md`

Date: 2025-12-18
Environment: local dev (no external services)

## Scenario 1) QA_CYCLE enforces pre-dev scenarios

**Prerequisites (as stated in scenarios)**
- None

**Actions taken**
- `rg -n "Pre-dev requirement|Planned Scenarios" docs/workflow/QA_CYCLE.md`

**Results**
- Pass. Output:
  - `12:## Pre-dev requirement (TDD)`
  - `14:Before implementation starts, every task README **must** define **Planned Scenarios (TDD)**:`

## Scenario 2) Task README template includes Planned Scenarios

**Prerequisites (as stated in scenarios)**
- None

**Actions taken**
- `rg -n "Planned Scenarios" docs/workflow/_templates/task_readme.md`

**Results**
- Pass. Output:
  - `19:## Planned Scenarios (TDD)`

## Scenario 3) TODO task READMEs contain Planned Scenarios

**Prerequisites (as stated in scenarios)**
- None

**Actions taken**
- `for t in 003 004 005 006 007 008 009 010 011 012 013; do echo "T-$t"; rg -n "Planned Scenarios" docs/workflow/T-$t/README.md; done`

**Results**
- Pass. Output shows each TODO README contains the Planned Scenarios section.

## Scenario 4) Implemented scenarios template references planned scenarios

**Prerequisites (as stated in scenarios)**
- None

**Actions taken**
- `rg -n "Planned scenarios source" docs/workflow/_templates/pr_scenarios.md`

**Results**
- Pass. Output:
  - `5:Planned scenarios source:`

## Human-in-the-middle required scenarios

- None for this task.

## Fixes required during verification

- None.
