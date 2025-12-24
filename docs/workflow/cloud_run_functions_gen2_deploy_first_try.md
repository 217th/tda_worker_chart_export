# Google Cloud Run Functions (gen2) — Deploy “First Try” Playbook (Universal)

This is a **single-file**, **English**, **high-detail**, **unambiguous** instruction intended to be followed by an agent (or a human acting as the agent) to deploy a Python service to **Google Cloud Run Functions (gen2)** with minimal retries.

It explicitly supports two situations:

1) **First-time deploy**: the function does not exist yet → bootstrap + validate everything.
2) **Update deploy**: the function already exists and previously worked → minimal changes; only re-validate when errors occur.

This playbook also defines when **human-in-the-middle** is required (when the agent cannot uniquely diagnose or should not take potentially destructive actions without explicit approval).

Security note (public repos):
- Do **not** commit real `PROJECT_ID`, database IDs, bucket names, service account emails, secret names, or URLs into tracked docs.
- Always use placeholders in this file. Only pass real values in the deploy request block at runtime.

---

## 0) Preconditions for the agent environment

The agent must have:
- `gcloud` installed and authenticated.
- Permissions in the target project to deploy Cloud Run Functions gen2 and to read/write IAM policies for the resources involved.

The agent must work from a clean working tree (or at least be able to clearly attribute any changes).

---

## 1) The deploy request block (human input)

When you request a deploy, provide this exact block. **Fill required fields** and omit optional blocks if not used.

```text
# Required
PROJECT_ID=
REGION=
FUNCTION_NAME=
RUNTIME=python313
SOURCE_DIR=.

# Trigger kind (required): firestore | http | pubsub
TRIGGER_KIND=firestore

# Firestore trigger (required if TRIGGER_KIND=firestore)
# FIRESTORE_DB is a database ID, e.g. "(default)" or "my-db" (not a full resource path).
FIRESTORE_DB=
FIRESTORE_NAMESPACE=(default)
FIRESTORE_TRIGGER_EVENT_TYPE=google.cloud.firestore.document.v1.updated
FIRESTORE_TRIGGER_DOCUMENT_PATH=flow_runs/{runId}

# HTTP trigger (optional, only if TRIGGER_KIND=http)
# If omitted: default is authenticated-only.
HTTP_ALLOW_UNAUTHENTICATED=false

# Pub/Sub trigger (required if TRIGGER_KIND=pubsub)
PUBSUB_TOPIC=
PUBSUB_TOPIC_CREATE_IF_MISSING=false

# Runtime Service Account (required)
RUNTIME_SA_EMAIL=

# Environment variables (optional; comma-separated KEY=VALUE)
ENV_VARS=

# Secrets (optional; comma-separated KEY=projects/<PROJECT_ID>/secrets/<NAME>:<VERSION>)
# Many services do not need secrets. If empty, do not set any secrets.
SECRET_ENV_VARS=

# Cloud Storage buckets used by the function (optional; comma-separated bucket names without gs://)
# Example: my-artifacts-bucket,my-logs-bucket
GCS_BUCKETS=

# Used GCP services (recommended; comma-separated)
# Example: firestore,storage,secretmanager,logging,eventarc
USED_GCP_SERVICES=

# Optional (opt-in) smoke verification
# If omitted or false, the agent must NOT run smoke verification that writes to GCP or consumes paid API quota.
APPROVE_SMOKE_VERIFY=false
SMOKE_VERIFY_MODE=safe_no_quota  # safe_no_quota | real_one_image
```

Important rules:
- `ENTRY_POINT` is **not provided** by the human. The agent must derive it from the codebase (Section 4.2).
- `SECRET_ENV_VARS` is optional. Do not force secrets for services that do not need them.
- IAM roles must be conditional on actual usage (`USED_GCP_SERVICES`) (Section 4.4).
- Smoke verification is opt-in only (Section 6). If not approved, the agent must stop after a successful deploy confirmation.

---

