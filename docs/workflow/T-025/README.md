# T-025: Simplify GCS artifact paths

## Summary

- Shorten Cloud Storage object paths for charts PNG + manifest (reduce nesting).

## Goal

- Define and implement a shorter, still deterministic, gs:// path scheme for chart artifacts and manifests.

## Scope

- Propose a new canonical path format for:
  - PNGs (chart images)
  - manifest.json
- Update worker code to write to the new paths.
- Update contracts/specs and test vectors under `docs-worker-chart-export/`.
- Update any runbooks/examples referencing old paths.
- Document migration/compatibility notes (old paths may exist in bucket).

## References

- `docs-worker-chart-export/spec/implementation_contract.md`
- `docs-worker-chart-export/contracts/charts_outputs_manifest.schema.json`
- `docs-worker-chart-export/contracts/charts_images_naming.md`
- `docs-worker-chart-export/test_vectors/*`
- `docs-gcp/runbook/prod_runbook_gcp.md`

## Plan

1) Propose shortened path scheme (PNG + manifest) and validate against specs.
2) Update contracts/specs + examples to use new scheme.
3) Update code paths in `worker_chart_export/` for writes and manifest generation.
4) Update tests and fixtures to the new scheme.
5) Add migration/compatibility note (old paths stay, manifest is source of truth).

## Planned Scenarios (TDD)

### Scenario 1: New canonical gs:// path scheme

**Prerequisites**
- Review current manifest and naming specs.
- Requires human-in-the-middle: NO

**Steps**
1) Define a shorter path for PNGs and manifest.
2) Confirm deterministic uniqueness (runId + stepId + templateId).

**Expected result**
- A single canonical path scheme is documented and unambiguous.

### Scenario 2: Code writes to new path

**Prerequisites**
- New path scheme defined.
- Requires human-in-the-middle: NO

**Steps**
1) Run a local CLI export with mock/record.
2) Inspect manifest outputs to verify new paths.

**Expected result**
- Manifest contains gs:// URIs using the new scheme.

### Scenario 3: Backward compatibility note

**Prerequisites**
- New path scheme defined.
- Requires human-in-the-middle: NO

**Steps**
1) Document that old objects remain in GCS and are not deleted.
2) State that consumers must rely on manifest only.

**Expected result**
- Clear migration note included in docs/runbook.

## Risks

- Downstream systems might assume old paths; ensure manifest is the source of truth.

## Verify Steps

- Check updated specs + test vectors reference the new gs:// paths.
- Run regression test bundle (per QA harness).

## Rollback Plan

- Revert the commit; code and docs return to old path scheme.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
