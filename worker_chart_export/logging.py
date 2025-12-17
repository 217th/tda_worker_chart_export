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
    logging.basicConfig(level=lvl, format="%(message)s")
    root = logging.getLogger()
    for handler in root.handlers:
        handler.setFormatter(JsonFormatter())


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    logger.info({"event": event, **fields})

