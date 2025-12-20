# T-026: Scenario — Chart-IMG account exhaustion

## Summary

- Validate CHART_API_LIMIT_EXCEEDED path when all accounts are exhausted.

## Goal

- Ensure the worker fails with `CHART_API_LIMIT_EXCEEDED` when all accounts are over dailyLimit, and produces failures[] without writing PNG/manifest.

## Scope

- Prepare Firestore `chart_img_accounts_usage` with `usageToday = dailyLimit` for all accounts in the secret.
- Run CLI against a READY flow_run.
- Verify Firestore step FAILED with error.code `CHART_API_LIMIT_EXCEEDED` and no GCS artifacts.

## References

- `docs-worker-chart-export/spec/implementation_contract.md` (Error model, usage accounting)
- `docs-worker-chart-export/contracts/flow_run.schema.json`
- `docs-worker-chart-export/contracts/charts_outputs_manifest.schema.json`

## Planned Scenarios (TDD)

### Scenario 1: All accounts exhausted

**Prerequisites**
- Firestore docs in `chart_img_accounts_usage` for all accounts.
- Requires human-in-the-middle: YES (real GCP)

**Steps**
1) For each account in `chart-img-accounts`, set `usageToday = dailyLimit`.
2) Create a READY flow_run step (CHART_EXPORT).
3) Run CLI (`run-local`) in `record` or `mock` mode.

**Expected result**
- Step FAILED with `error.code = "CHART_API_LIMIT_EXCEEDED"`.
- No PNG/manifest written to GCS.
- failures[] contains entries for each request.

## Risks

- Running in `record` may consume API limits; prefer `mock` with existing fixtures if possible.

## Verify Steps

- Confirm Firestore step error.code and absence of GCS artifacts.

## Rollback Plan

- Reset `usageToday` to 0 for all accounts.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
