# T-002: Bootstrap worker-chart-export (Python 3.13)

## Summary

- Create a minimal Python 3.13 project skeleton for `worker-chart-export` with typed config and structured logging.

## Goal

- Establish a clean foundation where CloudEvent handler and CLI reuse the same core engine (no duplicated business logic).

## Scope

- Python package layout, dependency management, and entrypoints (CloudEvent adapter + CLI).
- Typed config: env + CLI overrides for `CHART_IMG_ACCOUNTS_JSON`, `CHARTS_BUCKET`, `CHARTS_API_MODE`, `CHARTS_DEFAULT_TIMEZONE`.
- Structured JSON logging fields per `docs-gcp/runbook/prod_runbook_gcp.md`.
- References:
  - `docs-worker-chart-export/spec/implementation_contract.md` §11.1 (Chart-IMG accounts secret), §12.1 (CLI), §12.2 (modes)
  - `docs-gcp/runbook/prod_runbook_gcp.md` §1.3 (Secret Manager), §8 (Logging & Observability)

## Risks

- Cloud Run Functions (gen2) runtime support for Python 3.13 may require container-based deploy; document and validate early.

## Verify Steps

- `python -m compileall .`

## Rollback Plan

- Revert the bootstrap commit; no data migrations expected.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
