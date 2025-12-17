import os
import subprocess
import sys
import unittest


class TestScenarioConfig(unittest.TestCase):
    def test_config_loads_ok(self) -> None:
        env = os.environ.copy()
        env["CHARTS_BUCKET"] = "gs://dummy-bucket"
        env["CHARTS_DEFAULT_TIMEZONE"] = "UTC"
        env["CHART_IMG_ACCOUNTS_JSON"] = '[{"id":"acc1","apiKey":"SECRET1"}]'
        env.pop("CHARTS_API_MODE", None)

        proc = subprocess.run(
            [sys.executable, "-c", "from worker_chart_export.runtime import get_config; get_config()"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

    def test_config_invalid_accounts_json_is_fatal(self) -> None:
        env = os.environ.copy()
        env["CHARTS_BUCKET"] = "gs://dummy-bucket"
        env["CHARTS_DEFAULT_TIMEZONE"] = "UTC"
        env["CHART_IMG_ACCOUNTS_JSON"] = "not-json"

        proc = subprocess.run(
            [sys.executable, "-c", "from worker_chart_export.runtime import get_config; get_config()"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("CHART_IMG_ACCOUNTS_JSON", proc.stderr)

