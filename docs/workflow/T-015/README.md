# T-015: QA harness + regression runner

## Summary

- Standardize the QA cycle artifacts per task and provide a single-command regression runner that executes all accumulated tests.

## Goal

- After completing **any** task `T-###`, it is always possible to:
  - list the implemented scenarios (with explicit limitations),
  - run a reproducible set of manual checks (where feasible),
  - run automated tests/scripts for that task,
  - run a full regression bundle to detect accidental breakage of previously delivered behavior.

## Scope

- Test layout:
  - introduce/standardize an accumulated tests directory: `tests/tasks/T-###/…`
  - define conventions for updating older tests when requirements evolve (keep regression green and meaningful).
- Runner:
  - add `scripts/qa/run_all.sh` (and/or a Python runner) that executes the full bundle in a deterministic way.
  - document one canonical command for full regression.
- Templates for PR artifacts:
  - `docs/workflow/T-###/pr/scenarios.md` template:
    - scenarios list + limitations
    - manual test blocks per scenario: prerequisites / steps / expected result
    - explicit “human-in-the-middle required” marker when applicable
  - `docs/workflow/T-###/pr/verify_scenarios_report.md` template:
    - prerequisites + actions taken to satisfy them
    - step-by-step commands executed
    - results (exit codes, key output)
    - fixes made (what/why)
    - what could not be executed without a human and why
- Workflow documentation:
  - add/update a short internal doc (within this repo) that makes the 4-step QA cycle mandatory after each task.

## Acceptance Criteria

- There is a single command that runs **all** accumulated automated tests (regression).
- Each task PR artifact contains:
  - scenarios (with limitations),
  - manual test steps (where feasible),
  - automated tests/scripts,
  - verification report.
- For scenarios requiring human involvement (GCP, real external services, sandbox limitations), the artifacts explicitly flag “human-in-the-middle required” and provide exact steps.

## Risks

- Some sandbox environments may not allow opening sockets or accessing external services; the harness must clearly separate:
  - what can run in CI/sandbox automatically, and
  - what must be executed by a human in a real environment.

## Verify Steps

- `python -m unittest discover -s tests -p 'test_*.py' -q`
- `bash scripts/qa/run_all.sh` (once added)

## Rollback Plan

- Revert the QA harness commit(s); no runtime behavior should depend on these helpers.

