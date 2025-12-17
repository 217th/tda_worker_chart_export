# T-015 — Implemented Scenarios (QA harness)

References:
- `docs/workflow/QA_CYCLE.md` (new repository QA cycle rules)

---

## 1) Full regression runner (single command)

**Scenario**
- There is a single command that runs all accumulated automated tests under `tests/tasks/T-*`.

**Implemented in**
- `scripts/qa/run_all.sh:1`
- `scripts/qa/run_all.py:1`

**Limitations / stubs**
- This runner only covers tests that are expressible as local Python unittests (no GCP, no external network).

### Manual test

**Prerequisites**
- Python 3.13 available.
- Run from repo root (or any directory; the script resolves repo root itself).
- Requires human-in-the-middle: NO

**Steps**
1) List discovered task suites:
   - `bash scripts/qa/run_all.sh --list`
2) Run all suites:
   - `bash scripts/qa/run_all.sh`

**Expected result**
- Step (1) prints one line per `tests/tasks/T-*` directory.
- Step (2) exits with code `0` and prints unittest output for each task suite.

---

## 2) Standardized test layout (per task)

**Scenario**
- Automated tests accumulate under `tests/tasks/T-###/…`, making ownership and coverage explicit.

**Implemented in**
- `tests/tasks/README.md:1`
- migrated existing tests into: `tests/tasks/T-002/*`

**Limitations / stubs**
- Task directories contain hyphens (`T-002`), so naive `python -m unittest discover -s tests` may break.
  - The canonical runner is `bash scripts/qa/run_all.sh`.

### Manual test

**Prerequisites**
- Requires human-in-the-middle: NO

**Steps**
1) Inspect test directories:
   - `find tests/tasks -maxdepth 2 -type f -print`

**Expected result**
- Files exist under `tests/tasks/T-002/` and future tasks can add their own directories.

---

## 3) Templates for PR QA artifacts

**Scenario**
- There are templates for:
  - `docs/workflow/T-###/pr/scenarios.md`
  - `docs/workflow/T-###/pr/verify_scenarios_report.md`
  including an explicit marker for human-in-the-middle scenarios.

**Implemented in**
- `docs/workflow/_templates/pr_scenarios.md:1`
- `docs/workflow/_templates/pr_verify_scenarios_report.md:1`

**Limitations / stubs**
- Templates are not automatically copied by tooling; they are meant to be copied/edited per task PR.

### Manual test

**Prerequisites**
- Requires human-in-the-middle: NO

**Steps**
1) Open template files:
   - `sed -n '1,120p' docs/workflow/_templates/pr_scenarios.md`
   - `sed -n '1,120p' docs/workflow/_templates/pr_verify_scenarios_report.md`

**Expected result**
- Both templates exist and include a “Requires human-in-the-middle” field.

