import copy
import unittest
from typing import Any

from worker_chart_export.orchestration import (
    StepError,
    build_claim_update,
    build_finalize_failure_update,
    build_finalize_success_update,
    claim_step_transaction,
    finalize_step,
)


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


class FakeDocumentSnapshot:
    def __init__(self, data: dict[str, Any] | None) -> None:
        self._data = copy.deepcopy(data) if data is not None else None

    def to_dict(self) -> dict[str, Any] | None:
        return copy.deepcopy(self._data) if self._data is not None else None


class FakeTransaction:
    def __init__(self, client: FakeFirestoreClient) -> None:
        self._client = client
        self._updates: list[tuple[FakeDocumentRef, dict[str, Any]]] = []

    def update(self, doc_ref: FakeDocumentRef, update_data: dict[str, Any]) -> None:
        self._updates.append((doc_ref, update_data))

    def commit(self) -> None:
        for doc_ref, update_data in self._updates:
            doc_ref.update(update_data)
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


def _make_flow_run(status: str) -> dict[str, Any]:
    return {
        "runId": "run-1",
        "steps": {
            "stepA": {
                "stepType": "CHART_EXPORT",
                "status": status,
                "createdAt": "2025-12-01T00:00:00Z",
                "inputs": {"minImages": 1},
                "outputs": {"keep": "yes"},
            },
            "stepB": {
                "stepType": "OTHER",
                "status": "READY",
                "createdAt": "2025-12-01T00:00:00Z",
                "inputs": {},
                "outputs": {},
            },
        },
        "flowKey": "flow-1",
    }


class TestFirestoreClaimFinalize(unittest.TestCase):
    def test_claim_ready_transitions_to_running(self) -> None:
        client = FakeFirestoreClient({"flow_runs": {"run-1": _make_flow_run("READY")}})
        result = claim_step_transaction(client=client, run_id="run-1", step_id="stepA")
        self.assertTrue(result.claimed)
        flow_run = client._store["flow_runs"]["run-1"]
        self.assertEqual(flow_run["steps"]["stepA"]["status"], "RUNNING")

    def test_concurrent_claim_only_one_succeeds(self) -> None:
        client = FakeFirestoreClient({"flow_runs": {"run-1": _make_flow_run("READY")}})
        first = claim_step_transaction(client=client, run_id="run-1", step_id="stepA")
        second = claim_step_transaction(client=client, run_id="run-1", step_id="stepA")
        self.assertTrue(first.claimed)
        self.assertFalse(second.claimed)
        flow_run = client._store["flow_runs"]["run-1"]
        self.assertEqual(flow_run["steps"]["stepA"]["status"], "RUNNING")

    def test_claim_not_ready_is_noop(self) -> None:
        client = FakeFirestoreClient({"flow_runs": {"run-1": _make_flow_run("RUNNING")}})
        result = claim_step_transaction(client=client, run_id="run-1", step_id="stepA")
        self.assertFalse(result.claimed)
        flow_run = client._store["flow_runs"]["run-1"]
        self.assertEqual(flow_run["steps"]["stepA"]["status"], "RUNNING")

    def test_finalize_success_updates_minimal_fields(self) -> None:
        client = FakeFirestoreClient({"flow_runs": {"run-1": _make_flow_run("RUNNING")}})
        result = finalize_step(
            client=client,
            run_id="run-1",
            step_id="stepA",
            status="SUCCEEDED",
            finished_at="2025-12-15T10:26:15Z",
            outputs_manifest_gcs_uri="gs://bucket/charts/run-1/stepA/manifest.json",
        )
        self.assertTrue(result.updated)
        flow_run = client._store["flow_runs"]["run-1"]
        step = flow_run["steps"]["stepA"]
        self.assertEqual(step["status"], "SUCCEEDED")
        self.assertEqual(step["finishedAt"], "2025-12-15T10:26:15Z")
        self.assertEqual(
            step["outputs"]["outputsManifestGcsUri"],
            "gs://bucket/charts/run-1/stepA/manifest.json",
        )
        self.assertEqual(step["outputs"]["keep"], "yes")
        self.assertIn("stepB", flow_run["steps"])

    def test_finalize_failed_sets_error_payload(self) -> None:
        client = FakeFirestoreClient({"flow_runs": {"run-1": _make_flow_run("RUNNING")}})
        error = StepError(code="VALIDATION_FAILED", message="bad input")
        result = finalize_step(
            client=client,
            run_id="run-1",
            step_id="stepA",
            status="FAILED",
            finished_at="2025-12-15T10:26:15Z",
            error=error,
        )
        self.assertTrue(result.updated)
        step = client._store["flow_runs"]["run-1"]["steps"]["stepA"]
        self.assertEqual(step["status"], "FAILED")
        self.assertEqual(step["error"]["code"], "VALIDATION_FAILED")
        self.assertEqual(step["error"]["message"], "bad input")

    def test_finalize_idempotent_when_already_succeeded(self) -> None:
        flow_run = _make_flow_run("SUCCEEDED")
        flow_run["steps"]["stepA"]["outputs"]["outputsManifestGcsUri"] = "gs://old"
        client = FakeFirestoreClient({"flow_runs": {"run-1": flow_run}})
        result = finalize_step(
            client=client,
            run_id="run-1",
            step_id="stepA",
            status="SUCCEEDED",
            finished_at="2025-12-15T10:26:15Z",
            outputs_manifest_gcs_uri="gs://new",
        )
        self.assertFalse(result.updated)
        step = client._store["flow_runs"]["run-1"]["steps"]["stepA"]
        self.assertEqual(step["outputs"]["outputsManifestGcsUri"], "gs://old")

    def test_minimal_patch_uses_step_field_paths_only(self) -> None:
        step_id = "charts:1M:ctpl_price_ma1226_vol_v1"
        claim_update = build_claim_update(step_id)
        success_update = build_finalize_success_update(
            step_id=step_id,
            finished_at="2025-12-15T10:26:15Z",
            outputs_manifest_gcs_uri="gs://bucket/manifest.json",
        )
        failure_update = build_finalize_failure_update(
            step_id=step_id,
            finished_at="2025-12-15T10:26:15Z",
            error=StepError(code="FAILED", message="err"),
        )
        for update in (claim_update, success_update, failure_update):
            for key in update.keys():
                self.assertTrue(
                    key.startswith(f"steps.{step_id}."),
                    msg=f"Unexpected update path: {key}",
                )
                self.assertNotEqual(key, "steps")


if __name__ == "__main__":
    unittest.main()
