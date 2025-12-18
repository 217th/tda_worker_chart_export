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

## Planned Scenarios (TDD)

### Scenario 1: Schema validation (flow_run)

**Prerequisites**
- A valid flow_run fixture and an invalid one (missing required fields).
- Requires human-in-the-middle: NO

**Steps**
1) Validate both fixtures against the schema used by the worker.

**Expected result**
- Valid fixture passes; invalid fixture raises a validation error mapped to `VALIDATION_FAILED`.

### Scenario 2: Schema validation (manifest)

**Prerequisites**
- A valid manifest fixture and an invalid one.
- Requires human-in-the-middle: NO

**Steps**
1) Validate manifest JSON against `charts_outputs_manifest.schema.json`.

**Expected result**
- Valid manifest passes; invalid manifest fails validation.

### Scenario 3: Success rule vs minImages

**Prerequisites**
- Manifests with varying `items` counts and `minImages` values.
- Requires human-in-the-middle: NO

**Steps**
1) Evaluate step success for different combinations.

**Expected result**
- `SUCCEEDED` iff `len(items) >= minImages`; otherwise `FAILED`.

### Scenario 4: Error code mapping coverage

**Prerequisites**
- Controlled inputs that trigger each error code.
- Requires human-in-the-middle: NO

**Steps**
1) Trigger each error path and inspect the error code.

**Expected result**
- All required error codes are produced: `VALIDATION_FAILED`, `CHART_API_FAILED`, `CHART_API_LIMIT_EXCEEDED`, `CHART_API_MOCK_MISSING`, `GCS_WRITE_FAILED`, `MANIFEST_WRITE_FAILED`.

### Scenario 5: Canonical regression runner

**Prerequisites**
- Tests are organized under `tests/tasks/T-###/`.
- Requires human-in-the-middle: NO

**Steps**
1) Run the canonical regression command.

**Expected result**
- `bash scripts/qa/run_all.sh` executes all accumulated tests deterministically.

### Scenario 6: Naming + URI formatting (gs://, no kind, no gcs://)

**Prerequisites**
- A sample request with `runId`, `stepId`, `symbol`, `timeframe`, `chartTemplateId`.
- Requires human-in-the-middle: NO

**Steps**
1) Build PNG and manifest paths.

**Expected result**
- PNG uses `<generatedAt>_<symbolSlug>_<timeframe>_<chartTemplateId>.png`.
- Only `gs://` URIs are emitted (no `gcs://`).
- Filename does not include `kind`.

### Scenario 7: Secret redaction in logs and error details

**Prerequisites**
- A run that includes Chart-IMG credentials and an error path.
- Requires human-in-the-middle: NO

**Steps**
1) Inspect logs and error.details produced by failures.

**Expected result**
- `apiKey` and other secret values never appear in logs or `error.details`.

### Scenario 8: Duplicate chartTemplateId → validation error

**Prerequisites**
- `inputs.requests[]` contains duplicate `chartTemplateId`.
- Requires human-in-the-middle: NO

**Steps**
1) Validate inputs before processing.

**Expected result**
- `VALIDATION_FAILED` is produced for the step/request.

### Scenario 9: No silent drops invariant

**Prerequisites**
- A run with multiple logical requests and mixed success/failure outcomes.
- Requires human-in-the-middle: NO

**Steps**
1) Build the manifest for the run.

**Expected result**
- Every logical request appears in either `items[]` or `failures[]` (never missing).

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
