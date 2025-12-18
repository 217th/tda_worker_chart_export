import logging
import os
import unittest
from typing import Any

from worker_chart_export.entrypoints.cloud_event import worker_chart_export
from worker_chart_export.ingest import parse_flow_run_event, pick_ready_chart_export_step
from worker_chart_export.runtime import get_config


def _fs_string(value: str) -> dict:
    return {"stringValue": value}


def _fs_map(fields: dict) -> dict:
    return {"mapValue": {"fields": fields}}


class TestIngest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["CHARTS_BUCKET"] = "gs://dummy-bucket"
        os.environ["CHART_IMG_ACCOUNTS_JSON"] = '[{"id":"acc1","apiKey":"SECRET"}]'
        os.environ.setdefault("CHARTS_DEFAULT_TIMEZONE", "UTC")
        get_config.cache_clear()

    def test_parse_flow_run_event_extracts_run_id_and_steps(self) -> None:
        doc_name = (
            "projects/proj/databases/(default)/documents/"
            "flow_runs/20240101-010101_btcusdt_abcd"
        )
        event = {
            "id": "evt-1",
            "type": "google.cloud.firestore.document.v1.updated",
            "subject": doc_name,
            "data": {
                "value": {
                    "name": doc_name,
                    "fields": {
                        "flowKey": _fs_string("flow-1"),
                        "steps": _fs_map(
                            {
                                "stepA": _fs_map(
                                    {
                                        "stepType": _fs_string("CHART_EXPORT"),
                                        "status": _fs_string("READY"),
                                    }
                                )
                            }
                        ),
                    },
                }
            },
        }

        parsed = parse_flow_run_event(event)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.run_id, "20240101-010101_btcusdt_abcd")
        self.assertEqual(parsed.flow_run.get("flowKey"), "flow-1")
        self.assertEqual(parsed.flow_run["steps"]["stepA"]["status"], "READY")

    def test_parse_flow_run_event_filters_non_flow_runs(self) -> None:
        event = {
            "id": "evt-2",
            "type": "google.cloud.firestore.document.v1.updated",
            "subject": "projects/proj/databases/(default)/documents/other/123",
            "data": {"value": {"name": "projects/proj/databases/(default)/documents/other/123"}},
        }
        self.assertIsNone(parse_flow_run_event(event))

    def test_pick_ready_step_is_deterministic(self) -> None:
        flow_run = {
            "steps": {
                "b-step": {"stepType": "CHART_EXPORT", "status": "READY"},
                "a-step": {"stepType": "CHART_EXPORT", "status": "READY"},
            }
        }
        self.assertEqual(pick_ready_chart_export_step(flow_run), "a-step")

    def test_pick_ready_step_ignores_invalid_steps(self) -> None:
        flow_run = {"steps": ["not-a-map"]}
        self.assertIsNone(pick_ready_chart_export_step(flow_run))

    def test_handler_noop_when_no_ready_step(self) -> None:
        event = _build_flow_run_event(step_status="RUNNING")
        events = _capture_handler_events(event)
        self.assertIn("cloud_event_noop", _extract_event_names(events))

    def test_handler_ignores_non_update_event(self) -> None:
        event = _build_flow_run_event(
            step_status="READY",
            event_type="google.cloud.firestore.document.v1.created",
        )
        events = _capture_handler_events(event)
        self.assertIn("cloud_event_ignored", _extract_event_names(events))
        self.assertIn("event_type_filtered", _extract_reasons(events))

    def test_handler_ignores_other_collection(self) -> None:
        event = _build_flow_run_event(
            step_status="READY",
            subject="projects/p/databases/(default)/documents/other/123",
        )
        events = _capture_handler_events(event)
        self.assertIn("cloud_event_ignored", _extract_event_names(events))
        self.assertIn("event_filtered", _extract_reasons(events))

    def test_handler_ignores_invalid_steps_shape(self) -> None:
        event = _build_invalid_steps_event()
        events = _capture_handler_events(event)
        self.assertIn("cloud_event_ignored", _extract_event_names(events))
        self.assertIn("invalid_steps", _extract_reasons(events))


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


def _capture_handler_events(event: dict[str, Any]) -> list[dict[str, Any]]:
    logger = logging.getLogger("worker-chart-export")
    handler = _CaptureHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        worker_chart_export(event)
    finally:
        logger.removeHandler(handler)
    return handler.records


def _extract_reasons(events: list[dict[str, Any]]) -> set[str]:
    reasons = set()
    for payload in events:
        reason = payload.get("reason")
        if isinstance(reason, str):
            reasons.add(reason)
    return reasons


def _extract_event_names(events: list[dict[str, Any]]) -> set[str]:
    names = set()
    for payload in events:
        name = payload.get("event")
        if isinstance(name, str):
            names.add(name)
    return names


def _build_flow_run_event(
    *,
    step_status: str,
    event_type: str = "google.cloud.firestore.document.v1.updated",
    subject: str | None = None,
) -> dict[str, Any]:
    doc = subject or "projects/p/databases/(default)/documents/flow_runs/run-1"
    return {
        "id": "evt",
        "type": event_type,
        "subject": doc,
        "data": {
            "value": {
                "name": doc,
                "fields": {
                    "steps": _fs_map(
                        {
                            "stepA": _fs_map(
                                {
                                    "stepType": _fs_string("CHART_EXPORT"),
                                    "status": _fs_string(step_status),
                                }
                            )
                        }
                    )
                },
            }
        },
    }


def _build_invalid_steps_event() -> dict[str, Any]:
    doc = "projects/p/databases/(default)/documents/flow_runs/run-1"
    return {
        "id": "evt-invalid",
        "type": "google.cloud.firestore.document.v1.updated",
        "subject": doc,
        "data": {
            "value": {
                "name": doc,
                "fields": {
                    "steps": {"arrayValue": {"values": [{"stringValue": "bad"}]}},
                },
            }
        },
    }


if __name__ == "__main__":
    unittest.main()
