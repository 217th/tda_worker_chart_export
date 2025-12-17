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
