# T-005: Load chart_templates + build Chart-IMG request

## Summary

- Load `chart_templates/{chartTemplateId}` from Firestore and build Chart‑IMG request bodies from templates + dynamic `symbol/interval`.

## Goal

- Make `chartTemplateId` fully runtime-driven and populate `manifest.items[*].kind` from `template.description`.

## Scope

- Firestore reads from `chart_templates/{chartTemplateId}`.
- Merge logic: `template.request` as base + inject `symbol` and `interval` from `flow_run`.
- Template missing/invalid becomes a per-request failure and contributes to `minImages` evaluation.
- References:
  - `docs-worker-chart-export/spec/implementation_contract.md` §4 (inputs), §6 (manifest shape), §14 (template semantics)
  - `docs-worker-chart-export/chart-templates/README.md` (template structure)

## Planned Scenarios (TDD)

### Scenario 1: Valid template builds a Chart‑IMG request

**Prerequisites**
- Firestore `chart_templates/{chartTemplateId}` exists and contains a valid `request` object.
- A flow_run request with `symbol` and `timeframe`.
- Requires human-in-the-middle: NO

**Steps**
1) Load the template by `chartTemplateId`.
2) Build a Chart‑IMG request by merging template request + dynamic `symbol`/`interval`.

**Expected result**
- Final request contains template fields plus injected `symbol` and `interval`.
- Manifest item uses `kind = template.description` (as-is).

### Scenario 2: Template contains symbol/interval/timezone → overridden

**Prerequisites**
- Template `request` already includes `symbol`, `interval`, or `timezone`.
- Flow_run provides `symbol`/`timeframe` (and config provides default timezone if applicable).
- Requires human-in-the-middle: NO

**Steps**
1) Build a Chart‑IMG request from the template and flow_run/config.

**Expected result**
- The worker overwrites `symbol`, `interval`, and `timezone` with values derived from flow_run/config (template values do not leak through).

### Scenario 3: Missing template → validation failure

**Prerequisites**
- flow_run request references a nonexistent `chartTemplateId`.
- Requires human-in-the-middle: NO

**Steps**
1) Attempt to load the missing template.

**Expected result**
- The logical request is recorded in `manifest.failures[]` with `error.code = "VALIDATION_FAILED"`.

### Scenario 4: Invalid template schema → validation failure

**Prerequisites**
- Firestore template exists but is missing required fields (e.g., `request`).
- Requires human-in-the-middle: NO

**Steps**
1) Attempt to parse the template.

**Expected result**
- The logical request is recorded in `manifest.failures[]` with `error.code = "VALIDATION_FAILED"` and details.

### Scenario 5: Partial success across multiple requests

**Prerequisites**
- `inputs.requests[]` contains two entries: one with a valid template, one referencing a missing template.
- Requires human-in-the-middle: NO

**Steps**
1) Process both requests.

**Expected result**
- Manifest contains one `items[]` entry (success) and one `failures[]` entry (missing template).
- Final step status is computed using `minImages` against `len(items)`.

### Scenario 6: Duplicate chartTemplateId in inputs.requests[] → validation failure

**Prerequisites**
- `inputs.requests[]` contains duplicate `chartTemplateId` values.
- Requires human-in-the-middle: NO

**Steps**
1) Validate inputs before processing.

**Expected result**
- The step is marked `FAILED` with `error.code = "VALIDATION_FAILED"` to avoid PNG name collisions.

### Scenario 7: minImages > len(requests) → validation failure

**Prerequisites**
- `inputs.minImages` greater than the number of `inputs.requests`.
- Requires human-in-the-middle: NO

**Steps**
1) Validate inputs.

**Expected result**
- The step is marked `FAILED` with `error.code = "VALIDATION_FAILED"` and a clear message.

### Scenario 8: Description contains spaces/+ → preserved in kind

**Prerequisites**
- Template `description` contains spaces and `+`.
- Requires human-in-the-middle: NO

**Steps**
1) Build the manifest item for a successful request.

**Expected result**
- `manifest.items[*].kind` equals the original description string.

## Risks

- Template JSON may include unsupported fields for Chart‑IMG; validate and surface clear errors without leaking secrets.

## Verify Steps

- Unit tests for request building and `kind=description`.

## Rollback Plan

- Revert the commit; templates remain in Firestore.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