## 2) Decide deploy mode: first-time vs update deploy (agent step)

The agent must determine whether this is a first deploy or update deploy:

```bash
gcloud functions describe "${FUNCTION_NAME}" \
  --gen2 \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --format="value(name)" \
  >/dev/null
```

- If the command succeeds → **Update deploy** (Section 5).
- If it returns NOT_FOUND → **First-time deploy** (Section 4).

---

## 3) What “success” means (definition of done)

### 3.1 Deploy success (first deploy and update deploy)

Deploy is considered successful when:
- `gcloud functions describe ... --format="value(state)"` returns `ACTIVE`.
- The function has the intended trigger and runtime configuration.

### 3.2 Optional smoke verification success

Smoke verification is considered successful only if it is explicitly approved and the defined smoke scenarios pass (Section 6).

---

## 4) First-time deploy (bootstrap + validations)

### 4.1 Set gcloud context (always)

```bash
gcloud config set project "${PROJECT_ID}"
```

### 4.2 Verify source packaging for Cloud Run Functions gen2 (Python)

Rules:
- `gcloud functions deploy` uses **`.gcloudignore`** (not `.gitignore`) to decide what is uploaded.
- For Python runtimes (`python313`), the source must include a top-level **`main.py`** under `SOURCE_DIR`.

Agent checks (hard requirements):

```bash
test -f "${SOURCE_DIR}/main.py"
test -f "${SOURCE_DIR}/.gcloudignore"
```

Critical runtime-assets rule:
- If your code reads files at runtime (schemas, JSON templates, etc.), those files must be included in the deploy source.
- Therefore: do not place required runtime assets only under excluded folders like `docs-*` if `.gcloudignore` excludes them.

If the agent cannot confirm which files are runtime-required:
- human-in-the-middle required (Section 7.1). The human must confirm which files are needed at runtime.

#### 4.2.1 Monorepo / multiple `main.py` pitfall (wrong entrypoint packaged)

In real projects it is common to have:
- a repo-root `main.py` for a CLI or local runner, and
- a different function entrypoint under a subdirectory.

If you deploy from the repo root (`SOURCE_DIR=.`), Cloud Functions may package the wrong `main.py`.

Agent rule:
- If there are multiple `main.py` files in the repo, the agent must ensure `SOURCE_DIR` points at the directory that contains the intended Cloud Functions `main.py`.

Agent diagnostic:

```bash
python3 - <<'PY'
from pathlib import Path
paths = sorted(str(p) for p in Path(".").rglob("main.py"))
print("\n".join(paths))
PY
```

If more than one path is printed:
- human-in-the-middle is allowed (ask which one is the Cloud Function entrypoint), OR
- set `SOURCE_DIR` explicitly to the correct folder and re-run the packaging checks.

### 4.3 Derive `ENTRY_POINT` (agent-only, deterministic)

The agent must determine the Cloud Run Functions entry point from the codebase.

Definition:
- `ENTRY_POINT` is the python function symbol name passed to `gcloud functions deploy --entry-point`.

Procedure (agent must follow in this order):

1) Read `${SOURCE_DIR}/main.py`.
2) If `main.py` contains a line importing the handler symbol (common pattern), use the imported symbol name:
   - Example: `from mypkg.entrypoints.cloud_event import worker_chart_export`
   - Then: `ENTRY_POINT=worker_chart_export`
3) If `main.py` does not clearly identify the entry function:
   - Search for Functions Framework decorators:
     - `@functions_framework.cloud_event`
     - `@functions_framework.http`
4) If still ambiguous:
   - STOP. Ask the human to specify the entry-point symbol.

Human-in-the-middle request format:
```text
Provide ENTRY_POINT (python function symbol) and trigger kind (cloud_event/http/pubsub).
Paste the exact python file path and the function name to use.
```

### 4.4 Enable required APIs (one-time bootstrap)

Always enable these platform APIs (Cloud Run Functions gen2 stack):

