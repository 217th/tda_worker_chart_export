import json
import subprocess
import sys
import unittest


class TestScenarioLogging(unittest.TestCase):
    def test_json_log_event_format(self) -> None:
        code = (
            "import logging\n"
            "from worker_chart_export.logging import configure_logging, log_event\n"
            "configure_logging()\n"
            "log_event(logging.getLogger('worker-chart-export'), 'test_event', runId='r1', stepId='s1')\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        out = (proc.stdout + proc.stderr).strip().splitlines()
        self.assertGreaterEqual(len(out), 1)

        payload = json.loads(out[-1])
        self.assertEqual(payload["event"], "test_event")
        self.assertEqual(payload["runId"], "r1")
        self.assertEqual(payload["stepId"], "s1")
        self.assertIn("severity", payload)

