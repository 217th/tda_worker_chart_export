import copy
import logging
import unittest
from datetime import datetime, timedelta, timezone
from typing import Any

from worker_chart_export.config import ChartImgAccount
from worker_chart_export.usage import mark_account_exhausted, select_account_for_request


class FakeFirestoreClient:
    def __init__(self, store: dict[str, dict[str, Any]] | None = None) -> None:
        self._store: dict[str, dict[str, Any]] = copy.deepcopy(store or {})

    def collection(self, name: str) -> "FakeCollectionRef":
        return FakeCollectionRef(self, name)

    def transaction(self) -> "FakeTransaction":
        return FakeTransaction(self)


class FakeCollectionRef:
    def __init__(self, client: FakeFirestoreClient, name: str) -> None:
        self._client = client
        self._name = name

    def document(self, doc_id: str) -> "FakeDocumentRef":
        return FakeDocumentRef(self._client, self._name, doc_id)


class FakeDocumentRef:
    def __init__(self, client: FakeFirestoreClient, collection: str, doc_id: str) -> None:
        self._client = client
        self._collection = collection
        self._doc_id = doc_id

    def get(self, transaction: Any | None = None) -> "FakeDocumentSnapshot":
        _ = transaction
        data = self._client._store.get(self._collection, {}).get(self._doc_id)
        return FakeDocumentSnapshot(data)

    def update(self, update_data: dict[str, Any]) -> None:
        collection = self._client._store.setdefault(self._collection, {})
        doc = collection.setdefault(self._doc_id, {})
        _apply_update(doc, update_data)

    def set(self, data: dict[str, Any], merge: bool = True) -> None:
        collection = self._client._store.setdefault(self._collection, {})
        doc = collection.setdefault(self._doc_id, {})
        if merge:
            _apply_update(doc, data)
        else:
            collection[self._doc_id] = copy.deepcopy(data)


class FakeDocumentSnapshot:
    def __init__(self, data: dict[str, Any] | None) -> None:
        self._data = copy.deepcopy(data) if data is not None else None

    def to_dict(self) -> dict[str, Any] | None:
        return copy.deepcopy(self._data) if self._data is not None else None


class FakeTransaction:
    def __init__(self, client: FakeFirestoreClient) -> None:
        self._client = client
        self._updates: list[tuple[FakeDocumentRef, dict[str, Any], str, bool]] = []

    def update(self, doc_ref: FakeDocumentRef, update_data: dict[str, Any]) -> None:
        self._updates.append((doc_ref, update_data, "update", False))

    def set(self, doc_ref: FakeDocumentRef, data: dict[str, Any], merge: bool = True) -> None:
        self._updates.append((doc_ref, data, "set", merge))

    def commit(self) -> None:
        for doc_ref, data, kind, merge in self._updates:
            if kind == "set":
                doc_ref.set(data, merge=merge)
            else:
                doc_ref.update(data)
        self._updates.clear()


def _apply_update(doc: dict[str, Any], update_data: dict[str, Any]) -> None:
    for path, value in update_data.items():
        parts = path.split(".")
        current = doc
        for part in parts[:-1]:
            next_obj = current.get(part)
            if not isinstance(next_obj, dict):
                next_obj = {}
                current[part] = next_obj
            current = next_obj
        current[parts[-1]] = value


class _CaptureHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        payload = record.msg
        if isinstance(payload, dict):
            self.records.append(payload)
        else:
            self.records.append({"message": record.getMessage()})


