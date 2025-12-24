# Lessons Learned (worker-chart-export specific)

This document intentionally keeps **worker-chart-export-specific** lessons that are *not* universal deployment guidance.

For the universal Cloud Run Functions gen2 deployment playbook (first deploy vs update deploy, triggers, IAM, troubleshooting), use:
- `docs/workflow/cloud_run_functions_gen2_deploy_first_try.md`

---

## A) runId format matters (manifest schema validation)

This component validates outputs against a JSON schema that includes a strict `runId` pattern.

If the `runId` does not match the expected regex, the step can fail with `VALIDATION_FAILED` even if some upstream work succeeded.

Practical guidance:
- Generate `runId` values that follow the agreed contract for this system.
- When creating test runs manually, avoid ad-hoc IDs; use the canonical format.

---

## B) Missing chart template should surface the real root cause

If `inputs.requests[]` references a `chartTemplateId` that does not exist in `chart_templates/{chartTemplateId}`:
- The component should record a per-request failure for that request with a specific error message like “Chart template not found”.
- Avoid collapsing the entire situation into a generic message like “minImages not satisfied” if all requests failed for a concrete reason.

Why this matters:
- Operators can fix the underlying misconfiguration faster if the error message is specific.

---

## C) GCS bucket misconfiguration should be clearly distinguishable

If the bucket configured via env vars is invalid (typo, missing bucket, wrong project) or runtime SA lacks required permissions:
- PNG and/or manifest writes can fail.
- For this component, ensure failures map to clear worker-level error codes:
  - `GCS_WRITE_FAILED` (PNG write)
  - `MANIFEST_WRITE_FAILED` (manifest write)

This scenario is useful as a negative test to validate that:
- GCS wiring is correct.
- error reporting is actionable.

---

## D) Secret Manager misconfiguration fails fast

If `CHART_IMG_ACCOUNTS_JSON` (from Secret Manager) is present but not a valid JSON array:
- The service fails fast at config load time (before step execution).

Expected behavior:
- No chart requests should be executed.
- No artifacts should be written.
- Logs should include a clear `config_error` signal (and a stack trace in stderr).

---

## E) Cloud Run / Firestore-triggered execution does not accept CLI-like step overrides

This component supports explicit `--step-id` in the **CLI**.

In Cloud Run Functions gen2, execution is driven by Firestore events:
- The handler selects READY steps deterministically.
- A “CLI-style invalid stepId” scenario is therefore not directly reproducible in Cloud Run.

Operator implication:
- If you want to test “invalid stepId” behavior, do it via CLI.
- For Cloud Run, the equivalent negative case is typically “no READY steps” → no-op.
