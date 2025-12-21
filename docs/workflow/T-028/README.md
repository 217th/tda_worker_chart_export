# T-028: Finalize MVP

## Summary

- Update .gitignore with standard Python paths and MVP housekeeping patterns.

## Goal

- Ensure common Python artifacts and project-specific scratch paths are ignored by Git.

## Scope

- Add standard Python ignore entries.
- Add/normalize: `/docs-*`, `import-firestore*`, `/tmp`.
- Replace real GCP identifiers in `docs/workflow/*` with placeholders.

## References

- `.gitignore`

## Plan

1) Update `.gitignore` with required patterns.
2) Replace real GCP identifiers in `docs/workflow/*` with placeholders.
3) Validate there are no unintended deletions or overlaps with existing rules.

## Planned Scenarios (TDD)

### Scenario 1: Python artifacts ignored

**Prerequisites**
- None.

**Steps**
1) Inspect `.gitignore` for standard Python patterns.

**Expected result**
- Python cache/build/test artifacts are covered.

### Scenario 2: Project scratch paths ignored

**Prerequisites**
- None.

**Steps**
1) Inspect `.gitignore` for `/docs-*`, `import-firestore*`, and `/tmp`.

**Expected result**
- All requested patterns are present and normalized.

### Scenario 3: No real GCP identifiers in docs/workflow

**Prerequisites**
- None.

**Steps**
1) Scan `docs/workflow/*` for real project/bucket/db/region identifiers.

**Expected result**
- All real identifiers replaced by placeholders (e.g., `YOUR_PROJECT_ID`, `YOUR_FIRESTORE_DB`).

## Risks

- Overly broad patterns could hide unintended files (reviewed manually).

## Verify Steps

- Manual review of `.gitignore` entry list.

## Rollback Plan

- Revert the commit.
