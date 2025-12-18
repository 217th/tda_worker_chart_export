# T-006: Account selection + usage accounting (chart_img_accounts_usage)

## Summary

- Implement account selection and per-account daily usage tracking in Firestore `chart_img_accounts_usage/{accountId}`.

## Goal

- Respect provider limits (e.g. ~44 req/day per key) while supporting multiple Chart‑IMG accounts with bounded retries and clear observability.

## Scope

- Transactional usage algorithm (UTC day window reset + `usageToday` increment before HTTP call).
- Handle 429/Limit Exceeded by exhausting the account for the current window and switching accounts.
- Global exhaustion emits a structured `CHART_API_LIMIT_EXCEEDED` event listing exhausted `accountId`s.
- References:
  - `docs-worker-chart-export/spec/implementation_contract.md` §11.1 (accounts config), §13.4–13.5 (limits + error classification), §14.4 (persistent usage accounting)
  - `docs-gcp/runbook/prod_runbook_gcp.md` §1.1 (collections), §8 (logging fields)

## Planned Scenarios (TDD)

### Scenario 1: Missing usage doc → initialize and use account

**Prerequisites**
- `chart_img_accounts_usage/{accountId}` does not exist.
- Requires human-in-the-middle: NO

**Steps**
1) Attempt to select the account within a transaction.

**Expected result**
- Usage doc is created/reset with `usageToday = 0`, then incremented before the HTTP call.
- No `VALIDATION_FAILED` is emitted.

### Scenario 2: UTC window reset (windowStart yesterday)

**Prerequisites**
- Usage doc exists with `windowStart` set to yesterday (UTC).
- Requires human-in-the-middle: NO

**Steps**
1) Attempt to select the account within a transaction.

**Expected result**
- The window is reset (`usageToday = 0`, `windowStart = today`), then incremented for the current attempt.

### Scenario 3: Account order is deterministic

**Prerequisites**
- Multiple accounts listed in `CHART_IMG_ACCOUNTS_JSON`.
- Requires human-in-the-middle: NO

**Steps**
1) Run selection across accounts with identical usage states.

**Expected result**
- Account selection follows the order in `CHART_IMG_ACCOUNTS_JSON` deterministically.

### Scenario 4: Account at limit → skip account

**Prerequisites**
- `usageToday >= dailyLimit` for an account.
- Requires human-in-the-middle: NO

**Steps**
1) Run selection across accounts in priority order.

**Expected result**
- The exhausted account is skipped; next eligible account is selected.

### Scenario 5: All accounts exhausted → fail logical request without HTTP or increments

**Prerequisites**
- For all accounts, `usageToday >= dailyLimit`.
- Requires human-in-the-middle: NO

**Steps**
1) Run selection across accounts.

**Expected result**
- No HTTP call is made and no further usage increments occur; request is recorded in `manifest.failures[]` with `error.code = "CHART_API_LIMIT_EXCEEDED"`.
- A structured log event is emitted listing `exhaustedAccounts`.

### Scenario 6: 429/Limit Exceeded → exhaust current account

**Prerequisites**
- Selected account receives a 429/Limit Exceeded response.
- Requires human-in-the-middle: NO

**Steps**
1) Handle the response and update usage.

**Expected result**
- Account is marked exhausted for the current window (set `usageToday = dailyLimit`, not `dailyLimit+1`), and selection retries with another account if available.

### Scenario 7: usageToday counts attempts (pre-increment semantics)

**Prerequisites**
- A successful or failed API call after pre-increment.
- Requires human-in-the-middle: NO

**Steps**
1) Select an account and perform a request.

**Expected result**
- `usageToday` reflects attempts (increment occurs before the HTTP call, regardless of eventual success).

## Risks

- Incorrect transaction logic can double-count or exceed limits; keep updates transactional and unit-test edge cases.

## Verify Steps

- Unit tests for window reset, limit checks, and account switching on 429.

## Rollback Plan

- Revert the commit; usage docs remain and can be manually adjusted if needed.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- `docs/workflow/T-006/README.md`
- `docs/workflow/T-006/pr/diffstat.txt`
- `docs/workflow/T-006/pr/meta.json`
- `docs/workflow/T-006/pr/scenarios.md`
- `docs/workflow/T-006/pr/verify.log`
- `docs/workflow/T-006/pr/verify_scenarios_report.md`
- `tests/tasks/T-006/test_usage.py`
- `worker_chart_export/config.py`
- `worker_chart_export/usage.py`
<!-- END AUTO SUMMARY -->
