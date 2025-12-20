from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from .core import run_chart_export_step
from .errors import ConfigError, NotImplementedYetError
from .logging import configure_logging, log_event
from .runtime import get_config


def _ensure_default_api_mode(args: argparse.Namespace) -> None:
    """For local runs, default CHARTS_API_MODE to mock if neither env nor flag set."""
    if args.charts_api_mode:
        return
    if os.environ.get("CHARTS_API_MODE"):
        return
    os.environ["CHARTS_API_MODE"] = "mock"


def _add_run_local_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--flow-run-path", required=True)
    parser.add_argument("--step-id", default=None)
    parser.add_argument("--charts-api-mode", choices=["real", "mock", "record"], default=None)
    parser.add_argument("--charts-bucket", default=None)
    parser.add_argument("--accounts-config-path", default=None)
    parser.add_argument("--output-summary", choices=["none", "text", "json"], default="text")


def _run_local(args: argparse.Namespace) -> int:
    # CLI overrides are applied by setting env vars so the core runtime stays uniform.
    if args.accounts_config_path:
        accounts_json = Path(args.accounts_config_path).read_text(encoding="utf-8")
        os.environ["CHART_IMG_ACCOUNTS_JSON"] = accounts_json

    if args.charts_api_mode:
        os.environ["CHARTS_API_MODE"] = args.charts_api_mode

    if args.charts_bucket:
        os.environ["CHARTS_BUCKET"] = args.charts_bucket

    _ensure_default_api_mode(args)

    logger = logging.getLogger("worker-chart-export")
    log_event(
        logger,
        "local_run_started",
        mode="local",
        flowRunPath=args.flow_run_path,
        stepId=args.step_id,
        chartsApiMode=args.charts_api_mode or os.environ.get("CHARTS_API_MODE"),
    )

    config = get_config()
    flow_run = json.loads(Path(args.flow_run_path).read_text(encoding="utf-8"))

    result = run_chart_export_step(flow_run=flow_run, step_id=args.step_id, config=config)

    if args.output_summary == "json":
        print(json.dumps(_build_json_summary(result), ensure_ascii=False))
    elif args.output_summary == "text":
        print(_build_text_summary(result))
    return 0 if result.status == "SUCCEEDED" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="worker-chart-export")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_local = sub.add_parser("run-local", help="Run worker locally using a flow_run JSON file")
    _add_run_local_args(run_local)
    run_local.set_defaults(_handler=_run_local)

    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args._handler(args))
    except ConfigError as exc:
        print(f"CONFIG_ERROR: {exc}", file=sys.stderr)
        return 2
    except NotImplementedYetError as exc:
        print(f"NOT_IMPLEMENTED: {exc}", file=sys.stderr)
        return 3


def _build_text_summary(result: Any) -> str:
    manifest = result.outputs_manifest_gcs_uri or "-"
    items = "-" if result.items_count is None else result.items_count
    failures = "-" if result.failures_count is None else result.failures_count
    return (
        f"CHART_EXPORT {result.status}: "
        f"manifest={manifest}, items={items}, failures={failures}"
    )


def _build_json_summary(result: Any) -> dict[str, Any]:
    return {
        "status": result.status,
        "runId": result.run_id,
        "stepId": result.step_id,
        "outputsManifestGcsUri": result.outputs_manifest_gcs_uri,
        "itemsCount": result.items_count,
        "failuresCount": result.failures_count,
        "minImages": result.min_images,
        "errorCode": result.error_code,
    }


if __name__ == "__main__":
    raise SystemExit(main())
