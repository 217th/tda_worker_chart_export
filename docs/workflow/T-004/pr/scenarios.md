# T-004 — Implemented Scenarios

References:
- Spec: `docs-worker-chart-export/spec/implementation_contract.md` (§3.1–3.2)
- Orchestration rules: `docs-general/contracts/orchestration_rules.md`

---

## 1) Transactional claim succeeds only for READY

**Scenario**
- If the step is `READY`, claim transitions it to `RUNNING` within a transaction.

**Implemented in**
- `worker_chart_export/orchestration.py:1` (`claim_step_transaction`, `build_claim_update`)

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from worker_chart_export.orchestration import claim_step_transaction

   class FakeFirestore:
       def __init__(self):
           self.store = {"flow_runs": {"run-1": {"steps": {"stepA": {"status": "READY"}}}}}
       def collection(self, name):
           return self
       def document(self, doc_id):
           self._doc_id = doc_id
           return self
       def get(self, transaction=None):
           class Snap:
               def __init__(self, data):
                   self._data = data
               def to_dict(self):
                   return self._data
           return Snap(self.store["flow_runs"][self._doc_id])
       def update(self, update_data):
           self.store["flow_runs"][self._doc_id]["steps"]["stepA"]["status"] = update_data["steps.stepA.status"]
       def transaction(self):
           class Tx:
               def __init__(self, ref):
                   self.ref = ref
                   self._updates = []
               def update(self, doc_ref, update_data):
                   self._updates.append(update_data)
               def commit(self):
                   for update_data in self._updates:
                       self.ref.update(update_data)
           return Tx(self)

   client = FakeFirestore()
   result = claim_step_transaction(client=client, run_id="run-1", step_id="stepA")
   print(result.claimed, client.store["flow_runs"]["run-1"]["steps"]["stepA"]["status"])
   PY
   ```

**Expected result**
- Printed: `True RUNNING`.

---

## 2) Concurrent claim (two workers)

**Scenario**
- Two workers attempt to claim the same `READY` step; only one succeeds.

**Implemented in**
- `worker_chart_export/orchestration.py:1` (`claim_step_transaction`)

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from worker_chart_export.orchestration import claim_step_transaction

   class FakeFirestore:
       def __init__(self):
           self.store = {"flow_runs": {"run-1": {"steps": {"stepA": {"status": "READY"}}}}}
       def collection(self, name):
           return self
       def document(self, doc_id):
           self._doc_id = doc_id
           return self
       def get(self, transaction=None):
           class Snap:
               def __init__(self, data):
                   self._data = data
               def to_dict(self):
                   return self._data
           return Snap(self.store["flow_runs"][self._doc_id])
       def update(self, update_data):
           self.store["flow_runs"][self._doc_id]["steps"]["stepA"]["status"] = update_data["steps.stepA.status"]
       def transaction(self):
           class Tx:
               def __init__(self, ref):
                   self.ref = ref
                   self._updates = []
               def update(self, doc_ref, update_data):
                   self._updates.append(update_data)
               def commit(self):
                   for update_data in self._updates:
                       self.ref.update(update_data)
           return Tx(self)

   client = FakeFirestore()
   first = claim_step_transaction(client=client, run_id="run-1", step_id="stepA")
   second = claim_step_transaction(client=client, run_id="run-1", step_id="stepA")
   print(first.claimed, second.claimed)
   PY
   ```

**Expected result**
- Printed: `True False`.

---

## 3) Transactional claim is idempotent

**Scenario**
- If the step is not `READY`, claim is a no-op.

**Implemented in**
- `worker_chart_export/orchestration.py:1`

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from worker_chart_export.orchestration import claim_step_transaction

   class FakeFirestore:
       def __init__(self):
           self.store = {"flow_runs": {"run-1": {"steps": {"stepA": {"status": "RUNNING"}}}}}
       def collection(self, name):
           return self
       def document(self, doc_id):
           self._doc_id = doc_id
           return self
       def get(self, transaction=None):
           class Snap:
               def __init__(self, data):
                   self._data = data
               def to_dict(self):
                   return self._data
           return Snap(self.store["flow_runs"][self._doc_id])
       def update(self, update_data):
           self.store["flow_runs"][self._doc_id]["steps"]["stepA"]["status"] = update_data["steps.stepA.status"]
       def transaction(self):
           class Tx:
               def __init__(self, ref):
                   self.ref = ref
                   self._updates = []
               def update(self, doc_ref, update_data):
                   self._updates.append(update_data)
               def commit(self):
                   for update_data in self._updates:
                       self.ref.update(update_data)
           return Tx(self)

   client = FakeFirestore()
   result = claim_step_transaction(client=client, run_id="run-1", step_id="stepA")
   print(result.claimed, client.store["flow_runs"]["run-1"]["steps"]["stepA"]["status"])
   PY
   ```

**Expected result**
- Printed: `False RUNNING`.

---

## 4) Finalize SUCCEEDED with minimal patch

**Scenario**
- Finalize sets `status=SUCCEEDED`, `finishedAt`, and `outputs.outputsManifestGcsUri` without clobbering other fields.

**Implemented in**
- `worker_chart_export/orchestration.py:1` (`finalize_step`, `build_finalize_success_update`)

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from worker_chart_export.orchestration import finalize_step

   class FakeFirestore:
       def __init__(self):
           self.store = {"flow_runs": {"run-1": {"steps": {"stepA": {"status": "RUNNING", "outputs": {"keep": "yes"}}}}}}}
       def collection(self, name):
           return self
       def document(self, doc_id):
           self._doc_id = doc_id
           return self
       def get(self, transaction=None):
           class Snap:
               def __init__(self, data):
                   self._data = data
               def to_dict(self):
                   return self._data
           return Snap(self.store["flow_runs"][self._doc_id])
       def update(self, update_data):
           step = self.store["flow_runs"][self._doc_id]["steps"]["stepA"]
           step["status"] = update_data["steps.stepA.status"]
           step["finishedAt"] = update_data["steps.stepA.finishedAt"]
           step.setdefault("outputs", {})["outputsManifestGcsUri"] = update_data["steps.stepA.outputs.outputsManifestGcsUri"]

   client = FakeFirestore()
   finalize_step(
       client=client,
       run_id="run-1",
       step_id="stepA",
       status="SUCCEEDED",
       finished_at="2025-12-15T10:26:15Z",
       outputs_manifest_gcs_uri="gs://bucket/manifest.json",
   )
   step = client.store["flow_runs"]["run-1"]["steps"]["stepA"]
   print(step["status"], step["outputs"]["outputsManifestGcsUri"], step["outputs"]["keep"])
   PY
   ```

