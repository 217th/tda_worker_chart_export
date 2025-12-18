# T-003 — Implemented Scenarios

References:
- Spec: `docs-worker-chart-export/spec/implementation_contract.md` (§2.1–2.2)
- GCP logging: `docs-gcp/runbook/prod_runbook_gcp.md` (§8.1)

---

## 1) Firestore CloudEvent parsing (update on flow_runs/{runId})

**Scenario**
- Given a Firestore **update** CloudEvent for `flow_runs/{runId}`, the handler extracts `runId` and decodes `steps` from the document fields.

**Implemented in**
- `worker_chart_export/ingest.py:1` (`parse_flow_run_event`, `decode_firestore_fields`)
- `worker_chart_export/entrypoints/cloud_event.py:1` (uses parsed payload)

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from worker_chart_export.ingest import parse_flow_run_event

   doc = "projects/p/databases/(default)/documents/flow_runs/20240101-010101_btcusdt_abcd"
   event = {
       "id": "evt-1",
       "type": "google.cloud.firestore.document.v1.updated",
       "subject": doc,
       "data": {
           "value": {
               "name": doc,
               "fields": {
                   "steps": {
                       "mapValue": {
                           "fields": {
                               "stepA": {
                                   "mapValue": {
                                       "fields": {
                                           "stepType": {"stringValue": "CHART_EXPORT"},
                                           "status": {"stringValue": "READY"},
                                       }
                                   }
                               }
                           }
                       }
                   }
               }
           }
       },
   }
   parsed = parse_flow_run_event(event)
   print(parsed.run_id if parsed else None)
   PY
   ```

**Expected result**
- Printed `20240101-010101_btcusdt_abcd`.

---

## 2) Fast filter: no READY CHART_EXPORT → no-op

**Scenario**
- If no `CHART_EXPORT` step is `READY`, the handler exits without errors and logs a no-op.

**Implemented in**
- `worker_chart_export/entrypoints/cloud_event.py:1`

**Manual test**

**Prerequisites**
- Python 3.13.
- Minimal env:
  - `CHARTS_BUCKET="gs://dummy-bucket"`
  - `CHART_IMG_ACCOUNTS_JSON='[{"id":"acc1","apiKey":"SECRET"}]'`

**Steps**
1) Run:
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
       "data": {
           "value": {
               "name": doc,
               "fields": {
                   "steps": {
                       "mapValue": {
                           "fields": {
                               "stepA": {
                                   "mapValue": {
                                       "fields": {
                                           "stepType": {"stringValue": "CHART_EXPORT"},
                                           "status": {"stringValue": "RUNNING"},
                                       }
                                   }
                               }
                           }
                       }
                   }
               }
           }
       },
   }
   worker_chart_export(event)
   print("ok")
   PY
   ```

**Expected result**
- Process exits with `ok` and structured logs include `cloud_event_noop` with `reason=no_ready_step`.

---

## 3) Deterministic READY step pick

**Scenario**
- When multiple steps are `READY`, pick the lexicographically smallest `stepId`.

**Implemented in**
- `worker_chart_export/ingest.py:1` (`pick_ready_chart_export_step`)

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from worker_chart_export.ingest import pick_ready_chart_export_step

   flow_run = {
       "steps": {
           "b-step": {"stepType": "CHART_EXPORT", "status": "READY"},
           "a-step": {"stepType": "CHART_EXPORT", "status": "READY"},
       }
   }
   print(pick_ready_chart_export_step(flow_run))
   PY
   ```

**Expected result**
- Printed `a-step`.

---

## 4) At-least-once (double event) → safe no-op

**Scenario**
- Repeat event for a step already `RUNNING`/`SUCCEEDED`/`FAILED` results in no-op.

**Implemented in**
- `worker_chart_export/entrypoints/cloud_event.py:1` (no-op when no READY)

**Manual test**
- Same as Scenario 2 with status `RUNNING` or `SUCCEEDED`.

---

## 5) Noise filter: non-update events, other collections, malformed steps

**Scenario**
- Events that are not Firestore **update**, not in `flow_runs/{runId}`, or have non-map `steps` are ignored.

**Implemented in**
- `worker_chart_export/ingest.py:1` (`parse_flow_run_event`)
- `worker_chart_export/entrypoints/cloud_event.py:1` (reason `event_filtered` / `invalid_steps`)

**Manual test**

**Prerequisites**
- Python 3.13.
- Minimal env vars (same as Scenario 2).

**Steps**
1) Send event for another collection:
   ```bash
   CHARTS_BUCKET="gs://dummy-bucket" \
   CHART_IMG_ACCOUNTS_JSON='[{"id":"acc1","apiKey":"SECRET"}]' \
   python - << 'PY'
   from worker_chart_export.entrypoints.cloud_event import worker_chart_export

   event = {
       "id": "evt-3",
       "type": "google.cloud.firestore.document.v1.updated",
       "subject": "projects/p/databases/(default)/documents/other/123",
       "data": {"value": {"name": "projects/p/databases/(default)/documents/other/123"}},
   }
   worker_chart_export(event)
   print("ok")
   PY
   ```

**Expected result**
- Process exits with `ok` and logs include `cloud_event_ignored` with `reason=event_filtered`.

---

## What is intentionally NOT implemented yet

- Firestore transaction claim (`READY -> RUNNING`) and finalize patch (T-004).
- Chart export pipeline (T-005..T-008).
