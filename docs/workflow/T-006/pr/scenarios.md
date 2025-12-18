# T-006 — Implemented Scenarios

References:
- Spec: `docs-worker-chart-export/spec/implementation_contract.md` (§11.1, §13.4–13.5, §14.4)
- GCP logging: `docs-gcp/runbook/prod_runbook_gcp.md` (§8)

---

## 1) Missing usage doc → initialize and use account

**Scenario**
- If `chart_img_accounts_usage/{accountId}` does not exist, it is created/reset and incremented.

**Implemented in**
- `worker_chart_export/usage.py:1` (`select_account_for_request`)

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from datetime import datetime, timezone
   from worker_chart_export.config import ChartImgAccount
   from worker_chart_export.usage import select_account_for_request

   class Client:
       def __init__(self):
           self.store = {}
       def collection(self, name):
           self._name = name
           return self
       def document(self, doc_id):
           self._doc_id = doc_id
           return self
       def get(self, transaction=None):
           class Snap:
               def __init__(self, data): self._data = data
               def to_dict(self): return self._data
           return Snap(self.store.get(self._name, {}).get(self._doc_id))
       def update(self, update_data):
           col = self.store.setdefault(self._name, {})
           doc = col.setdefault(self._doc_id, {})
           for k, v in update_data.items():
               doc[k] = v
       def set(self, data, merge=True):
           col = self.store.setdefault(self._name, {})
           doc = col.setdefault(self._doc_id, {})
           if merge:
               doc.update(data)
           else:
               col[self._doc_id] = data
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

**Expected result**
- Output includes `acc1 1`.

---

## 2) UTC window reset (windowStart yesterday)

**Scenario**
- If `windowStart` is yesterday, it resets to today and increments.

**Implemented in**
- `worker_chart_export/usage.py:1`

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
   ```bash
   python - << 'PY'
   from datetime import datetime, timedelta, timezone
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
       def update(self, update_data):
           doc = self.store[self._name][self._doc_id]
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
   account = ChartImgAccount(id="acc1", api_key="k1", daily_limit=3)
   now = datetime(2025,12,18,12,0,0,tzinfo=timezone.utc)
   result = select_account_for_request(client=client, accounts=[account], now=now)
   print(result.account.id, client.store["chart_img_accounts_usage"]["acc1"]["usageToday"], client.store["chart_img_accounts_usage"]["acc1"]["windowStart"])
   PY
   ```

**Expected result**
- Output includes `acc1 1 2025-12-18T00:00:00Z`.

---

## 3) Account order is deterministic

**Scenario**
- Accounts are selected in the order of `CHART_IMG_ACCOUNTS_JSON`.

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
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

**Expected result**
- Output: `acc1`.

---

## 4) Account at limit → skip account

**Scenario**
- If `usageToday >= dailyLimit`, account is skipped.

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
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

**Expected result**
- Output: `acc2`.

---

## 5) All accounts exhausted → no HTTP and log event

**Scenario**
- When all accounts are exhausted, no selection is made and an event is logged with `exhaustedAccounts`.

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
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

**Expected result**
- Output: `None`
- Logs include `event="chart_api_limit_exceeded"` with `error.code="CHART_API_LIMIT_EXCEEDED"` and `exhaustedAccounts=["acc1","acc2"]`.

---

## 6) 429/Limit Exceeded → exhaust account

**Scenario**
- Account is marked as exhausted for the current window (`usageToday=dailyLimit`).

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
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

**Expected result**
- Output: `3 3`

---

## 7) usageToday counts attempts (pre-increment)

**Scenario**
- Increment happens before the HTTP call, so usage counts attempts.

**Manual test**

**Prerequisites**
- Python 3.13.

**Steps**
1) Run:
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

**Expected result**
- Output: `1`
