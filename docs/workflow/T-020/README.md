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

## Candidates (to decide)

### Firestore

- **Firebase Local Emulator Suite (Firestore emulator)**: official emulator for Firestore, started via Firebase CLI; requires Node.js and Java; does not enforce production limits.
- **In‑memory fake**: lightweight fake for tests (no external process); faster but lower fidelity (no real indexes/transactions).

### GCS

- **fake‑gcs‑server**: community HTTP server emulating GCS API; usable in CI/local.
- **Filesystem‑backed fake**: simple local file storage adapter (no HTTP), fastest but least faithful.

## Plan

1) Choose Firestore harness (emulator vs fake) and document rationale and setup.
2) Choose GCS harness (fake‑gcs‑server vs filesystem fake) and document rationale and setup.
3) Document CI startup: commands, env vars, ports, health checks, teardown.
4) Document limitations vs prod (auth, consistency, missing APIs).
5) Update `docs/workflow/T-011/README.md` to reference the chosen harness.

## Planned Scenarios (TDD)

### Scenario 1: Firestore harness selection + setup

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) Decide Firestore harness (Firebase emulator vs in‑memory fake).
2) Document setup and teardown steps for local and CI.
3) Record required tooling (e.g., Node/Java if emulator).

**Expected result**
- A concrete, reproducible Firestore setup is documented.

### Scenario 2: GCS harness selection + setup

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) Decide GCS harness (fake‑gcs‑server vs filesystem-backed fake).
2) Document setup and teardown steps for local and CI.

**Expected result**
- A concrete, reproducible GCS setup is documented.

### Scenario 3: CI startup instructions

**Prerequisites**
- Chosen harness components.
- Requires human-in-the-middle: NO

**Steps**
1) Document CI commands to start emulators/fakes (or in‑process fakes).
2) Document required env vars, ports, and health checks.
3) Document shutdown/cleanup steps.

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

### Scenario 5: Offline/no‑network guarantee

**Prerequisites**
- Harness decisions.
- Requires human-in-the-middle: NO

**Steps**
1) Document how tests enforce “no external network” (e.g., block HTTP except local emulator ports).

**Expected result**
- Integration tests are guaranteed offline except emulator/fake endpoints.

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
