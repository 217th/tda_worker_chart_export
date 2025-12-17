# T-014: Refine WBS: invariants, deps, spec links

## Summary

- Refine the WBS to reduce spec drift and make invariants explicit (manifest completeness, config parsing ownership, observability dependencies).

## Goal

- Make each task self-contained with clear references to the service specs and acceptance criteria.

## Scope

- Update `tasks.json` (via `agentctl`) to clarify responsibilities and dependencies:
  - `CHART_IMG_ACCOUNTS_JSON` parsing/validation is owned by bootstrap (`T-002`) and is a fatal misconfiguration if invalid.
  - Observability (`T-013`) depends on stabilized error model work (`T-006`, `T-007`, `T-008`).
- Update `docs/workflow/T-002..T-013/README.md`:
  - Add explicit references to `docs-worker-chart-export`, `docs-general`, `docs-gcp` (and section pointers).
  - Add the invariant: every logical request must result in `manifest.items[]` or `manifest.failures[]` (no silent drops).

## Risks

- Over-constraining early tasks could slow iteration; keep the invariant and log schema stable, while allowing non-breaking refinements.

## Verify Steps

- `python scripts/agentctl.py task lint`

## Rollback Plan

- Revert the commit that updates planning docs and task metadata.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
