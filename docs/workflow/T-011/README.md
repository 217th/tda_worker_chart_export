# T-011: Integration tests (local, mock-only)

## Summary

- Add integration tests for the worker pipeline using mock fixtures (no real Chart‑IMG).

## Goal

- Validate the “happy path” wiring: Firestore inputs → Chart API mock → GCS writes → manifest → step patch.

## Scope

- Use `CHARTS_API_MODE=mock` + repo fixtures.
- Scenario-level assertions for object paths and outputs.
- References:
  - `docs-worker-chart-export/spec/implementation_contract.md` §12.2 (mock/record), §9 (idempotency expectations)

## Planned Scenarios (TDD)

### Scenario 1: Harness definition (Firestore + GCS fakes)

**Prerequisites**
- Harness choice decided (see proposed task T-017 if specs are insufficient).
- Requires human-in-the-middle: NO

**Steps**
1) Use the agreed harness for Firestore (emulator or in-memory fake) and GCS (filesystem-backed fake or server).

**Expected result**
- Integration tests run deterministically without external network calls.

### Scenario 2: End-to-end mock run (ingest → claim → work → artifacts → finalize)

**Prerequisites**
- Local test harness for Firestore and GCS (emulators or fakes).
- Mock fixture exists for the request.
- Requires human-in-the-middle: NO

**Steps**
1) Send a CloudEvent update for a flow_run.
2) Handler selects a READY step and claims it.
3) Worker performs mock Chart‑IMG processing.
4) Worker writes PNG + manifest to the fake GCS.
5) Worker finalizes the step patch.

**Expected result**
- Manifest contains an item; PNG and manifest paths are correct; step patch sets `SUCCEEDED` with `outputsManifestGcsUri`.

### Scenario 3: Mock fixture missing → CHART_API_MOCK_MISSING

**Prerequisites**
- Mock fixture is absent for the request.
- Requires human-in-the-middle: NO

**Steps**
1) Run the core worker in mock mode.

**Expected result**
- Manifest records a failure with `error.code = "CHART_API_MOCK_MISSING"`; step status follows `minImages`.

### Scenario 4: Mixed outcomes + minImages

**Prerequisites**
- Multiple requests: one has a valid fixture, one is missing.
- Requires human-in-the-middle: NO

**Steps**
1) Run the worker in mock mode.

**Expected result**
- Manifest contains both `items[]` and `failures[]`; final status determined by `minImages`.

### Scenario 5: No network in mock mode

**Prerequisites**
- HTTP client instrumented to fail on any network call.
- Requires human-in-the-middle: NO

**Steps**
1) Run the worker in mock mode.

**Expected result**
- No external HTTP calls are attempted (test fails if network is used).

### Scenario 6: Idempotent rerun

**Prerequisites**
- A completed run with existing manifest/PNGs.
- Requires human-in-the-middle: NO

**Steps**
1) Run the same flow_run again in mock mode.

**Expected result**
- Manifest is overwritten at the deterministic path; new PNGs may be created with new `generatedAt`, old PNGs remain.

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
