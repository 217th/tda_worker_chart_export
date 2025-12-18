# T-004 — Scenarios Verification Report

Date: 2025-12-18  
Branch: `task/T-004/firestore-claim`

Source checklist: `docs/workflow/T-004/README.md`

---

## Environment / prerequisites

**Prerequisites (as stated in scenarios)**
- Python 3.13

**Observed environment**
- Python: `3.13.11`

---

## Automated checks executed

**Command**
```bash
python3 scripts/qa/run_all.py --task T-004
```

**Result**
- Exit code: `0`
- Tests executed: 7
- Status: **PASS**

---

## Scenario coverage (auto)

| Scenario (README) | Coverage | Test(s) |
| --- | --- | --- |
| 1) Transactional claim succeeds only for READY | Auto | `tests/tasks/T-004/test_orchestration.py::test_claim_ready_transitions_to_running` |
| 2) Concurrent claim (two workers) | Auto | `tests/tasks/T-004/test_orchestration.py::test_concurrent_claim_only_one_succeeds` |
| 3) Transactional claim is idempotent | Auto | `tests/tasks/T-004/test_orchestration.py::test_claim_not_ready_is_noop` |
| 4) Finalize SUCCEEDED with minimal patch | Auto | `tests/tasks/T-004/test_orchestration.py::test_finalize_success_updates_minimal_fields` |
| 5) Finalize FAILED with error payload | Auto | `tests/tasks/T-004/test_orchestration.py::test_finalize_failed_sets_error_payload` |
| 6) Finalize is idempotent | Auto | `tests/tasks/T-004/test_orchestration.py::test_finalize_idempotent_when_already_succeeded` |
| 7) Minimal Firestore patch uses steps.<stepId>.* only | Auto | `tests/tasks/T-004/test_orchestration.py::test_minimal_patch_uses_step_field_paths_only` |

---

## Manual scenario checks

- Not executed in this environment (auto coverage exists for all listed scenarios).
