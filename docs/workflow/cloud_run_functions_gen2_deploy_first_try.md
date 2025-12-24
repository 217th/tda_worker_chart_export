# Google Cloud Run Functions (gen2) — First‑Try Deploy & Smoke Verify (Playbook)

This file is a **single, unambiguous instruction** you can paste to the Codex agent whenever you want it to deploy a service to **Google Cloud Run Functions (gen2)** and verify it.

It is written to avoid the common failure modes we hit in this repo (Eventarc filters, Firestore DB/region mismatch, missing invoker permissions, Artifact Registry cache permissions, oversized source bundles, etc.).

---

## 0) What you (the human) must provide in the prompt

When you ask the agent to deploy, include the following values explicitly (copy/paste the block and fill it):

```text
PROJECT_ID=
REGION=
FUNCTION_NAME=
RUNTIME=python313
SOURCE_DIR=.
ENTRY_POINT=

# Firestore trigger
FIRESTORE_DB=
FIRESTORE_TRIGGER_DOCUMENT_PATH=flow_runs/{runId}
FIRESTORE_TRIGGER_EVENT_TYPE=google.cloud.firestore.document.v1.updated
FIRESTORE_NAMESPACE=(default)

# Runtime configuration
CHARTS_BUCKET_GS=gs://
CHARTS_DEFAULT_TIMEZONE=Etc/UTC

# Secrets
CHART_IMG_ACCOUNTS_SECRET_NAME=

# Service accounts
RUNTIME_SA_EMAIL=
BUILD_SA_EMAIL=

# Optional: smoke test control
SMOKE_TEST_MODE=safe_no_quota   # allowed: safe_no_quota | real_one_image
```

Notes:
- `ENTRY_POINT` is the exported Functions Framework handler. In this repo it is `worker_chart_export` (see `main.py`).
- `FIRESTORE_DB` is the **database ID** (e.g. `(default)` or `my-db-name`), not a full resource path.

---

## 1) Preconditions the agent will verify (and fix if possible)

### 1.1 gcloud context

```bash
gcloud config set project "${PROJECT_ID}"
gcloud config set run/region "${REGION}" >/dev/null 2>&1 || true
```

### 1.2 Required APIs

Enable once per project:

```bash
gcloud services enable \
  run.googleapis.com \
  eventarc.googleapis.com \
  firestore.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  logging.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --project "${PROJECT_ID}"
```

### 1.3 Firestore DB exists in the same region

Cloud Run Functions gen2 + Eventarc **require region alignment**.

Check:

```bash
gcloud firestore databases list --project "${PROJECT_ID}" \
  --format="table(name,locationId,type)"
```

Requirement:
- The database named `projects/${PROJECT_ID}/databases/${FIRESTORE_DB}` must exist.
- Its `locationId` must be exactly `${REGION}`.

If not aligned, **stop** and create/move the database (this is a one‑time infra decision).

### 1.4 Source bundle correctness (.gcloudignore + main.py)

Rules:
- `gcloud` deploy uses **`.gcloudignore`**, not `.gitignore`.
- For `python313`, the source must include `main.py`.

Verify:

```bash
test -f .gcloudignore
test -f main.py
```

---

## 2) IAM: make deploy work on the first attempt

### 2.1 Resolve project number

```bash
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
```

### 2.2 Runtime SA permissions

Grant the minimal permissions the function needs at runtime:

```bash
# Firestore (read/write the required collections)
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
  --role="roles/datastore.user"

# Secret Manager: read the accounts secret
#gcloud secrets add-iam-policy-binding is per-secret (preferred)
gcloud secrets add-iam-policy-binding "${CHART_IMG_ACCOUNTS_SECRET_NAME}" \
  --project "${PROJECT_ID}" \
  --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

# Cloud Storage write (bucket‑level binding; adjust role if you want stricter)
BUCKET_NAME="${CHARTS_BUCKET_GS#gs://}"
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --project "${PROJECT_ID}" \
  --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
  --role="roles/storage.objectAdmin"

# Eventarc delivery (required for Firestore → Eventarc → Cloud Run)
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
  --role="roles/eventarc.eventReceiver"
```

