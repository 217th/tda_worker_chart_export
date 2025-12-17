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

## Risks

- Divergence between CLI and prod code paths; keep all business logic in core engine and unit-test both adapters.

## Verify Steps

- CLI smoke: `--output-summary=json` on a sample `flow_run` with `CHARTS_API_MODE=mock`.

## Rollback Plan

- Revert the commit; prod deployment unaffected.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
