# T-005 — Scenarios Verification Report

Date: 2025-12-18  
Branch: `task/T-005/templates-requests`

Source checklist: `docs/workflow/T-005/README.md`

---

## Environment / prerequisites

**Prerequisites (as stated in scenarios)**
- Python 3.13

**Observed environment**
- Python: `3.13.11`

---

## Automated checks executed

**Command**
```bash
python3 scripts/qa/run_all.py --task T-005
```

**Result**
- Exit code: `0`
- Tests executed: 9
- Status: **PASS**

---

## Scenario coverage (auto)

| Scenario (README) | Coverage | Test(s) |
| --- | --- | --- |
| 1) Valid template builds a Chart‑IMG request | Auto | `tests/tasks/T-005/test_templates.py::test_valid_template_builds_request` |
| 2) Template contains symbol/interval/timezone → overridden | Auto | `tests/tasks/T-005/test_templates.py::test_template_overrides_symbol_interval_timezone` |
| 3) Missing template → validation failure | Auto | `tests/tasks/T-005/test_templates.py::test_missing_template_records_failure` |
| 4) Invalid template schema → validation failure | Auto | `tests/tasks/T-005/test_templates.py::test_invalid_template_schema_records_failure` |
| 5) Partial success across multiple requests | Auto | `tests/tasks/T-005/test_templates.py::test_partial_success_across_requests` |
| 6) Duplicate chartTemplateId → validation failure | Auto | `tests/tasks/T-005/test_templates.py::test_duplicate_chart_template_id_is_validation_error` |
| 7) minImages > len(requests) → validation failure | Auto | `tests/tasks/T-005/test_templates.py::test_min_images_greater_than_requests_validation_error` |
| 8) Description contains spaces/+ → preserved in kind | Auto | `tests/tasks/T-005/test_templates.py::test_description_with_spaces_plus_preserved_as_kind` |

---

## Manual scenario checks (executed)

### Scenario 1) Valid template builds request

**Command**
```bash
python - << 'PY'
from worker_chart_export.templates import build_chart_requests
class Store:
    def get(self, chart_template_id):
        return {"id": chart_template_id, "description": "Price + Volume",
                "chartImgSymbolTemplate": "BINANCE:{symbol}",
                "request": {"theme": "dark", "style": "baseline"}}
result = build_chart_requests(requests=[{"chartTemplateId": "ctpl_ok"}],
                              scope_symbol="BTCUSDT", timeframe="1h",
                              default_timezone="UTC", template_store=Store(),
                              min_images=1)
item = result.items[0]
print(item.request["symbol"], item.request["interval"], item.kind)
PY
```

**Result**
- Output: `BINANCE:BTCUSDT 1h Price + Volume`

### Scenario 2) Template overrides symbol/interval/timezone

**Command**
```bash
python - << 'PY'
from worker_chart_export.templates import build_chart_requests
class Store:
    def get(self, chart_template_id):
        return {"id": chart_template_id, "description": "Override",
                "chartImgSymbolTemplate": "BYBIT:{symbol}.P",
                "request": {"symbol": "X", "interval": "99m", "timezone": "Europe/Paris"}}
result = build_chart_requests(requests=[{"chartTemplateId": "ctpl_override"}],
                              scope_symbol="ETHUSDT", timeframe="4h",
                              default_timezone="UTC", template_store=Store())
item = result.items[0]
print(item.request["symbol"], item.request["interval"], item.request["timezone"])
PY
```

**Result**
- Output: `BYBIT:ETHUSDT.P 4h UTC`

### Scenario 3) Missing template → failure

**Command**
```bash
python - << 'PY'
from worker_chart_export.templates import build_chart_requests
class Store:
    def get(self, chart_template_id): return None
result = build_chart_requests(requests=[{"chartTemplateId": "missing"}],
                              scope_symbol="BTCUSDT", timeframe="1h",
                              default_timezone="UTC", template_store=Store())
print(result.failures[0].error.code)
PY
```

**Result**
- Output: `VALIDATION_FAILED`

### Scenario 4) Invalid template schema → failure

**Command**
```bash
python - << 'PY'
from worker_chart_export.templates import build_chart_requests
class Store:
    def get(self, chart_template_id): return {"id": chart_template_id, "description": "Bad"}
result = build_chart_requests(requests=[{"chartTemplateId": "bad"}],
                              scope_symbol="BTCUSDT", timeframe="1h",
                              default_timezone="UTC", template_store=Store())
print(result.failures[0].error.code)
PY
```

**Result**
- Output: `VALIDATION_FAILED`

### Scenario 5) Partial success across requests

**Command**
```bash
python - << 'PY'
from worker_chart_export.templates import build_chart_requests
class Store:
    def get(self, chart_template_id):
        if chart_template_id == "ctpl_ok":
            return {"id": chart_template_id, "description": "Ok",
                    "chartImgSymbolTemplate": "BINANCE:{symbol}", "request": {}}
        return None
result = build_chart_requests(requests=[{"chartTemplateId": "ctpl_ok"}, {"chartTemplateId": "missing"}],
                              scope_symbol="BTCUSDT", timeframe="1d",
                              default_timezone="UTC", template_store=Store(),
                              min_images=1)
print(len(result.items), len(result.failures))
PY
```

**Result**
- Output: `1 1`

### Scenario 6) Duplicate chartTemplateId → validation failure

**Command**
```bash
python - << 'PY'
from worker_chart_export.templates import build_chart_requests
class Store:
    def get(self, chart_template_id):
        return {"id": chart_template_id, "description": "Dup",
                "chartImgSymbolTemplate": "BINANCE:{symbol}", "request": {}}
result = build_chart_requests(requests=[{"chartTemplateId": "dup"}, {"chartTemplateId": "dup"}],
                              scope_symbol="BTCUSDT", timeframe="1h",
                              default_timezone="UTC", template_store=Store(),
                              min_images=1)
print(result.validation_error.code)
PY
```

**Result**
- Output: `VALIDATION_FAILED`

### Scenario 7) minImages > len(requests) → validation failure

**Command**
```bash
python - << 'PY'
from worker_chart_export.templates import build_chart_requests
class Store:
    def get(self, chart_template_id):
        return {"id": chart_template_id, "description": "Ok",
                "chartImgSymbolTemplate": "BINANCE:{symbol}", "request": {}}
result = build_chart_requests(requests=[{"chartTemplateId": "ctpl_ok"}],
                              scope_symbol="BTCUSDT", timeframe="1h",
                              default_timezone="UTC", template_store=Store(),
                              min_images=2)
print(result.validation_error.code)
PY
```

**Result**
- Output: `VALIDATION_FAILED`

### Scenario 8) Description preserved as kind

**Command**
```bash
python - << 'PY'
from worker_chart_export.templates import build_chart_requests
class Store:
    def get(self, chart_template_id):
        return {"id": chart_template_id, "description": "Price + Volume",
                "chartImgSymbolTemplate": "BINANCE:{symbol}", "request": {}}
result = build_chart_requests(requests=[{"chartTemplateId": "ctpl_kind"}],
                              scope_symbol="BTCUSDT", timeframe="1h",
                              default_timezone="UTC", template_store=Store())
print(result.items[0].kind)
PY
```

**Result**
- Output: `Price + Volume`
