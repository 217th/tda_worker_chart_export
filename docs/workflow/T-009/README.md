# T-009: CLI run-local wrapper (thin adapter over core engine)

## Summary

- Add `run-local` CLI as a thin adapter over the same core engine used by the CloudEvent handler.

## Goal

- Make local debugging deterministic and faithful to prod behavior (differences treated as bugs).

## Scope

- Implement flags per `docs-worker-chart-export/spec/implementation_contract.md`.
- Support `--accounts-config-path` to load `chart-img.accounts.local.json` and inject `CHART_IMG_ACCOUNTS_JSON`.
- Provide `--output-summary=none|text|json`.
- References:
  - `docs-worker-chart-export/spec/implementation_contract.md` §12.1 (CLI requirements), §12.2 (modes)

## Planned Scenarios (TDD)

### Scenario 1: CLI runs a specific step by id

**Prerequisites**
- A valid `flow_run` JSON file and an existing `stepId` in `READY`.
- Requires human-in-the-middle: NO

**Steps**
1) Run `worker-chart-export run-local --flow-run-path=<file> --step-id=<id>`.

**Expected result**
- The CLI executes the same core engine path as the CloudEvent handler for that step.

### Scenario 2: Invalid --step-id → VALIDATION_FAILED + non-zero exit

**Prerequisites**
- A `flow_run` JSON file where the provided `stepId` is missing or not `CHART_EXPORT`.
- Requires human-in-the-middle: NO

**Steps**
1) Run `worker-chart-export run-local --flow-run-path=<file> --step-id=<invalid>`.

**Expected result**
- CLI exits with a non-zero code and reports `error.code = "VALIDATION_FAILED"` in logs/summary.

### Scenario 3: CLI auto-selects first READY step

**Prerequisites**
- A `flow_run` JSON file with multiple READY `CHART_EXPORT` steps.
- Requires human-in-the-middle: NO

**Steps**
1) Run CLI without `--step-id`.

**Expected result**
- The CLI selects the first READY step using the deterministic ordering.

### Scenario 4: CLI flags override env

**Prerequisites**
- Environment variables set for bucket/mode; CLI flags provided with different values.
- Requires human-in-the-middle: NO

**Steps**
1) Run CLI with `--charts-bucket=gs://...` and `--charts-api-mode=mock|real|record`.

**Expected result**
- CLI flags take priority over environment variables.

### Scenario 5: Accounts config file loads and injects JSON

**Prerequisites**
- A valid `chart-img.accounts.local.json` file.
- Requires human-in-the-middle: NO

**Steps**
1) Run CLI with `--accounts-config-path=<file>`.

**Expected result**
- CLI loads the file and uses it as `CHART_IMG_ACCOUNTS_JSON`.

### Scenario 6: Exit codes and JSON summary format

**Prerequisites**
- A successful or failed run-local execution.
- Requires human-in-the-middle: NO

**Steps**
1) Run CLI with `--output-summary=json` on a successful run.
2) Run CLI with `--output-summary=json` on a failed run.

**Expected result**
- Exit code is `0` on success, non-zero on failure.
- JSON summary includes at least: `status`, `runId`, `stepId`, `manifestUri` (if available), `items`, `failures`, `minImages`.

## Risks

- Divergence between CLI and prod code paths; keep all business logic in core engine and unit-test both adapters.

## Verify Steps

- Automated: `python -m pytest tests/tasks/T-009/test_cli.py`.
- Manual (blocked until core is implemented): run planned scenarios 1–6 against real `flow_run` once the core engine (T-003..T-008 wiring) is available.

## Rollback Plan

- Revert the commit; prod deployment unaffected.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- `docs/workflow/T-009/README.md`
- `docs/workflow/T-009/pr/diffstat.txt`
- `docs/workflow/T-009/pr/meta.json`
- `docs/workflow/T-009/pr/review.md`
- `docs/workflow/T-009/pr/verify.log`
- `tests/tasks/T-009/test_cli.py`
- `worker_chart_export/cli.py`
- `worker_chart_export/core.py`
<!-- END AUTO SUMMARY -->
