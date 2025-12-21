# worker_chart_export

Trading Decisions Assistant component that renders PNG charts via Chart-IMG based on declarative templates and writes artifacts (PNG + manifest) to GCS. Runs as an Eventarc-triggered worker and has a CLI adapter for local runs.

## Overview

- **Purpose**: Consume `flow_runs/{runId}` documents, pick READY `CHART_EXPORT` steps, render a chart per request, upload PNGs to GCS, write a manifest, and finalize the step status.
- **Runtime**: Python 3.13, Functions Framework / Cloud Run. CLI and CloudEvent use the same core engine.
- **Specs & context**: The authoritative specs live outside this public repo. If you have the spec packs, place them at repo root as `docs-worker-chart-export/`, `docs-general/`, `docs-gcp/`.

## Quickstart (local)

1) Python 3.13 + venv:
   - `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
2) Prepare Chart-IMG accounts (local file):
   - Create `chart-img.accounts.local.json` with a JSON array:
     ```json
     [{"id":"acc-1","apiKey":"<API_KEY>","dailyLimit":50}]
     ```
3) Set required env:
   - `CHARTS_BUCKET=gs://<bucket>`
   - Optional: `CHARTS_API_MODE=mock|real|record`, `CHARTS_DEFAULT_TIMEZONE=Etc/UTC`
4) Run CLI:
   - `python -m worker_chart_export.cli run-local --flow-run-path ./tmp/flow_run.json --step-id charts:1H:ctpl_price_ma1226_vol_v1 --charts-bucket gs://<bucket> --charts-api-mode mock --accounts-config-path ./chart-img.accounts.local.json`

Minimal `flow_run.json` example:
```json
{
  "schemaVersion": 1,
  "runId": "20251221-120000_BTCUSDT_demo",
  "flowKey": "scheduled_month_week_report_v1",
  "status": "RUNNING",
  "createdAt": "2025-12-21T12:00:00Z",
  "trigger": {"type": "MANUAL", "source": "local"},
  "scope": {"symbol": "BTCUSDT"},
  "steps": {
    "charts:1H:ctpl_price_ma1226_vol_v1": {
      "stepType": "CHART_EXPORT",
      "status": "READY",
      "timeframe": "1h",
      "createdAt": "2025-12-21T12:00:01Z",
      "dependsOn": ["_dummy"],
      "inputs": {
        "minImages": 1,
        "requests": [{"chartTemplateId": "ctpl_price_ma1226_vol_v1"}]
      },
      "outputs": {}
    }
  }
}
```

## Processing Flow (high level)

1) **CloudEvent ingest**: fast filter for Firestore `update` on `flow_runs/{runId}`; deterministic READY step selection; idempotent no-op on repeats.
2) **Claim**: optimistic update `READY -> RUNNING`; two-phase finalize with minimal patch.
3) **Templates**: load `chart_templates/{chartTemplateId}`; required `chartImgSymbolTemplate`; `scope.symbol` expected without slash (e.g., `BTCUSDT`).
4) **Accounts & limits**: usage in `chart_img_accounts_usage/{accountId}`, daily window reset (UTC), attempts counted, 429 marks account exhausted.
5) **Chart-IMG client**: modes `real|mock|record`; bounded retries/backoff; errors `CHART_API_FAILED | CHART_API_LIMIT_EXCEEDED | CHART_API_MOCK_MISSING`.
6) **Artifacts**: PNG path `charts/<runId>/<stepId>/<generatedAt>_<symbolSlug>_<timeframe>_<chartTemplateId>.png`; manifest path `charts/<runId>/<stepId>/manifest.json`; URIs `gs://...`; manifest validated; no `signed_url/expires_at`.
7) **Finalize**: patch `RUNNING -> SUCCEEDED|FAILED` with outputs or error code; idempotent on repeated finalize.

## Configuration (env)

