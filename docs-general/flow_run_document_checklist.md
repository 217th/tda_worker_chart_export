# Flow Run Document — Checklist

- Fields: must include `schemaVersion`, `runId`, `flowKey`, `status`, `createdAt`, `trigger`, `scope`, `steps`; optional `updatedAt`, `finishedAt`, `progress`, `error`. См. docs/contracts/schemas/flow_run.schema.json.
- ID formats: `runId = YYYYMMDD-HHmmss_<symbolSlug>_<suffix>`; `stepId` deterministic (`stepType:timeframe:variant`). См. docs/contracts/schemas/flow_run.schema.json.
- Status model: run = PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED; step = PENDING/READY/RUNNING/SUCCEEDED/FAILED/SKIPPED/CANCELLED. См. docs/contracts/orchestration_rules.md.
- Scope: must contain `symbol`; allow extension without breaking existing fields (additionalProperties=true). Document new scope keys.
- Steps map: each entry matches `$defs` per step type, has `dependsOn`, `inputs`, `outputs`, timestamps, `error` (code/message/details).
- Progress: keep `currentStepId` and `stepCounts` consistent after every transition.
- Artifacts: only store GCS URIs, signed URLs + expiry if needed; large payloads live in GCS. См. docs/contracts/README.md.
- Validation: update matching example (`docs/contracts/examples/flow_run.example.json`) and rerun schema validation (AJV).
