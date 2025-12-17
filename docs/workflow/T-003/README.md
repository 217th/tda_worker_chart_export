# T-003: CloudEvent ingest: fast filter + deterministic READY pick

## Summary

- Implement CloudEvent ingest logic: fast no-op filter, deterministic READY step selection, explicit at-least-once safety.

## Goal

- Ensure repeated Firestore update events do not trigger duplicate work and that the worker remains safe under retries.

## Scope

- Functions Framework CloudEvent adapter.
- Fast no-op if no `CHART_EXPORT` step is `READY`.
- Deterministic pick: sort `stepId` ascending, pick first `READY`.
- No network calls inside Firestore transactions; transaction is reserved for claim only.
- References:
  - `docs-worker-chart-export/spec/implementation_contract.md` §2 (Trigger/filter), §3.1 (Claim)
  - `docs-general/contracts/orchestration_rules.md` (“READY -> RUNNING -> SUCCEEDED|FAILED”, idempotency key `runId+stepId`)
  - `docs-gcp/runbook/prod_runbook_gcp.md` §4 (Eventarc/Firestore triggers), §8 (log fields)

## Risks

- If selection/claim logic diverges between CLI and CloudEvent paths, behavior becomes unpredictable; keep selection logic in shared core module.

## Verify Steps

- Unit tests for fast-filter + deterministic pick.

## Rollback Plan

- Revert the commit; redeploy previous revision.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
