# Lessons Learned: Cloud Functions Gen2 Deploy (worker-chart-export)

## Context

This document captures the issues we hit and the fixes that led to a successful
deploy of `worker-chart-export` to Cloud Functions (gen2) in `europe-west4`.

## Key outcomes

- Deploy succeeded after aligning Eventarc filters with Firestore provider
  requirements, granting correct IAM roles, and sanitizing the source bundle
  with `.gcloudignore`.
- Firestore trigger works for a **non-default** database in `europe-west4`.

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
