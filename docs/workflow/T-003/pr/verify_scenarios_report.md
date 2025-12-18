# T-003 — Scenarios Verification Report

Date: 2025-12-18  
Branch: `task/T-003/cloudevent-ingest` (manual re-run from `task/T-005/templates-requests`)

Source checklist: `docs/workflow/T-003/README.md`

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

## Manual scenario checks (executed)

### Scenario 1) Firestore CloudEvent parsing

**Command**
```bash
python - << 'PY'
from worker_chart_export.ingest import parse_flow_run_event

doc = "projects/p/databases/(default)/documents/flow_runs/20240101-010101_btcusdt_abcd"
event = {
    "id": "evt-1",
    "type": "google.cloud.firestore.document.v1.updated",
    "subject": doc,
    "data": {"value": {"name": doc, "fields": {"steps": {"mapValue": {"fields": {
        "stepA": {"mapValue": {"fields": {"stepType": {"stringValue": "CHART_EXPORT"}, "status": {"stringValue": "READY"}}}}
    }}}}}},
}
parsed = parse_flow_run_event(event)
print(parsed.run_id if parsed else None)
PY
```

**Result**
- Output: `20240101-010101_btcusdt_abcd`

### Scenario 2) No READY → no-op

**Command**
```bash
CHARTS_BUCKET="gs://dummy-bucket" \
CHART_IMG_ACCOUNTS_JSON='[{"id":"acc1","apiKey":"SECRET"}]' \
python - << 'PY'
from worker_chart_export.entrypoints.cloud_event import worker_chart_export

doc = "projects/p/databases/(default)/documents/flow_runs/run-1"
event = {
    "id": "evt-2",
    "type": "google.cloud.firestore.document.v1.updated",
    "subject": doc,
    "data": {"value": {"name": doc, "fields": {"steps": {"mapValue": {"fields": {
        "stepA": {"mapValue": {"fields": {"stepType": {"stringValue": "CHART_EXPORT"}, "status": {"stringValue": "RUNNING"}}}}
    }}}}}},
}
worker_chart_export(event)
print("ok")
PY
```

**Result**
- Output includes `ok`
- Logs include `cloud_event_noop` with `reason="no_ready_step"`

### Scenario 3) Deterministic READY pick

**Command**
```bash
python - << 'PY'
from worker_chart_export.ingest import pick_ready_chart_export_step
flow_run = {"steps": {"b-step": {"stepType": "CHART_EXPORT", "status": "READY"},
                      "a-step": {"stepType": "CHART_EXPORT", "status": "READY"}}}
print(pick_ready_chart_export_step(flow_run))
PY
```

**Result**
- Output: `a-step`

### Scenario 4) Double event → safe no-op

**Command**
```bash
CHARTS_BUCKET="gs://dummy-bucket" \
CHART_IMG_ACCOUNTS_JSON='[{"id":"acc1","apiKey":"SECRET"}]' \
python - << 'PY'
from worker_chart_export.entrypoints.cloud_event import worker_chart_export
doc = "projects/p/databases/(default)/documents/flow_runs/run-1"
event = {
    "id": "evt-4",
    "type": "google.cloud.firestore.document.v1.updated",
    "subject": doc,
    "data": {"value": {"name": doc, "fields": {"steps": {"mapValue": {"fields": {
        "stepA": {"mapValue": {"fields": {"stepType": {"stringValue": "CHART_EXPORT"}, "status": {"stringValue": "SUCCEEDED"}}}}
    }}}}}},
}
worker_chart_export(event)
print("ok")
PY
```

**Result**
- Output includes `ok`
- Logs include `cloud_event_noop` with `reason="no_ready_step"`

### Scenario 5) Noise filter (other collection / non-update / invalid steps)

**Commands**
```bash
# other collection
CHARTS_BUCKET="gs://dummy-bucket" \
CHART_IMG_ACCOUNTS_JSON='[{"id":"acc1","apiKey":"SECRET"}]' \
python - << 'PY'
from worker_chart_export.entrypoints.cloud_event import worker_chart_export
event = {"id": "evt-3", "type": "google.cloud.firestore.document.v1.updated",
         "subject": "projects/p/databases/(default)/documents/other/123",
         "data": {"value": {"name": "projects/p/databases/(default)/documents/other/123"}}}
worker_chart_export(event)
print("ok")
PY

# non-update event
CHARTS_BUCKET="gs://dummy-bucket" \
CHART_IMG_ACCOUNTS_JSON='[{"id":"acc1","apiKey":"SECRET"}]' \
python - << 'PY'
from worker_chart_export.entrypoints.cloud_event import worker_chart_export
doc = "projects/p/databases/(default)/documents/flow_runs/run-2"
event = {"id": "evt-5", "type": "google.cloud.firestore.document.v1.created",
         "subject": doc, "data": {"value": {"name": doc}}}
worker_chart_export(event)
print("ok")
PY

# invalid steps shape
CHARTS_BUCKET="gs://dummy-bucket" \
CHART_IMG_ACCOUNTS_JSON='[{"id":"acc1","apiKey":"SECRET"}]' \
python - << 'PY'
from worker_chart_export.entrypoints.cloud_event import worker_chart_export
doc = "projects/p/databases/(default)/documents/flow_runs/run-3"
event = {"id": "evt-6", "type": "google.cloud.firestore.document.v1.updated",
         "subject": doc, "data": {"value": {"name": doc, "fields": {"steps": {"arrayValue": {"values": [{"stringValue": "bad"}]}}}}}}
worker_chart_export(event)
print("ok")
PY
```

**Result**
- All commands printed `ok`.
- Logs include `cloud_event_ignored` with `reason="event_filtered"`, `reason="event_type_filtered"`, and `reason="invalid_steps"` respectively.
