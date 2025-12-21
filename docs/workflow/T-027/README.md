# T-027: Add cloud_event_parsed log with runId/flowKey

## Summary

- Emit an explicit log event after flow_run parsing so runId/flowKey are present.

## Goal

- Add a new structured log event `cloud_event_parsed` that includes `runId` and `flowKey` (when available), without changing existing semantics.

## Scope

- Update CloudEvent handler to log `cloud_event_parsed` after parsing (and after optional Firestore fallback load).
- Ensure log payload includes at least: `eventId`, `eventType`, `subject`, `runId`, `flowKey` (if present), `service`, `env`.
- Update tests and QA scenarios to assert the new event appears in the expected flow.
- Update docs/runbooks that enumerate structured logging events (if any).

## References

- `worker_chart_export/entrypoints/cloud_event.py`
- `docs-worker-chart-export/spec/implementation_contract.md` (logging section)
- `docs/workflow/cloud_regression_practice.md`

## Plan

1) Add `cloud_event_parsed` log after parsing flow_run (and Firestore fallback).
2) Extend unit tests (or logging tests) to assert the new log event and fields.
3) Update QA scenarios / verify log expectations.
4) Document the new event in logging references.

## Planned Scenarios (TDD)

### Scenario 1: cloud_event_parsed emitted after successful parse

**Prerequisites**
- Valid Firestore update event for `flow_runs/{runId}`.
- Requires human-in-the-middle: NO

**Steps**
1) Trigger a Firestore update event with a valid `flow_run`.
2) Inspect structured logs.

**Expected result**
- `cloud_event_received` appears without runId/flowKey.
- `cloud_event_parsed` appears with runId and flowKey.

### Scenario 2: Parsed via Firestore fallback

**Prerequisites**
- Event payload missing data; runId extractable from subject.
- Requires human-in-the-middle: NO

**Steps**
1) Trigger a Firestore update event where `parse_flow_run_event` returns None.
2) Handler loads flow_run from Firestore.

**Expected result**
- `cloud_event_parsed` appears with runId and (if present) flowKey.

### Scenario 3: Ignored/no-op paths unchanged

**Prerequisites**
- Event that is filtered or has invalid steps.
- Requires human-in-the-middle: NO

**Steps**
1) Trigger an event that is ignored.
2) Inspect logs.

**Expected result**
- `cloud_event_parsed` is not emitted if no flow_run is parsed.
- Existing `cloud_event_ignored`/`cloud_event_noop` behavior unchanged.

## Risks

- Log volume increase (one extra event per successful parse).

## Verify Steps

- Run unit tests for logging (once added).
- Run cloud regression checklist log checks (optional).

## Rollback Plan

- Revert the commit; logging reverts to previous behavior.
