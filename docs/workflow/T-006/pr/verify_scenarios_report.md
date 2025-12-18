# T-006 — Scenarios Verification Report

Date: 2025-12-18  
Branch: `task/T-006/usage-accounts`

Source checklist: `docs/workflow/T-006/README.md`

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
python3 scripts/qa/run_all.py --task T-006
```

**Result**
- Exit code: `0`
- Tests executed: 7
- Status: **PASS**

---

## Scenario coverage (auto)

| Scenario (README) | Coverage | Test(s) |
| --- | --- | --- |
| 1) Missing usage doc → initialize and use account | Auto | `tests/tasks/T-006/test_usage.py::test_missing_usage_doc_initializes_and_increments` |
| 2) UTC window reset | Auto | `tests/tasks/T-006/test_usage.py::test_window_reset_when_yesterday` |
| 3) Account order is deterministic | Auto | `tests/tasks/T-006/test_usage.py::test_account_order_is_deterministic` |
| 4) Account at limit → skip account | Auto | `tests/tasks/T-006/test_usage.py::test_account_at_limit_is_skipped` |
| 5) All accounts exhausted → log event | Auto | `tests/tasks/T-006/test_usage.py::test_all_accounts_exhausted_logs_event` |
| 6) 429/Limit Exceeded → exhaust account | Auto | `tests/tasks/T-006/test_usage.py::test_mark_account_exhausted_sets_limit` |
| 7) usageToday counts attempts | Auto | `tests/tasks/T-006/test_usage.py::test_usage_counts_attempts_pre_increment` |

---

## Manual scenario checks (executed)

### Scenario 1) Missing usage doc

**Command**
```bash
python - << 'PY'
from datetime import datetime, timezone
from worker_chart_export.config import ChartImgAccount
from worker_chart_export.usage import select_account_for_request

class Client:
    def __init__(self): self.store = {}
    def collection(self, name): self._name = name; return self
    def document(self, doc_id): self._doc_id = doc_id; return self
    def get(self, transaction=None):
        class Snap:
            def __init__(self, data): self._data = data
            def to_dict(self): return self._data
        return Snap(self.store.get(self._name, {}).get(self._doc_id))
    def update(self, update_data):
        col = self.store.setdefault(self._name, {})
        doc = col.setdefault(self._doc_id, {})
        for k, v in update_data.items(): doc[k] = v
    def set(self, data, merge=True):
        col = self.store.setdefault(self._name, {})
        doc = col.setdefault(self._doc_id, {})
        if merge: doc.update(data)
        else: col[self._doc_id] = data
    def transaction(self):
        class Tx:
            def __init__(self, ref): self.ref = ref; self._updates = []
            def update(self, doc_ref, update_data): self._updates.append(("update", update_data))
            def set(self, doc_ref, data, merge=True): self._updates.append(("set", data))
            def commit(self):
                for kind, data in self._updates:
                    if kind == "set": self.ref.set(data, merge=True)
                    else: self.ref.update(data)
        return Tx(self)

client = Client()
account = ChartImgAccount(id="acc1", api_key="k1", daily_limit=3)
result = select_account_for_request(client=client, accounts=[account], now=datetime(2025,12,18,12,0,0,tzinfo=timezone.utc))
print(result.account.id, client.store["chart_img_accounts_usage"]["acc1"]["usageToday"])
PY
```

**Result**
- Output: `acc1 1`

### Scenario 2) UTC window reset

**Command**
```bash
python - << 'PY'
from datetime import datetime, timezone
from worker_chart_export.config import ChartImgAccount
from worker_chart_export.usage import select_account_for_request

class Client:
    def __init__(self):
        self.store = {"chart_img_accounts_usage": {"acc1": {"usageToday": 2, "windowStart": "2025-12-17T00:00:00Z"}}}
    def collection(self, name): self._name = name; return self
    def document(self, doc_id): self._doc_id = doc_id; return self
    def get(self, transaction=None):
        class Snap:
            def __init__(self, data): self._data = data
            def to_dict(self): return self._data
        return Snap(self.store.get(self._name, {}).get(self._doc_id))
    def update(self, update_data): self.store[self._name][self._doc_id].update(update_data)
    def set(self, data, merge=True): self.update(data)
    def transaction(self):
        class Tx:
            def __init__(self, ref): self.ref = ref; self._updates = []
            def update(self, doc_ref, update_data): self._updates.append(update_data)
            def set(self, doc_ref, data, merge=True): self._updates.append(data)
            def commit(self):
                for update_data in self._updates: self.ref.update(update_data)
        return Tx(self)

