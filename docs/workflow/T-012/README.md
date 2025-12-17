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
