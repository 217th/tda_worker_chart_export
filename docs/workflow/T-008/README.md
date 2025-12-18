# T-008: Write PNG + manifest to GCS (gs://) + validate manifest

## Summary

- Write PNG + `ChartsOutputsManifest` to GCS with deterministic paths and `gs://` URIs; validate manifest schema.

## Goal

- Ensure retries are safe: manifest overwrite is allowed; downstream relies on manifest, not directory listing.

## Scope

- PNG path: `runs/<runId>/charts/<timeframe>/<chartTemplateId>/<generatedAt>_<symbolSlug>_<timeframe>_<chartTemplateId>.png`.
- Manifest path: `runs/<runId>/steps/<stepId>/charts/manifest.json` (deterministic, overwrite allowed).
- Emit `gs://<bucket>/<path>` URIs in outputs/manifest.
- Validate manifest against `docs-worker-chart-export/contracts/charts_outputs_manifest.schema.json`.
- Invariant: for every logical request (`inputs.requests[*]`) the manifest must contain either an `items[]` element or a corresponding `failures[]` element (no “missing” requests).
- References:
  - `docs-worker-chart-export/spec/implementation_contract.md` §5 (GCS paths), §6 (manifest), §9 (retry/idempotency)
  - `docs-worker-chart-export/contracts/charts_outputs_manifest.schema.json`

## Planned Scenarios (TDD)

### Scenario 1: Successful PNG + manifest write

**Prerequisites**
- A successful Chart‑IMG response and a configured `CHARTS_BUCKET`.
- Requires human-in-the-middle: NO

**Steps**
1) Upload PNG to the computed path.
2) Write manifest to the deterministic path.

**Expected result**
- PNG stored at `gs://<bucket>/runs/<runId>/steps/<stepId>/charts/<generatedAt>_<symbolSlug>_<timeframe>_<chartTemplateId>.png`.
- Manifest stored at `gs://<bucket>/runs/<runId>/steps/<stepId>/charts/manifest.json`.
- Manifest validates against the JSON schema.

### Scenario 2: Partial GCS failure (one PNG fails, others succeed)

**Prerequisites**
- Multiple logical requests; simulate a PNG write failure for one request only.
- Requires human-in-the-middle: NO

**Steps**
1) Execute writes for multiple PNGs, forcing one upload to fail.

**Expected result**
- The failed request is recorded in `manifest.failures[]` with `error.code = "GCS_WRITE_FAILED"`.
- Other requests proceed and can still produce `items[]`.
- Final step status is computed via `minImages`.

### Scenario 3: PNG upload failure → GCS_WRITE_FAILED

**Prerequisites**
- Simulate a GCS write failure for the PNG upload.
- Requires human-in-the-middle: NO

**Steps**
1) Attempt to upload PNG and force a failure.

**Expected result**
- The logical request is recorded in `manifest.failures[]` with `error.code = "GCS_WRITE_FAILED"`.

### Scenario 4: Manifest write failure → MANIFEST_WRITE_FAILED

**Prerequisites**
- Simulate a failure when writing `manifest.json`.
- Requires human-in-the-middle: NO

**Steps**
1) Attempt to write the manifest and force a failure.

**Expected result**
- Step finalization uses `error.code = "MANIFEST_WRITE_FAILED"`; `outputsManifestGcsUri` is absent or stale.

### Scenario 5: Manifest schema validation fails → VALIDATION_FAILED

**Prerequisites**
- Build a manifest that fails JSON schema validation.
- Requires human-in-the-middle: NO

**Steps**
1) Validate manifest before write.

**Expected result**
- The step is marked `FAILED` with `error.code = "VALIDATION_FAILED"`.
- `MANIFEST_WRITE_FAILED` is reserved for storage write errors, not schema validation errors.

### Scenario 6: Worker does not write signed_url / expires_at

**Prerequisites**
- A successful PNG + manifest write.
- Requires human-in-the-middle: NO

**Steps**
1) Inspect `manifest.items[]` entries.

**Expected result**
- `signed_url` and `expires_at` are absent (never set by the worker).

### Scenario 7: Retry overwrites manifest but keeps old PNGs

**Prerequisites**
- A previous run already wrote PNGs and a manifest for the same `runId`/`stepId`.
- Requires human-in-the-middle: NO

**Steps**
1) Re-run the step and write a new PNG + manifest.

**Expected result**
- Manifest is overwritten at the same path; new PNG appears with a new `generatedAt` value; old PNGs remain untouched.

## Risks

- URI scheme mismatches (`gcs://` vs `gs://`) can break downstream parsing; enforce `gs://` end-to-end in worker docs and code.

## Verify Steps

- Unit tests: path building, URI formatting, schema validation behavior.

## Rollback Plan

- Revert the commit; old manifests remain addressable by their prior URIs.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
