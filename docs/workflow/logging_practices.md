# Logging practices (worker_chart_export)

This document captures the logging approach implemented in `worker_chart_export` and can be reused as a baseline for other components.

## Goals

- Provide **structured JSON logs** suitable for Google Cloud Logging.
- Emit **domain events** with consistent naming and predictable fields.
- Support **idempotent tracing** across retries (e.g., repeated Firestore triggers).
- Avoid leaking secrets or sensitive payloads.

## Transport & integration with Google Cloud Logging

- Logs are emitted via **stdout/stderr** using Python `logging`.
- Cloud Run / Cloud Functions gen2 **automatically ingests stdout/stderr** into Google Cloud Logging.
- No direct Cloud Logging SDK usage is required.
- JSON logs become `jsonPayload` entries; severity is derived from the `severity` field.

## Implementation in code

**Core logger utilities:**

- `worker_chart_export/logging.py`
  - `JsonFormatter` converts log records to JSON.
  - `configure_logging()` attaches the formatter and sets level (default `INFO`, overridable via `LOG_LEVEL`).
  - `log_event(logger, event, **fields)` wraps event emission with consistent structure.

**Event emitters:**

- CloudEvent entrypoint: `worker_chart_export/entrypoints/cloud_event.py`
- Core workflow: `worker_chart_export/core.py`
- Chart-IMG client: `worker_chart_export/chart_img.py`
- Usage accounting: `worker_chart_export/usage.py`
- CLI adapter: `worker_chart_export/cli.py`

## Base JSON structure

All event logs follow the same envelope (fields may vary per event):

```json
{
  "event": "cloud_event_received",
  "message": "cloud_event_received",
  "severity": "INFO",
  "logger": "worker-chart-export",
  "time": "2025-12-21T09:18:15.321061+00:00",
  "service": "worker-chart-export",
  "env": "prod",
  "eventId": "<cloud_event_id>",
  "eventType": "google.cloud.firestore.document.v1.updated",
  "subject": "documents/flow_runs/<runId>",
  "runId": "<runId>",
  "flowKey": "<flowKey>",
  "stepId": "<stepId>"
}
```

Common envelope fields:

- `event` — **event name** (snake_case).
- `message` — default equals `event`.
- `severity` — logging level (`INFO` by default in `log_event`).
- `logger` — logger name (usually `worker-chart-export`).
- `time` — RFC3339 timestamp (UTC).
- `exception` — present if an exception is attached to the log record.

Component-specific fields are appended per event (see below).

## Event catalog

The following events are emitted by the current implementation.

### CloudEvent ingestion

| Event | Where | Fields | Notes |
| --- | --- | --- | --- |
| `config_error` | `entrypoints/cloud_event.py` | `eventId`, `eventType`, `subject`, `error` | Misconfiguration, e.g., invalid secret JSON. Emitted before raising exception. |
| `cloud_event_received` | `entrypoints/cloud_event.py` | `service`, `env`, `eventId`, `eventType`, `subject` | Emitted for every incoming event. |
| `cloud_event_ignored` | `entrypoints/cloud_event.py` | Base fields + `reason`; optional `dataType`, `dataPreview`, `runId` | Reasons include `event_type_filtered`, `event_filtered`, `flow_run_not_found`, `invalid_steps`. |
| `cloud_event_parsed` | `entrypoints/cloud_event.py` | Base fields + `runId`, optional `flowKey` | Emitted after runId/flowKey extracted. |
| `depends_on_blocked` | `entrypoints/cloud_event.py`, `core.py` | `blockedSteps` or `unmetDependencies` | One or more READY steps blocked because dependencies are not `SUCCEEDED`. |
| `cloud_event_noop` | `entrypoints/cloud_event.py` | Base fields + `reason` | `reason=no_ready_step`. |
| `ready_step_selected` | `entrypoints/cloud_event.py` | Base fields + `stepId` | Indicates which step will be processed. |
| `cloud_event_finished` | `entrypoints/cloud_event.py` | Base fields + `stepId`, `status`, `outputsManifestGcsUri`, `itemsCount`, `failuresCount`, `errorCode` | Final outcome emitted after core finishes. |

