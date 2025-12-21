from __future__ import annotations

from types import SimpleNamespace

from worker_chart_export import core
from worker_chart_export.core import CoreResult
from worker_chart_export.orchestration import StepError
from worker_chart_export.templates import RequestFailure
from worker_chart_export.chart_img import ChartApiResult, ChartApiError


class DummyConfig:
    charts_bucket = "gs://dummy"
    charts_api_mode = "mock"
    charts_default_timezone = "Etc/UTC"
    chart_img_accounts = []
    firestore_database = "tda-db"
    service = "worker-chart-export"
    env = "test"


def test_no_ready_step_returns_validation_failed(monkeypatch):
    flow_run = {"runId": "run1", "steps": {}}

    monkeypatch.setattr(core, "_firestore_client", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(core, "_storage_client", lambda: object())

    result = core.run_chart_export_step(flow_run=flow_run, step_id=None, config=DummyConfig())

    assert isinstance(result, CoreResult)
    assert result.status == "FAILED"
    assert result.error_code == "VALIDATION_FAILED"


def test_build_requests_failure_propagates(monkeypatch):
    flow_run = {
        "runId": "run1",
        "scope": {"symbol": "BTCUSDT"},
        "steps": {
            "s1": {
                "stepType": "CHART_EXPORT",
                "status": "READY",
                "timeframe": "1h",
                "inputs": {"requests": [{"chartTemplateId": "missing"}]},
            }
        },
    }

    monkeypatch.setattr(
        core,
        "claim_step_transaction",
        lambda client, run_id, step_id: SimpleNamespace(claimed=True, status="READY"),
    )
    monkeypatch.setattr(
        core,
        "build_chart_requests",
        lambda **kwargs: SimpleNamespace(
            items=[],
            failures=[
                RequestFailure(
                    chart_template_id="missing",
                    error=StepError(code="VALIDATION_FAILED", message="missing template"),
                )
            ],
            validation_error=None,
        ),
    )
    monkeypatch.setattr(core, "_build_chart_img_client", lambda cfg: None)
    monkeypatch.setattr(
        core,
        "upload_pngs",
        lambda **kwargs: SimpleNamespace(items=[], failures=[]),
    )
    monkeypatch.setattr(core, "validate_manifest", lambda **kwargs: None)
    monkeypatch.setattr(
        core,
        "write_manifest",
        lambda **kwargs: ("gs://dummy/charts/run1/s1/manifest.json", None),
    )
    finalized = {}

    def fake_finalize(**kwargs):
        finalized["status"] = kwargs.get("status")
        finalized["error"] = kwargs.get("error")

    monkeypatch.setattr(core, "finalize_step", fake_finalize)
    monkeypatch.setattr(core, "_firestore_client", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(core, "_storage_client", lambda: object())

    result = core.run_chart_export_step(flow_run=flow_run, step_id=None, config=DummyConfig())

    assert result.status == "FAILED"
    assert result.error_code == "VALIDATION_FAILED"
    assert finalized["status"] == "FAILED"


def test_no_accounts_limit_exceeded(monkeypatch):
    flow_run = {
        "runId": "run1",
        "scope": {"symbol": "BTCUSDT"},
        "steps": {
            "s1": {
                "stepType": "CHART_EXPORT",
                "status": "READY",
                "timeframe": "1h",
                "inputs": {"requests": [{"chartTemplateId": "ctpl"}]},
            }
        },
    }

    monkeypatch.setattr(
        core,
        "claim_step_transaction",
        lambda client, run_id, step_id: SimpleNamespace(claimed=True, status="READY"),
    )
    monkeypatch.setattr(
        core,
        "build_chart_requests",
        lambda **kwargs: SimpleNamespace(
            items=[
                SimpleNamespace(
                    chart_template_id="ctpl",
                    kind="k",
                    chart_img_symbol="BINANCE:BTCUSDT",
                    interval="1h",
                    request={},
                )
            ],
            failures=[],
            validation_error=None,
        ),
    )
    # return limit exceeded
    monkeypatch.setattr(
        core,
        "_execute_chart_request",
        lambda **kwargs: ChartApiResult(
            ok=False,
            error=ChartApiError(code="CHART_API_LIMIT_EXCEEDED", message="limit"),
        ),
    )
    monkeypatch.setattr(
        core,
        "upload_pngs",
        lambda **kwargs: SimpleNamespace(items=[], failures=[]),
    )
    monkeypatch.setattr(core, "validate_manifest", lambda **kwargs: None)
    monkeypatch.setattr(
        core,
        "write_manifest",
        lambda **kwargs: ("gs://dummy/charts/run1/s1/manifest.json", None),
    )
    monkeypatch.setattr(core, "finalize_step", lambda **kwargs: None)
    monkeypatch.setattr(core, "_firestore_client", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(core, "_storage_client", lambda: object())

    result = core.run_chart_export_step(flow_run=flow_run, step_id=None, config=DummyConfig())
    assert result.status == "FAILED"
    assert result.error_code == "CHART_API_LIMIT_EXCEEDED"
