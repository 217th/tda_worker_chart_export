# T-004 — Scenarios Verification Report

Date: 2025-12-18  
Branch: `task/T-004/firestore-claim` (manual re-run from `task/T-005/templates-requests`)

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

## Manual scenario checks (executed)

### Scenario 1) Claim READY → RUNNING

**Command**
```bash
python - << 'PY'
from worker_chart_export.orchestration import claim_step_transaction
class FakeFirestore:
    def __init__(self):
        self.store = {"flow_runs": {"run-1": {"steps": {"stepA": {"status": "READY"}}}}}
    def collection(self, name): return self
    def document(self, doc_id): self._doc_id = doc_id; return self
    def get(self, transaction=None):
        class Snap:
            def __init__(self, data): self._data = data
            def to_dict(self): return self._data
        return Snap(self.store["flow_runs"][self._doc_id])
    def update(self, update_data):
        self.store["flow_runs"][self._doc_id]["steps"]["stepA"]["status"] = update_data["steps.stepA.status"]
    def transaction(self):
        class Tx:
            def __init__(self, ref): self.ref = ref; self._updates = []
            def update(self, doc_ref, update_data): self._updates.append(update_data)
            def commit(self):
                for update_data in self._updates: self.ref.update(update_data)
        return Tx(self)
client = FakeFirestore()
result = claim_step_transaction(client=client, run_id="run-1", step_id="stepA")
print(result.claimed, client.store["flow_runs"]["run-1"]["steps"]["stepA"]["status"])
PY
```

**Result**
- Output: `True RUNNING`

### Scenario 2) Concurrent claim

**Command**
```bash
python - << 'PY'
from worker_chart_export.orchestration import claim_step_transaction
class FakeFirestore:
    def __init__(self):
        self.store = {"flow_runs": {"run-1": {"steps": {"stepA": {"status": "READY"}}}}}
    def collection(self, name): return self
    def document(self, doc_id): self._doc_id = doc_id; return self
    def get(self, transaction=None):
        class Snap:
            def __init__(self, data): self._data = data
            def to_dict(self): return self._data
        return Snap(self.store["flow_runs"][self._doc_id])
    def update(self, update_data):
        self.store["flow_runs"][self._doc_id]["steps"]["stepA"]["status"] = update_data["steps.stepA.status"]
    def transaction(self):
        class Tx:
            def __init__(self, ref): self.ref = ref; self._updates = []
            def update(self, doc_ref, update_data): self._updates.append(update_data)
            def commit(self):
                for update_data in self._updates: self.ref.update(update_data)
        return Tx(self)
client = FakeFirestore()
first = claim_step_transaction(client=client, run_id="run-1", step_id="stepA")
second = claim_step_transaction(client=client, run_id="run-1", step_id="stepA")
print(first.claimed, second.claimed)
PY
```

**Result**
- Output: `True False`

### Scenario 3) Claim idempotent (not READY)

**Command**
```bash
python - << 'PY'
from worker_chart_export.orchestration import claim_step_transaction
class FakeFirestore:
    def __init__(self):
        self.store = {"flow_runs": {"run-1": {"steps": {"stepA": {"status": "RUNNING"}}}}}
    def collection(self, name): return self
    def document(self, doc_id): self._doc_id = doc_id; return self
    def get(self, transaction=None):
        class Snap:
            def __init__(self, data): self._data = data
            def to_dict(self): return self._data
        return Snap(self.store["flow_runs"][self._doc_id])
    def update(self, update_data):
        self.store["flow_runs"][self._doc_id]["steps"]["stepA"]["status"] = update_data["steps.stepA.status"]
    def transaction(self):
        class Tx:
            def __init__(self, ref): self.ref = ref; self._updates = []
            def update(self, doc_ref, update_data): self._updates.append(update_data)
            def commit(self):
                for update_data in self._updates: self.ref.update(update_data)
        return Tx(self)
client = FakeFirestore()
result = claim_step_transaction(client=client, run_id="run-1", step_id="stepA")
print(result.claimed, client.store["flow_runs"]["run-1"]["steps"]["stepA"]["status"])
PY
```

**Result**
- Output: `False RUNNING`

### Scenario 4) Finalize SUCCEEDED

