# Lessons Learned: Cloud Functions Gen2 Deploy (worker-chart-export)

## Context

This document captures the issues we hit and the fixes that led to a successful
deploy of `worker-chart-export` to Cloud Functions (gen2) in `europe-west4`.

## Key outcomes

- Deploy succeeded after aligning Eventarc filters with Firestore provider
  requirements, granting correct IAM roles, and sanitizing the source bundle
  with `.gcloudignore`.
- Firestore trigger works for a **non-default** database in `europe-west4`.
- CloudEvent payload for Firestore updates may arrive without `data`; handler
  should fallback to fetching `flow_run` from Firestore by `subject` runId.
- Manifest schema must be bundled with runtime; docs-only paths are excluded
  by `.gcloudignore`.

## Issues and fixes

### 1) Source bundle contained extra directories

**Symptom:** Deploy ZIP included docs, codex-swarm, etc.  
**Fix:** Maintain `.gcloudignore` and exclude non-runtime directories:
- `.codex-swarm/`, `.codex-resume`
- `docs/`, `docs-*`, `tests/`, `scripts/`
- `tasks.json`, `AGENTS.md`, `README.md`

**Lesson:** `gcloud` uses `.gcloudignore` (not `.gitignore`), so add explicit
exclusions there to keep Cloud Function bundles minimal.

### 2) Missing `main.py` for python313 runtime

**Symptom:** `--source` missing required `main.py`.  
**Fix:** Provide `main.py` that exports the entry point:
`worker_chart_export`.

**Lesson:** Gen2 Python runtime still expects `main.py` unless you use a custom
container. Keep `main.py` small and delegate to application entrypoint.

### 3) Eventarc filter validation errors

**Symptom:** `missing required attribute "database"` or database not found.  
**Fix:** Use Eventarc Firestore provider filter format:

```
--trigger-event-filters="type=google.cloud.firestore.document.v1.updated"
--trigger-event-filters="database=tda-db-europe-west4"
--trigger-event-filters="namespace=(default)"
--trigger-event-filters-path-pattern="document=flow_runs/{runId}"
```

**Lesson:** For Firestore triggers:
- `database` is the **DB ID only**, not full resource name.
- `namespace` must be included (`(default)`).
- Use **path-pattern** for the document.

### 4) Eventarc permissions missing

**Symptom:** `Permission "eventarc.events.receiveEvent" denied`.  
**Fix:** Grant `roles/eventarc.eventReceiver` to the runtime SA:

```
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:<RUNTIME_SA>" \
  --role="roles/eventarc.eventReceiver"
```

**Lesson:** Eventarc trigger delivery is blocked without `eventReceiver`.

### 5) Cloud Run invocation permissions missing

**Symptom:** HTTP 403 from Cloud Run on Eventarc delivery.  
**Fix:** Grant `roles/run.invoker` to the Eventarc trigger service account:

```
gcloud run services add-iam-policy-binding worker-chart-export \
  --region=europe-west4 \
  --project <PROJECT_ID> \
  --member="serviceAccount:<RUNTIME_SA>" \
  --role="roles/run.invoker"
```

**Lesson:** Eventarc triggers require Cloud Run invoker permissions.

### 5) Region and DB alignment

**Symptom:** Trigger validation errors when Firestore DB region mismatched.  
**Fix:** Use Firestore DB in the same region as Eventarc trigger:
`europe-west4` in our case.

**Lesson:** Firestore DB, Eventarc trigger region, and Cloud Function region
must be aligned.

### 6) gcloud deploy crash in this environment

**Symptom:** `AttributeError: 'NoneType' object has no attribute 'dockerRepository'`.  
**Fix:** Re-run deploy from a stable `gcloud` installation (or Cloud Shell).

**Lesson:** If `gcloud` crashes mid-deploy, retry from a known-good environment
before debugging the config.

### 7) Firestore event data missing in CloudEvent

**Symptom:** CloudEvent `data` is `None`, causing `event_filtered`.  
**Fix:** Extract `runId` from `subject` and fetch `flow_run` from Firestore.

**Lesson:** CloudEvent payloads may not include document data; avoid relying
solely on `data` for Firestore-triggered flows.

### 8) Manifest schema missing in runtime bundle

**Symptom:** `FileNotFoundError` on manifest schema path in Cloud Run.  
**Fix:** Package schema inside the application (resources) and load from there.

**Lesson:** Anything required at runtime must be bundled; `docs-*` are excluded.

### 9) Manifest validation failure due to runId format

**Symptom:** `VALIDATION_FAILED` with runId regex mismatch.  
**Fix:** Use runId suffix without `_` (only `[a-z0-9]{3,6}`).

**Lesson:** runId format is part of manifest schema validation; invalid runId
will fail the step even if PNG generation succeeds.

### 10) Missing chart template should surface original error

**Symptom:** Missing template produced `VALIDATION_FAILED` with generic
`minImages not satisfied`.
**Fix:** Preserve original failure message (e.g., `Chart template not found`)
when `minImages` fails because all items failed.

**Lesson:** Validation failures should be specific to the root cause to avoid
misleading operators.

### 11) GCS bucket typo causes manifest write failure

**Symptom:** Step fails with `MANIFEST_WRITE_FAILED` and `NotFound` on
`runs/<runId>/steps/<stepId>/charts/manifest.json`.
**Fix:** Ensure `CHARTS_BUCKET` points to an existing bucket and runtime SA
has `storage.objectAdmin`.

**Lesson:** Manifest write failures surface clearly via `MANIFEST_WRITE_FAILED`;
use this scenario to validate GCS wiring.

## Canonical deploy command (post-fixes)

```
gcloud functions deploy worker-chart-export \
  --gen2 \
  --region=europe-west4 \
  --runtime=python313 \
  --source=. \
  --entry-point=worker_chart_export \
  --service-account=tda-worker-chart-export-test@kb-agent-479608.iam.gserviceaccount.com \
  --set-env-vars="ARTIFACTS_BUCKET=tda-artifacts-test,FIRESTORE_DB=tda-db-europe-west4,CHARTS_API_MODE=record" \
  --set-secrets="CHART_IMG_ACCOUNTS_JSON=projects/kb-agent-479608/secrets/chart-img-accounts:latest" \
  --trigger-location=europe-west4 \
  --trigger-event-filters="type=google.cloud.firestore.document.v1.updated" \
  --trigger-event-filters="database=tda-db-europe-west4" \
  --trigger-event-filters="namespace=(default)" \
  --trigger-event-filters-path-pattern="document=flow_runs/{runId}"
```

## Verification checklist

- Cloud Function `worker-chart-export` is ACTIVE.
- Eventarc trigger exists and references the function.
- Firestore update on `flow_runs/{runId}` triggers the function.
- Logs appear in Cloud Logging.
- Artifacts land in `gs://tda-artifacts-test/...`.
