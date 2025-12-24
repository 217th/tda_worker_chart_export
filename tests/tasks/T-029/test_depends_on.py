import unittest
from unittest.mock import patch

from worker_chart_export.ingest import pick_ready_chart_export_step
from worker_chart_export import core


class DummyConfig:
    charts_bucket = "gs://dummy"
    charts_api_mode = "mock"
    charts_default_timezone = "Etc/UTC"
    chart_img_accounts = []
    firestore_database = "(default)"
    service = "worker-chart-export"
    env = "test"


def _flow_run(steps):
    return {
        "runId": "run-1",
        "scope": {"symbol": "BTCUSDT"},
        "steps": steps,
    }


class TestDependsOnPick(unittest.TestCase):
    def test_ready_with_unmet_dependency_is_blocked(self):
        flow_run = _flow_run(
            {
                "stepA": {
                    "stepType": "CHART_EXPORT",
                    "status": "READY",
                    "dependsOn": ["stepB"],
                },
                "stepB": {"stepType": "OTHER", "status": "READY"},
            }
        )
        pick = pick_ready_chart_export_step(flow_run)
        self.assertIsNone(pick.step_id)
        self.assertEqual(len(pick.blocked), 1)
        self.assertEqual(pick.blocked[0].step_id, "stepA")
        self.assertEqual(pick.blocked[0].unmet[0].step_id, "stepB")
        self.assertEqual(pick.blocked[0].unmet[0].status, "READY")

    def test_ready_with_satisfied_dependencies_is_selected(self):
        flow_run = _flow_run(
            {
                "stepA": {
                    "stepType": "CHART_EXPORT",
                    "status": "READY",
                    "dependsOn": ["stepB"],
                },
                "stepB": {"stepType": "OTHER", "status": "SUCCEEDED"},
            }
        )
        pick = pick_ready_chart_export_step(flow_run)
        self.assertEqual(pick.step_id, "stepA")
        self.assertEqual(pick.blocked, ())

    def test_only_eligible_ready_step_is_selected(self):
        flow_run = _flow_run(
            {
                "stepA": {
                    "stepType": "CHART_EXPORT",
                    "status": "READY",
                    "dependsOn": ["stepB"],
                },
                "stepB": {"stepType": "OTHER", "status": "READY"},
                "stepC": {
                    "stepType": "CHART_EXPORT",
                    "status": "READY",
                    "dependsOn": [],
                },
            }
        )
        pick = pick_ready_chart_export_step(flow_run)
        self.assertEqual(pick.step_id, "stepC")
        self.assertEqual(len(pick.blocked), 1)


class TestDependsOnCore(unittest.TestCase):
    def test_core_blocks_when_depends_unmet(self):
        flow_run = _flow_run(
            {
                "stepA": {
                    "stepType": "CHART_EXPORT",
                    "status": "READY",
                    "dependsOn": ["stepB"],
                    "timeframe": "1h",
                    "inputs": {"requests": [{"chartTemplateId": "ctpl"}]},
                },
                "stepB": {"stepType": "OTHER", "status": "READY"},
            }
        )
        with patch.object(core, "_firestore_client", return_value=object()), patch.object(
            core, "_storage_client", return_value=object()
        ), patch.object(core, "_build_chart_img_client", return_value=None), patch.object(
            core, "claim_step_transaction"
        ) as claim:
            result = core.run_chart_export_step(
                flow_run=flow_run, step_id="stepA", config=DummyConfig()
            )
            self.assertEqual(result.status, "FAILED")
            self.assertEqual(result.error_code, "VALIDATION_FAILED")
            claim.assert_not_called()


if __name__ == "__main__":
    unittest.main()