```bash
gcloud services enable \
  cloudfunctions.googleapis.com \
  run.googleapis.com \
  eventarc.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  logging.googleapis.com \
  --project "${PROJECT_ID}"
```

Enable additional APIs only if your function actually uses those services:

- Firestore data access or Firestore trigger: `firestore.googleapis.com`
- Cloud Storage: `storage.googleapis.com`
- Secret Manager: `secretmanager.googleapis.com`

Example:

```bash
gcloud services enable \
  firestore.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  --project "${PROJECT_ID}"
```

If the agent is unsure which APIs are needed:
- it must use `USED_GCP_SERVICES` (Section 1) or ask the human.

### 4.5 Firestore database region alignment (required for TRIGGER_KIND=firestore)

For Firestore → Eventarc → Cloud Run Functions gen2, these must be aligned:
- Firestore database location == `${REGION}`
- Eventarc trigger location == `${REGION}`
- Function region == `${REGION}`

Check Firestore databases:

```bash
gcloud firestore databases list \
  --project "${PROJECT_ID}" \
  --format="table(name,locationId,type)"
```

Requirement:
- `projects/${PROJECT_ID}/databases/${FIRESTORE_DB}` must exist
- its `locationId` must equal `${REGION}`

If the required DB does not exist in that region:
- human-in-the-middle required (Section 7.2).

### 4.6 IAM (runtime SA) — conditional roles only

IAM depends on which services the function uses.

The agent must build an IAM plan using (in priority order):
1) `USED_GCP_SERVICES` from the request block (best).
2) Infer from code (imports and dependencies) (acceptable).
3) If uncertain: ask the human to confirm (required).

#### 4.6.1 Minimal role mapping (use only what applies)

Use the smallest roles that satisfy required actions:

- Firestore **read/write**: `roles/datastore.user` (project-level)
- Firestore **read-only**: `roles/datastore.viewer` (project-level)
- Cloud Storage (GCS) **write objects**:
  - simplest: bucket-level `roles/storage.objectAdmin`
  - stricter: bucket-level `roles/storage.objectCreator` + `roles/storage.objectViewer` (only if compatible with your code)
- Secret Manager **read secret values**:
  - secret-level `roles/secretmanager.secretAccessor`
- Cloud Logging:
  - Cloud Run Functions automatically ships stdout/stderr to Cloud Logging; no IAM role is usually needed for that.
  - Only grant `roles/logging.logWriter` if your code calls Cloud Logging API directly.

#### 4.6.2 Eventarc roles (only for TRIGGER_KIND=firestore)

If using Firestore/Eventarc:
- runtime SA needs: `roles/eventarc.eventReceiver` (project-level)
- the Eventarc trigger SA must be allowed to invoke the Cloud Run service (roles/run.invoker) (Section 4.9)

Grant Eventarc receiver to runtime SA:

```bash
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
  --role="roles/eventarc.eventReceiver"
```

#### 4.6.3 Bucket + secret bindings (recommended scope)

Bucket-level binding is preferred over project-level. If `GCS_BUCKETS` is empty, the agent must either:
- ask the human for bucket names, or
- fall back to project-level roles (less strict; only if explicitly approved by the human).

Secret-level binding (preferred over project-level):
- human must provide secret names if secrets are used.

#### 4.6.4 IAM verification without keys (recommended)

Prefer verifying permissions via **service account impersonation** (no JSON keys).

Examples:

```bash
# Confirm the SA exists
gcloud iam service-accounts describe "${RUNTIME_SA_EMAIL}" --project "${PROJECT_ID}"

# GCS: list bucket contents as the runtime SA
gcloud storage ls "gs://<BUCKET_NAME>/" \
  --project "${PROJECT_ID}" \
  --impersonate-service-account="${RUNTIME_SA_EMAIL}"
```

Notes:
- Many `gcloud` commands support `--impersonate-service-account`.
- If impersonation is blocked by org policy, human-in-the-middle is required to run verification from an allowed environment.

