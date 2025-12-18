# T-007 — Scenarios Verification Report

Date: 2025-12-18  
Branch: `task/T-007/chart-img-client`

Source checklist: `docs/workflow/T-007/pr/scenarios.md`

---

## Environment / prerequisites

**Prerequisites (as stated in scenarios)**
- Local Python environment.
- Valid Chart‑IMG credentials available via local secrets file.

**Actions performed**
- Ran automated tests:
  - `python scripts/qa/run_all.py --task T-007`
- Ran manual scenario script for non‑human scenarios:
  - `python - <<'PY' ... PY` (see per-scenario notes below)
- Ran real Chart‑IMG calls for Scenarios 1 and 6.

**Observed**
- Automated tests: PASS.
- Manual script checks: PASS for Scenarios 2–5, 7–11.
- Real API checks: PASS for Scenarios 1 and 6 after using `timezone = "Etc/UTC"`.

---

## Scenario 1) Real mode success (HTTP 200)

**Command(s) executed**
```bash
python - <<'PY'
# Real API call; uses chart template + Etc/UTC timezone
# Output: Scenario 1: PASS (http_status=200)
PY
```

**Observed result**
- PASS (HTTP 200, PNG returned).

**Fixes (if any)**
- Initial attempt with `timezone="UTC"` returned HTTP 422:
  - `must be a supported timezone` (Chart‑IMG expects `Etc/UTC`).

---

## Scenario 2) HTTP 200 but body is not PNG → CHART_API_FAILED

**Command(s) executed**
```bash
python - <<'PY'
# See consolidated manual script (Scenario 2 PASS)
PY
```

**Observed result**
- Scenario 2: PASS (manual script output)

**Fixes (if any)**
- None.

---

## Scenario 3) Mock mode success (fixture hit, deterministic key)

**Command(s) executed**
```bash
python - <<'PY'
# See consolidated manual script (Scenario 3 PASS)
PY
```

**Observed result**
- Scenario 3: PASS (manual script output)

**Fixes (if any)**
- None.

---

## Scenario 4) Mock mode missing fixture → CHART_API_MOCK_MISSING

**Command(s) executed**
```bash
python - <<'PY'
# See consolidated manual script (Scenario 4 PASS)
PY
```

**Observed result**
- Scenario 4: PASS (manual script output)

**Fixes (if any)**
- None.

---

## Scenario 5) Mock mode guaranteed no‑network

**Command(s) executed**
```bash
python - <<'PY'
# See consolidated manual script (Scenario 5 PASS)
PY
```

**Observed result**
- Scenario 5: PASS (manual script output)

**Fixes (if any)**
- None.

---

## Scenario 6) Record mode saves fixtures

**Command(s) executed**
```bash
python - <<'PY'
# Record mode; uses chart template + Etc/UTC timezone
# Output: Scenario 6: PASS (fixture created)
PY
```

**Observed result**
- PASS. Fixture created at:
  - `docs-worker-chart-export/fixtures/chart-api/chart-img/advanced-chart-v2/BINANCE_BTCUSDT__1h__ctpl_price_psar_adi_v1.png`

**Fixes (if any)**
- Removed stale error fixture from earlier 422 attempt:
  - `docs-worker-chart-export/fixtures/chart-api/chart-img/advanced-chart-v2/BINANCE_BTCUSDT__1h__ctpl_price_psar_adi_v1__422_CHART_IMG_REQUEST_FAILED.json`

---

## Scenario 7) Record mode is not allowed in prod

**Command(s) executed**
```bash
python - <<'PY'
# See consolidated manual script (Scenario 7 PASS)
PY
```

**Observed result**
- Scenario 7: PASS (manual script output)

**Fixes (if any)**
- None.

---

## Scenario 8) Non‑retriable 4xx → CHART_API_FAILED

**Command(s) executed**
```bash
python - <<'PY'
# See consolidated manual script (Scenario 8 PASS)
PY
```

**Observed result**
- Scenario 8: PASS (manual script output)

**Fixes (if any)**
- None.

---

## Scenario 9) Retriable 5xx/timeout → bounded retries then failure

**Command(s) executed**
```bash
python - <<'PY'
# See consolidated manual script (Scenario 9 PASS)
PY
```

**Observed result**
- Scenario 9: PASS (manual script output)

**Fixes (if any)**
- None.

---

## Scenario 10) Bounded retries across accounts (max total attempts)

**Command(s) executed**
```bash
python - <<'PY'
# See consolidated manual script (Scenario 10 PASS)
PY
```

**Observed result**
- Scenario 10: PASS (manual script output)

**Fixes (if any)**
- None.

---

## Scenario 11) 429 / Limit Exceeded → account exhaustion flow

**Command(s) executed**
```bash
python - <<'PY'
# See consolidated manual script (Scenario 11 PASS)
PY
```

**Observed result**
- Scenario 11: PASS (manual script output)

**Fixes (if any)**
- None.

---

## Human-in-the-middle required scenarios

- Scenario 1 and Scenario 6 executed successfully using real Chart‑IMG credentials.
