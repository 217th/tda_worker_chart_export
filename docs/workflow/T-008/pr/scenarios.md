# T-008 — Implemented Scenarios (task-level)

Planned scenarios source:
- `docs/workflow/T-008/README.md` → **Planned Scenarios (TDD)**

References:
- `docs-worker-chart-export/spec/implementation_contract.md` §5–6, §8
- `docs-worker-chart-export/contracts/charts_outputs_manifest.schema.json`

---

## 1) Successful PNG + manifest write

**Scenario**
- PNG upload and manifest write produce `gs://` URIs and valid schema.

**Implemented in**
- `worker_chart_export/gcs_artifacts.py`
- `tests/tasks/T-008/test_gcs_artifacts.py`

**Limitations / stubs**
- Uses in‑memory fake uploader (no real GCS).

### Manual test

**Prerequisites**
- Local Python environment.
- Requires human-in-the-middle: NO

**Steps**
1) Call `upload_pngs` with a fake uploader.
2) Validate manifest with `validate_manifest`.

**Expected result**
- PNG `gs://` URI is built.
- Manifest validates.

---

## 2) Partial GCS failure (one PNG fails, others succeed)

**Scenario**
- One PNG upload fails while others succeed.

**Implemented in**
- `worker_chart_export/gcs_artifacts.py`
- `tests/tasks/T-008/test_gcs_artifacts.py`

**Limitations / stubs**
- Failure simulated by fake uploader.

### Manual test

**Prerequisites**
- Local Python environment.
- Requires human-in-the-middle: NO

**Steps**
1) Configure fake uploader to fail one object path.

**Expected result**
- Failure recorded with `error.code = "GCS_WRITE_FAILED"`; other items succeed.

---

## 3) PNG upload failure → GCS_WRITE_FAILED

**Scenario**
- A PNG upload failure maps to `GCS_WRITE_FAILED`.

**Implemented in**
- `worker_chart_export/gcs_artifacts.py`
- `tests/tasks/T-008/test_gcs_artifacts.py`

**Limitations / stubs**
- Uses fake uploader to throw.

### Manual test

**Prerequisites**
- Local Python environment.
- Requires human-in-the-middle: NO

**Steps**
1) Force upload error for a PNG path.

**Expected result**
- Failure entry has `error.code = "GCS_WRITE_FAILED"`.

---

## 4) Manifest write failure → MANIFEST_WRITE_FAILED

**Scenario**
- Manifest write failure results in `MANIFEST_WRITE_FAILED`.

**Implemented in**
- `worker_chart_export/gcs_artifacts.py`
- `tests/tasks/T-008/test_gcs_artifacts.py`

**Limitations / stubs**
- Uses fake uploader to throw.

### Manual test

**Prerequisites**
- Local Python environment.
- Requires human-in-the-middle: NO

**Steps**
1) Force upload error for manifest path.

**Expected result**
- Manifest write returns `error.code = "MANIFEST_WRITE_FAILED"`.

---

## 5) Manifest schema validation fails → VALIDATION_FAILED

**Scenario**
- Invalid manifest fails JSON schema validation.

**Implemented in**
- `worker_chart_export/gcs_artifacts.py`
- `tests/tasks/T-008/test_gcs_artifacts.py`

**Limitations / stubs**
- Uses local schema file.

### Manual test

**Prerequisites**
- Local Python environment.
- Requires human-in-the-middle: NO

**Steps**
1) Validate a manifest missing `runId`.

**Expected result**
- `StepError.code = "VALIDATION_FAILED"`.

---

## 6) Worker does not write signed_url / expires_at

**Scenario**
- Manifest items never include `signed_url` or `expires_at`.

**Implemented in**
- `worker_chart_export/gcs_artifacts.py`
- `tests/tasks/T-008/test_gcs_artifacts.py`

**Limitations / stubs**
- None.

### Manual test

**Prerequisites**
- Local Python environment.
- Requires human-in-the-middle: NO

**Steps**
1) Upload a PNG and inspect manifest item fields.

**Expected result**
- `signed_url` and `expires_at` are absent.

---

## 7) Retry overwrites manifest but keeps old PNGs

**Scenario**
- Manifest path is deterministic and can be overwritten.

**Implemented in**
- `worker_chart_export/gcs_artifacts.py`
- `tests/tasks/T-008/test_gcs_artifacts.py`

**Limitations / stubs**
- Uses fake uploader; does not delete PNGs.

### Manual test

**Prerequisites**
- Local Python environment.
- Requires human-in-the-middle: NO

**Steps**
1) Call `write_manifest` twice with same runId/stepId.

**Expected result**
- Same path is written twice (overwrite OK).
