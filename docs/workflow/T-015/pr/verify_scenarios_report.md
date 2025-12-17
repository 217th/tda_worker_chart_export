# T-015 — Scenarios Verification Report

Date: 2025-12-17  
Branch: `task/T-015/qa-harness`

Source checklist: `docs/workflow/T-015/pr/scenarios.md`

---

## Environment / prerequisites

**Prerequisites**
- Python 3.13
- Local filesystem access (no network/GCP required)

**Actions performed**
- Ran the regression runner commands from repo root.
- Verified output ordering and fixed `run_all.py` to flush suite headers.

**Observed**
- `bash scripts/qa/run_all.sh` runs the accumulated test suite(s) successfully.

---

## Scenario 1) Full regression runner

**Commands executed**
```bash
bash scripts/qa/run_all.sh --list
bash scripts/qa/run_all.sh
```

**Observed result**
- `--list` printed:
  - `.../tests/tasks/T-002`
- Full run printed:
  - `=== T-002 ===`
  - 5 passing tests
- Exit code: `0`

**Fixes**
- Adjusted `scripts/qa/run_all.py` to `flush=True` when printing suite headers so they appear before test output.

---

## Scenario 2) Standardized test layout

**Commands executed**
```bash
find tests/tasks -maxdepth 2 -type f -print
```

**Observed result**
- Test files exist under `tests/tasks/T-002/` and no longer live directly under `tests/`.

---

## Scenario 3) Templates for PR QA artifacts

**Commands executed**
```bash
sed -n '1,120p' docs/workflow/_templates/pr_scenarios.md
sed -n '1,120p' docs/workflow/_templates/pr_verify_scenarios_report.md
```

**Observed result**
- Templates exist and include “Requires human-in-the-middle: YES|NO”.

