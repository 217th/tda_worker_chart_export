from __future__ import annotations

from dataclasses import dataclass
import logging
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


def _run_transaction(client: Any, fn: Any) -> Any:
    transaction = client.transaction()
    # google-cloud-firestore transactions must be explicitly started; for fakes, just call fn+commit.
    begin = getattr(transaction, "_begin", None)
    if callable(begin):
        begin()
        try:
            result = fn(transaction)
            transaction.commit()
            return result
        except Exception:
            rollback = getattr(transaction, "_rollback", None)
            if callable(rollback):
                try:
                    rollback()
                except Exception:
                    pass
            raise

    result = fn(transaction)
    commit = getattr(transaction, "commit", None)
    if callable(commit):
        commit()
    return result


def claim_step_transaction(*, client: Any, run_id: str, step_id: str) -> ClaimResult:
    doc_ref = client.collection("flow_runs").document(run_id)

    def _claim(transaction: Any) -> ClaimResult:
        snapshot = doc_ref.get(transaction=transaction)
        flow_run = snapshot.to_dict() if snapshot is not None else None
        flow_run = flow_run if isinstance(flow_run, dict) else {}
        status = _get_step_status(flow_run, step_id)
        if status != "READY":
            return ClaimResult(claimed=False, status=status, reason="not_ready")
        update = build_claim_update(step_id)
        transaction.update(doc_ref, update)
        return ClaimResult(claimed=True, status=status)

    try:
        return _run_transaction(client, _claim)
    except Exception as exc:
        logger = logging.getLogger("worker-chart-export")
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

    def _finalize(transaction: Any) -> FinalizeResult:
        snapshot = doc_ref.get(transaction=transaction)
        flow_run = snapshot.to_dict() if snapshot is not None else None
        flow_run = flow_run if isinstance(flow_run, dict) else {}
        current_status = _get_step_status(flow_run, step_id)

        if current_status in ("SUCCEEDED", "FAILED"):
            return FinalizeResult(
                updated=False, status=current_status, reason="already_final"
            )
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

        transaction.update(doc_ref, update)
        return FinalizeResult(updated=True, status=current_status)

    return _run_transaction(client, _finalize)
