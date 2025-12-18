# T-002 — Scenarios Verification Report (manual checks)

Date: 2025-12-17  
Branch: `task/T-002/bootstrap-python-skeleton`

Source checklist: `docs/workflow/T-002/pr/scenarios.md`

---

## Environment / prerequisites

**Prerequisites (as stated in scenarios)**
- Python 3.13
- Run from repository root (or this task worktree) so `worker_chart_export/` is importable
- No external dependencies required for scenarios 1–4 (the optional Functions Framework server does require deps)

**Actions performed**
- Verified Python + package import:
  - `python -c 'import sys; print(sys.version)'`
  - `python -c 'import worker_chart_export; print(worker_chart_export.__version__)'`

**Observed**
- Python: `3.13.11`
- Package version: `0.0.0`

---

## Scenario 1) Config parsing from env (fatal misconfig on invalid secret)

### Step 1–2: valid config loads

**Command**
```bash
CHARTS_BUCKET='gs://dummy-bucket' \
CHARTS_DEFAULT_TIMEZONE='UTC' \
CHART_IMG_ACCOUNTS_JSON='[{"id":"acc1","apiKey":"SECRET1"}]' \
python -c 'from worker_chart_export.runtime import get_config; get_config()'
```

**Result**
- Exit code: `0`
- STDOUT: empty
- STDERR: empty

### Step 3: invalid `CHART_IMG_ACCOUNTS_JSON` fails fast

**Command**
```bash
CHARTS_BUCKET='gs://dummy-bucket' \
CHARTS_DEFAULT_TIMEZONE='UTC' \
CHART_IMG_ACCOUNTS_JSON='not-json' \
python -c 'from worker_chart_export.runtime import get_config; get_config()'
```

**Result**
- Exit code: `1`
- STDERR ends with:
  - `worker_chart_export.errors.ConfigError: CHART_IMG_ACCOUNTS_JSON must be a valid JSON array`

---

## Scenario 2) Structured JSON logging

### Step 1: emit one structured log event

**Command**
```bash
python -c 'import logging; from worker_chart_export.logging import configure_logging, log_event; configure_logging(); log_event(logging.getLogger("worker-chart-export"), "test_event", runId="r1", stepId="s1")'
```

**Result**
- Exit code: `0`
- Emitted JSON log line:
  - `{"event":"test_event","runId":"r1","stepId":"s1","severity":"INFO",...}`

**Note**
- The line was emitted on **STDERR** (Python logging default stream). Cloud Run/Cloud Logging still ingests both streams, but the original manual test text said “STDOUT”.

---

## Scenario 3) CLI `run-local` entrypoint

### Step 1: create minimal `flow_run`

**Command**
```bash
cat > /tmp/flow_run.min.json << 'JSON'
{}
JSON
```

### Step 2: run CLI

**Command**
```bash
CHARTS_BUCKET='gs://dummy-bucket' \
CHART_IMG_ACCOUNTS_JSON='[{"id":"acc1","apiKey":"SECRET1"}]' \
python -m worker_chart_export.cli run-local \
  --flow-run-path /tmp/flow_run.min.json \
  --output-summary text
```

**Result**
- Exit code: `3`
- STDERR contained:
  - structured log: `{"event":"local_run_started", ...}`
  - `NOT_IMPLEMENTED: Core engine is not implemented yet (see T-003..T-008).`

---

## Scenario 4) CloudEvent handler skeleton

### Direct function call (no Functions Framework server)

**Command**
```bash
python - << 'PY'
import os
os.environ["CHARTS_BUCKET"] = "gs://dummy-bucket"
os.environ["CHART_IMG_ACCOUNTS_JSON"] = '[{"id":"acc1","apiKey":"SECRET1"}]'
from worker_chart_export.entrypoints.cloud_event import worker_chart_export
try:
    worker_chart_export({"id":"evt1","type":"test.event"})
except Exception as e:
    print(type(e).__name__, str(e))
PY
```

**Result**
- Exit code: `0`
- STDOUT:
  - no exception output (non-Firestore events are ignored)
- STDERR:
  - structured log line with `event="cloud_event_received"` and `eventId="evt1"`
  - structured log line with `event="cloud_event_ignored"` and `reason="event_type_filtered"`

---

## Scenario 4) Optional: Functions Framework local server

### Status: Executed (required elevated sandbox permissions)

In the default sandbox environment, creating sockets was blocked (`PermissionError: [Errno 1] Operation not permitted`), which prevents starting any local HTTP server.

**Evidence**
```bash
python - <<'PY'
import socket
s=socket.socket()
s.bind(('127.0.0.1',0))
print('bound', s.getsockname())
s.close()
PY
```

**Observed**
- `PermissionError: [Errno 1] Operation not permitted`

To actually execute this scenario **in this Codex environment**, I reran it using **elevated sandbox permissions**, which allowed creating sockets and binding a local port.

### Execution (elevated permissions)

**Prerequisites**
- Dependencies installed (already present in this environment): `functions-framework`, `cloudevents`
- Ability to open a local listening socket (in this environment: requires elevated sandbox permissions)

**Command**
```bash
cd .codex-swarm/worktrees/T-002-bootstrap-python-skeleton
export CHARTS_BUCKET='gs://dummy-bucket'
export CHART_IMG_ACCOUNTS_JSON='[{"id":"acc1","apiKey":"SECRET1"}]'
export PYTHONPATH="$(pwd)"

PORT=8099
functions-framework --host 127.0.0.1 --port "$PORT" \
  --source worker_chart_export/entrypoints/cloud_event.py \
  --target worker_chart_export \
  --signature-type cloudevent

# then (2nd terminal):
curl -X POST "http://127.0.0.1:$PORT" \
  -H 'Content-Type: application/cloudevents+json' \
  -d '{"specversion":"1.0","type":"test.event","source":"local","id":"evt1","data":{}}'
```

**Observed result**
- Socket creation succeeded (example): `bound ('127.0.0.1', 39585)`
- `curl` result: `http=2xx` (handler ignores non-Firestore events; no error)
- Server log contained:
  - `{"event":"cloud_event_received","eventId":"evt1","eventType":"test.event",...}`
  - no stack trace (non-Firestore events are ignored)

**How to run it on a normal machine**
- Ensure deps installed (venv + `pip install -r requirements.txt`).
- Then run the same `functions-framework ...` command and the `curl` request above.
