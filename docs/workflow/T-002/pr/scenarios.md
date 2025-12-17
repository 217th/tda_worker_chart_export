# T-002 — Implemented Scenarios (skeleton-level)

This file lists **concrete runnable scenarios** that exist after T-002. Some of them intentionally have **incomplete business logic** (the actual CHART_EXPORT processing is implemented in T-003..T-008).

References:
- Spec: `docs-worker-chart-export/spec/implementation_contract.md` (§10, §11.1, §11.2, §12.1, §12.2)
- GCP runbook logging: `docs-gcp/runbook/prod_runbook_gcp.md` (§8)

---

## 1) Process startup: parse config from env (fatal misconfig on invalid secret)

**Scenario**
- When the process starts (CloudEvent handler or CLI), configuration is loaded from environment variables.
- `CHART_IMG_ACCOUNTS_JSON` is parsed **once per process**; invalid JSON/shape is treated as **fatal misconfiguration** (raises `ConfigError`).

**Implemented in**
- `worker_chart_export/config.py:1` (`WorkerConfig.from_env`, `_parse_accounts_json`)
- `worker_chart_export/runtime.py:1` (`get_config()` cached with `lru_cache`)

**Inputs**
- `CHART_IMG_ACCOUNTS_JSON` (required): JSON array `[{ "id": "...", "apiKey": "..." }, ...]`
- `CHARTS_BUCKET` (required): bucket name or `gs://<bucket>` (no path)
- `CHARTS_API_MODE` (optional): `real|mock|record` (default `real`)
- `CHARTS_DEFAULT_TIMEZONE` (optional): IANA name (default `UTC`)

**What is intentionally NOT implemented yet**
- Any per-step validation (`VALIDATION_FAILED`) is not part of this scenario (belongs to step execution logic).

### Manual test

**Prerequisites**
- Run inside the task worktree (or after integration on `main`) with Python 3.13 available.
- No external deps required for this scenario.

**Steps**
1) Set minimal required env vars (valid config):
   - `export CHARTS_BUCKET="gs://dummy-bucket"`
   - `export CHARTS_DEFAULT_TIMEZONE="UTC"`
   - `export CHART_IMG_ACCOUNTS_JSON='[{"id":"acc1","apiKey":"SECRET1"}]'`
2) Validate config loads without printing secrets:
   - `python -c 'from worker_chart_export.runtime import get_config; get_config()'`
3) Negative case (invalid JSON):
   - `export CHART_IMG_ACCOUNTS_JSON='not-json'`
   - `python -c 'from worker_chart_export.runtime import get_config; get_config()'`

**Expected result**
- Step (2) exits with code `0` and produces no output (or only structured logs if you add logging).
- Step (3) exits non-zero with a `ConfigError` (message mentions `CHART_IMG_ACCOUNTS_JSON`).

---

## 2) Logging: structured JSON logs (Cloud Logging-friendly)

**Scenario**
- All entrypoints can configure logging to emit JSON lines with stable fields.

**Implemented in**
- `worker_chart_export/logging.py:1`
  - `configure_logging()` sets root logging handler formatter to JSON.
  - `log_event(logger, event, **fields)` logs structured events.

**Notes**
- This is the foundation for later log-based metrics (T-013).

### Manual test

**Prerequisites**
- Python 3.13.
- No external deps required.

**Steps**
1) Run a single log event:
   - `python -c 'import logging; from worker_chart_export.logging import configure_logging, log_event; configure_logging(); log_event(logging.getLogger(\"worker-chart-export\"), \"test_event\", runId=\"r1\", stepId=\"s1\")'`

**Expected result**
- STDOUT contains exactly one JSON line with at least:
  - `event="test_event"`
  - `runId="r1"`, `stepId="s1"`
  - `severity="INFO"`

---

## 3) CLI: local runner entrypoint (`worker-chart-export run-local …`)

**Scenario**
- Run the worker locally against a `flow_run` JSON file, using the **same env-driven config model** as prod.
- CLI applies overrides by setting env vars before calling the core engine.

