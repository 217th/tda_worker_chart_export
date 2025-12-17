# T-001: Align docs-worker URIs & PNG naming

## Summary

- Align `docs-worker-chart-export` contracts/examples to agreed MVP conventions (`gs://` URIs, PNG naming without `kind`, real `chartTemplateId` in test vectors).

## Goal

- Remove ambiguity so the implementation can follow `docs-worker-chart-export` as the service source of truth (while keeping `docs-general` unchanged).

## Scope

- Update `docs-worker-chart-export/contracts/*` and `docs-worker-chart-export/spec/*` where they reference `gcs://` or old PNG naming.
- Update `docs-worker-chart-export/test_vectors/*` to stop using `ctpl_default_v1` and to reflect `1 request -> 1 PNG`.
- No changes under `docs-general/` (known mismatch intentionally preserved).

## Risks

- Drift between `docs-general` and `docs-worker-chart-export` may confuse downstream readers; mitigate by calling out the mismatch explicitly in worker docs.

## Verify Steps

- `python scripts/agentctl.py task lint`
- Spot-check that updated JSON examples still validate against updated schemas (when schemas are adjusted).

## Rollback Plan

- Revert the commit that updates `docs-worker-chart-export/*`.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- `docs-worker-chart-export/README.md`
- `docs-worker-chart-export/chart-templates/README.md`
- `docs-worker-chart-export/contracts/charts_images_naming.md`
- `docs-worker-chart-export/contracts/charts_outputs_manifest.schema.json`
- `docs-worker-chart-export/contracts/flow_run.schema.json`
- `docs-worker-chart-export/spec/implementation_contract.md`
- `docs-worker-chart-export/test_vectors/expected_flow_run_step_patch.json`
- `docs-worker-chart-export/test_vectors/expected_manifest.json`
- `docs-worker-chart-export/test_vectors/flow_run_ready_chart_step.json`
- `docs/workflow/T-001/pr/diffstat.txt`
- `docs/workflow/T-001/pr/meta.json`
- `docs/workflow/T-001/pr/review.md`
- `docs/workflow/T-001/pr/verify.log`
<!-- END AUTO SUMMARY -->
