# T-016 — Implemented Scenarios (task-level)

This file lists the concrete scenarios implemented in this task. If some logic is incomplete, explicitly mark limitations.

Planned scenarios source:
- `docs/workflow/T-016/README.md` → **Planned Scenarios (TDD)**
- Each implemented scenario should map to a planned one (or explicitly note a justified deviation).

References:
- Spec(s):
  - `docs/workflow/QA_CYCLE.md`

---

## 1) QA_CYCLE enforces pre-dev scenarios

**Scenario**
- QA workflow requires Planned Scenarios in task READMEs before implementation.

**Implemented in**
- `docs/workflow/QA_CYCLE.md`

**Limitations / stubs**
- None.

### Manual test

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) Open `docs/workflow/QA_CYCLE.md` and verify the Pre-dev requirement section.

**Expected result**
- The document states Planned Scenarios (TDD) must be defined in task READMEs before implementation.

---

## 2) Task README template includes Planned Scenarios

**Scenario**
- A template exists with a standard Planned Scenarios (TDD) section.

**Implemented in**
- `docs/workflow/_templates/task_readme.md`

**Limitations / stubs**
- None.

### Manual test

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) Open `docs/workflow/_templates/task_readme.md`.

**Expected result**
- The template includes a Planned Scenarios section with prerequisites/steps/expected results.

---

## 3) TODO task READMEs contain Planned Scenarios

**Scenario**
- All TODO tasks T-003..T-013 include Planned Scenarios (TDD) in their README.

**Implemented in**
- `docs/workflow/T-003/README.md`
- `docs/workflow/T-004/README.md`
- `docs/workflow/T-005/README.md`
- `docs/workflow/T-006/README.md`
- `docs/workflow/T-007/README.md`
- `docs/workflow/T-008/README.md`
- `docs/workflow/T-009/README.md`
- `docs/workflow/T-010/README.md`
- `docs/workflow/T-011/README.md`
- `docs/workflow/T-012/README.md`
- `docs/workflow/T-013/README.md`

**Limitations / stubs**
- None.

### Manual test

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) Open each README listed above.
2) Verify a "Planned Scenarios (TDD)" section exists with prerequisites/steps/expected results.

**Expected result**
- All TODO task READMEs contain a Planned Scenarios (TDD) section with structured scenarios.

---

## 4) Implemented scenarios template references planned scenarios

**Scenario**
- The implemented-scenarios template links to the Planned Scenarios section in the task README.

**Implemented in**
- `docs/workflow/_templates/pr_scenarios.md`

**Limitations / stubs**
- None.

### Manual test

**Prerequisites**
- None
- Requires human-in-the-middle: NO

**Steps**
1) Open `docs/workflow/_templates/pr_scenarios.md`.

**Expected result**
- The template explicitly references `docs/workflow/T-XXX/README.md` Planned Scenarios.
