# worker_chart_export

Trading Decisions Assistant component that renders PNG charts via Chart-IMG based on declarative templates and writes artifacts (PNG + manifest) to GCS. Runs as an Eventarc-triggered worker and has a CLI adapter for local runs.

## Overview

- **Purpose**: Consume `flow_runs/{runId}` documents, pick READY `CHART_EXPORT` steps, render a chart per request, upload PNGs to GCS, write a manifest, and finalize the step status.
- **Runtime**: Python 3.13, Functions Framework / Cloud Run. CLI и CloudEvent используют один и тот же core engine.
- **Sources of truth**: `docs-worker-chart-export/*` (contracts, schemas, templates), `docs-general/*` (system context, read-only), `docs-gcp/*` (deployment guidance).

## Quickstart (local)

1) Python 3.13 + venv: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
2) Prepare Chart-IMG accounts secret: copy `scripts/templates/chart-img.accounts.local.json.template`, fill keys, set `CHART_IMG_ACCOUNTS_JSON="$(cat ...)"`.
3) Set required env: `CHARTS_BUCKET=gs://<bucket>`, optional `CHARTS_API_MODE=mock|real|record`, `CHARTS_DEFAULT_TIMEZONE=Etc/UTC` (default).
4) Run CLI: `python -m worker_chart_export.cli run-local --flow-run-path ./tmp/flow_run.json --step-id step-1 --charts-bucket gs://<bucket> --charts-api-mode mock --accounts-config-path ./chart-img.accounts.local.json`.
5) Tests: `python -m pytest tests/tasks`.

## Processing Flow (high level)

1) **CloudEvent ingest** (T-003): fast filter for Firestore `update` on `flow_runs/{runId}`; deterministic READY step selection; idempotent no-op on repeats.
2) **Claim** (T-004): Firestore transaction `READY -> RUNNING`; two-phase finalize with minimal patch.
3) **Templates** (T-005): load `chart_templates/{chartTemplateId}`; required `chartImgSymbolTemplate`; `scope.symbol` expected without slash (e.g., `BTCUSDT`).
4) **Accounts & limits** (T-006): transactional usage in `chart_img_accounts_usage/{accountId}`, daily window reset (UTC), attempts counted, 429 marks account exhausted.
5) **Chart-IMG client** (T-007): modes `real|mock|record`; bounded retries/backoff; errors `CHART_API_FAILED | CHART_API_LIMIT_EXCEEDED | CHART_API_MOCK_MISSING`; timezone default `Etc/UTC`.
6) **Artifacts** (T-008): PNG path `charts/<runId>/<stepId>/<generatedAt>_<symbolSlug>_<timeframe>_<chartTemplateId>.png`; manifest path `charts/<runId>/<stepId>/manifest.json`; URIs `gs://...`; manifest validated; no `signed_url/expires_at`.
7) **Finalize** (T-004): patch `RUNNING -> SUCCEEDED|FAILED` with outputs or error code; idempotent on repeated finalize.

## Configuration (env)

- `CHARTS_BUCKET` (required) — `gs://<bucket>`.
- `CHART_IMG_ACCOUNTS_JSON` (required) — JSON array of `{id, apiKey, dailyLimit?}`; parsed once at startup.
- `CHARTS_API_MODE` — `real|mock|record` (default `real`, `record` forbidden in prod).
- `CHARTS_DEFAULT_TIMEZONE` — IANA zone, default `Etc/UTC`.
- `TDA_ENV`/`ENV` — environment label; `prod` blocks record mode.

## Data stores

- **Firestore**: `flow_runs/{runId}`, `chart_templates/{chartTemplateId}`, `chart_img_accounts_usage/{accountId}` (usage window, attempts counted).
- **GCS**: shared artifacts bucket for PNGs and manifest (no signed URLs).
- **Secrets Manager**: stores `CHART_IMG_ACCOUNTS_JSON` source; never logged.

## CLI

- Command: `worker-chart-export run-local` with flags `--flow-run-path`, `--step-id`, `--charts-api-mode`, `--charts-bucket`, `--accounts-config-path`, `--output-summary (text|json|none)`.
- Exit codes: 0 success, non-zero on failure.
- CLI — тонкая обёртка над core; поведение совпадает с CloudEvent.

## Testing

- **Unit**: `python -m pytest tests/tasks` (covers T-002..T-008).
- **QA bundle**: `python scripts/qa/run_all.py --task T-00X` produces reports in `docs/workflow/T-00X/pr/verify.log`.
- **Integration (mock/fake)**: planned in T-011 with harness choices from T-017/T-020 (Firestore in-memory fake, filesystem fake GCS).
- **Manual real Chart-IMG**: optional; requires local accounts file (not committed).

## Deploy (outline, T-012)

- Target: Cloud Run / Functions Framework (gen2). If Python 3.13 not native, container image.
- Eventarc trigger: Firestore `update` on `flow_runs/{runId}`; retries rely on idempotent claim/finalize.
- Service account: minimal roles for Firestore RW, GCS write, Secret Manager access to accounts.
- Bucket: shared artifacts bucket, public read if required by product (no signed URLs).

## Observability (outline, T-013)

- Structured logs: service, env, runId, stepId, eventId, error.code, chartsApi.accountId/httpStatus/durationMs/chartTemplateId/mode/fixtureKey; no secrets/PII.
- Log-based metrics + alerts: Chart-IMG error rate, global exhaustion, per-account usage, latency, success rate of CHART_EXPORT steps.

## Known limitations / TODO

- Integration harness (Firestore/GCS) tracked in T-017/T-020.
- Symbol/exchange architecture alignment planned in T-019.
- Keep README in sync with future task outcomes.

## References

- `docs-worker-chart-export/implementation_contract.md`
- `docs-worker-chart-export/contracts/*.json`
- `docs-worker-chart-export/chart-templates/*.json`
- `docs-general/*` (context, read-only)
- `docs-gcp/*` (deployment/infra)
