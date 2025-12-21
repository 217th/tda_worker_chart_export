from __future__ import annotations

import logging
from typing import Any

from worker_chart_export.core import run_chart_export_step
from worker_chart_export.errors import ConfigError
from worker_chart_export.ingest import (
    is_firestore_update_event,
    parse_flow_run_event,
    pick_ready_chart_export_step,
    get_cloud_event_attr,
)
from worker_chart_export.logging import configure_logging, log_event
from worker_chart_export.runtime import get_config

try:  # Optional import to keep local tooling usable without installing deps yet.
    import functions_framework
except Exception:  # pragma: no cover
    functions_framework = None  # type: ignore[assignment]


def _handle_cloud_event(cloud_event: Any) -> None:
    configure_logging()
    logger = logging.getLogger("worker-chart-export")

    event_id = get_cloud_event_attr(cloud_event, "id")
    event_type = get_cloud_event_attr(cloud_event, "type")
    subject = get_cloud_event_attr(cloud_event, "subject")

    try:
        # Config is parsed once per process; errors should fail fast (misconfiguration).
        config = get_config()
    except ConfigError as exc:
        log_event(
            logger,
            "config_error",
            eventId=event_id,
            eventType=event_type,
            subject=subject,
            error=str(exc),
        )
        raise

    base_fields = {
        "service": config.service,
        "env": config.env,
        "eventId": event_id,
        "eventType": event_type,
        "subject": subject,
    }

    log_event(logger, "cloud_event_received", **base_fields)

    if not is_firestore_update_event(event_type):
        log_event(logger, "cloud_event_ignored", **base_fields, reason="event_type_filtered")
        return

    parsed = parse_flow_run_event(cloud_event)
    if parsed is None:
        log_event(logger, "cloud_event_ignored", **base_fields, reason="event_filtered")
        return

    flow_run = parsed.flow_run
    run_id = parsed.run_id
    base_fields["runId"] = run_id

    flow_key = flow_run.get("flowKey") if isinstance(flow_run, dict) else None
    if isinstance(flow_key, str):
        base_fields["flowKey"] = flow_key

    steps = flow_run.get("steps") if isinstance(flow_run, dict) else None
    if not isinstance(steps, dict):
        log_event(logger, "cloud_event_ignored", **base_fields, reason="invalid_steps")
        return

    step_id = pick_ready_chart_export_step(flow_run)
    if step_id is None:
        log_event(logger, "cloud_event_noop", **base_fields, reason="no_ready_step")
        return

    log_event(logger, "ready_step_selected", **base_fields, stepId=step_id)
    result = run_chart_export_step(flow_run=flow_run, step_id=step_id, config=config)
    log_event(
        logger,
        "cloud_event_finished",
        **base_fields,
        stepId=step_id,
        status=result.status,
        outputsManifestGcsUri=result.outputs_manifest_gcs_uri,
        itemsCount=result.items_count,
        failuresCount=result.failures_count,
        errorCode=result.error_code,
    )


if functions_framework is not None:  # pragma: no cover

    @functions_framework.cloud_event
    def worker_chart_export(cloud_event: Any) -> None:
        _handle_cloud_event(cloud_event)

else:

    def worker_chart_export(cloud_event: Any) -> None:
        _handle_cloud_event(cloud_event)
