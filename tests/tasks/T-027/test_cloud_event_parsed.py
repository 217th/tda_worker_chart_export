import json
import subprocess
import sys
import unittest


class TestCloudEventParsed(unittest.TestCase):
    def test_cloud_event_parsed_includes_run_id_and_flow_key(self) -> None:
        run_id = "20251221-142000_BTCUSDT_demo27"
        flow_key = "scheduled_month_week_report_v1"

        event = {
            "id": "evt-123",
            "type": "google.cloud.firestore.document.v1.updated",
            "subject": f"projects/p/databases/(default)/documents/flow_runs/{run_id}",
            "data": {
                "value": {
                    "name": f"projects/p/databases/(default)/documents/flow_runs/{run_id}",
                    "fields": {
                        "flowKey": {"stringValue": flow_key},
                        "steps": {"mapValue": {"fields": {}}},
                    },
                }
            },
        }

        code = (
            "import json, os\n"
            "os.environ['CHARTS_BUCKET'] = 'gs://dummy-bucket'\n"
            "os.environ['CHARTS_API_MODE'] = 'mock'\n"
            "os.environ['CHART_IMG_ACCOUNTS_JSON'] = '[{\"id\":\"acc1\",\"apiKey\":\"SECRET1\"}]'\n"
            "from worker_chart_export.entrypoints.cloud_event import worker_chart_export\n"
            f"event = {json.dumps(event)}\n"
            "worker_chart_export(event)\n"
        )

        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=False,
        )

        combined = (proc.stdout + proc.stderr).splitlines()
        json_lines = []
        for line in combined:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                json_lines.append(json.loads(line))
            except Exception:
                continue

        parsed = [item for item in json_lines if item.get("event") == "cloud_event_parsed"]
        self.assertTrue(parsed, "cloud_event_parsed not found in logs")
        payload = parsed[-1]
        self.assertEqual(payload.get("runId"), run_id)
        self.assertEqual(payload.get("flowKey"), flow_key)
