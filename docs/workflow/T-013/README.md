# T-013: Observability (Cloud Logging + Monitoring)

## Summary

- Define logging fields and provide Cloud Monitoring setup (log-based metrics, alerts, dashboards) for `worker-chart-export`.

## Goal

- Enable fast diagnosis of failures, rate-limit exhaustion, and latency regressions in prod-like environments.

## Scope

- Structured logs with `service/env/runId/flowKey/stepId/eventId/severity/error.*` and `chartsApi.*` (accountId, httpStatus, durationMs, chartTemplateId).
- Log-based metrics + alert policies for `CHART_API_LIMIT_EXCEEDED`, error rate, latency, step success rate.
- Dashboard spec/instructions and runbook actions.
- References:
  - `docs-worker-chart-export/spec/implementation_contract.md` §10 (logging minimum), §13.4–13.5 (Chart-IMG limits/errors), §14.4 (global exhaustion event fields)
  - `docs-gcp/runbook/prod_runbook_gcp.md` §8 (Logging & Observability)

## Planned Scenarios (TDD)

### Scenario 1: Strict log field naming (required + chartsApi.*)

**Prerequisites**
- A completed step (success or failure).
- Requires human-in-the-middle: NO

**Steps**
1) Emit logs for step lifecycle and Chart‑IMG calls.

**Expected result**
- Logs include required fields from `docs-gcp/runbook/prod_runbook_gcp.md` §8.1:
  - `service`, `env`, `runId`, `flowKey`, `stepId`, `eventId`, `severity`, `message`
  - `error.code`, `error.message`, `error.details` (only on errors)
- Chart‑IMG logs use strict naming:
  - `chartsApi.accountId`, `chartsApi.httpStatus`, `chartsApi.durationMs`,
  - `chartsApi.chartTemplateId`, `chartsApi.mode`, `chartsApi.fixtureKey` (if mock/record),
  - plus `runId`, `stepId` for correlation.

### Scenario 2: All required events are logged

**Prerequisites**
- A run that reaches each milestone.
- Requires human-in-the-middle: NO

**Steps**
1) Execute a full run that includes claim, API calls, and artifact writes.

**Expected result**
- The following events are logged at least once per step:
  - received/ingest
  - claim attempt (and result)
  - Chart‑IMG request start + finish
  - manifest written
  - step completed
  - global exhaustion (when applicable)

### Scenario 3: Global exhaustion event

**Prerequisites**
- All accounts exhausted for a logical request.
- Requires human-in-the-middle: NO

**Steps**
1) Emit the exhaustion event when limits are hit.

**Expected result**
- Log entry includes `error.code = "CHART_API_LIMIT_EXCEEDED"` and `exhaustedAccounts[]`.

### Scenario 4: Secrets never appear in logs

**Prerequisites**
- A run that uses Chart‑IMG credentials and hits an error path.
- Requires human-in-the-middle: NO

**Steps**
1) Inspect logs for secret values (apiKey, tokens, PII).

**Expected result**
- No secrets/PII are present in logs or `error.details`.

### Scenario 5: Log-based metrics and alerts in GCP (example filters)

**Prerequisites**
- GCP project access for Cloud Logging/Monitoring.
- Requires human-in-the-middle: YES

**Steps**
1) Create log-based metrics using example filters (e.g.):
   - errors by code: `jsonPayload.error.code=\"CHART_API_FAILED\"`
   - global exhaustion: `jsonPayload.error.code=\"CHART_API_LIMIT_EXCEEDED\"`
   - step completed: `jsonPayload.event=\"step.completed\"`
2) Attach alert policies to these metrics.
3) Test with sample logs (local or staging).
2) Create alert policies and a dashboard.

**Expected result**
- Metrics and alerts evaluate against sample logs; dashboard panels show expected time series.

## Risks

- Missing/unstable log fields break metrics; treat log schema as a contract and cover with tests where feasible.

## Verify Steps

- Validate log field presence in unit/integration tests; dry-run metric filters against sample logs.

## Rollback Plan

- Disable/adjust alert policies; revert dashboard/metric changes if noisy.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
