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
