# T-007: Chart-IMG client + mock/record fixtures

## Summary

- Implement Chart‑IMG v2 Advanced Chart client plus `real|mock|record` modes with repository fixtures.

## Goal

- Allow reliable local/CI testing without consuming real Chart‑IMG limits while keeping prod behavior faithful.

## Scope

- HTTP client: `POST /v2/tradingview/advanced-chart`, `x-api-key` auth, PNG success vs JSON error parsing.
- Error classification (4xx non-retriable, 5xx/timeouts retriable, 429 triggers account switch).
- Modes: `real|mock|record` (`CHARTS_API_MODE` / CLI flag).
- Fixtures path: `docs-worker-chart-export/fixtures/chart-api/chart-img/advanced-chart-v2`.

## Risks

- CI must not call real Chart‑IMG; enforce defaults and add guardrails in tests/docs.

## Verify Steps

- Unit tests for error classification and fixture resolution (including `CHART_API_MOCK_MISSING`).

## Rollback Plan

- Revert the commit; switch `CHARTS_API_MODE` to `mock` for safety.

## Changes Summary (auto)

<!-- BEGIN AUTO SUMMARY -->
- (no file changes)
<!-- END AUTO SUMMARY -->
