# T-016: TDD planned scenarios in task READMEs

## Summary

- Require each task to define Planned Scenarios (TDD) in its README before implementation, and align templates/docs accordingly.

## Goal

- Move scenario definition **before** coding so development is driven by explicit, verifiable scenarios.

## Scope

- Update QA workflow documentation to require a pre-dev scenario list in each task README.
- Add/adjust templates so tasks have a standard “Planned Scenarios (TDD)” section with prerequisites/steps/expected results.
- Backfill Planned Scenarios for all TODO tasks (T-003..T-013) in their READMEs.

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
- (no file changes)
<!-- END AUTO SUMMARY -->