### 4.7 Build identity (Build SA) — do not introduce unless required

Recommendation:
- Do **not** set a custom build service account (do not use `--build-service-account`) unless required by policy.

Build identity is relevant only when:
- Cloud Build fails (often due to Artifact Registry permissions) (Section 8.1).

### 4.8 Deploy command (first deploy)

Agent composes the deploy command based on `TRIGGER_KIND`.

Important:
- If `ENV_VARS` is empty, omit `--set-env-vars` entirely.
- If `SECRET_ENV_VARS` is empty, omit `--set-secrets` entirely.

#### 4.8.1 Firestore trigger (Eventarc) — recommended filters and meaning

Filters:
- `type`: which Firestore CloudEvent to receive
- `database`: database ID (required)
- `namespace`: namespace (required; typically `(default)`)
- `document` (path pattern): which document path to match and which variables to extract

Recommended event type:
- `google.cloud.firestore.document.v1.updated` (update-only).

Alternatives:
- `.written` (created/updated/deleted) — use only if you intentionally want those events.

Deploy:

```bash
gcloud functions deploy "${FUNCTION_NAME}" \
  --gen2 \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --runtime "${RUNTIME}" \
  --source "${SOURCE_DIR}" \
  --entry-point "${ENTRY_POINT}" \
  --service-account "${RUNTIME_SA_EMAIL}" \
  --trigger-location "${REGION}" \
  --trigger-event-filters "type=${FIRESTORE_TRIGGER_EVENT_TYPE}" \
  --trigger-event-filters "database=${FIRESTORE_DB}" \
  --trigger-event-filters "namespace=${FIRESTORE_NAMESPACE}" \
  --trigger-event-filters-path-pattern "document=${FIRESTORE_TRIGGER_DOCUMENT_PATH}"
```

If you have env vars:
```bash
  --set-env-vars "${ENV_VARS}"
```

If you have secrets:
```bash
  --set-secrets "${SECRET_ENV_VARS}"
```

#### 4.8.2 HTTP trigger

Deploy:

```bash
gcloud functions deploy "${FUNCTION_NAME}" \
  --gen2 \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --runtime "${RUNTIME}" \
  --source "${SOURCE_DIR}" \
  --entry-point "${ENTRY_POINT}" \
  --service-account "${RUNTIME_SA_EMAIL}" \
  --trigger-http
```

If `HTTP_ALLOW_UNAUTHENTICATED=true`, also add:
```bash
  --allow-unauthenticated
```

#### 4.8.3 Pub/Sub trigger

Human must supply `PUBSUB_TOPIC`.

If `PUBSUB_TOPIC_CREATE_IF_MISSING=true`:
```bash
gcloud pubsub topics create "${PUBSUB_TOPIC}" --project "${PROJECT_ID}" || true
```

Deploy:
```bash
gcloud functions deploy "${FUNCTION_NAME}" \
  --gen2 \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --runtime "${RUNTIME}" \
  --source "${SOURCE_DIR}" \
  --entry-point "${ENTRY_POINT}" \
  --service-account "${RUNTIME_SA_EMAIL}" \
  --trigger-topic "${PUBSUB_TOPIC}"
```

### 4.9 Post-deploy: allow Eventarc delivery to invoke Cloud Run service (firestore only)

If `TRIGGER_KIND=firestore`, ensure the Eventarc trigger identity can invoke the Cloud Run service.

1) Determine which service account the trigger uses:

```bash
gcloud functions describe "${FUNCTION_NAME}" \
  --gen2 \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --format="value(eventTrigger.serviceAccountEmail)"
```

2) Grant Cloud Run invoker to that identity:

Note:
- In Cloud Run Functions gen2, the Cloud Run **service name** is usually the same as `FUNCTION_NAME`.
- If it is not, get the service resource from:
  `gcloud functions describe ... --format="value(serviceConfig.service)"` and use that service’s name for `gcloud run services ...`.