### 2.3 Build SA permissions (Artifact Registry cache)

Cloud Functions gen2 builds use Artifact Registry (`gcf-artifacts` repository in the function region).
Missing these permissions commonly breaks deploy with:
`artifactregistry.repositories.downloadArtifacts denied`.

Ensure `gcf-artifacts` exists, then grant build SA `reader` + `writer`:

```bash
# Ensure repository exists (if this fails, list repos and adjust the name)
gcloud artifacts repositories describe gcf-artifacts \
  --location "${REGION}" \
  --project "${PROJECT_ID}" \
  >/dev/null

gcloud artifacts repositories add-iam-policy-binding gcf-artifacts \
  --location "${REGION}" \
  --project "${PROJECT_ID}" \
  --member="serviceAccount:${BUILD_SA_EMAIL}" \
  --role="roles/artifactregistry.reader"

gcloud artifacts repositories add-iam-policy-binding gcf-artifacts \
  --location "${REGION}" \
  --project "${PROJECT_ID}" \
  --member="serviceAccount:${BUILD_SA_EMAIL}" \
  --role="roles/artifactregistry.writer"
```

Also ensure Cloud Build can act as the build SA:

```bash
gcloud iam service-accounts add-iam-policy-binding "${BUILD_SA_EMAIL}" \
  --project "${PROJECT_ID}" \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

---

## 3) Deploy (canonical command)

Run from repo root (or `${SOURCE_DIR}`):

```bash
gcloud functions deploy "${FUNCTION_NAME}" \
  --gen2 \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --runtime="${RUNTIME}" \
  --source="${SOURCE_DIR}" \
  --entry-point="${ENTRY_POINT}" \
  --service-account="${RUNTIME_SA_EMAIL}" \
  --build-service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILD_SA_EMAIL}" \
  --set-env-vars="CHARTS_BUCKET=${CHARTS_BUCKET_GS},CHARTS_DEFAULT_TIMEZONE=${CHARTS_DEFAULT_TIMEZONE},FIRESTORE_DB=${FIRESTORE_DB}" \
  --set-secrets="CHART_IMG_ACCOUNTS_JSON=projects/${PROJECT_ID}/secrets/${CHART_IMG_ACCOUNTS_SECRET_NAME}:latest" \
  --trigger-location="${REGION}" \
  --trigger-event-filters="type=${FIRESTORE_TRIGGER_EVENT_TYPE}" \
  --trigger-event-filters="database=${FIRESTORE_DB}" \
  --trigger-event-filters="namespace=${FIRESTORE_NAMESPACE}" \
  --trigger-event-filters-path-pattern="document=${FIRESTORE_TRIGGER_DOCUMENT_PATH}"
```

After a successful deploy, always grant Cloud Run invoker to the runtime SA (this prevents Eventarc 403s):

```bash
gcloud run services add-iam-policy-binding "${FUNCTION_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
  --role="roles/run.invoker"
```

---

## 4) Smoke verification (Cloud Logging + Firestore)

### 4.1 Create a test flow_run document

You must create a document in:
- collection: `flow_runs`
- document id: a valid `runId` (must match your schema regex).

**Important:** Firestore triggers fire on *updates*. To guarantee an update event:
- `set(...)` the document
- then `update(...)` any field

Use this script (safe by default):

```bash
RUN_ID="$(date -u +%Y%m%d-%H%M%S)_BTCUSDT_demo"
STEP_ID="charts:1H:ctpl_price_ma1226_vol_v1"

python3 - <<'PY'
import os, uuid
from datetime import datetime, timezone
from google.cloud import firestore

project = os.environ["PROJECT_ID"]
database = os.environ["FIRESTORE_DB"]
run_id = os.environ["RUN_ID"]
step_id = os.environ["STEP_ID"]

client = firestore.Client(project=project, database=database)
doc = client.collection("flow_runs").document(run_id)

