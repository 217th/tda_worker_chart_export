from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import WorkerConfig
from .errors import NotImplementedYetError


@dataclass(frozen=True, slots=True)
class CoreResult:
    status: str
    run_id: str | None = None
    step_id: str | None = None
    outputs_manifest_gcs_uri: str | None = None


def run_chart_export_step(
    *, flow_run: dict[str, Any], step_id: str | None, config: WorkerConfig
) -> CoreResult:
    raise NotImplementedYetError(
        "Core engine is not implemented yet (see T-003..T-008)."
    )