**Expected result**
- Printed: `SUCCEEDED gs://bucket/manifest.json yes`.

---

## 5) Finalize FAILED with error payload

**Scenario**
- Finalize failure writes `status=FAILED`, `finishedAt`, and `error` fields.

**Implemented in**
- `worker_chart_export/orchestration.py:1` (`finalize_step`, `build_finalize_failure_update`)

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from worker_chart_export.orchestration import finalize_step, StepError

   class FakeFirestore:
       def __init__(self):
           self.store = {"flow_runs": {"run-1": {"steps": {"stepA": {"status": "RUNNING"}}}}}
       def collection(self, name):
           return self
       def document(self, doc_id):
           self._doc_id = doc_id
           return self
       def get(self, transaction=None):
           class Snap:
               def __init__(self, data):
                   self._data = data
               def to_dict(self):
                   return self._data
           return Snap(self.store["flow_runs"][self._doc_id])
       def update(self, update_data):
           step = self.store["flow_runs"][self._doc_id]["steps"]["stepA"]
           step["status"] = update_data["steps.stepA.status"]
           step["error"] = update_data["steps.stepA.error"]

   client = FakeFirestore()
   finalize_step(
       client=client,
       run_id="run-1",
       step_id="stepA",
       status="FAILED",
       finished_at="2025-12-15T10:26:15Z",
       error=StepError(code="VALIDATION_FAILED", message="bad input"),
   )
   step = client.store["flow_runs"]["run-1"]["steps"]["stepA"]
   print(step["status"], step["error"]["code"], step["error"]["message"])
   PY
   ```

**Expected result**
- Printed: `FAILED VALIDATION_FAILED bad input`.

---

## 6) Finalize is idempotent (already SUCCEEDED/FAILED)

**Scenario**
- Repeated finalize does not alter already finalized steps.

**Implemented in**
- `worker_chart_export/orchestration.py:1` (`finalize_step` guard)

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from worker_chart_export.orchestration import finalize_step

   class FakeFirestore:
       def __init__(self):
           self.store = {"flow_runs": {"run-1": {"steps": {"stepA": {"status": "SUCCEEDED", "outputs": {"outputsManifestGcsUri": "gs://old"}}}}}}}
       def collection(self, name):
           return self
       def document(self, doc_id):
           self._doc_id = doc_id
           return self
       def get(self, transaction=None):
           class Snap:
               def __init__(self, data):
                   self._data = data
               def to_dict(self):
                   return self._data
           return Snap(self.store["flow_runs"][self._doc_id])
       def update(self, update_data):
           self.store["flow_runs"][self._doc_id]["steps"]["stepA"]["status"] = update_data["steps.stepA.status"]

   client = FakeFirestore()
   result = finalize_step(
       client=client,
       run_id="run-1",
       step_id="stepA",
       status="SUCCEEDED",
       finished_at="2025-12-15T10:26:15Z",
       outputs_manifest_gcs_uri="gs://new",
   )
   step = client.store["flow_runs"]["run-1"]["steps"]["stepA"]
   print(result.updated, step["outputs"]["outputsManifestGcsUri"])
   PY
   ```

**Expected result**
- Printed: `False gs://old`.

---

## 7) Minimal Firestore patch uses steps.<stepId>.* only

**Scenario**
- Update payloads target only `steps.<stepId>.*` paths (no full `steps` map overwrite).

**Implemented in**
- `worker_chart_export/orchestration.py:1` (`build_claim_update`, `build_finalize_success_update`, `build_finalize_failure_update`)

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from worker_chart_export.orchestration import build_claim_update, build_finalize_success_update, build_finalize_failure_update, StepError

   step_id = "charts:1M:ctpl_price_ma1226_vol_v1"
   claim = build_claim_update(step_id)
   success = build_finalize_success_update(
       step_id=step_id,
       finished_at="2025-12-15T10:26:15Z",
       outputs_manifest_gcs_uri="gs://bucket/manifest.json",
   )
   failed = build_finalize_failure_update(
       step_id=step_id,
       finished_at="2025-12-15T10:26:15Z",
       error=StepError(code="FAILED", message="err"),
   )
   print(sorted(list(claim.keys()) + list(success.keys()) + list(failed.keys())))
   PY
   ```

**Expected result**
- All keys start with `steps.<stepId>.` and there is no top-level `steps` update.
