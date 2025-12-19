from __future__ import annotations

import json
import os
from pathlib import Path

from worker_chart_export import cli
from worker_chart_export.core import CoreResult


class DummyConfig:
    pass


def make_flow_run_file(tmp_path: Path) -> Path:
    path = tmp_path / "flow_run.json"
    path.write_text(
        json.dumps({"steps": {"s1": {"status": "READY", "stepType": "CHART_EXPORT"}}}),
        encoding="utf-8",
    )
    return path


def test_text_summary_success(monkeypatch, capsys, tmp_path):
    flow_path = make_flow_run_file(tmp_path)

    def stub_run_chart_export_step(**kwargs):
        return CoreResult(
            status="SUCCEEDED",
            run_id="run1",
            step_id="s1",
            outputs_manifest_gcs_uri="gs://bucket/runs/run1/manifest.json",
            items_count=2,
            failures_count=0,
        )

    monkeypatch.setattr(cli, "run_chart_export_step", stub_run_chart_export_step)
    monkeypatch.setattr(cli, "get_config", lambda: DummyConfig())
    monkeypatch.delenv("CHARTS_API_MODE", raising=False)

    rc = cli.main(
        [
            "run-local",
            "--flow-run-path",
            str(flow_path),
            "--step-id",
            "s1",
            "--charts-bucket",
            "gs://bucket",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert "CHART_EXPORT SUCCEEDED" in captured.out
    assert "items=2" in captured.out
    assert "failures=0" in captured.out


def test_json_summary_failed(monkeypatch, capsys, tmp_path):
    flow_path = make_flow_run_file(tmp_path)

    def stub_run_chart_export_step(**kwargs):
        return CoreResult(
            status="FAILED",
            run_id="runX",
            step_id="missing",
            outputs_manifest_gcs_uri=None,
            items_count=0,
            failures_count=1,
            min_images=1,
            error_code="VALIDATION_FAILED",
        )

    monkeypatch.setattr(cli, "run_chart_export_step", stub_run_chart_export_step)
    monkeypatch.setattr(cli, "get_config", lambda: DummyConfig())

    rc = cli.main(
        [
            "run-local",
            "--flow-run-path",
            str(flow_path),
            "--step-id",
            "missing",
            "--output-summary",
            "json",
        ]
    )
    captured = capsys.readouterr()
    summary = json.loads(captured.out.strip())
    assert rc == 1
    assert summary["status"] == "FAILED"
    assert summary["errorCode"] == "VALIDATION_FAILED"
    assert summary["failuresCount"] == 1
    assert summary["minImages"] == 1


def test_default_charts_api_mode_set_to_mock(monkeypatch, tmp_path):
    flow_path = make_flow_run_file(tmp_path)
    monkeypatch.delenv("CHARTS_API_MODE", raising=False)

    seen_mode = {}

    def stub_run_chart_export_step(**kwargs):
        seen_mode["mode"] = os.environ.get("CHARTS_API_MODE")
        return CoreResult(status="SUCCEEDED")

    monkeypatch.setattr(cli, "run_chart_export_step", stub_run_chart_export_step)
    monkeypatch.setattr(cli, "get_config", lambda: DummyConfig())

    rc = cli.main(["run-local", "--flow-run-path", str(flow_path)])
    assert rc == 0
    assert seen_mode["mode"] == "mock"


def test_flag_overrides_env(monkeypatch, tmp_path):
    flow_path = make_flow_run_file(tmp_path)
    monkeypatch.setenv("CHARTS_API_MODE", "real")
    monkeypatch.setenv("CHARTS_BUCKET", "gs://old")

    seen_env = {}

    def stub_run_chart_export_step(**kwargs):
        seen_env["mode"] = os.environ.get("CHARTS_API_MODE")
        seen_env["bucket"] = os.environ.get("CHARTS_BUCKET")
        return CoreResult(status="SUCCEEDED")

    monkeypatch.setattr(cli, "run_chart_export_step", stub_run_chart_export_step)
    monkeypatch.setattr(cli, "get_config", lambda: DummyConfig())

    rc = cli.main(
        [
            "run-local",
            "--flow-run-path",
            str(flow_path),
            "--charts-api-mode",
            "record",
            "--charts-bucket",
            "gs://new-bucket",
        ]
    )
    assert rc == 0
    assert seen_env["mode"] == "record"
    assert seen_env["bucket"] == "gs://new-bucket"


def test_accounts_config_path_injected(monkeypatch, tmp_path):
    flow_path = make_flow_run_file(tmp_path)
    accounts_file = tmp_path / "accounts.json"
    accounts_file.write_text('[{"id":"a1","apiKey":"k"}]', encoding="utf-8")

    seen_json = {}

    def stub_run_chart_export_step(**kwargs):
        seen_json["value"] = os.environ.get("CHART_IMG_ACCOUNTS_JSON")
        return CoreResult(status="SUCCEEDED")

    monkeypatch.setattr(cli, "run_chart_export_step", stub_run_chart_export_step)
    monkeypatch.setattr(cli, "get_config", lambda: DummyConfig())

    rc = cli.main(
        [
            "run-local",
            "--flow-run-path",
            str(flow_path),
            "--accounts-config-path",
            str(accounts_file),
        ]
    )
    assert rc == 0
    assert seen_json["value"] == accounts_file.read_text(encoding="utf-8")