**Implemented in**
- `worker_chart_export/cli.py:1`
  - Command: `worker-chart-export run-local`
  - Flags (per spec §12.1):
    - `--flow-run-path=PATH` (required)
    - `--step-id=ID` (optional)
    - `--charts-api-mode=real|mock|record` (optional; overrides env)
    - `--charts-bucket=gs://...` (optional; overrides env)
    - `--accounts-config-path=PATH` (optional; reads JSON and writes to env `CHART_IMG_ACCOUNTS_JSON`)
    - `--output-summary=none|text|json` (optional; default `text`)

**What is intentionally NOT implemented yet**
- The actual CHART_EXPORT core execution: `worker_chart_export/core.py:1` raises `NotImplementedYetError`.
- Output summary contains only placeholder fields until core returns real results.

### Manual test

**Prerequisites**
- Python 3.13.
- No external deps required (CLI uses stdlib only), but you must provide required env/config inputs.

**Steps**
1) Create a minimal `flow_run` JSON (content is irrelevant at T-002 stage because the core is a stub):
   - `cat > /tmp/flow_run.min.json << 'JSON'\n{}\nJSON`
2) Run CLI with required config in env:
   - `CHARTS_BUCKET="gs://dummy-bucket" CHART_IMG_ACCOUNTS_JSON='[{"id":"acc1","apiKey":"SECRET1"}]' python -m worker_chart_export.cli run-local --flow-run-path /tmp/flow_run.min.json --output-summary text`

**Expected result**
- Exit code is `3`.
- STDERR starts with `NOT_IMPLEMENTED:` (from `NotImplementedYetError`).
- STDOUT may include JSON logs such as `{"event":"local_run_started", ...}` (format is JSON).

---

## 4) CloudEvent handler skeleton (Functions Framework)

**Scenario**
- A CloudEvent-triggered handler exists and is compatible with Google Functions Framework.
- On invocation it configures logging, loads config (fatal if misconfigured), and logs a “received” event.

**Implemented in**
- `worker_chart_export/entrypoints/cloud_event.py:1`
  - Function name: `worker_chart_export`
  - Decorator: `@functions_framework.cloud_event` when dependency is installed.

**What is intentionally NOT implemented yet**
- Firestore event parsing / fast-filter / deterministic step pick (T-003).
- Firestore claim/finalize patches (T-004).
- Actual chart generation pipeline (T-005..T-008).

### Manual test (direct function call, no Functions Framework)

**Prerequisites**
- Python 3.13.
- No external deps required.

**Steps**
1) Invoke the handler directly with a dict-like CloudEvent and minimal config:
   - `python - << 'PY'\nimport os\nos.environ[\"CHARTS_BUCKET\"] = \"gs://dummy-bucket\"\nos.environ[\"CHART_IMG_ACCOUNTS_JSON\"] = '[{\"id\":\"acc1\",\"apiKey\":\"SECRET1\"}]'\nfrom worker_chart_export.entrypoints.cloud_event import worker_chart_export\ntry:\n    worker_chart_export({\"id\":\"evt1\",\"type\":\"test.event\"})\nexcept Exception as e:\n    print(type(e).__name__, str(e))\nPY`

**Expected result**
- One structured log line is emitted with `event="cloud_event_received"` (JSON).
- The printed exception is `NotImplementedError CloudEvent processing not implemented yet.` (or equivalent).

### Manual test (optional: Functions Framework local server)

**Prerequisites**
- Python 3.13.
- A venv with dependencies installed:
  - `python -m venv .venv && . .venv/bin/activate`
  - `python -m pip install -U pip`
  - `python -m pip install -r requirements.txt`

**Steps**
1) Start local server:
   - `export CHARTS_BUCKET="gs://dummy-bucket"`
   - `export CHART_IMG_ACCOUNTS_JSON='[{"id":"acc1","apiKey":"SECRET1"}]'`
   - `functions-framework --source worker_chart_export/entrypoints/cloud_event.py --target worker_chart_export --signature-type cloudevent`
2) In a second terminal, send a CloudEvent:
   - `curl -X POST localhost:8080 -H 'Content-Type: application/cloudevents+json' -d '{\"specversion\":\"1.0\",\"type\":\"test.event\",\"source\":\"local\",\"id\":\"evt1\",\"data\":{}}'`

**Expected result**
- Server logs show `cloud_event_received`.
- Request fails with 5xx (because handler raises `NotImplementedError`), which is expected at T-002 stage.
