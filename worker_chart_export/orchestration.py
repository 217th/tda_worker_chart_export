from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from typing import Any, Mapping, Literal


@dataclass(frozen=True, slots=True)
class ClaimResult:
    claimed: bool
    status: str | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class StepError:
    code: str
    message: str
    details: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class FinalizeResult:
    updated: bool
    status: str | None
    reason: str | None = None


def _get_step_status(flow_run: Mapping[str, Any], step_id: str) -> str | None:
    steps = flow_run.get("steps")
    if not isinstance(steps, Mapping):
        return None
    step = steps.get(step_id)
    if not isinstance(step, Mapping):
        return None
    status = step.get("status")
    return status if isinstance(status, str) else None


def _build_step_update(step_id: str, updates: Mapping[str, Any]) -> dict[str, Any]:
    return {f"steps.{step_id}.{key}": value for key, value in updates.items()}


def build_claim_update(step_id: str) -> dict[str, Any]:
    return _build_step_update(step_id, {"status": "RUNNING"})


def build_finalize_success_update(
    *, step_id: str, finished_at: str, outputs_manifest_gcs_uri: str
) -> dict[str, Any]:
    return _build_step_update(
        step_id,
        {
            "status": "SUCCEEDED",
            "finishedAt": finished_at,
            "outputs.outputsManifestGcsUri": outputs_manifest_gcs_uri,
        },
    )


def build_finalize_failure_update(
    *, step_id: str, finished_at: str, error: StepError
) -> dict[str, Any]:
    error_payload: dict[str, Any] = {"code": error.code, "message": error.message}
    if error.details is not None:
        error_payload["details"] = error.details
    return _build_step_update(
        step_id,
        {
            "status": "FAILED",
            "finishedAt": finished_at,
            "error": error_payload,
        },
    )


def _is_aborted_error(exc: Exception) -> bool:
    try:
        from google.api_core import exceptions as gax_exceptions
    except Exception:
        gax_exceptions = None
    if gax_exceptions is not None and isinstance(exc, gax_exceptions.Aborted):
        return True
    return exc.__class__.__name__ == "Aborted"


def _is_precondition_error(exc: Exception) -> bool:
    try:
        from google.api_core import exceptions as gax_exceptions
    except Exception:
        gax_exceptions = None
    if gax_exceptions is not None and isinstance(
        exc, (gax_exceptions.FailedPrecondition, gax_exceptions.Conflict)
    ):
        return True
    return exc.__class__.__name__ in ("FailedPrecondition", "PreconditionFailed", "Conflict")


def claim_step_transaction(*, client: Any, run_id: str, step_id: str) -> ClaimResult:
    doc_ref = client.collection("flow_runs").document(run_id)
    logger = logging.getLogger("worker-chart-export")
    max_attempts = 3
    base_backoff = 0.2
    last_status: str | None = None
    for attempt in range(max_attempts):
        snapshot = doc_ref.get()
        flow_run = snapshot.to_dict() if snapshot is not None else None
        flow_run = flow_run if isinstance(flow_run, dict) else {}
        status = _get_step_status(flow_run, step_id)
        last_status = status
        if status != "READY":
            return ClaimResult(claimed=False, status=status, reason="not_ready")
        update = build_claim_update(step_id)
        try:
            update_time = getattr(snapshot, "update_time", None)
            if update_time is not None and hasattr(client, "write_option"):
                option = client.write_option(last_update_time=update_time)
                doc_ref.update(update, option=option)
            else:
                doc_ref.update(update)
            return ClaimResult(claimed=True, status=status)
        except Exception as exc:
            if _is_precondition_error(exc) or _is_aborted_error(exc):
                if attempt < max_attempts - 1:
                    time.sleep(base_backoff * (2**attempt))
                    continue
                logger.info(
                    {
                        "event": "firestore_claim_precondition_failed",
                        "message": "firestore_claim_precondition_failed",
                        "runId": run_id,
                        "stepId": step_id,
                        "status": last_status,
                        "attempts": attempt + 1,
                    }
                )
                return ClaimResult(claimed=False, status=last_status, reason="precondition_failed")
            logger.error(
                {
                    "event": "firestore_claim_error",
                    "message": "firestore_claim_error",
                    "runId": run_id,
                    "stepId": step_id,
                    "error": type(exc).__name__,
                },
                exc_info=True,
            )
            raise
    return ClaimResult(claimed=False, status=last_status, reason="precondition_failed")


def finalize_step(
    *,
    client: Any,
    run_id: str,
    step_id: str,
    status: Literal["SUCCEEDED", "FAILED"],
    finished_at: str,
    outputs_manifest_gcs_uri: str | None = None,
    error: StepError | None = None,
) -> FinalizeResult:
    doc_ref = client.collection("flow_runs").document(run_id)
    logger = logging.getLogger("worker-chart-export")
    max_attempts = 3
    base_backoff = 0.2
    last_status: str | None = None
    for attempt in range(max_attempts):
        snapshot = doc_ref.get()
        flow_run = snapshot.to_dict() if snapshot is not None else None
        flow_run = flow_run if isinstance(flow_run, dict) else {}
        current_status = _get_step_status(flow_run, step_id)
        last_status = current_status

        if current_status in ("SUCCEEDED", "FAILED"):
            return FinalizeResult(updated=False, status=current_status, reason="already_final")
        if current_status != "RUNNING":
            return FinalizeResult(updated=False, status=current_status, reason="not_running")

        if status == "SUCCEEDED":
            if outputs_manifest_gcs_uri is None:
                raise ValueError("outputs_manifest_gcs_uri is required for SUCCEEDED")
            update = build_finalize_success_update(
                step_id=step_id,
                finished_at=finished_at,
                outputs_manifest_gcs_uri=outputs_manifest_gcs_uri,
            )
        else:
            if error is None:
                raise ValueError("error is required for FAILED")
            update = build_finalize_failure_update(
                step_id=step_id,
                finished_at=finished_at,
                error=error,
            )
        try:
            update_time = getattr(snapshot, "update_time", None)
            if update_time is not None and hasattr(client, "write_option"):
                option = client.write_option(last_update_time=update_time)
                doc_ref.update(update, option=option)
            else:
                doc_ref.update(update)
            return FinalizeResult(updated=True, status=current_status)
        except Exception as exc:
            if _is_precondition_error(exc) or _is_aborted_error(exc):
                if attempt < max_attempts - 1:
                    time.sleep(base_backoff * (2**attempt))
                    continue
                logger.info(
                    {
                        "event": "firestore_finalize_precondition_failed",
                        "message": "firestore_finalize_precondition_failed",
                        "runId": run_id,
                        "stepId": step_id,
                        "status": last_status,
                        "attempts": attempt + 1,
                    }
                )
                return FinalizeResult(updated=False, status=last_status, reason="precondition_failed")
            logger.error(
                {
                    "event": "firestore_finalize_error",
                    "message": "firestore_finalize_error",
                    "runId": run_id,
                    "stepId": step_id,
                    "error": type(exc).__name__,
                },
                exc_info=True,
            )
            raise

    return FinalizeResult(updated=False, status=last_status, reason="precondition_failed")
