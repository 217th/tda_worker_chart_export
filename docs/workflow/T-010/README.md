# T-010: Unit tests (schema, idempotency, error codes, naming)

## Summary

- Add unit tests covering schema validation, idempotency, error mapping, and naming/URI formatting.

## Goal

- Provide fast, deterministic coverage without external dependencies (no real Chart‑IMG calls).

## Scope

- Schema validation for `flow_run` and `ChartsOutputsManifest`.
- Status rule: `SUCCEEDED` iff `items >= minImages`.
- Error code coverage: `VALIDATION_FAILED`, `CHART_API_FAILED`, `CHART_API_LIMIT_EXCEEDED`, `CHART_API_MOCK_MISSING`, `GCS_WRITE_FAILED`, `MANIFEST_WRITE_FAILED`.
- PNG naming + `gs://` formatting.
- Invariant: no “silent drops” — every logical request must end up in `items[]` or `failures[]`.
- References:
  - `docs-worker-chart-export/spec/implementation_contract.md` §6–§9 (manifest + success rule + retries), §8 (error codes)
  - `docs-worker-chart-export/contracts/charts_outputs_manifest.schema.json`

## Risks

- Flaky tests if they depend on real network/services; enforce `CHARTS_API_MODE=mock` in test defaults.

## Verify Steps

- `python -m pytest -q`

## Rollback Plan

- Revert the commit; no runtime impact.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
