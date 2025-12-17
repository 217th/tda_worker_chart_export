# T-002: Bootstrap worker-chart-export (Python 3.13)

## Summary

- Create a minimal Python 3.13 project skeleton for `worker-chart-export` with typed config and structured logging.

## Goal

- Establish a clean foundation where CloudEvent handler and CLI reuse the same core engine (no duplicated business logic).

## Scope

- Python package layout, dependency management, and entrypoints (CloudEvent adapter + CLI).
- Typed config: env + CLI overrides for `CHART_IMG_ACCOUNTS_JSON`, `CHARTS_BUCKET`, `CHARTS_API_MODE`, `CHARTS_DEFAULT_TIMEZONE`.
  - `CHART_IMG_ACCOUNTS_JSON` is parsed and validated once per process start; invalid secret is a fatal misconfiguration (not per-step `VALIDATION_FAILED`).
- Structured JSON logging fields per `docs-gcp/runbook/prod_runbook_gcp.md`.
- References:
  - `docs-worker-chart-export/spec/implementation_contract.md` §11.1 (Chart-IMG accounts secret), §12.1 (CLI), §12.2 (modes)
  - `docs-gcp/runbook/prod_runbook_gcp.md` §1.3 (Secret Manager), §8 (Logging & Observability)

## Risks

- Cloud Run Functions (gen2) runtime support for Python 3.13 may require container-based deploy; document and validate early.

## Verify Steps

- `python -m compileall .`
- `python -m unittest discover -s tests -p 'test_*.py' -q`
- (optional) create venv + install deps:
  - `python -m venv .venv && . .venv/bin/activate`
  - `python -m pip install -U pip && python -m pip install -r requirements.txt`

## Rollback Plan

- Revert the bootstrap commit; no data migrations expected.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- `docs/workflow/T-002/README.md`
- `docs/workflow/T-002/pr/diffstat.txt`
- `docs/workflow/T-002/pr/meta.json`
- `docs/workflow/T-002/pr/review.md`
- `docs/workflow/T-002/pr/scenarios.md`
- `docs/workflow/T-002/pr/verify.log`
- `docs/workflow/T-002/pr/verify_scenarios_report.md`
- `pyproject.toml`
- `requirements.txt`
- `tests/test_scenarios_cli.py`
- `tests/test_scenarios_cloud_event.py`
- `tests/test_scenarios_config.py`
- `tests/test_scenarios_logging.py`
- `worker_chart_export/__init__.py`
- `worker_chart_export/cli.py`
- `worker_chart_export/config.py`
- `worker_chart_export/core.py`
- `worker_chart_export/entrypoints/__init__.py`
- `worker_chart_export/entrypoints/cloud_event.py`
- `worker_chart_export/errors.py`
<!-- END AUTO SUMMARY -->
