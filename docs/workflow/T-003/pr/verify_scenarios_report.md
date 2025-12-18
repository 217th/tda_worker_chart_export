# T-003 — Scenarios Verification Report

Date: 2025-12-18  
Branch: `task/T-003/cloudevent-ingest`

Source checklist: `docs/workflow/T-003/README.md`

---

## Environment / prerequisites

**Prerequisites (as stated in scenarios)**
- Python 3.13

**Observed environment**
- Python: `3.10.12` (sandbox default)

**Note**
- Automated tests executed under Python 3.10 due to sandbox constraints. Re-run under Python 3.13 in your environment for full compliance.

---

## Automated checks executed

**Command**
```bash
python3 scripts/qa/run_all.py --task T-003
```

**Result**
- Exit code: `0`
- Tests executed: 8
- Status: **PASS**

---

## Scenario coverage (auto)

| Scenario (README) | Coverage | Test(s) |
| --- | --- | --- |
| 1) Realistic Firestore CloudEvent payload parsed | Auto | `tests/tasks/T-003/test_ingest.py::test_parse_flow_run_event_extracts_run_id_and_steps` |
| 2) No READY CHART_EXPORT → no-op | Auto | `tests/tasks/T-003/test_ingest.py::test_handler_noop_when_no_ready_step` |
| 3) Multiple READY → deterministic pick | Auto | `tests/tasks/T-003/test_ingest.py::test_pick_ready_step_is_deterministic` |
| 4) Double event → safe no-op | Auto | `tests/tasks/T-003/test_ingest.py::test_handler_noop_when_no_ready_step` (RUNNING status) |
| 5) Step already RUNNING/SUCCEEDED/FAILED → no-op | Auto | `tests/tasks/T-003/test_ingest.py::test_handler_noop_when_no_ready_step` |
| 6) Non-target/malformed → ignore | Auto | `tests/tasks/T-003/test_ingest.py::test_handler_ignores_non_update_event`, `test_handler_ignores_other_collection`, `test_handler_ignores_invalid_steps_shape` |

---

## Manual scenario checks

- Not executed in this environment (auto coverage exists for all listed scenarios).
