# T-008 — Scenarios Verification Report

Date: 2025-12-18  
Branch: `task/T-008/gcs-manifest`

Source checklist: `docs/workflow/T-008/pr/scenarios.md`

---

## Environment / prerequisites

**Prerequisites (as stated in scenarios)**
- Local Python environment.
- `jsonschema` installed in a local venv for schema validation.

**Actions performed**
- Created venv: `python -m venv .venv`
- Installed dependency: `.venv/bin/pip install jsonschema`
- Ran automated tests:
  - `.venv/bin/python scripts/qa/run_all.py --task T-008`

**Observed**
- All T‑008 automated tests passed (see `docs/workflow/T-008/pr/verify.log`).

---

## Scenario 1) Successful PNG + manifest write

**Command(s) executed**
```bash
.venv/bin/python scripts/qa/run_all.py --task T-008
```

**Observed result**
- PASS (see tests for path building + schema validation).

**Fixes (if any)**
- None.

---

## Scenario 2) Partial GCS failure (one PNG fails, others succeed)

**Command(s) executed**
```bash
.venv/bin/python scripts/qa/run_all.py --task T-008
```

**Observed result**
- PASS (failure recorded as `GCS_WRITE_FAILED` while other items succeed).

**Fixes (if any)**
- None.

---

## Scenario 3) PNG upload failure → GCS_WRITE_FAILED

**Command(s) executed**
```bash
.venv/bin/python scripts/qa/run_all.py --task T-008
```

**Observed result**
- PASS.

**Fixes (if any)**
- None.

---

## Scenario 4) Manifest write failure → MANIFEST_WRITE_FAILED

**Command(s) executed**
```bash
.venv/bin/python scripts/qa/run_all.py --task T-008
```

**Observed result**
- PASS.

**Fixes (if any)**
- None.

---

## Scenario 5) Manifest schema validation fails → VALIDATION_FAILED

**Command(s) executed**
```bash
.venv/bin/python scripts/qa/run_all.py --task T-008
```

**Observed result**
- PASS (invalid manifest triggers `VALIDATION_FAILED`).

**Fixes (if any)**
- None.

---

## Scenario 6) Worker does not write signed_url / expires_at

**Command(s) executed**
```bash
.venv/bin/python scripts/qa/run_all.py --task T-008
```

**Observed result**
- PASS (fields absent in items).

**Fixes (if any)**
- None.

---

## Scenario 7) Retry overwrites manifest but keeps old PNGs

**Command(s) executed**
```bash
.venv/bin/python scripts/qa/run_all.py --task T-008
```

**Observed result**
- PASS (manifest path stable and overwrite safe).

**Fixes (if any)**
- None.

---

## Human-in-the-middle required scenarios

- None (all scenarios executed locally via fake uploader + schema validation).
