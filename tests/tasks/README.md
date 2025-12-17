# QA tests layout

This repository keeps automated tests **per task** under:

- `tests/tasks/T-###/`

Rationale:
- tasks are atomic; tests should accumulate in a way that makes it obvious what feature they cover
- full regression should always be runnable after any task

Notes:
- Task directories use `T-###` naming (with a hyphen). Python's `unittest` discovery cannot import packages with hyphens, so the canonical runner is:
  - `bash scripts/qa/run_all.sh`
  - (or) `python scripts/qa/run_all.py`