```bash
gcloud run services add-iam-policy-binding "${FUNCTION_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --member="serviceAccount:<EVENTARC_TRIGGER_SA_EMAIL>" \
  --role="roles/run.invoker"
```

#### 4.9.1 Eventarc “service agent” invoker (common hidden identity)

In some projects, Eventarc may deliver events using the **Eventarc service agent**:

`service-${PROJECT_NUMBER}@gcp-sa-eventarc.iam.gserviceaccount.com`

If your logs show Eventarc delivery attempts but the Cloud Run request log reports `403`, grant invoker to the delivery identity.

Agent steps:
1) Get project number:
```bash
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
```
2) Compose Eventarc service agent:
```bash
EVENTARC_SERVICE_AGENT="service-${PROJECT_NUMBER}@gcp-sa-eventarc.iam.gserviceaccount.com"
```
3) Grant invoker (if required):
```bash
gcloud run services add-iam-policy-binding "${FUNCTION_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --member="serviceAccount:${EVENTARC_SERVICE_AGENT}" \
  --role="roles/run.invoker"
```

Human-in-the-middle:
- Only apply this if there is evidence (403 delivery) and you can identify the actual caller identity from logs/trigger config.

### 4.10 Confirm deploy status

```bash
gcloud functions describe "${FUNCTION_NAME}" \
  --gen2 \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --format="value(state,serviceConfig.revision,updateTime)"
```

---

## 5) Update deploy (function already exists)

Update deploy is intentionally minimal: redeploy the source while preserving trigger and configuration.

### 5.1 Read current deployed configuration (agent step)

```bash
gcloud functions describe "${FUNCTION_NAME}" \
  --gen2 \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --format="yaml(serviceConfig.environmentVariables,serviceConfig.secretEnvironmentVariables,eventTrigger,buildConfig,serviceConfig.serviceAccountEmail,url)"
```

Agent must reuse (unless human explicitly requests changes):
- runtime SA: `serviceConfig.serviceAccountEmail`
- env vars: `serviceConfig.environmentVariables`
- secrets mapping: `serviceConfig.secretEnvironmentVariables`
- trigger config: `eventTrigger` (if present)

### 5.2 Derive `ENTRY_POINT` again (agent step)

Always re-derive entry point from code (Section 4.3). Do not assume it stayed the same.

### 5.3 Deploy update (explicit, deterministic)

Rules:
- Use the same trigger kind as currently deployed unless the human requests a trigger change.
- Keep existing env vars and secrets unless the human requests changes.
- Do not redo API enablement and IAM unless errors occur.

Perform the same deploy command as in first deploy (Section 4.8) using:
- existing trigger values from `eventTrigger` (preferred), and/or
- the human-provided input block.

### 5.4 Confirm deploy status

```bash
gcloud functions describe "${FUNCTION_NAME}" \
  --gen2 \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --format="value(state,serviceConfig.revision,updateTime)"
```

If the function does not become ACTIVE, go to troubleshooting (Section 8).

---

## 6) Optional smoke verification (opt‑in only)

Smoke verification must only be executed if `APPROVE_SMOKE_VERIFY=true`.

If not approved, stop after deploy confirmation.

### 6.1 Cloud Logging transport (what exists by default)

Cloud Run Functions gen2 automatically ships `stdout`/`stderr` to Cloud Logging.

If the application prints **JSON per line**, Cloud Logging typically renders it under `jsonPayload`.
If the application prints plain text, it appears under `textPayload`.

#### 6.1.1 Gen2 log resource type (common confusion)

For Cloud Run Functions gen2, application logs commonly appear under:
- `resource.type="cloud_run_revision"`
- `resource.labels.service_name="<function_name>"`

Quick query template:

```bash
gcloud logging read \
  'resource.type="cloud_run_revision"
   resource.labels.service_name="'"${FUNCTION_NAME}"'"' \
  --project "${PROJECT_ID}" \
  --limit 50 \
  --freshness 30m
```

### 6.2 Logs and event names differ by component and step types

