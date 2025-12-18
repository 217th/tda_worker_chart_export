# T-017: Define integration test harness (Firestore/GCS)

## Summary

- Decide and document the concrete harness for integration tests (Firestore + GCS) so tests are deterministic and offline.

## Goal

- Ensure T-011 integration tests run without external network calls, with a clear, reproducible harness choice.

## Scope

- Choose Firestore harness: emulator vs in-memory fake.
- Choose GCS harness: fake-gcs-server vs filesystem-backed fake (or equivalent).
- Document setup steps and limitations for the chosen harness.
- Update T-011 implementation plan to use the chosen harness.
- References:
  - `docs-worker-chart-export/spec/implementation_contract.md` §12.2 (mock mode: no network)
  - `docs-worker-chart-export/spec/implementation_contract.md` §9 (idempotency expectations)

## Planned Scenarios (TDD)

### Scenario 1: Firestore harness decision

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) Evaluate Firestore emulator vs in-memory fake for CI/local usage.
2) Choose one and document the rationale.

**Expected result**
- A clear decision with setup steps and limitations recorded in docs.

### Scenario 2: GCS harness decision

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) Evaluate fake-gcs-server vs filesystem-backed fake.
2) Choose one and document the rationale.

**Expected result**
- A clear decision with setup steps and limitations recorded in docs.

### Scenario 3: T-011 updated to reference the chosen harness

**Prerequisites**
- Harness decisions from Scenarios 1–2.
- Requires human-in-the-middle: NO

**Steps**
1) Update T-011 README to reference the chosen harness and required setup.

**Expected result**
- T-011 scenarios explicitly target the chosen harness.

## Risks

- Incompatible harness may cause flakiness or slow tests; document tradeoffs and constraints.

## Verify Steps

- Read T-011 README and confirm harness references match the documented decision.

## Rollback Plan

- Revert the commit; T-011 can fall back to a placeholder harness description.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
