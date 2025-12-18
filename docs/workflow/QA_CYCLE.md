# QA cycle (mandatory after each task)

This repository uses an explicit QA cycle for **every** task `T-###`.

Deliverables live under each task's PR artifact folder:
- `docs/workflow/T-###/pr/scenarios.md`
- `docs/workflow/T-###/pr/verify_scenarios_report.md`

Automated tests accumulate under:
- `tests/tasks/T-###/`

## Pre-dev requirement (TDD)

Before implementation starts, every task README **must** define **Planned Scenarios (TDD)**:
- Put them in `docs/workflow/T-###/README.md`.
- For each scenario, include: prerequisites / steps / expected result.
- These scenarios are the source of truth for development; if scope changes, update them first.
- Template: `docs/workflow/_templates/task_readme.md`.

## The 4-step QA cycle

1) **List implemented scenarios**
   - For the current task, list the concrete runnable scenarios that were implemented.
   - Explicitly mark limitations/stubs/unsupported modes.

2) **Manual tests (human-verifiable)**
   - For each scenario, provide: prerequisites / steps / expected result.
   - If the scenario needs a human in the loop (GCP project, IAM, secrets, real external APIs, local server, etc.), explicitly mark:
     - `Requires human-in-the-middle: YES`
     - and provide exact steps.

3) **Automated tests/scripts**
   - Add tests under `tests/tasks/T-###/` that reproduce the manual checks where feasible.
   - If an older test becomes outdated due to an agreed spec change, update it (do not silently delete coverage).

4) **Verification report**
   - Record what was actually executed, with commands and results.
   - Include any fixes that were required to make tests pass.
   - If something could not be executed without a human, record it with the reason and the steps for a human run.

## Regression rule

After any task, it must be possible to run the full bundle of automated tests to prevent regressions.

Canonical command:
- `bash scripts/qa/run_all.sh`

## Notes on `T-###` directory naming

Task directories use a hyphen (e.g. `T-002`). This is not a valid Python package name, so standard `unittest discover` cannot always import nested paths directly.

Use the repository runner:
- `python scripts/qa/run_all.py`
