# T-005: Load chart_templates + build Chart-IMG request

## Summary

- Load `chart_templates/{chartTemplateId}` from Firestore and build Chart‑IMG request bodies from templates + dynamic `symbol/interval`.

## Goal

- Make `chartTemplateId` fully runtime-driven and populate `manifest.items[*].kind` from `template.description`.

## Scope

- Firestore reads from `chart_templates/{chartTemplateId}`.
- Merge logic: `template.request` as base + inject `symbol` and `interval` from `flow_run`.
- Template missing/invalid becomes a per-request failure and contributes to `minImages` evaluation.

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
