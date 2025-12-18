# T-004: Firestore two-phase claim + finalize step patch

## Summary

- Implement two-phase orchestration updates: transactional claim `READY->RUNNING`, then finalize `RUNNING->SUCCEEDED|FAILED` after work.

## Goal

- Preserve orchestration invariants and keep transactions small (no external calls inside transactions).

## Scope

- Phase 1 (transaction): guard + claim `READY -> RUNNING` only.
- Phase 2 (non-transactional update): set `finishedAt`, `outputs.outputsManifestGcsUri` (required on success), and `error` on failure.
- Minimal patching: do not clobber unrelated step fields or other steps.
- References:
  - `docs-worker-chart-export/spec/implementation_contract.md` §3 (Claim + завершение), §7 (success rule), §8 (error codes)
  - `docs-general/contracts/orchestration_rules.md` (step status model + who sets READY)

## Planned Scenarios (TDD)

### Scenario 1: Transactional claim succeeds only for READY

**Prerequisites**
- Firestore flow_run with `steps[stepId].status == "READY"`.
- Requires human-in-the-middle: NO

**Steps**
1) Run the claim transaction for the step.

**Expected result**
- The step transitions to `RUNNING`; no external calls occur inside the transaction.

### Scenario 2: Concurrent claim (two workers)

**Prerequisites**
- Firestore flow_run with `steps[stepId].status == "READY"`.
- Requires human-in-the-middle: NO

**Steps**
1) Two workers attempt to claim the same step concurrently.

**Expected result**
- Only one worker successfully updates the step to `RUNNING`; the other observes no-op.

### Scenario 3: Transactional claim is idempotent

**Prerequisites**
- Firestore flow_run with `steps[stepId].status != "READY"`.
- Requires human-in-the-middle: NO

**Steps**
1) Run the claim transaction for the step.

**Expected result**
- Transaction exits with no update (no-op), preserving idempotency for retries.

### Scenario 4: Finalize SUCCEEDED with minimal patch

**Prerequisites**
- A `RUNNING` step and a valid manifest GCS URI.
- Requires human-in-the-middle: NO

**Steps**
1) Apply the finalize patch for success.

**Expected result**
- `status=SUCCEEDED`, `finishedAt` set, `outputs.outputsManifestGcsUri` set; unrelated fields/steps remain untouched.

### Scenario 5: Finalize FAILED with error payload

**Prerequisites**
- A `RUNNING` step and a failure result (error code/message).
- Requires human-in-the-middle: NO

**Steps**
1) Apply the finalize patch for failure.

**Expected result**
- `status=FAILED`, `finishedAt` set, `error.code` and `error.message` present; unrelated fields/steps remain untouched.

### Scenario 6: Finalize is idempotent (already SUCCEEDED/FAILED)

**Prerequisites**
- A step already finalized as `SUCCEEDED` or `FAILED`.
- Requires human-in-the-middle: NO

**Steps**
1) Call finalize again for the same step.

**Expected result**
- The step is not altered (no-op or safe overwrite with identical fields); no regression of status.

### Scenario 7: Minimal Firestore patch uses steps.<stepId>.* only

**Prerequisites**
- A flow_run document with multiple steps.
- Requires human-in-the-middle: NO

**Steps**
1) Apply claim/finalize updates.

**Expected result**
- Firestore update targets only `steps.<stepId>.*` fields (no full `steps` map overwrite).

## Risks

- Overwriting `steps` map or unrelated fields would break other workers; use field-level updates and validate patches.

## Verify Steps

- Unit tests: claim idempotency and expected step patch (based on `docs-worker-chart-export/test_vectors/expected_flow_run_step_patch.json` once updated).

## Rollback Plan

- Revert the commit; redeploy previous revision.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- `docs/workflow/T-004/pr/diffstat.txt`
- `docs/workflow/T-004/pr/meta.json`
- `docs/workflow/T-004/pr/scenarios.md`
- `docs/workflow/T-004/pr/verify.log`
- `docs/workflow/T-004/pr/verify_scenarios_report.md`
- `tests/tasks/T-004/test_orchestration.py`
- `worker_chart_export/orchestration.py`
<!-- END AUTO SUMMARY -->
