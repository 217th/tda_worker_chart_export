# T-020: Integration test harness infra

## Summary

- Define and document the concrete integration-test harness for Firestore + GCS, including CI startup and limitations.

## Goal

- Ensure integration tests run deterministically and offline while remaining prod‑representative.

## Scope

- Choose Firestore emulator vs in‑memory fake and document rationale.
- Choose GCS emulator/fake (e.g., fake‑gcs‑server or filesystem-backed fake) and document rationale.
- Provide CI setup steps (commands, env vars, ports).
- Document limitations (eventual consistency gaps, auth differences, unsupported APIs).
- Update T‑011 to reference this harness in its scenarios and implementation notes.

## Planned Scenarios (TDD)

### Scenario 1: Firestore harness selection + setup

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) Decide Firestore harness (emulator or fake).
2) Document setup and teardown steps for local and CI.

**Expected result**
- A concrete, reproducible Firestore setup is documented.

### Scenario 2: GCS harness selection + setup

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) Decide GCS harness (fake server or filesystem-backed fake).
2) Document setup and teardown steps for local and CI.

**Expected result**
- A concrete, reproducible GCS setup is documented.

### Scenario 3: CI startup instructions

**Prerequisites**
- Chosen harness components.
- Requires human-in-the-middle: NO

**Steps**
1) Document CI commands to start emulators/fakes.
2) Document required env vars and health checks.

**Expected result**
- CI can boot harness consistently and run integration tests without network.

### Scenario 4: Limitations and fidelity

**Prerequisites**
- Harness decisions.
- Requires human-in-the-middle: NO

**Steps**
1) Document mismatches vs prod (auth, consistency, APIs).

**Expected result**
- Clear list of limitations and how tests should compensate.

## Risks

- Divergence between emulator and prod behavior can mask real issues; document known gaps.

## Verify Steps

- Read `docs/workflow/T-011/README.md` and confirm it references the chosen harness.

## Rollback Plan

- Revert the commit; T‑011 will keep placeholder harness wording.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
