import json
import os
import subprocess
import sys
import unittest


class TestScenarioCloudEvent(unittest.TestCase):
    def test_cloud_event_direct_call_logs_and_raises(self) -> None:
        code = (
            "import os\n"
            "os.environ['CHARTS_BUCKET'] = 'gs://dummy-bucket'\n"
            "os.environ['CHART_IMG_ACCOUNTS_JSON'] = '[{\"id\":\"acc1\",\"apiKey\":\"SECRET1\"}]'\n"
            "from worker_chart_export.entrypoints.cloud_event import worker_chart_export\n"
            "try:\n"
            "  worker_chart_export({'id':'evt1','type':'test.event'})\n"
            "except Exception as e:\n"
            "  print(type(e).__name__ + ':' + str(e))\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=False,
        )

        combined = (proc.stdout + proc.stderr).splitlines()

        # The handler intentionally raises NotImplementedError in T-002 stage.
        self.assertTrue(any("NotImplementedError:CloudEvent processing not implemented yet." in ln for ln in combined))

        # Ensure a structured "cloud_event_received" log is emitted.
        json_lines = []
        for line in combined:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                json_lines.append(json.loads(line))
            except Exception:
                continue
        self.assertTrue(any(item.get("event") == "cloud_event_received" for item in json_lines))

