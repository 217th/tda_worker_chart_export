# T-031 Refine gen2 deploy playbook

## Summary
Refine `docs/workflow/cloud_run_functions_gen2_deploy_first_try.md` so it can be reused for other components and so deploy works on the first attempt.

## Goals

- Split guidance into:
  1) first-time deploy (bootstrap + validations)
  2) update deploy (minimal checks; full checks only on errors)
- Make `ENTRY_POINT` and build service account handling agent-driven.
- Explain Firestore Eventarc trigger filters and when to use each.
- Make secrets and IAM conditional on the services actually used by the function.
- Add human-in-the-middle instructions when the agent cannot uniquely diagnose an issue.
- Keep it a single file, English, unambiguous.

## Verify

- Read `docs/workflow/cloud_run_functions_gen2_deploy_first_try.md` and confirm:
  - Clearly split: first deploy vs update deploy.
  - `ENTRY_POINT` is agent-derived (not human-supplied).
  - Firestore trigger filters explained (type/database/namespace/document path pattern).
  - Secrets and IAM are explicitly conditional on used services.
  - Smoke verification is opt-in only.
  - No real GCP identifiers are hardcoded (placeholders only).
