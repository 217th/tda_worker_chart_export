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
- Invariant: for every logical request (`inputs.requests[*]`) produce exactly one of:
  - `ChartsOutputsManifest.items[]` entry (success), or
  - `ChartsOutputsManifest.failures[]` entry with an `error.code` (failure).
  No “silent drops”.
- References:
  - `docs-worker-chart-export/spec/implementation_contract.md` §8 (error model), §12.2 (mock/record + CHART_API_MOCK_MISSING), §13 (Chart-IMG v2)
  - `docs-worker-chart-export/chart-img-docs/API Documentation.htm` (`POST /v2/tradingview/advanced-chart`)

## Planned Scenarios (TDD)

### Scenario 1: Real mode success (HTTP 200)

**Prerequisites**
- `CHARTS_API_MODE=real` with valid account credentials.
- Requires human-in-the-middle: YES (real external API)

**Steps**
1) Send a valid request to Chart‑IMG.

**Expected result**
- PNG bytes returned and recorded as a successful manifest item.

### Scenario 2: HTTP 200 but body is not PNG → CHART_API_FAILED

**Prerequisites**
- HTTP 200 response with non-PNG body or unexpected `Content-Type`.
- Requires human-in-the-middle: NO (use fixture or stubbed response)

**Steps**
1) Execute the request and inspect response headers/body.

**Expected result**
- The request is recorded in `manifest.failures[]` with `error.code = "CHART_API_FAILED"`.

### Scenario 3: Mock mode success (fixture hit, deterministic key)

**Prerequisites**
- `CHARTS_API_MODE=mock` and fixture exists for the request key.
- Requires human-in-the-middle: NO

**Steps**
1) Build the fixture key using:
   - provider `chart-img`
   - endpoint `advanced-chart-v2`
   - `symbol` normalized with `:` → `_` (e.g., `BINANCE:BTCUSDT` → `BINANCE_BTCUSDT`)
   - `timeframe`
   - `chartTemplateId`
2) Load the PNG fixture from:
   - `docs-worker-chart-export/fixtures/chart-api/chart-img/advanced-chart-v2/`
   - filename format: `<SYMBOL>__<TIMEFRAME>__<CHART_TEMPLATE_ID>.png`

**Expected result**
- A manifest item is produced without any external HTTP call.

### Scenario 4: Mock mode missing fixture → CHART_API_MOCK_MISSING

**Prerequisites**
- `CHARTS_API_MODE=mock` and fixture is absent.
- Requires human-in-the-middle: NO

**Steps**
1) Attempt to resolve the fixture.

**Expected result**
- Request is recorded in `manifest.failures[]` with `error.code = "CHART_API_MOCK_MISSING"` and a structured log event is emitted.

### Scenario 5: Mock mode is guaranteed no‑network

**Prerequisites**
- `CHARTS_API_MODE=mock` with HTTP client instrumented to fail on any network call.
- Requires human-in-the-middle: NO

**Steps**
1) Run a mock-mode request with a fixture.

**Expected result**
- No HTTP call is attempted (test fails if a network call happens).

### Scenario 6: Record mode saves fixtures

**Prerequisites**
- `CHARTS_API_MODE=record` and valid credentials.
- Requires human-in-the-middle: YES (real external API)

**Steps**
1) Send a request to Chart‑IMG.

**Expected result**
- PNG response is saved under the fixtures path and returned for the current run.

### Scenario 7: Record mode is not allowed in prod

**Prerequisites**
- `env=prod` and `CHARTS_API_MODE=record`.
- Requires human-in-the-middle: NO

**Steps**
1) Load config/start worker in prod mode with record enabled.

**Expected result**
- Service refuses to start (config validation error) with a clear message that record mode is disallowed in prod.

### Scenario 8: Non‑retriable 4xx → CHART_API_FAILED

**Prerequisites**
- A request that produces a 4xx response (non‑limit).
- Requires human-in-the-middle: NO (use fixture or stubbed response)

**Steps**
1) Execute request and parse error response.

**Expected result**
- Request is recorded in `manifest.failures[]` with `error.code = "CHART_API_FAILED"` and no retries are attempted.

### Scenario 9: Retriable 5xx/timeout → bounded retries then failure

**Prerequisites**
- A request that produces a 5xx/timeout response.
- Requires human-in-the-middle: NO (use fixture or stubbed response)

**Steps**
1) Execute request and apply retry policy.

**Expected result**
- Retries are attempted up to the limit; if still failing, the request is recorded with `error.code = "CHART_API_FAILED"`.

### Scenario 10: Bounded retries across accounts (max total attempts)

**Prerequisites**
- Multiple accounts available; retriable errors simulated.
- Requires human-in-the-middle: NO

**Steps**
1) Execute a request that triggers retriable errors.
2) Track the number of attempts across accounts.

**Expected result**
- Total attempts per logical request are capped (e.g., max 3 total attempts across all accounts) with exponential backoff.
- 429 responses trigger a switch to another account (if available).

### Scenario 11: 429 / Limit Exceeded → account exhaustion flow

**Prerequisites**
- Response indicates 429/Limit Exceeded for the selected account.
- Requires human-in-the-middle: NO (use fixture or stubbed response)

**Steps**
1) Execute request and receive 429/Limit Exceeded.

**Expected result**
- Request failure is recorded as `CHART_API_LIMIT_EXCEEDED`; account is marked exhausted and selection switches to another account if available.

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
