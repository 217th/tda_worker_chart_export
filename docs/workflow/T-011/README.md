# T-011: Integration tests (local, mock-only)

## Summary

- Add integration tests for the worker pipeline using mock fixtures (no real Chart‑IMG).

## Goal

- Validate the “happy path” wiring: Firestore inputs → Chart API mock → GCS writes → manifest → step patch.

## Scope

- Use `CHARTS_API_MODE=mock` + repo fixtures.
- Scenario-level assertions for object paths and outputs.

## Risks

- Test harness complexity (Firestore/GCS emulation); keep CI-safe and avoid real GCP/Chart‑IMG calls.

## Verify Steps

- `python -m pytest -q`

## Rollback Plan

- Revert the commit; no runtime impact.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
