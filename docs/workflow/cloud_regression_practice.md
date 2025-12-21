# Cloud Regression Practice (Codex-run)

Purpose: a repeatable, Codex-driven checklist for running cloud regression
scenarios (deploy -> trigger -> verify logs -> verify GCS) without manual console
work. Use this whenever a task requires verification in real GCP.

## Preconditions

- `gcloud` installed and authenticated (active account has deploy + runtime perms).
- Project, Firestore DB, bucket, and Secret Manager are provisioned.
- Cloud Function triggers Firestore updates on `flow_runs/{runId}`.
- `.gcloudignore` excludes non-runtime files (docs, codex-swarm, etc.).
- Access to the Chart-IMG secret in Secret Manager.

## Safety & hygiene

- Never paste API keys in chat; always read secrets from Secret Manager.
- Use `CHARTS_API_MODE=record` only when you intend real Chart-IMG calls.
- Use unique `runId` values to avoid confusion and conflicts.
- Prefer deleting test flow_runs and GCS objects after verification.

## Standard environment variables

```
export PROJECT_ID="kb-agent-479608"
export FIRESTORE_DB="tda-db-europe-west4"
export ARTIFACTS_BUCKET="tda-artifacts-test"
export REGION="europe-west4"
export FUNCTION_NAME="worker-chart-export"
export STEP_ID="charts:1H:ctpl_price_ma1226_vol_v1"
```

## 1) Deploy from current branch

Run from repo root (same branch you are verifying):

```
gcloud functions deploy "${FUNCTION_NAME}" \
  --gen2 \
  --region="${REGION}" \
  --runtime=python313 \
  --source=. \
  --entry-point=worker_chart_export \
  --service-account="tda-worker-chart-export-test@${PROJECT_ID}.iam.gserviceaccount.com" \
  --set-env-vars="ARTIFACTS_BUCKET=${ARTIFACTS_BUCKET},CHARTS_BUCKET=gs://${ARTIFACTS_BUCKET},CHARTS_DEFAULT_TIMEZONE=Etc/UTC,FIRESTORE_DB=${FIRESTORE_DB},CHARTS_API_MODE=record" \
  --set-secrets="CHART_IMG_ACCOUNTS_JSON=projects/${PROJECT_ID}/secrets/chart-img-accounts:latest" \
  --trigger-location="${REGION}" \
  --trigger-event-filters="type=google.cloud.firestore.document.v1.updated" \
  --trigger-event-filters="database=${FIRESTORE_DB}" \
  --trigger-event-filters="namespace=(default)" \
  --trigger-event-filters-path-pattern="document=flow_runs/{runId}"
```

Notes:
- If deploy returns `unable to queue the operation`, wait ~20s and retry.
- Make sure function is redeployed after code changes to avoid stale behavior.
- In automation, deploy/log commands may time out locally while the GCP operation continues.
  If you see a timeout without a hard error, re-run with a longer timeout and/or
  confirm status in Cloud Console or with a fresh `gcloud functions describe`.
- Expect multiple Firestore update triggers per run:
  - The worker writes claim/finalize updates to the same `flow_runs/{runId}` document.
  - Each write emits a new Eventarc event with a new `eventId`.
  - Only the first event typically performs work; subsequent events should log
    `cloud_event_noop` with `reason=no_ready_step`. This is normal/idempotent.

## 2) Create a flow_run and trigger update

Use a valid runId (regex must match: `YYYYMMDD-HHMMSS_SYMBOL_slug`).

```
export RUN_ID="20251221-142000_BTCUSDT_demo25"

python - <<'PY'
import os, uuid
from datetime import datetime, timezone
from google.cloud import firestore

project = os.environ["PROJECT_ID"]
database = os.environ["FIRESTORE_DB"]
run_id = os.environ["RUN_ID"]
step_id = os.environ["STEP_ID"]

client = firestore.Client(project=project, database=database)
doc = client.collection("flow_runs").document(run_id)

now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
flow_run = {
    "schemaVersion": 1,
    "runId": run_id,
    "flowKey": "scheduled_month_week_report_v1",
    "status": "RUNNING",
    "createdAt": now,
    "trigger": {"type": "MANUAL", "source": "tda-cloud-verify"},
    "scope": {"symbol": "BTCUSDT"},
    "steps": {
        step_id: {
            "stepType": "CHART_EXPORT",
            "status": "READY",
            "timeframe": "1h",
            "createdAt": now,
            "dependsOn": [],
            "inputs": {
                "minImages": 1,
                "requests": [
                    {"chartTemplateId": "ctpl_price_ma1226_vol_v1"},
                    {"chartTemplateId": "ctpl_price_rsi14_stochrsi_v1"},
                    {"chartTemplateId": "ctpl_price_psar_adi_v1"},
                ],
            },
            "outputs": {},
        }
    },
}

doc.set(flow_run)
doc.update({"trigger.source": f"tda-cloud-verify-{uuid.uuid4().hex[:6]}"})
print("created+updated", run_id)
PY
```

