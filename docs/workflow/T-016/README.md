# T-016: TDD planned scenarios in task READMEs

## Summary

- Require each task to define Planned Scenarios (TDD) in its README before implementation, and align templates/docs accordingly.

## Goal

- Move scenario definition **before** coding so development is driven by explicit, verifiable scenarios.

## Scope

- Update QA workflow documentation to require a pre-dev scenario list in each task README.
- Add/adjust templates so tasks have a standard “Planned Scenarios (TDD)” section with prerequisites/steps/expected results.
- Backfill Planned Scenarios for all TODO tasks (T-003..T-013) in their READMEs.

## Planned Scenarios (TDD)

### Scenario 1: QA_CYCLE enforces pre-dev scenarios

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) Update `docs/workflow/QA_CYCLE.md` to require Planned Scenarios in task READMEs.

**Expected result**
- QA_CYCLE explicitly describes the pre-dev requirement and references the template.

### Scenario 2: Task README template includes Planned Scenarios

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) Add a template under `docs/workflow/_templates/task_readme.md`.

**Expected result**
- Template includes a Planned Scenarios section with prerequisites/steps/expected results.

### Scenario 3: TODO task READMEs include Planned Scenarios

**Prerequisites**
- Existing TODO tasks T-003..T-013.
- Requires human-in-the-middle: NO

**Steps**
1) Add a Planned Scenarios (TDD) section to each TODO task README.

**Expected result**
- Each TODO task README contains concrete, testable scenario descriptions.

## Acceptance Criteria

- `docs/workflow/QA_CYCLE.md` explicitly requires Planned Scenarios (TDD) in each task README before implementation.
- A task README template exists with a Planned Scenarios section.
- TODO task READMEs T-003..T-013 include Planned Scenarios with prerequisites/steps/expected results.

## Risks

- If Planned Scenarios are too vague, they will not guide implementation or QA; the template must enforce concrete, testable steps.

## Verify Steps

- Read a TODO task README (e.g. `docs/workflow/T-003/README.md`) and confirm Planned Scenarios are present and structured.

## Rollback Plan

- Revert the commits; task READMEs and templates will return to prior structure.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- `docs/workflow/QA_CYCLE.md`
- `docs/workflow/T-003/README.md`
- `docs/workflow/T-004/README.md`
- `docs/workflow/T-005/README.md`
- `docs/workflow/T-006/README.md`
- `docs/workflow/T-007/README.md`
- `docs/workflow/T-008/README.md`
- `docs/workflow/T-009/README.md`
- `docs/workflow/T-010/README.md`
- `docs/workflow/T-011/README.md`
- `docs/workflow/T-012/README.md`
- `docs/workflow/T-013/README.md`
- `docs/workflow/T-016/README.md`
- `docs/workflow/T-016/pr/diffstat.txt`
- `docs/workflow/T-016/pr/meta.json`
- `docs/workflow/T-016/pr/review.md`
- `docs/workflow/T-016/pr/scenarios.md`
- `docs/workflow/T-016/pr/verify.log`
- `docs/workflow/T-016/pr/verify_scenarios_report.md`
- `docs/workflow/_templates/pr_scenarios.md`
<!-- END AUTO SUMMARY -->
