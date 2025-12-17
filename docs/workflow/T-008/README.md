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