## 3) Verify logs (Cloud Logging)

```
gcloud logging read \
  'resource.type="cloud_run_revision"
   resource.labels.service_name="worker-chart-export"
   jsonPayload.runId="'"${RUN_ID}"'"
   jsonPayload.event:("ready_step_selected" OR "step_completed" OR "cloud_event_finished")' \
  --limit=20 --freshness=15m
```

Expected:
- `ready_step_selected`
- `step_completed`
- `cloud_event_finished` with status `SUCCEEDED`

## 4) Verify GCS artifacts

```
gsutil ls gs://${ARTIFACTS_BUCKET}/charts/${RUN_ID}/${STEP_ID}/
gsutil cat gs://${ARTIFACTS_BUCKET}/charts/${RUN_ID}/${STEP_ID}/manifest.json | head -n 20
```

Expected:
- PNGs and `manifest.json` exist under the new `charts/<runId>/<stepId>/` path.
- Manifest `items[].png_gcs_uri` matches the same base path.

## 5) Idempotent retry

```
python - <<'PY'
import os, uuid
from google.cloud import firestore

client = firestore.Client(project=os.environ["PROJECT_ID"], database=os.environ["FIRESTORE_DB"])
doc = client.collection("flow_runs").document(os.environ["RUN_ID"])
doc.update({"trigger.source": f"tda-retry-{uuid.uuid4().hex[:6]}"})
print("updated", os.environ["RUN_ID"])
PY
```

Then verify `cloud_event_noop` in logs:
```
gcloud logging read \
  'resource.type="cloud_run_revision"
   resource.labels.service_name="worker-chart-export"
   jsonPayload.runId="'"${RUN_ID}"'"
   jsonPayload.event="cloud_event_noop"' \
  --limit=10 --freshness=10m
```

## 6) Missing chart template (negative)

```
export RUN_ID="20251221-143000_BTCUSDT_demo25m"
python - <<'PY'
import os, uuid
from datetime import datetime, timezone
from google.cloud import firestore

project = os.environ["PROJECT_ID"]
database = os.environ["FIRESTORE_DB"]
run_id = os.environ["RUN_ID"]
step_id = os.environ["STEP_ID"]

client = firestore.Client(project=project, database=database)
doc = client.collection("flow_runs").document(run_id)

now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
flow_run = {
    "schemaVersion": 1,
    "runId": run_id,
    "flowKey": "scheduled_month_week_report_v1",
    "status": "RUNNING",
    "createdAt": now,
    "trigger": {"type": "MANUAL", "source": "tda-cloud-verify"},
    "scope": {"symbol": "BTCUSDT"},
    "steps": {
        step_id: {
            "stepType": "CHART_EXPORT",
            "status": "READY",
            "timeframe": "1h",
            "createdAt": now,
            "dependsOn": [],
            "inputs": {"minImages": 1, "requests": [{"chartTemplateId": "ctpl_missing_v1"}]},
            "outputs": {},
        }
    },
}

doc.set(flow_run)
doc.update({"trigger.source": f"tda-missing-{uuid.uuid4().hex[:6]}"})
print("created+updated", run_id)
PY
```

Expected:
- `cloud_event_finished` with `errorCode=VALIDATION_FAILED`
- No objects under `gs://${ARTIFACTS_BUCKET}/charts/<runId>/<stepId>/`

## 7) Non-CHART_EXPORT step (no-op)

Purpose: ensure non-target steps do not trigger processing.

```
export RUN_ID="20251221-144000_BTCUSDT_demo25no"
python - <<'PY'
import os, uuid
from datetime import datetime, timezone
from google.cloud import firestore

project = os.environ["PROJECT_ID"]
database = os.environ["FIRESTORE_DB"]
run_id = os.environ["RUN_ID"]

client = firestore.Client(project=project, database=database)
doc = client.collection("flow_runs").document(run_id)

now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
flow_run = {
    "schemaVersion": 1,
    "runId": run_id,
    "flowKey": "scheduled_month_week_report_v1",
    "status": "RUNNING",
    "createdAt": now,
    "trigger": {"type": "MANUAL", "source": "tda-cloud-verify"},
    "scope": {"symbol": "BTCUSDT"},
    "steps": {
        "analysis:1H:dummy": {
            "stepType": "ANALYSIS",
            "status": "READY",
            "timeframe": "1h",
            "createdAt": now,
            "dependsOn": [],
            "inputs": {},
            "outputs": {},
        }
    },
}

doc.set(flow_run)
doc.update({"trigger.source": f"tda-noop-{uuid.uuid4().hex[:6]}"})
print("created+updated", run_id)
PY
```

