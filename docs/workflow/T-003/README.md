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

## Planned Scenarios (TDD)

### Scenario 1: Realistic Firestore CloudEvent payload is parsed correctly

**Prerequisites**
- A representative Eventarc Firestore **update** CloudEvent payload for `flow_runs/{runId}` (document name/path + fields).
- Requires human-in-the-middle: NO

**Steps**
1) Feed the CloudEvent payload into the handler.

**Expected result**
- The handler recognizes the event as `flow_runs/{runId}` update, extracts `runId`, and reads `steps` from the document fields.

### Scenario 2: No READY CHART_EXPORT step → no-op (explicit handler result + log fields)

**Prerequisites**
- A flow_run document with no `steps[*].type == "CHART_EXPORT"` in `READY`.
- Requires human-in-the-middle: NO

**Steps**
1) Send a CloudEvent for the flow_run update to the handler.

**Expected result**
- Handler returns a successful response (no exception; no retry trigger).
- INFO log entry includes required fields (at minimum: `service`, `env`, `runId`, `eventId`, `severity`, `reason=no_ready_step`).

### Scenario 3: Multiple READY steps → deterministic pick

**Prerequisites**
- A flow_run document with two `CHART_EXPORT` steps in `READY`, with different `stepId` values.
- Requires human-in-the-middle: NO

**Steps**
1) Invoke the deterministic selection helper (via handler).

**Expected result**
- The worker selects the lexicographically smallest `stepId` and attempts claim only for that step.

### Scenario 4: Double event (at-least-once) → safe no-op on repeat

**Prerequisites**
- A flow_run event that has already triggered a claim (step is now `RUNNING`).
- Requires human-in-the-middle: NO

**Steps**
1) Send the same CloudEvent again.

**Expected result**
- The handler does not attempt work again; it exits via claim no-op with an INFO log.

### Scenario 5: Step already RUNNING/SUCCEEDED/FAILED → no-op

**Prerequisites**
- A flow_run document where the target `CHART_EXPORT` step is not `READY`.
- Requires human-in-the-middle: NO

**Steps**
1) Send a CloudEvent for the flow_run update to the handler.

**Expected result**
- No claim is attempted; handler exits with a no-op log (idempotent retry safety).

### Scenario 6: Non-target event or malformed document → ignore (noise filter)

**Prerequisites**
- Firestore **create/delete** events, events for other collections, or `flow_run` documents with invalid `steps` (not a map/object, missing `status` or `stepType`).
- Requires human-in-the-middle: NO

**Steps**
1) Send the event to the handler.

**Expected result**
- Handler ignores the event (no claim, no errors).

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