### Core execution

| Event | Where | Fields | Notes |
| --- | --- | --- | --- |
| `core_start` | `core.py` | `runId`, `stepId` | Beginning of core processing. |
| `core_noop_already_final` | `core.py` | `runId`, `stepId`, `status` | Step already `SUCCEEDED`/`FAILED`. |
| `claim_attempt` | `core.py` | `runId`, `stepId`, `claimed`, `status` | Firestore claim result. |
| `chart_api_call_start` | `core.py` | `runId`, `stepId`, `chartTemplateId`, `chartImgSymbol` | Before calling Chart-IMG. |
| `chart_api_call_finished` | `core.py` | `runId`, `stepId`, `chartTemplateId`, `chartImgSymbol`, `ok`, `errorCode` | After Chart-IMG call. |
| `step_completed` | `core.py` | `runId`, `stepId`, `status`, `itemsCount`, `failuresCount`, `minImages`, `outputsManifestGcsUri` | Emitted on success. |
| `finalize_failed` | `core.py` | `runId`, `stepId`, `error` | Finalize failed (best-effort log). |

### Chart-IMG client

| Event | Where | Fields | Notes |
| --- | --- | --- | --- |
| `chart_api_mock_missing` | `chart_img.py` | `error.code`, `fixtureStem`, `fixturesDir`, optional `chartTemplateId` | Missing fixture in mock mode. |

### Account usage / limits

| Event | Where | Fields | Notes |
| --- | --- | --- | --- |
| `chart_api_usage_claim_conflict` | `usage.py` | `accountId`, optional `chartTemplateId` | Firestore contention when claiming usage. |
| `chart_api_limit_exceeded` | `usage.py` | `error.code`, `exhaustedAccounts`, optional `chartTemplateId` | All accounts exhausted. |
| `usage_mark_exhausted_precondition_failed` | `usage.py` | `accountId` | Precondition failure while marking exhausted. |

### CLI

| Event | Where | Fields | Notes |
| --- | --- | --- | --- |
| `local_run_started` | `cli.py` | `mode`, `flowRunPath`, `stepId`, `chartsApiMode` | CLI entry event. |

## Event naming conventions

- `snake_case`, short and action-oriented.
- All event names are **stable API** for dashboards/alerts.
- Errors appear as **event names** and/or `errorCode` fields, not in free-form text.

## Error handling & codes

- Error classification is surfaced via `errorCode` fields (e.g., `VALIDATION_FAILED`, `CHART_API_FAILED`, `CHART_API_LIMIT_EXCEEDED`, `CHART_API_MOCK_MISSING`, `GCS_WRITE_FAILED`, `MANIFEST_WRITE_FAILED`).
- For failures during finalize, `finalize_failed` is emitted with the error code.

## Privacy & safety

- `CHART_IMG_ACCOUNTS_JSON` and API keys **must never be logged**.
- Payload previews are **truncated to 512 chars** when logging filtered events.
- Use structured fields instead of embedding sensitive content in `message`.

## Operational notes

- In Cloud Run gen2, logs appear under `run.googleapis.com/stdout` and `run.googleapis.com/stderr`.
- If you need per-event filtering, query `jsonPayload.event` in Cloud Logging.
- `cloud_event_received` may appear multiple times for a single run due to Firestore updates; follow with `cloud_event_noop` for expected retries.

## Reuse checklist for other components

- Implement a local `logging.py` with `JsonFormatter` + `configure_logging()` + `log_event()`.
- Adopt a **small, explicit event catalog** with stable names.
- Ensure ingestion logs include **correlation identifiers** (`runId`, `stepId`, `eventId`).
- Keep all logs JSON-structured; avoid ad-hoc strings for operational signals.
