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

## Risks

- Incorrect transaction logic can double-count or exceed limits; keep updates transactional and unit-test edge cases.

## Verify Steps

- Unit tests for window reset, limit checks, and account switching on 429.

## Rollback Plan

- Revert the commit; usage docs remain and can be manually adjusted if needed.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
