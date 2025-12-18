# T-012: Prod-like GCP scenario + deploy scripts/runbook

## Summary

- Provide deploy scripts and a prod-like verification runbook for a dev/staging GCP project.

## Goal

- Make it straightforward to deploy, seed required Firestore collections, run a smoke scenario, and roll back safely.

## Scope

- gcloud deploy instructions for Cloud Run Functions (gen2): `concurrency=1`, timeouts, runtime SA, Secret Manager env wiring.
- Seed scripts/instructions for `chart_templates` and `chart_img_accounts_usage`.
- Manual verification steps that do not run in CI by default.
- References:
  - `docs-gcp/runbook/prod_runbook_gcp.md` §1–§4 (resources/IAM/triggers), §6–§7 (pre/post deploy checks)
  - `docs-worker-chart-export/spec/implementation_contract.md` §10 (logging events), §11 (secrets), §14.4 (usage docs)

## Planned Scenarios (TDD)

### Scenario 1: Python 3.13 deploy strategy (runtime vs container)

**Prerequisites**
- GCP project access with Cloud Run Functions (gen2).
- Requires human-in-the-middle: YES

**Steps**
1) Verify whether Python 3.13 is supported as a native runtime for gen2.
2) If not supported, deploy via container (build/push + deploy).

**Expected result**
- A documented, tested deploy path for Python 3.13 is established (runtime or container), with explicit commands.

### Scenario 2: Deploy Cloud Run function with required config

**Prerequisites**
- Access to a dev/staging GCP project with required IAM.
- Requires human-in-the-middle: YES

**Steps**
1) Run the deployment script (or documented gcloud commands).
2) Configure env vars and Secret Manager bindings.

**Expected result**
- Service deploys successfully with correct runtime, concurrency, and trigger configuration.

### Scenario 3: Eventarc trigger correctness (flow_runs update only)

**Prerequisites**
- Eventarc trigger configured for Firestore.
- Requires human-in-the-middle: YES

**Steps**
1) Configure Eventarc filters for updates on `flow_runs/{runId}`.
2) Trigger a non-update or different collection event.
3) Trigger a valid update on `flow_runs/{runId}`.

**Expected result**
- Only the intended update event invokes the worker.
- Retries are enabled only for idempotent behavior (no duplicate work on retry).

### Scenario 4: IAM + Secret Manager wiring

**Prerequisites**
- Runtime service account configured.
- Secret `chart-img-accounts` (or equivalent) exists in Secret Manager.
- Requires human-in-the-middle: YES

**Steps**
1) Grant runtime SA access to Firestore, GCS, and Secret Manager.
2) Deploy with `CHART_IMG_ACCOUNTS_JSON` sourced from Secret Manager.
3) Verify the worker reads the secret at runtime.

**Expected result**
- Runtime SA has minimal required roles.
- `CHART_IMG_ACCOUNTS_JSON` is loaded from Secret Manager (not hardcoded).

### Scenario 5: Public bucket access (no signed URLs)

**Prerequisites**
- GCS bucket created for artifacts.
- Requires human-in-the-middle: YES

**Steps**
1) Configure bucket for public read access (as per MVP requirement).
2) Run a worker execution that writes PNG + manifest.

**Expected result**
- Objects are readable via public access; worker does not emit signed URLs.

### Scenario 6: Seed Firestore collections

**Prerequisites**
- Access to Firestore in the target project.
- Requires human-in-the-middle: YES

**Steps**
1) Run the seed script or follow the runbook to create `chart_templates` and `chart_img_accounts_usage` docs.

**Expected result**
- Templates and usage docs exist and match expected schema.

### Scenario 7: Prod-like smoke run

**Prerequisites**
- Deployed service, seeded data, configured GCS bucket.
- Requires human-in-the-middle: YES

**Steps**
1) Create/update a flow_run with a READY `CHART_EXPORT` step.
2) Observe logs and GCS outputs.

**Expected result**
- Step transitions to SUCCEEDED/FAILED per rules; manifest and PNGs appear in GCS; logs include required structured events.

### Scenario 8: Rollback procedure

**Prerequisites**
- A previous revision available for rollback.
- Requires human-in-the-middle: YES

**Steps**
1) Roll back to the previous revision and re-run a smoke check.

**Expected result**
- Previous revision is serving; trigger behaves as expected.

## Risks

- Environment drift (IAM, buckets, triggers) causing hard-to-debug failures; include explicit pre/post checks and rollback steps.

## Verify Steps

- Follow the documented dev/staging smoke scenario end-to-end.

## Rollback Plan

- Redeploy previous function revision; disable trigger if needed.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
