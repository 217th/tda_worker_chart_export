# T-031 Review Notes

## Summary
- Refines the universal Cloud Run Functions gen2 deploy playbook for first-try deploys.
- Folds practical lessons learned from real deployments.

## Key Decisions
- ENV vars: prefer `--env-vars-file` via `ENV_VARS_MODE=file` to avoid comma/JSON parsing issues.
- Explicit separation of `RUNTIME_SA_EMAIL` and `TRIGGER_SA_EMAIL`.
- Update deploy must not change trigger config without explicit confirmation.

## Handoff Notes
- None.
