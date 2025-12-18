import json
import os
import subprocess
import sys
import tempfile
import unittest


class TestScenarioCli(unittest.TestCase):
    def test_cli_run_local_not_implemented(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fp:
            fp.write("{}\n")
            flow_run_path = fp.name

        env = os.environ.copy()
        env["CHARTS_BUCKET"] = "gs://dummy-bucket"
        env["CHART_IMG_ACCOUNTS_JSON"] = '[{"id":"acc1","apiKey":"SECRET1"}]'

        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "worker_chart_export.cli",
                "run-local",
                "--flow-run-path",
                flow_run_path,
                "--output-summary",
                "text",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(proc.returncode, 3)
        self.assertIn("NOT_IMPLEMENTED:", proc.stderr)

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
        self.assertTrue(any(item.get("event") == "local_run_started" for item in json_lines))

    def test_cli_exit_code_failed_result(self) -> None:
        from worker_chart_export import cli as cli_module

        class DummyResult:
            status = "FAILED"
            run_id = "run-1"
            step_id = "stepA"
            outputs_manifest_gcs_uri = None

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fp:
            fp.write("{}\n")
            flow_run_path = fp.name

        env = os.environ.copy()
        env["CHARTS_BUCKET"] = "gs://dummy-bucket"
        env["CHART_IMG_ACCOUNTS_JSON"] = '[{"id":"acc1","apiKey":"SECRET1"}]'

        for key, value in env.items():
            os.environ[key] = value

        original = cli_module.run_chart_export_step
        try:
            cli_module.run_chart_export_step = lambda **_: DummyResult()
            args = cli_module.build_parser().parse_args(
                [
                    "run-local",
                    "--flow-run-path",
                    flow_run_path,
                    "--output-summary",
                    "none",
                ]
            )
            exit_code = cli_module._run_local(args)
        finally:
            cli_module.run_chart_export_step = original

        self.assertEqual(exit_code, 1)