class TestAccountUsage(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2025, 12, 18, 12, 0, 0, tzinfo=timezone.utc)
        self.account_a = ChartImgAccount(id="acc1", api_key="k1", daily_limit=3)
        self.account_b = ChartImgAccount(id="acc2", api_key="k2", daily_limit=3)

    def test_missing_usage_doc_initializes_and_increments(self) -> None:
        client = FakeFirestoreClient()
        result = select_account_for_request(
            client=client,
            accounts=[self.account_a],
            now=self.now,
        )
        self.assertIsNotNone(result.account)
        usage = client._store["chart_img_accounts_usage"]["acc1"]
        self.assertEqual(usage["usageToday"], 1)
        self.assertTrue(usage["windowStart"].startswith("2025-12-18T00:00:00"))

    def test_window_reset_when_yesterday(self) -> None:
        yesterday = (self.now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        client = FakeFirestoreClient(
            {
                "chart_img_accounts_usage": {
                    "acc1": {
                        "usageToday": 2,
                        "windowStart": yesterday.isoformat().replace("+00:00", "Z"),
                    }
                }
            }
        )
        result = select_account_for_request(
            client=client,
            accounts=[self.account_a],
            now=self.now,
        )
        usage = client._store["chart_img_accounts_usage"]["acc1"]
        self.assertEqual(usage["usageToday"], 1)
        self.assertTrue(usage["windowStart"].startswith("2025-12-18T00:00:00"))
        self.assertEqual(result.account.id, "acc1")

    def test_account_order_is_deterministic(self) -> None:
        client = FakeFirestoreClient()
        result = select_account_for_request(
            client=client,
            accounts=[self.account_a, self.account_b],
            now=self.now,
        )
        self.assertEqual(result.account.id, "acc1")

    def test_account_at_limit_is_skipped(self) -> None:
        client = FakeFirestoreClient(
            {
                "chart_img_accounts_usage": {
                    "acc1": {"usageToday": 3, "windowStart": "2025-12-18T00:00:00Z"},
                    "acc2": {"usageToday": 1, "windowStart": "2025-12-18T00:00:00Z"},
                }
            }
        )
        result = select_account_for_request(
            client=client,
            accounts=[self.account_a, self.account_b],
            now=self.now,
        )
        self.assertEqual(result.account.id, "acc2")
        self.assertEqual(client._store["chart_img_accounts_usage"]["acc1"]["usageToday"], 3)

    def test_all_accounts_exhausted_logs_event(self) -> None:
        client = FakeFirestoreClient(
            {
                "chart_img_accounts_usage": {
                    "acc1": {"usageToday": 3, "windowStart": "2025-12-18T00:00:00Z"},
                    "acc2": {"usageToday": 3, "windowStart": "2025-12-18T00:00:00Z"},
                }
            }
        )
        logger = logging.getLogger("worker-chart-export")
        handler = _CaptureHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        try:
            result = select_account_for_request(
                client=client,
                accounts=[self.account_a, self.account_b],
                now=self.now,
                logger=logger,
                log_context={"runId": "run-1", "stepId": "stepA"},
            )
        finally:
            logger.removeHandler(handler)
        self.assertIsNone(result.account)
        self.assertEqual(result.exhausted_accounts, ["acc1", "acc2"])
        events = [payload for payload in handler.records if payload.get("event") == "chart_api_limit_exceeded"]
        self.assertTrue(events)
        self.assertEqual(events[0].get("error", {}).get("code"), "CHART_API_LIMIT_EXCEEDED")

    def test_mark_account_exhausted_sets_limit(self) -> None:
        client = FakeFirestoreClient(
            {
                "chart_img_accounts_usage": {
                    "acc1": {"usageToday": 2, "windowStart": "2025-12-18T00:00:00Z"},
                }
            }
        )
        usage = mark_account_exhausted(client=client, account=self.account_a, now=self.now)
        self.assertEqual(usage.usage_today, 3)
        self.assertEqual(client._store["chart_img_accounts_usage"]["acc1"]["usageToday"], 3)

    def test_usage_counts_attempts_pre_increment(self) -> None:
        client = FakeFirestoreClient(
            {
                "chart_img_accounts_usage": {
                    "acc1": {"usageToday": 0, "windowStart": "2025-12-18T00:00:00Z"},
                }
            }
        )
        result = select_account_for_request(
            client=client,
            accounts=[self.account_a],
            now=self.now,
        )
        self.assertIsNotNone(result.account)
        usage = client._store["chart_img_accounts_usage"]["acc1"]
        self.assertEqual(usage["usageToday"], 1)


if __name__ == "__main__":
    unittest.main()
