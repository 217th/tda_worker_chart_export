from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base: dict[str, Any]
        if isinstance(record.msg, dict):
            base = dict(record.msg)
        else:
            base = {"message": record.getMessage()}

        # Google Cloud Logging recognizes "severity".
        base.setdefault("severity", record.levelname)
        base.setdefault("logger", record.name)
        base.setdefault(
            "time",
            datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
        )

        if record.exc_info:
            base.setdefault("exception", self.formatException(record.exc_info))

        return json.dumps(base, ensure_ascii=False, separators=(",", ":"))


def configure_logging(*, level: str | None = None) -> None:
    lvl = (level or os.environ.get("LOG_LEVEL") or "INFO").upper().strip()
    root = logging.getLogger()
    root.setLevel(lvl)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(lvl)
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
        return
    for handler in root.handlers:
        handler.setLevel(lvl)
        handler.setFormatter(JsonFormatter())


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    payload.setdefault("message", event)
    logger.info(payload)