now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

# By default this is a safe/no-quota test (missing template => VALIDATION_FAILED before Chart-IMG).
smoke_mode = os.environ.get("SMOKE_TEST_MODE", "safe_no_quota")
if smoke_mode == "real_one_image":
    requests = [{"chartTemplateId": "ctpl_price_ma1226_vol_v1"}]
else:
    requests = [{"chartTemplateId": "ctpl_missing_v1"}]

flow_run = {
    "schemaVersion": 1,
    "runId": run_id,
    "flowKey": "smoke_test",
    "status": "RUNNING",
    "createdAt": now,
    "trigger": {"type": "MANUAL", "source": "deploy-smoke"},
    "scope": {"symbol": "BTCUSDT"},
    "steps": {
        step_id: {
            "stepType": "CHART_EXPORT",
            "status": "READY",
            "timeframe": "1h",
            "createdAt": now,
            "dependsOn": [],
            "inputs": {"minImages": 1, "requests": requests},
            "outputs": {},
        }
    },
}

doc.set(flow_run)
# Force an update event

doc.update({"trigger.source": f"deploy-smoke-{uuid.uuid4().hex[:6]}"})
print("runId=", run_id)
print("stepId=", step_id)
PY
```

### 4.2 Observe logs

Filter by `runId` and expected events:

```bash
gcloud logging read \
  'resource.type="cloud_run_revision"\
   resource.labels.service_name="'"${FUNCTION_NAME}"'"\
   jsonPayload.runId="'"${RUN_ID}"'"\
   jsonPayload.event:("cloud_event_received" OR "cloud_event_parsed" OR "ready_step_selected" OR "depends_on_blocked" OR "cloud_event_finished" OR "step_completed")' \
  --project "${PROJECT_ID}" \
  --limit 50 \
  --freshness 15m
```

Expected outcomes:

- If `SMOKE_TEST_MODE=safe_no_quota`:
  - You should see `cloud_event_received` → `cloud_event_parsed` → `ready_step_selected` → `cloud_event_finished` with `errorCode=VALIDATION_FAILED`.
  - **No Chart‑IMG usage** is consumed.

- If `SMOKE_TEST_MODE=real_one_image`:
  - You should see `step_completed` and `cloud_event_finished` with `status=SUCCEEDED`.
  - This consumes **exactly one** Chart‑IMG image (assuming templates exist).

### 4.3 Idempotency note (multiple triggers)

It is normal to see multiple `cloud_event_received` events for the same `runId`:
- the worker itself updates `flow_runs/{runId}` (claim/finalize), producing additional Firestore update events.
- subsequent events should log `cloud_event_noop` with `reason=no_ready_step`.

---

## 5) Troubleshooting decision tree (fast)

### A) Build failed: Artifact Registry permissions

Symptoms:
- `artifactregistry.repositories.downloadArtifacts denied`

Fix:
- Ensure build SA has `roles/artifactregistry.reader` and `roles/artifactregistry.writer` on `gcf-artifacts` in `${REGION}`.

### B) Eventarc delivery returns HTTP 403

Symptoms:
- Cloud Run request logs show 403 unauthenticated

Fix:
- Ensure `roles/run.invoker` binding exists for the runtime SA on the Cloud Run service.

### C) Trigger validation errors

Symptoms:
- deploy fails: missing required event filter attributes

Fix:
- Ensure the trigger filters include:
  - `type=google.cloud.firestore.document.v1.updated`
  - `database=${FIRESTORE_DB}`
  - `namespace=(default)`
  - document path pattern

### D) No worker logs after Firestore update

Fix:
- Ensure you performed an `update(...)` after `set(...)`.
- Ensure Firestore DB location == `${REGION}`.
- Ensure trigger exists and targets the correct database and document pattern.

---

## 6) Cleanup (optional)

- Delete the test `flow_runs/{runId}` document.
- Delete test objects under `gs://<bucket>/charts/<runId>/...` if you ran real mode.