client = Client()
account = ChartImgAccount(id="acc1", api_key="k1", daily_limit=3)
now = datetime(2025,12,18,12,0,0,tzinfo=timezone.utc)
result = select_account_for_request(client=client, accounts=[account], now=now)
print(result.account.id, client.store["chart_img_accounts_usage"]["acc1"]["usageToday"], client.store["chart_img_accounts_usage"]["acc1"]["windowStart"])
PY
```

**Result**
- Output: `acc1 1 2025-12-18T00:00:00Z`

### Scenario 3) Deterministic account order

**Command**
```bash
python - << 'PY'
from datetime import datetime, timezone
from worker_chart_export.config import ChartImgAccount
from worker_chart_export.usage import select_account_for_request

class Client:
    def __init__(self): self.store = {}
    def collection(self, name): self._name = name; return self
    def document(self, doc_id): self._doc_id = doc_id; return self
    def get(self, transaction=None):
        class Snap:
            def __init__(self, data): self._data = data
            def to_dict(self): return self._data
        return Snap(self.store.get(self._name, {}).get(self._doc_id))
    def update(self, update_data):
        col = self.store.setdefault(self._name, {})
        doc = col.setdefault(self._doc_id, {})
        doc.update(update_data)
    def set(self, data, merge=True): self.update(data)
    def transaction(self):
        class Tx:
            def __init__(self, ref): self.ref = ref; self._updates = []
            def update(self, doc_ref, update_data): self._updates.append(update_data)
            def set(self, doc_ref, data, merge=True): self._updates.append(data)
            def commit(self):
                for update_data in self._updates: self.ref.update(update_data)
        return Tx(self)

client = Client()
acc1 = ChartImgAccount(id="acc1", api_key="k1", daily_limit=3)
acc2 = ChartImgAccount(id="acc2", api_key="k2", daily_limit=3)
result = select_account_for_request(client=client, accounts=[acc1, acc2], now=datetime(2025,12,18,12,0,0,tzinfo=timezone.utc))
print(result.account.id)
PY
```

**Result**
- Output: `acc1`

### Scenario 4) Skip account at limit

**Command**
```bash
python - << 'PY'
from datetime import datetime, timezone
from worker_chart_export.config import ChartImgAccount
from worker_chart_export.usage import select_account_for_request

class Client:
    def __init__(self):
        self.store = {"chart_img_accounts_usage": {"acc1": {"usageToday": 3, "windowStart": "2025-12-18T00:00:00Z"}, "acc2": {"usageToday": 1, "windowStart": "2025-12-18T00:00:00Z"}}}
    def collection(self, name): self._name = name; return self
    def document(self, doc_id): self._doc_id = doc_id; return self
    def get(self, transaction=None):
        class Snap:
            def __init__(self, data): self._data = data
            def to_dict(self): return self._data
        return Snap(self.store[self._name].get(self._doc_id))
    def update(self, update_data): self.store[self._name][self._doc_id].update(update_data)
    def set(self, data, merge=True): self.update(data)
    def transaction(self):
        class Tx:
            def __init__(self, ref): self.ref = ref; self._updates = []
            def update(self, doc_ref, update_data): self._updates.append(update_data)
            def set(self, doc_ref, data, merge=True): self._updates.append(data)
            def commit(self):
                for update_data in self._updates: self.ref.update(update_data)
        return Tx(self)

client = Client()
acc1 = ChartImgAccount(id="acc1", api_key="k1", daily_limit=3)
acc2 = ChartImgAccount(id="acc2", api_key="k2", daily_limit=3)
result = select_account_for_request(client=client, accounts=[acc1, acc2], now=datetime(2025,12,18,12,0,0,tzinfo=timezone.utc))
print(result.account.id)
PY
```

**Result**
- Output: `acc2`

### Scenario 5) All accounts exhausted

**Command**
```bash
python - << 'PY'
import logging
from datetime import datetime, timezone
from worker_chart_export.config import ChartImgAccount
from worker_chart_export.usage import select_account_for_request

