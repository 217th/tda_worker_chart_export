# T-005 — Implemented Scenarios

References:
- Spec: `docs-worker-chart-export/spec/implementation_contract.md` (§4, §6, §14)
- Templates: `docs-worker-chart-export/chart-templates/README.md`

---

## 1) Valid template builds a Chart‑IMG request

**Scenario**
- Valid template and flow inputs build a Chart‑IMG request with injected `symbol` and `interval`.

**Implemented in**
- `worker_chart_export/templates.py:1` (`build_chart_requests`)

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from worker_chart_export.templates import build_chart_requests

   class Store:
       def get(self, chart_template_id):
           return {
               "id": chart_template_id,
               "description": "Price + Volume",
               "chartImgSymbolTemplate": "BINANCE:{symbol}",
               "request": {"theme": "dark", "style": "baseline"},
           }

   result = build_chart_requests(
       requests=[{"chartTemplateId": "ctpl_ok"}],
       scope_symbol="BTCUSDT",
       timeframe="1h",
       default_timezone="UTC",
       template_store=Store(),
       min_images=1,
   )
   item = result.items[0]
   print(item.request["symbol"], item.request["interval"], item.kind)
   PY
   ```

**Expected result**
- Printed: `BINANCE:BTCUSDT 1h Price + Volume`.

---

## 2) Template contains symbol/interval/timezone → overridden

**Scenario**
- Template-defined `symbol`/`interval`/`timezone` are overwritten by flow/config values.

**Implemented in**
- `worker_chart_export/templates.py:1`

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from worker_chart_export.templates import build_chart_requests

   class Store:
       def get(self, chart_template_id):
           return {
               "id": chart_template_id,
               "description": "Override",
               "chartImgSymbolTemplate": "BYBIT:{symbol}.P",
               "request": {"symbol": "X", "interval": "99m", "timezone": "Europe/Paris"},
           }

   result = build_chart_requests(
       requests=[{"chartTemplateId": "ctpl_override"}],
       scope_symbol="ETHUSDT",
       timeframe="4h",
       default_timezone="UTC",
       template_store=Store(),
   )
   item = result.items[0]
   print(item.request["symbol"], item.request["interval"], item.request["timezone"])
   PY
   ```

**Expected result**
- Printed: `BYBIT:ETHUSDT.P 4h UTC`.

---

## 3) Missing template → validation failure

**Scenario**
- Missing Firestore template yields a per-request `VALIDATION_FAILED` failure.

**Implemented in**
- `worker_chart_export/templates.py:1`

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from worker_chart_export.templates import build_chart_requests

   class Store:
       def get(self, chart_template_id):
           return None

   result = build_chart_requests(
       requests=[{"chartTemplateId": "missing"}],
       scope_symbol="BTCUSDT",
       timeframe="1h",
       default_timezone="UTC",
       template_store=Store(),
   )
   print(result.failures[0].error.code)
   PY
   ```

**Expected result**
- Printed: `VALIDATION_FAILED`.

---

## 4) Invalid template schema → validation failure

**Scenario**
- Template missing required fields yields a per-request `VALIDATION_FAILED`.

**Implemented in**
- `worker_chart_export/templates.py:1` (`parse_chart_template`)

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from worker_chart_export.templates import build_chart_requests

   class Store:
       def get(self, chart_template_id):
           return {"id": chart_template_id, "description": "Bad"}

   result = build_chart_requests(
       requests=[{"chartTemplateId": "bad"}],
       scope_symbol="BTCUSDT",
       timeframe="1h",
       default_timezone="UTC",
       template_store=Store(),
   )
   print(result.failures[0].error.code)
   PY
   ```

**Expected result**
- Printed: `VALIDATION_FAILED`.

---

## 5) Partial success across multiple requests

**Scenario**
- One request succeeds and another fails; both are recorded.

**Implemented in**
- `worker_chart_export/templates.py:1`

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from worker_chart_export.templates import build_chart_requests

   class Store:
       def get(self, chart_template_id):
           if chart_template_id == "ctpl_ok":
               return {
                   "id": chart_template_id,
                   "description": "Ok",
                   "chartImgSymbolTemplate": "BINANCE:{symbol}",
                   "request": {},
               }
           return None

   result = build_chart_requests(
       requests=[{"chartTemplateId": "ctpl_ok"}, {"chartTemplateId": "missing"}],
       scope_symbol="BTCUSDT",
       timeframe="1d",
       default_timezone="UTC",
       template_store=Store(),
       min_images=1,
   )
   print(len(result.items), len(result.failures))
   PY
   ```

**Expected result**
- Printed: `1 1`.

---

## 6) Duplicate chartTemplateId in requests → validation failure

**Scenario**
- Duplicate `chartTemplateId` values are rejected to avoid PNG name collisions.

**Implemented in**
- `worker_chart_export/templates.py:1` (`validate_requests`)

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from worker_chart_export.templates import build_chart_requests

   class Store:
       def get(self, chart_template_id):
           return {
               "id": chart_template_id,
               "description": "Dup",
               "chartImgSymbolTemplate": "BINANCE:{symbol}",
               "request": {},
           }

   result = build_chart_requests(
       requests=[{"chartTemplateId": "dup"}, {"chartTemplateId": "dup"}],
       scope_symbol="BTCUSDT",
       timeframe="1h",
       default_timezone="UTC",
       template_store=Store(),
       min_images=1,
   )
   print(result.validation_error.code)
   PY
   ```

**Expected result**
- Printed: `VALIDATION_FAILED`.

---

## 7) minImages > len(requests) → validation failure

**Scenario**
- `minImages` cannot exceed the number of requests.

**Implemented in**
- `worker_chart_export/templates.py:1` (`validate_requests`)

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from worker_chart_export.templates import build_chart_requests

   class Store:
       def get(self, chart_template_id):
           return {
               "id": chart_template_id,
               "description": "Ok",
               "chartImgSymbolTemplate": "BINANCE:{symbol}",
               "request": {},
           }

   result = build_chart_requests(
       requests=[{"chartTemplateId": "ctpl_ok"}],
       scope_symbol="BTCUSDT",
       timeframe="1h",
       default_timezone="UTC",
       template_store=Store(),
       min_images=2,
   )
   print(result.validation_error.code)
   PY
   ```

**Expected result**
- Printed: `VALIDATION_FAILED`.

---

## 8) Description contains spaces/+ → preserved in kind

**Scenario**
- Template description is used verbatim as manifest `kind`.

**Implemented in**
- `worker_chart_export/templates.py:1`

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from worker_chart_export.templates import build_chart_requests

   class Store:
       def get(self, chart_template_id):
           return {
               "id": chart_template_id,
               "description": "Price + Volume",
               "chartImgSymbolTemplate": "BINANCE:{symbol}",
               "request": {},
           }

   result = build_chart_requests(
       requests=[{"chartTemplateId": "ctpl_kind"}],
       scope_symbol="BTCUSDT",
       timeframe="1h",
       default_timezone="UTC",
       template_store=Store(),
   )
   print(result.items[0].kind)
   PY
   ```

**Expected result**
- Printed: `Price + Volume`.