- `CHARTS_BUCKET` (required) — `gs://<bucket>`.
- `CHART_IMG_ACCOUNTS_JSON` (required) — JSON array of `{id, apiKey, dailyLimit?}`; parsed once at startup.
- `CHARTS_API_MODE` — `real|mock|record` (default `real`, `record` blocked if `ENV`/`TDA_ENV` is `prod`).
- `CHARTS_DEFAULT_TIMEZONE` — IANA zone, default `Etc/UTC`.
- `FIRESTORE_DB` — Firestore database name (default `(default)`).

## Data stores

- **Firestore**: `flow_runs/{runId}`, `chart_templates/{chartTemplateId}`, `chart_img_accounts_usage/{accountId}`.
- **GCS**: shared artifacts bucket for PNGs and manifest (no signed URLs).
- **Secret Manager**: stores `CHART_IMG_ACCOUNTS_JSON` source; never logged.

## CLI

- Command: `worker-chart-export run-local` with flags `--flow-run-path`, `--step-id`, `--charts-api-mode`, `--charts-bucket`, `--accounts-config-path`, `--output-summary (text|json|none)`.
- Exit codes: 0 success, non-zero on failure.
- CLI is a thin wrapper over the core engine; behavior matches CloudEvent.

## Testing

- Task tests (unittest discovery): `python scripts/qa/run_all.py`.
- List available task suites: `python scripts/qa/run_all.py --list`.

## Deploy & run in Google Cloud (notes)

The runtime is Cloud Run Functions gen2 (Functions Framework). Example deploy (placeholders):

```bash
PROJECT_ID=<PROJECT_ID>
REGION=<REGION>
RUNTIME_SA=<RUNTIME_SA_EMAIL>
FIRESTORE_DB=<FIRESTORE_DB_NAME>
CHARTS_BUCKET=gs://<BUCKET>
SECRET_NAME=<SECRET_NAME>

# APIs (once per project)
gcloud services enable \
  run.googleapis.com eventarc.googleapis.com firestore.googleapis.com \
  secretmanager.googleapis.com storage.googleapis.com logging.googleapis.com \
  cloudbuild.googleapis.com artifactregistry.googleapis.com \
  --project "$PROJECT_ID"

# Deploy

gcloud functions deploy worker-chart-export \
  --gen2 \
  --region="$REGION" \
  --runtime=python313 \
  --source=. \
  --entry-point=worker_chart_export \
  --service-account="$RUNTIME_SA" \
  --set-env-vars="CHARTS_BUCKET=$CHARTS_BUCKET,FIRESTORE_DB=$FIRESTORE_DB,CHARTS_DEFAULT_TIMEZONE=Etc/UTC" \
  --set-secrets="CHART_IMG_ACCOUNTS_JSON=projects/$PROJECT_ID/secrets/$SECRET_NAME:latest" \
  --trigger-location="$REGION" \
  --trigger-event-filters="type=google.cloud.firestore.document.v1.updated" \
  --trigger-event-filters="database=$FIRESTORE_DB" \
  --trigger-event-filters="namespace=(default)" \
  --trigger-event-filters-path-pattern="document=flow_runs/{runId}"

# Allow Eventarc to invoke the Cloud Run service (if needed)
gcloud run services add-iam-policy-binding worker-chart-export \
  --region="$REGION" \
  --project "$PROJECT_ID" \
  --member="serviceAccount:$RUNTIME_SA" \
  --role="roles/run.invoker"
```

Triggering a run: create/update a `flow_runs/{runId}` document. Any update emits a Firestore event; the worker ignores non-READY steps with a no-op log.

Cloud Logging: structured JSON logs are written to stdout/stderr and collected automatically by Cloud Run.

## References

- Package schema used at runtime: `worker_chart_export/contracts/charts_outputs_manifest.schema.json`.
- Task runbooks and QA logs: `docs/workflow/`.

## Credits

Thanks to the authors of `https://github.com/basilisk-labs/codex-swarm/` for the workflow tooling inspiration.
