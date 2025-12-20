from worker_chart_export import orchestration


class _FakeSnapshot:
    def __init__(self, data):
        self._data = data

    def to_dict(self):
        return self._data


class _FakeDocRef:
    def __init__(self, data):
        self._data = data

    def get(self, transaction=None):
        return _FakeSnapshot(self._data)


class _FakeCollection:
    def __init__(self, data):
        self._data = data

    def document(self, _run_id):
        return _FakeDocRef(self._data)


class _FakeClient:
    def __init__(self, data):
        self._data = data

    def collection(self, _name):
        return _FakeCollection(self._data)


def test_claim_handles_aborted_as_noop(monkeypatch):
    class Aborted(Exception):
        pass

    def _raise_aborted(_client, _fn):
        raise Aborted("contention")

    monkeypatch.setattr(orchestration, "_run_transaction", _raise_aborted)

    step_id = "charts:1H:ctpl_price_ma1226_vol_v1"
    fake_flow_run = {"steps": {step_id: {"status": "RUNNING"}}}
    client = _FakeClient(fake_flow_run)

    result = orchestration.claim_step_transaction(
        client=client, run_id="run-1", step_id=step_id
    )

    assert result.claimed is False
    assert result.status == "RUNNING"
    assert result.reason == "aborted"
