# T-029 Honor dependsOn before processing

## Summary
Ensure the worker only starts a `CHART_EXPORT` step when **all** steps listed in `dependsOn` are `SUCCEEDED`. This gate must apply to both CloudEvent-triggered runs and explicit CLI runs.

## Scope

- Add dependency gating before starting work on a step.
- Emit a clear structured log event when a READY step is blocked by unmet dependencies.
- Add tests and QA scenarios for dependency gating behavior.

## Out of scope

- Changing upstream orchestration rules that set step status to `READY`.
- Modifying schema or `dependsOn` structure.

## References

- `docs-worker-chart-export/contracts/flow_run.schema.json` (baseStep.dependsOn)
- `docs-worker-chart-export/spec/implementation_contract.md`
- `worker_chart_export/ingest.py`
- `worker_chart_export/core.py`
- `worker_chart_export/logging.py`

## Scenarios (TDD)

1) **READY step with empty dependsOn**
   - Preconditions: step `status=READY`, `dependsOn=[]`.
   - Expected: step can be selected/started; normal claim flow continues.

2) **READY step with all dependencies SUCCEEDED**
   - Preconditions: step `dependsOn=["stepA","stepB"]`, those steps `SUCCEEDED`.
   - Expected: step can be selected/started.

3) **READY step with any dependency not SUCCEEDED**
   - Preconditions: `dependsOn=["stepA"]`, `stepA` in `PENDING|READY|RUNNING|FAILED|SKIPPED|CANCELLED`.
   - Expected: worker does **not** start this step; no Firestore claim; logs a dependency-blocked event with unmet step ids/statuses.

4) **READY step with dependency missing from steps**
   - Preconditions: `dependsOn=["missingStep"]`, not present in `steps` map.
   - Expected: treated as unmet dependency; worker does not start; logs blocked event.

5) **Multiple READY steps; only one satisfies dependsOn**
   - Preconditions: multiple `READY` steps; only one has all deps `SUCCEEDED`.
   - Expected: picker returns the eligible step; blocked ones ignored.

6) **CLI run-local with explicit step-id and unmet dependsOn**
   - Preconditions: CLI uses `--step-id` for a READY step; deps not all `SUCCEEDED`.
   - Expected: core returns `FAILED` with `VALIDATION_FAILED` (or specific error), no Firestore claim; log indicates dependency block.

## Risks

- If upstream marks steps `READY` early, worker will now no-op more often; ensure logs are clear to aid diagnosis.

## Verify steps

- Unit tests in `tests/tasks/T-029/`.
- QA scenario report in `docs/workflow/T-029/pr/verify.log`.

## Rollback plan

- Revert the commits for T-029.
