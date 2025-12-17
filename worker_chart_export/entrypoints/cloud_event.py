from __future__ import annotations

import logging
from typing import Any

from worker_chart_export.logging import configure_logging, log_event
from worker_chart_export.runtime import get_config

try:  # Optional import to keep local tooling usable without installing deps yet.
    import functions_framework
except Exception:  # pragma: no cover
    functions_framework = None  # type: ignore[assignment]


def _handle_cloud_event(cloud_event: Any) -> None:
    configure_logging()
    logger = logging.getLogger("worker-chart-export")

    # Config is parsed once per process; errors should fail fast (misconfiguration).
    _ = get_config()

    log_event(
        logger,
        "cloud_event_received",
        eventId=getattr(cloud_event, "get", lambda k, d=None: d)("id", None)
        if cloud_event is not None
        else None,
        eventType=getattr(cloud_event, "get", lambda k, d=None: d)("type", None)
        if cloud_event is not None
        else None,
    )

    # Real processing is implemented in T-003..T-008.
    raise NotImplementedError("CloudEvent processing not implemented yet.")


if functions_framework is not None:  # pragma: no cover

    @functions_framework.cloud_event
    def worker_chart_export(cloud_event: Any) -> None:
        _handle_cloud_event(cloud_event)

else:

    def worker_chart_export(cloud_event: Any) -> None:
        _handle_cloud_event(cloud_event)