class Client:
    def __init__(self):
        self.store = {"chart_img_accounts_usage": {"acc1": {"usageToday": 3, "windowStart": "2025-12-18T00:00:00Z"}, "acc2": {"usageToday": 3, "windowStart": "2025-12-18T00:00:00Z"}}}
    def collection(self, name): self._name = name; return self
    def document(self, doc_id): self._doc_id = doc_id; return self
    def get(self, transaction=None):
        class Snap:
            def __init__(self, data): self._data = data
            def to_dict(self): return self._data
        return Snap(self.store[self._name].get(self._doc_id))
    def update(self, update_data): self.store[self._name][self._doc_id].update(update_data)
    def set(self, data, merge=True): self.update(data)
    def transaction(self):
        class Tx:
            def __init__(self, ref): self.ref = ref; self._updates = []
            def update(self, doc_ref, update_data): self._updates.append(update_data)
            def set(self, doc_ref, data, merge=True): self._updates.append(data)
            def commit(self):
                for update_data in self._updates: self.ref.update(update_data)
        return Tx(self)

logger = logging.getLogger("worker-chart-export")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

client = Client()
acc1 = ChartImgAccount(id="acc1", api_key="k1", daily_limit=3)
acc2 = ChartImgAccount(id="acc2", api_key="k2", daily_limit=3)
result = select_account_for_request(client=client, accounts=[acc1, acc2], now=datetime(2025,12,18,12,0,0,tzinfo=timezone.utc), logger=logger, log_context={"runId": "run-1", "stepId": "stepA"})
print(result.account)
PY
```

**Result**
- Output includes `None`.
- Log includes event `chart_api_limit_exceeded` with `error.code="CHART_API_LIMIT_EXCEEDED"` and `exhaustedAccounts=["acc1","acc2"]`.

### Scenario 6) Mark account exhausted on 429

**Command**
```bash
python - << 'PY'
from datetime import datetime, timezone
from worker_chart_export.config import ChartImgAccount
from worker_chart_export.usage import mark_account_exhausted

class Client:
    def __init__(self):
        self.store = {"chart_img_accounts_usage": {"acc1": {"usageToday": 2, "windowStart": "2025-12-18T00:00:00Z"}}}
    def collection(self, name): self._name = name; return self
    def document(self, doc_id): self._doc_id = doc_id; return self
    def get(self, transaction=None):
        class Snap:
            def __init__(self, data): self._data = data
            def to_dict(self): return self._data
        return Snap(self.store[self._name].get(self._doc_id))
    def update(self, update_data): self.store[self._name][self._doc_id].update(update_data)
    def set(self, data, merge=True): self.update(data)
    def transaction(self):
        class Tx:
            def __init__(self, ref): self.ref = ref; self._updates = []
            def update(self, doc_ref, update_data): self._updates.append(update_data)
            def set(self, doc_ref, data, merge=True): self._updates.append(data)
            def commit(self):
                for update_data in self._updates: self.ref.update(update_data)
        return Tx(self)

client = Client()
acc1 = ChartImgAccount(id="acc1", api_key="k1", daily_limit=3)
usage = mark_account_exhausted(client=client, account=acc1, now=datetime(2025,12,18,12,0,0,tzinfo=timezone.utc))
print(usage.usage_today, client.store["chart_img_accounts_usage"]["acc1"]["usageToday"])
PY
```

**Result**
- Output: `3 3`

### Scenario 7) usageToday counts attempts

**Command**
```bash
python - << 'PY'
from datetime import datetime, timezone
from worker_chart_export.config import ChartImgAccount
from worker_chart_export.usage import select_account_for_request

class Client:
    def __init__(self):
        self.store = {"chart_img_accounts_usage": {"acc1": {"usageToday": 0, "windowStart": "2025-12-18T00:00:00Z"}}}
    def collection(self, name): self._name = name; return self
    def document(self, doc_id): self._doc_id = doc_id; return self
    def get(self, transaction=None):
        class Snap:
            def __init__(self, data): self._data = data
            def to_dict(self): return self._data
        return Snap(self.store[self._name].get(self._doc_id))
    def update(self, update_data): self.store[self._name][self._doc_id].update(update_data)
    def set(self, data, merge=True): self.update(data)
    def transaction(self):
        class Tx:
            def __init__(self, ref): self.ref = ref; self._updates = []
            def update(self, doc_ref, update_data): self._updates.append(update_data)
            def set(self, doc_ref, data, merge=True): self._updates.append(data)
            def commit(self):
                for update_data in self._updates: self.ref.update(update_data)
        return Tx(self)

client = Client()
acc1 = ChartImgAccount(id="acc1", api_key="k1", daily_limit=3)
select_account_for_request(client=client, accounts=[acc1], now=datetime(2025,12,18,12,0,0,tzinfo=timezone.utc))
print(client.store["chart_img_accounts_usage"]["acc1"]["usageToday"])
PY
```

**Result**
- Output: `1`
