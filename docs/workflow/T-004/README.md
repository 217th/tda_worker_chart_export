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

## Risks

- Overwriting `steps` map or unrelated fields would break other workers; use field-level updates and validate patches.

## Verify Steps

- Unit tests: claim idempotency and expected step patch (based on `docs-worker-chart-export/test_vectors/expected_flow_run_step_patch.json` once updated).

## Rollback Plan

- Revert the commit; redeploy previous revision.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
