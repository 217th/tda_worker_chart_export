from worker_chart_export import orchestration


class _FakeSnapshot:
    def __init__(self, data, update_time="ts1"):
        self._data = data
        self.update_time = update_time

    def to_dict(self):
        return self._data


class _FakeDocRef:
    def __init__(self, data, update_error=None):
        self._data = data
        self._update_error = update_error
        self.updated = False
        self.last_option = None

    def get(self):
        return _FakeSnapshot(self._data)

    def update(self, update, option=None):
        self.last_option = option
        if self._update_error is not None:
            raise self._update_error
        self.updated = True


class _FakeCollection:
    def __init__(self, doc_ref):
        self._doc_ref = doc_ref

    def document(self, _run_id):
        return self._doc_ref


class _FakeClient:
    def __init__(self, doc_ref):
        self._doc_ref = doc_ref

    def collection(self, _name):
        return _FakeCollection(self._doc_ref)

    def write_option(self, **_kwargs):
        return object()


def test_claim_success_with_precondition():
    step_id = "charts:1H:ctpl_price_ma1226_vol_v1"
    doc_ref = _FakeDocRef({"steps": {step_id: {"status": "READY"}}})
    client = _FakeClient(doc_ref)

    result = orchestration.claim_step_transaction(
        client=client, run_id="run-1", step_id=step_id
    )

    assert result.claimed is True
    assert result.status == "READY"
    assert doc_ref.updated is True


def test_claim_precondition_failure_returns_noop(monkeypatch):
    class FailedPrecondition(Exception):
        pass

    step_id = "charts:1H:ctpl_price_ma1226_vol_v1"
    doc_ref = _FakeDocRef(
        {"steps": {step_id: {"status": "READY"}}},
        update_error=FailedPrecondition("conflict"),
    )
    client = _FakeClient(doc_ref)

    monkeypatch.setattr(orchestration, "_is_precondition_error", lambda exc: True)
    monkeypatch.setattr(orchestration.time, "sleep", lambda *_args, **_kwargs: None)

    result = orchestration.claim_step_transaction(
        client=client, run_id="run-1", step_id=step_id
    )

    assert result.claimed is False
    assert result.status == "READY"
    assert result.reason == "precondition_failed"