Different components (and even different step types in the same component) can emit different log events.

Therefore:
- The agent must not assume the presence of specific event names.
- The agent must first scan code for event naming conventions (e.g., look for a stable `event` key).

### 6.3 Firestore-triggered smoke is human-driven by default

The agent cannot safely create a valid Firestore document for an unknown schema.

Human must provide:
- the exact Firestore path to write (collection + document ID)
- a minimal JSON document that should trigger processing
- which field to update to “poke” it (update) and trigger the event
- expected outcomes (which fields should change; which artifacts should appear)

### 6.4 Paid API quota safety

If the service uses a paid external API:
- Default `SMOKE_VERIFY_MODE=safe_no_quota` must not consume paid requests.
- `SMOKE_VERIFY_MODE=real_one_image` must be explicitly approved and must be designed to consume at most one paid request.

---

## 7) Human-in-the-middle checkpoints (explicit)

### 7.1 Runtime assets are unclear

If the agent cannot determine whether the function reads non-code files at runtime:
Human must confirm:
- which exact files are required at runtime
- where they live in the repo
- whether `.gcloudignore` includes them

### 7.2 Firestore DB creation / region mismatch

If Firestore DB does not exist in `${REGION}`:
Human must:
1) Create a Firestore database in that region (or select an existing one).
2) Provide its database ID for `FIRESTORE_DB`.
3) Paste the output of:

```bash
gcloud firestore databases list --project "${PROJECT_ID}" --format="table(name,locationId,type)"
```

### 7.3 Optional smoke verification

If smoke verification is requested:
- Human must set `APPROVE_SMOKE_VERIFY=true`.
- Human must approve any action that writes to Firestore / GCS or consumes paid API quota.

---

## 8) Troubleshooting (when something fails)

### 8.1 Cloud Build fails: Artifact Registry permission denied

Symptoms:
- `artifactregistry.repositories.downloadArtifacts` denied
- build fails when trying to access `gcf-artifacts`

Cause:
- the **build identity** (not the runtime SA) lacks permissions on Artifact Registry.

Step 1: find build identity for this function:

```bash
gcloud functions describe "${FUNCTION_NAME}" \
  --gen2 \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --format="value(buildConfig.serviceAccount)"
```

Step 2: grant it reader+writer on `gcf-artifacts`:

```bash
gcloud artifacts repositories add-iam-policy-binding gcf-artifacts \
  --location "${REGION}" \
  --project "${PROJECT_ID}" \
  --member="serviceAccount:<BUILD_IDENTITY_EMAIL>" \
  --role="roles/artifactregistry.reader"

gcloud artifacts repositories add-iam-policy-binding gcf-artifacts \
  --location "${REGION}" \
  --project "${PROJECT_ID}" \
  --member="serviceAccount:<BUILD_IDENTITY_EMAIL>" \
  --role="roles/artifactregistry.writer"
```

If the agent cannot access build logs or cannot identify build identity:
- human-in-the-middle required: paste the Cloud Build error lines and the build URL.

### 8.2 Deploy fails: “Provided source directory does not have file [main.py]”

Cause:
- Python runtime for Cloud Run Functions gen2 expects `main.py` in the uploaded source root.

Fix:
- Add `main.py` under `SOURCE_DIR` and ensure it exposes/imports the entry function.

### 8.3 Runtime errors: missing required env var / config errors

Cause:
- required env vars were not set.

Fix:
- provide `ENV_VARS` (and/or `SECRET_ENV_VARS`) explicitly
- ensure update deploy preserves required values (Section 5.1)

### 8.4 Eventarc delivery returns 403 (Firestore trigger)

Cause:
- the Eventarc trigger identity cannot invoke the Cloud Run service.

