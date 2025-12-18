# T-007 — Implemented Scenarios (task-level)

Planned scenarios source:
- `docs/workflow/T-007/README.md` → **Planned Scenarios (TDD)**

References:
- `docs-worker-chart-export/spec/implementation_contract.md` §12.2, §13.1–13.5
- `docs-worker-chart-export/chart-img-docs/API Documentation.htm` (POST `/v2/tradingview/advanced-chart`)

---

## 1) Real mode success (HTTP 200)

**Scenario**
- Real Chart‑IMG request returns PNG.

**Implemented in**
- `worker_chart_export/chart_img.py`

**Limitations / stubs**
- Requires real Chart‑IMG credentials and network.

### Manual test

**Prerequisites**
- Valid Chart‑IMG account in `CHART_IMG_ACCOUNTS_JSON`
- `CHARTS_API_MODE=real`
- Requires human-in-the-middle: YES

**Steps**
1) Run the worker with a real Chart‑IMG request.

**Expected result**
- `ChartApiResult.ok = True` and PNG bytes returned.

---

## 2) HTTP 200 but body is not PNG → CHART_API_FAILED

**Scenario**
- HTTP status 200 with non‑PNG body is classified as `CHART_API_FAILED`.

**Implemented in**
- `worker_chart_export/chart_img.py`
- `tests/tasks/T-007/test_chart_img_client.py`

**Limitations / stubs**
- None.

### Manual test

**Prerequisites**
- Local Python environment.
- Requires human-in-the-middle: NO

**Steps**
1) Use a stubbed HTTP response with status 200 and non‑PNG bytes.

**Expected result**
- `ChartApiResult.ok = False`, `error.code = "CHART_API_FAILED"`.

---

## 3) Mock mode success (fixture hit, deterministic key)

**Scenario**
- Mock mode resolves a PNG fixture via deterministic key.

**Implemented in**
- `worker_chart_export/chart_img.py`
- `tests/tasks/T-007/test_chart_img_client.py`

**Limitations / stubs**
- Requires local fixture file.

### Manual test

**Prerequisites**
- Create PNG fixture under `docs-worker-chart-export/fixtures/chart-api/chart-img/advanced-chart-v2/`
- Requires human-in-the-middle: NO

**Steps**
1) Place `<SYMBOL>__<TIMEFRAME>__<CHART_TEMPLATE_ID>.png` in fixtures dir.
2) Run mock mode request.

**Expected result**
- `ChartApiResult.ok = True`, `from_fixture = True`.

---

## 4) Mock mode missing fixture → CHART_API_MOCK_MISSING

**Scenario**
- Missing fixture results in `CHART_API_MOCK_MISSING` without network calls.

**Implemented in**
- `worker_chart_export/chart_img.py`
- `tests/tasks/T-007/test_chart_img_client.py`

**Limitations / stubs**
- None.

### Manual test

**Prerequisites**
- No fixture file present.
- Requires human-in-the-middle: NO

**Steps**
1) Run mock mode request without fixture.

**Expected result**
- `ChartApiResult.ok = False`, `error.code = "CHART_API_MOCK_MISSING"`.

---

## 5) Mock mode guaranteed no‑network

**Scenario**
- Mock mode must not attempt HTTP requests.

**Implemented in**
- `worker_chart_export/chart_img.py`
- `tests/tasks/T-007/test_chart_img_client.py`

**Limitations / stubs**
- None.

### Manual test

**Prerequisites**
- Instrument HTTP client to raise if called.
- Requires human-in-the-middle: NO

**Steps**
1) Run mock mode with a valid fixture.

**Expected result**
- No HTTP call is made.

---

## 6) Record mode saves fixtures

**Scenario**
- Record mode persists PNG/JSON fixtures after real API calls.

**Implemented in**
- `worker_chart_export/chart_img.py`
- `tests/tasks/T-007/test_chart_img_client.py` (stubbed)

**Limitations / stubs**
- Real API call requires human-in-the-middle.

### Manual test

**Prerequisites**
- `CHARTS_API_MODE=record`
- Valid Chart‑IMG credentials
- Requires human-in-the-middle: YES

**Steps**
1) Run record mode request.

**Expected result**
- PNG/JSON fixture saved under fixtures path.

---

## 7) Record mode is not allowed in prod

**Scenario**
- `CHARTS_API_MODE=record` with `env=prod` should fail configuration.

**Implemented in**
- `worker_chart_export/config.py`
- `tests/tasks/T-007/test_chart_img_client.py`

**Limitations / stubs**
- None.

### Manual test

**Prerequisites**
- `TDA_ENV=prod` and `CHARTS_API_MODE=record`
- Requires human-in-the-middle: NO

**Steps**
1) Call `WorkerConfig.from_env()` with prod env.

**Expected result**
- `ConfigError` raised.

---

## 8) Non‑retriable 4xx → CHART_API_FAILED

**Scenario**
- 4xx errors are classified as `CHART_API_FAILED` and non‑retriable.

**Implemented in**
- `worker_chart_export/chart_img.py`
- `tests/tasks/T-007/test_chart_img_client.py`

**Limitations / stubs**
- None.

### Manual test

**Prerequisites**
- Stubbed HTTP response (e.g. 400).
- Requires human-in-the-middle: NO

**Steps**
1) Run request with HTTP 400 JSON error.

**Expected result**
- `error.code = "CHART_API_FAILED"`, `retriable = False`.

---

## 9) Retriable 5xx/timeout → bounded retries then failure

**Scenario**
- 5xx is retriable and bounded retry logic is applied by caller.

**Implemented in**
- `worker_chart_export/chart_img.py`
- `tests/tasks/T-007/test_chart_img_client.py`

**Limitations / stubs**
- Timeout path uses stubbed network error.

### Manual test

**Prerequisites**
- Stubbed HTTP response (e.g. 500).
- Requires human-in-the-middle: NO

**Steps**
1) Run request with HTTP 500 response.

**Expected result**
- `error.retriable = True`.

---

## 10) Bounded retries across accounts (max total attempts)

**Scenario**
- Total attempts per logical request are capped; retries can span multiple accounts.

**Implemented in**
- `worker_chart_export/chart_img.py` (`fetch_with_retries`)
- `tests/tasks/T-007/test_chart_img_client.py`

**Limitations / stubs**
- Account selection is stubbed in tests.

### Manual test

**Prerequisites**
- Stubbed HTTP response (5xx).
- Requires human-in-the-middle: NO

**Steps**
1) Execute `fetch_with_retries` with `max_attempts=2`.

**Expected result**
- Exactly 2 HTTP attempts are made.

---

## 11) 429 / Limit Exceeded → account exhaustion flow

**Scenario**
- 429 triggers `CHART_API_LIMIT_EXCEEDED` and account exhaustion switching.

**Implemented in**
- `worker_chart_export/chart_img.py`
- `tests/tasks/T-007/test_chart_img_client.py`

**Limitations / stubs**
- Uses stubbed HTTP responses and stubbed `mark_account_exhausted`.

### Manual test

**Prerequisites**
- Stubbed 429 then 200 response.
- Requires human-in-the-middle: NO

**Steps**
1) Execute `fetch_with_retries` with an account list.

**Expected result**
- First account marked exhausted; next account succeeds.