**Command**
```bash
python - << 'PY'
from worker_chart_export.orchestration import finalize_step
class FakeFirestore:
    def __init__(self):
        self.store = {"flow_runs": {"run-1": {"steps": {"stepA": {"status": "RUNNING", "outputs": {"keep": "yes"}}}}}}
    def collection(self, name): return self
    def document(self, doc_id): self._doc_id = doc_id; return self
    def get(self, transaction=None):
        class Snap:
            def __init__(self, data): self._data = data
            def to_dict(self): return self._data
        return Snap(self.store["flow_runs"][self._doc_id])
    def update(self, update_data):
        step = self.store["flow_runs"][self._doc_id]["steps"]["stepA"]
        step["status"] = update_data["steps.stepA.status"]
        step["finishedAt"] = update_data["steps.stepA.finishedAt"]
        step.setdefault("outputs", {})["outputsManifestGcsUri"] = update_data["steps.stepA.outputs.outputsManifestGcsUri"]
    def transaction(self):
        class Tx:
            def __init__(self, ref): self.ref = ref; self._updates = []
            def update(self, doc_ref, update_data): self._updates.append(update_data)
            def commit(self):
                for update_data in self._updates: self.ref.update(update_data)
        return Tx(self)
client = FakeFirestore()
finalize_step(client=client, run_id="run-1", step_id="stepA", status="SUCCEEDED",
              finished_at="2025-12-15T10:26:15Z", outputs_manifest_gcs_uri="gs://bucket/manifest.json")
step = client.store["flow_runs"]["run-1"]["steps"]["stepA"]
print(step["status"], step["outputs"]["outputsManifestGcsUri"], step["outputs"]["keep"])
PY
```

**Result**
- Output: `SUCCEEDED gs://bucket/manifest.json yes`

### Scenario 5) Finalize FAILED

**Command**
```bash
python - << 'PY'
from worker_chart_export.orchestration import finalize_step, StepError
class FakeFirestore:
    def __init__(self):
        self.store = {"flow_runs": {"run-1": {"steps": {"stepA": {"status": "RUNNING"}}}}}
    def collection(self, name): return self
    def document(self, doc_id): self._doc_id = doc_id; return self
    def get(self, transaction=None):
        class Snap:
            def __init__(self, data): self._data = data
            def to_dict(self): return self._data
        return Snap(self.store["flow_runs"][self._doc_id])
    def update(self, update_data):
        step = self.store["flow_runs"][self._doc_id]["steps"]["stepA"]
        step["status"] = update_data["steps.stepA.status"]
        step["error"] = update_data["steps.stepA.error"]
    def transaction(self):
        class Tx:
            def __init__(self, ref): self.ref = ref; self._updates = []
            def update(self, doc_ref, update_data): self._updates.append(update_data)
            def commit(self):
                for update_data in self._updates: self.ref.update(update_data)
        return Tx(self)
client = FakeFirestore()
finalize_step(client=client, run_id="run-1", step_id="stepA", status="FAILED",
              finished_at="2025-12-15T10:26:15Z", error=StepError(code="VALIDATION_FAILED", message="bad input"))
step = client.store["flow_runs"]["run-1"]["steps"]["stepA"]
print(step["status"], step["error"]["code"], step["error"]["message"])
PY
```

**Result**
- Output: `FAILED VALIDATION_FAILED bad input`

### Scenario 6) Finalize idempotent (already SUCCEEDED)

**Command**
```bash
python - << 'PY'
from worker_chart_export.orchestration import finalize_step
class FakeFirestore:
    def __init__(self):
        self.store = {"flow_runs": {"run-1": {"steps": {"stepA": {"status": "SUCCEEDED", "outputs": {"outputsManifestGcsUri": "gs://old"}}}}}}
    def collection(self, name): return self
    def document(self, doc_id): self._doc_id = doc_id; return self
    def get(self, transaction=None):
        class Snap:
            def __init__(self, data): self._data = data
            def to_dict(self): return self._data
        return Snap(self.store["flow_runs"][self._doc_id])
    def update(self, update_data):
        self.store["flow_runs"][self._doc_id]["steps"]["stepA"]["status"] = update_data["steps.stepA.status"]
    def transaction(self):
        class Tx:
            def __init__(self, ref): self.ref = ref; self._updates = []
            def update(self, doc_ref, update_data): self._updates.append(update_data)
            def commit(self):
                for update_data in self._updates: self.ref.update(update_data)
        return Tx(self)
client = FakeFirestore()
result = finalize_step(client=client, run_id="run-1", step_id="stepA", status="SUCCEEDED",
                       finished_at="2025-12-15T10:26:15Z", outputs_manifest_gcs_uri="gs://new")
step = client.store["flow_runs"]["run-1"]["steps"]["stepA"]
print(result.updated, step["outputs"]["outputsManifestGcsUri"])
PY
```

**Result**
- Output: `False gs://old`

### Scenario 7) Minimal Firestore patch keys

**Command**
```bash
python - << 'PY'
from worker_chart_export.orchestration import build_claim_update, build_finalize_success_update, build_finalize_failure_update, StepError
step_id = "charts:1M:ctpl_price_ma1226_vol_v1"
claim = build_claim_update(step_id)
success = build_finalize_success_update(step_id=step_id, finished_at="2025-12-15T10:26:15Z",
                                       outputs_manifest_gcs_uri="gs://bucket/manifest.json")
failed = build_finalize_failure_update(step_id=step_id, finished_at="2025-12-15T10:26:15Z",
                                      error=StepError(code="FAILED", message="err"))
print(sorted(list(claim.keys()) + list(success.keys()) + list(failed.keys())))
PY
```

**Result**
- Output keys all start with `steps.<stepId>.` (no top-level `steps` overwrite).