Fix:
1) Determine trigger SA:
```bash
gcloud functions describe "${FUNCTION_NAME}" --gen2 --project "${PROJECT_ID}" --region "${REGION}" \
  --format="value(eventTrigger.serviceAccountEmail)"
```
2) Grant invoker:
```bash
gcloud run services add-iam-policy-binding "${FUNCTION_NAME}" --project "${PROJECT_ID}" --region "${REGION}" \
  --member="serviceAccount:<EVENTARC_TRIGGER_SA_EMAIL>" \
  --role="roles/run.invoker"
```

### 8.5 Trigger fires but function ignores the event

Possible causes:
- your handler intentionally filters out irrelevant events
- your Firestore document path pattern does not match the subject you think it matches
- for Firestore CloudEvents, the event payload may omit the document body (`data` may be empty/None); if your handler relies only on `data`, it may incorrectly treat the event as “filtered”. Prefer extracting the document path (or `runId`) from the CloudEvent subject and fetching the document from Firestore.

Human-in-the-middle:
- provide the event ID and the function logs around that time.

### 8.6 `gcloud functions deploy` crashes (agent environment instability)

Symptom examples:
- `AttributeError: 'NoneType' object has no attribute 'dockerRepository'`
- other unexpected Python exceptions inside `gcloud`, especially mid-deploy

Cause:
- unstable/broken `gcloud` installation in the agent environment

Fix:
- retry deploy from a known-good environment (recommended: Cloud Shell) or update `gcloud`
- do not assume the failure is due to config until you have a stable deploy run

Human-in-the-middle:
- provide the full crash stack trace from the agent environment
- confirm whether a Cloud Build job was created (and share its build URL if present)

### 8.7 Deploy request appears to “hang” or times out locally

This can happen when the local execution environment imposes time limits on long-running commands.
The GCP operation may still continue in the background even if the local command times out.

Fix:
1) Re-check the function state:
```bash
gcloud functions describe "${FUNCTION_NAME}" --gen2 --project "${PROJECT_ID}" --region "${REGION}" \
  --format="value(state,serviceConfig.revision,updateTime)"
```
2) If build is still running, check the latest build logs (human-in-the-middle may be needed):
```bash
gcloud builds list --region "${REGION}" --project "${PROJECT_ID}" --limit 3
```
3) If deploy is not progressing, rerun the deploy command once (do not spam retries).

### 8.8 Existing Cloud Run service name conflicts

In some projects a Cloud Run service with the same name may already exist (created manually or by another system).
This can create confusing behavior for Cloud Functions gen2, because gen2 is backed by Cloud Run.

Symptoms:
- deploy fails with errors referencing Cloud Run service/revisions
- function appears deployed but traffic/logs do not match expected code

Agent-safe options (prefer least destructive):
1) Rename the function (use a new `FUNCTION_NAME`) for a clean deploy.
2) If you must reuse the same name, human-in-the-middle is required to decide whether deleting the existing Cloud Run service is safe.

Human-in-the-middle checklist:
- confirm whether the existing Cloud Run service is managed by Cloud Functions
- confirm deletion is acceptable
- provide:
```bash
gcloud run services describe "${FUNCTION_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format="yaml(metadata)"
```

---

## 9) Notes for agents (to avoid “first try” regressions)

1) Prefer explicit deploy flags over relying on defaults.
2) Do not add secrets unless needed.
3) IAM must be conditional; do not request roles for services not used by the function.
4) For Firestore triggers, region alignment matters (Firestore DB region must match function/trigger region).
5) `.gcloudignore` controls upload; ensure runtime-required files are included.
6) Smoke verification is opt-in and may be expensive; do not run it without explicit approval.
7) Firestore/Eventarc delivery is at-least-once. Your system must be idempotent.
8) If the function writes back to the same Firestore document that triggers it, expect multiple trigger invocations for a single logical run (one per write). This is normal; later invocations should typically be safe no-ops.
9) If `gcloud functions deploy` returns `unable to queue the operation`, wait briefly (e.g., ~20s) and retry once.
10) Prefer `--env-vars-file` only if the project already uses a reviewed env file workflow; otherwise keep env vars inline and explicit in the deploy request block.