Expected:
- `cloud_event_noop` with reason `no_ready_step`.

## 8) Eventarc filter sanity (other collection)

Purpose: ensure updates outside `flow_runs/` do not invoke the function.

1) Update any `chart_templates/{id}` document:
```
python - <<'PY'
import os, uuid
from google.cloud import firestore

client = firestore.Client(project=os.environ["PROJECT_ID"], database=os.environ["FIRESTORE_DB"])
doc = client.collection("chart_templates").document("ctpl_price_ma1226_vol_v1")
doc.update({"_lastTouched": uuid.uuid4().hex})
print("updated chart_templates")
PY
```

2) Verify no new `cloud_event_received` entries for the function in the next 1-2 minutes.

## 9) GCS write failure (negative)

Purpose: validate `MANIFEST_WRITE_FAILED` when bucket is invalid.

Steps:
1) Redeploy with a bad bucket name:
```
gcloud functions deploy "${FUNCTION_NAME}" \
  --gen2 \
  --region="${REGION}" \
  --runtime=python313 \
  --source=. \
  --entry-point=worker_chart_export \
  --service-account="tda-worker-chart-export-test@${PROJECT_ID}.iam.gserviceaccount.com" \
  --set-env-vars="ARTIFACTS_BUCKET=bad-bucket-name,CHARTS_BUCKET=gs://bad-bucket-name,CHARTS_DEFAULT_TIMEZONE=Etc/UTC,FIRESTORE_DB=${FIRESTORE_DB},CHARTS_API_MODE=record" \
  --set-secrets="CHART_IMG_ACCOUNTS_JSON=projects/${PROJECT_ID}/secrets/chart-img-accounts:latest" \
  --trigger-location="${REGION}" \
  --trigger-event-filters="type=google.cloud.firestore.document.v1.updated" \
  --trigger-event-filters="database=${FIRESTORE_DB}" \
  --trigger-event-filters="namespace=(default)" \
  --trigger-event-filters-path-pattern="document=flow_runs/{runId}"
```

2) Run the happy path (section 2).
3) Expect `cloud_event_finished` with `errorCode=MANIFEST_WRITE_FAILED` or `GCS_WRITE_FAILED`.
4) Redeploy back with the correct bucket immediately after.

## 10) Secret Manager misconfig (negative)

Purpose: ensure bad secret format fails fast with `config_error`.

Steps:
1) Add a temporary bad version:
```
echo "not-json" | gcloud secrets versions add chart-img-accounts \
  --project "${PROJECT_ID}" --data-file=-
```
2) Trigger any flow_run update.
3) Expect `config_error` in logs and exception in stderr.
4) Restore secret by adding a valid JSON version (or roll back to previous latest).

## 11) Account exhaustion (negative)

Purpose: if all accounts are exhausted, expect `CHART_API_LIMIT_EXCEEDED`.

Steps:
```
python - <<'PY'
import os
from datetime import datetime, timezone
from google.cloud import firestore

client = firestore.Client(project=os.environ["PROJECT_ID"], database=os.environ["FIRESTORE_DB"])
now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

for doc in client.collection("chart_img_accounts_usage").stream():
    data = doc.to_dict()
    daily_limit = data.get("dailyLimit", 0)
    doc.reference.set({
        "accountId": data.get("accountId", doc.id),
        "dailyLimit": daily_limit,
        "usageToday": daily_limit,
        "windowStart": now,
    }, merge=True)
    print("exhausted", doc.id)
PY
```

Expected:
- `cloud_event_finished` with `errorCode=CHART_API_LIMIT_EXCEEDED`
- No new PNGs/manifest in GCS.

## 12) Invalid runId (negative)

Purpose: confirm regex enforcement (may still upload PNG before failure).

Steps:
1) Use a runId that violates regex (e.g. suffix too long).
2) Trigger flow_run update.

Expected:
- `cloud_event_finished` with `errorCode=VALIDATION_FAILED`.
- Potential partial artifacts (PNG) may appear; clean up after.

## 13) Structured logging sanity

Purpose: ensure essential fields are present.

```
gcloud logging read \
  'resource.type="cloud_run_revision"
   resource.labels.service_name="worker-chart-export"
   jsonPayload.event="step_completed"' \
  --limit=5 --freshness=10m
```

Check presence of: `runId`, `stepId`, `status`, `itemsCount`, `failuresCount`,
`outputsManifestGcsUri`.

## Cleanup (optional)

- Delete test docs in `flow_runs/`.
- Remove test artifacts from `gs://<bucket>/charts/<runId>/`.
