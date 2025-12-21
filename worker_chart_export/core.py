from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Mapping, Sequence
from datetime import datetime, timezone

from .chart_img import (
    ChartApiResult,
    ChartImgClient,
    ChartImgRequest,
    HttpxRequester,
    fetch_with_retries,
)
from .config import WorkerConfig
from .errors import WorkerChartExportError
from .gcs_artifacts import (
    GcsUploader,
    build_manifest,
    format_generated_at,
    upload_pngs,
    validate_manifest,
    write_manifest,
)
from .ingest import pick_ready_chart_export_step
from .logging import log_event
from .orchestration import StepError, claim_step_transaction, finalize_step
from .templates import (
    BuiltChartRequest,
    FirestoreChartTemplateStore,
    RequestFailure,
    build_chart_requests,
)
from .usage import select_account_for_request, mark_account_exhausted


@dataclass(frozen=True, slots=True)
class CoreResult:
    status: str
    run_id: str | None = None
    step_id: str | None = None
    outputs_manifest_gcs_uri: str | None = None
    items_count: int | None = None
    failures_count: int | None = None
    min_images: int | None = None
    error_code: str | None = None


def run_chart_export_step(
    *,
    flow_run: dict[str, Any],
    step_id: str | None,
    config: WorkerConfig,
    firestore_client: Any | None = None,
    storage_client: Any | None = None,
    chart_img_client: ChartImgClient | None = None,
    now: datetime | None = None,
) -> CoreResult:
    logger = logging.getLogger("worker-chart-export")
    firestore_client = firestore_client or _firestore_client(config.firestore_database)
    storage_client = storage_client or _storage_client()
    chart_img_client = chart_img_client or _build_chart_img_client(config)
    now = now or datetime.now(timezone.utc)

    run_id = _require_run_id(flow_run)
    step_id = step_id or pick_ready_chart_export_step(flow_run)
    log_event(logger, "core_start", runId=run_id, stepId=step_id)
    if not step_id:
        return CoreResult(status="FAILED", run_id=run_id, error_code="VALIDATION_FAILED")

    step = _get_step(flow_run, step_id)
    if isinstance(step, StepError):
        return CoreResult(status="FAILED", run_id=run_id, step_id=step_id, error_code=step.code)

    if step.get("status") in ("SUCCEEDED", "FAILED"):
        log_event(logger, "core_noop_already_final", runId=run_id, stepId=step_id, status=step.get("status"))
        return CoreResult(status=step["status"], run_id=run_id, step_id=step_id)

    if step.get("status") != "READY":
        return CoreResult(status="FAILED", run_id=run_id, step_id=step_id, error_code="VALIDATION_FAILED")

    claim = claim_step_transaction(client=firestore_client, run_id=run_id, step_id=step_id)
    log_event(logger, "claim_attempt", runId=run_id, stepId=step_id, claimed=claim.claimed, status=claim.status)
    if not claim.claimed:
        return CoreResult(
            status=claim.status or "FAILED",
            run_id=run_id,
            step_id=step_id,
            error_code="VALIDATION_FAILED" if claim.status is None else None,
        )

    min_images, min_error = _get_min_images(step)
    if min_error:
        return _finalize_failure(
            firestore_client,
            run_id,
            step_id,
            min_error,
            logger,
        )

    template_store = FirestoreChartTemplateStore(firestore_client)
    build_result = build_chart_requests(
        requests=_get_requests(step),
        scope_symbol=_get_scope_symbol(flow_run),
        timeframe=_get_timeframe(step),
        default_timezone=config.charts_default_timezone,
        template_store=template_store,
        min_images=min_images,
    )
    if build_result.validation_error:
        return _finalize_failure(
            firestore_client, run_id, step_id, build_result.validation_error, logger
        )

    if not build_result.items and not build_result.failures:
        return _finalize_failure(
            firestore_client,
            run_id,
            step_id,
            StepError(code="VALIDATION_FAILED", message="requests must not be empty"),
            logger,
        )

    successes: list[tuple[BuiltChartRequest, bytes]] = []
    failures: list[dict[str, Any]] = [_failure_from_request(f) for f in build_result.failures]

    for item in build_result.items:
        log_event(
            logger,
            "chart_api_call_start",
            runId=run_id,
            stepId=step_id,
            chartTemplateId=item.chart_template_id,
            chartImgSymbol=item.chart_img_symbol,
        )
        api_result = _execute_chart_request(
            chart_img_client=chart_img_client,
            request=item,
            config=config,
            firestore_client=firestore_client,
            logger=logger,
        )
        if api_result.ok and api_result.png_bytes:
            successes.append((item, api_result.png_bytes))
        else:
            failures.append(_chart_failure(item, api_result))
        log_event(
            logger,
            "chart_api_call_finished",
            runId=run_id,
            stepId=step_id,
            chartTemplateId=item.chart_template_id,
            chartImgSymbol=item.chart_img_symbol,
            ok=api_result.ok,
            errorCode=getattr(api_result.error, "code", None) if api_result.error else None,
        )

    if _all_accounts_exhausted(failures, successes, build_result.items):
        return _finalize_failure(
            firestore_client,
            run_id,
            step_id,
            StepError(code="CHART_API_LIMIT_EXCEEDED", message="No Chart-IMG accounts available"),
            logger,
        )

    generated_at = format_generated_at(now)
    uploader = GcsUploader(client=storage_client, bucket_gs=config.charts_bucket)

    from .gcs_artifacts import PngUploadInput

    symbol_slug = _get_scope_symbol(flow_run)
    png_inputs = [
        PngUploadInput(
            chart_template_id=req.chart_template_id,
            kind=req.kind,
            png_bytes=png,
            generated_at=generated_at,
            symbol_slug=symbol_slug,
            timeframe=req.interval,
        )
        for req, png in successes
    ]
    upload_result = upload_pngs(
        uploader=uploader,
        run_id=run_id,
        step_id=step_id,
        inputs=png_inputs,
    )
    failures.extend(upload_result.failures)
    manifest_items = upload_result.items

    manifest = build_manifest(
        run_id=run_id,
        step_id=step_id,
        created_at=generated_at.rfc3339,
        symbol=_get_scope_symbol(flow_run),
        timeframe=_get_timeframe(step),
        min_images=min_images,
        requested=_get_requests(step),
        items=manifest_items,
        failures=failures,
    )

    schema_error = validate_manifest(manifest=manifest)
    if schema_error:
        return _finalize_failure(firestore_client, run_id, step_id, schema_error, logger)

    manifest_uri, manifest_write_error = write_manifest(
        uploader=uploader, run_id=run_id, step_id=step_id, manifest=manifest
    )
    if manifest_write_error:
        return _finalize_failure(
            firestore_client, run_id, step_id, manifest_write_error, logger
        )

    success = len(manifest_items) >= min_images
    if not success:
        first_error = failures[0]["error"] if failures else {"code": "VALIDATION_FAILED", "message": "minImages not satisfied"}
        code = first_error.get("code", "VALIDATION_FAILED")
        message = first_error.get("message", "minImages not satisfied")
        return _finalize_failure(
            firestore_client,
            run_id,
            step_id,
            StepError(code=code, message=message),
            logger,
            outputs_manifest_gcs_uri=manifest_uri,
            items_count=len(manifest_items),
            failures_count=len(failures),
            min_images=min_images,
        )

    finalize_step(
        client=firestore_client,
        run_id=run_id,
        step_id=step_id,
        status="SUCCEEDED",
        finished_at=generated_at.rfc3339,
        outputs_manifest_gcs_uri=manifest_uri,
    )
    log_event(
        logger,
        "step_completed",
        runId=run_id,
        stepId=step_id,
        status="SUCCEEDED",
        itemsCount=len(manifest_items),
        failuresCount=len(failures),
        minImages=min_images,
        outputsManifestGcsUri=manifest_uri,
    )

    return CoreResult(
        status="SUCCEEDED",
        run_id=run_id,
        step_id=step_id,
        outputs_manifest_gcs_uri=manifest_uri,
        items_count=len(manifest_items),
        failures_count=len(failures),
        min_images=min_images,
    )


def _execute_chart_request(
    *,
    chart_img_client: ChartImgClient,
    request: BuiltChartRequest,
    config: WorkerConfig,
    firestore_client: Any,
    logger: logging.Logger,
) -> ChartApiResult:
    def select_next_account():
        result = select_account_for_request(
            client=firestore_client,
            accounts=config.chart_img_accounts,
            logger=logger,
            log_context={"chartTemplateId": request.chart_template_id},
        )
        return result.account

    def mark_exhausted(account):
        mark_account_exhausted(client=firestore_client, account=account)

    chart_request = ChartImgRequest(
        chart_template_id=request.chart_template_id,
        chart_img_symbol=request.chart_img_symbol,
        timeframe=request.interval,
        payload=request.request,
    )

    result = fetch_with_retries(
        client=chart_img_client,
        request=chart_request,
        select_account=select_next_account,
        mark_account_exhausted=mark_exhausted,
    )
    return result


def _chart_failure(req: BuiltChartRequest, api_result: ChartApiResult) -> dict[str, Any]:
    error = api_result.error or StepError(code="CHART_API_FAILED", message="Chart API failed")
    return {
        "request": {"chartTemplateId": req.chart_template_id},
        "error": {
            "code": getattr(error, "code", "CHART_API_FAILED"),
            "message": getattr(error, "message", "Chart API failed"),
            "details": getattr(error, "details", None),
        },
    }


def _failure_from_request(failure: RequestFailure) -> dict[str, Any]:
    return {
        "request": {"chartTemplateId": failure.chart_template_id},
        "error": {
            "code": failure.error.code,
            "message": failure.error.message,
            "details": failure.error.details,
        },
    }


def _all_accounts_exhausted(
    failures: Sequence[Mapping[str, Any]],
    successes: Sequence[tuple[BuiltChartRequest, bytes]],
    items: Sequence[BuiltChartRequest],
) -> bool:
    return (
        len(successes) == 0
        and len(items) > 0
        and any(f.get("error", {}).get("code") == "CHART_API_LIMIT_EXCEEDED" for f in failures)
    )


def _get_min_images(step: Mapping[str, Any]) -> tuple[int, StepError | None]:
    inputs = step.get("inputs") if isinstance(step, Mapping) else {}
    value = inputs.get("minImages") if isinstance(inputs, Mapping) else None
    if value is None:
        reqs = inputs.get("requests") if isinstance(inputs, Mapping) else []
        count = len(reqs) if isinstance(reqs, list) else 0
        return (max(1, count or 1), None)
    if isinstance(value, int) and value > 0:
        reqs = inputs.get("requests") if isinstance(inputs, Mapping) else []
        req_count = len(reqs) if isinstance(reqs, list) else 0
        if req_count and value > req_count:
            return (
                value,
                StepError(
                    code="VALIDATION_FAILED",
                    message="minImages cannot exceed number of requests",
                    details={"minImages": value, "requestsCount": req_count},
                ),
            )
        return (value, None)
    return (
        1,
        StepError(
            code="VALIDATION_FAILED",
            message="minImages must be a positive integer",
            details={"minImages": value},
        ),
    )


def _get_requests(step: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    inputs = step.get("inputs") if isinstance(step, Mapping) else {}
    reqs = inputs.get("requests") if isinstance(inputs, Mapping) else None
    return reqs if isinstance(reqs, list) else []


def _get_timeframe(step: Mapping[str, Any]) -> str:
    timeframe = step.get("timeframe") if isinstance(step, Mapping) else None
    if not isinstance(timeframe, str) or timeframe.strip() == "":
        raise WorkerChartExportError("timeframe is required")
    return timeframe


def _get_scope_symbol(flow_run: Mapping[str, Any]) -> str:
    scope = flow_run.get("scope") if isinstance(flow_run, Mapping) else None
    symbol = scope.get("symbol") if isinstance(scope, Mapping) else None
    if not isinstance(symbol, str) or symbol.strip() == "":
        raise WorkerChartExportError("scope.symbol is required")
    return symbol.strip()


def _get_step(flow_run: Mapping[str, Any], step_id: str) -> Mapping[str, Any] | StepError:
    steps = flow_run.get("steps") if isinstance(flow_run, Mapping) else None
    if not isinstance(steps, Mapping):
        return StepError(code="VALIDATION_FAILED", message="steps must be an object")
    step = steps.get(step_id)
    if not isinstance(step, Mapping):
        return StepError(code="VALIDATION_FAILED", message="step not found", details={"stepId": step_id})
    if step.get("stepType") != "CHART_EXPORT":
        return StepError(code="VALIDATION_FAILED", message="stepType must be CHART_EXPORT")
    return step


def _require_run_id(flow_run: Mapping[str, Any]) -> str:
    run_id = flow_run.get("runId") if isinstance(flow_run, Mapping) else None
    if not isinstance(run_id, str) or run_id.strip() == "":
        raise WorkerChartExportError("runId is required in flow_run")
    return run_id


_FS_CLIENT = None
_STORAGE_CLIENT = None


def _firestore_client():
    raise RuntimeError("Use _firestore_client(database=...)")


_FS_CLIENTS: dict[str, Any] = {}


def _firestore_client(database: str):
    client = _FS_CLIENTS.get(database)
    if client is None:
        from google.cloud import firestore  # type: ignore

        client = firestore.Client(database=database)
        _FS_CLIENTS[database] = client
    return client


def _storage_client():
    global _STORAGE_CLIENT
    if _STORAGE_CLIENT is None:
        from google.cloud import storage  # type: ignore

        _STORAGE_CLIENT = storage.Client()
    return _STORAGE_CLIENT


def _build_chart_img_client(config: WorkerConfig) -> ChartImgClient:
    if config.charts_api_mode == "mock":
        return ChartImgClient(mode="mock")
    return ChartImgClient(mode=config.charts_api_mode, http=HttpxRequester())


def _finalize_failure(
    client: Any,
    run_id: str,
    step_id: str,
    error: StepError,
    logger: logging.Logger,
    *,
    outputs_manifest_gcs_uri: str | None = None,
    items_count: int | None = None,
    failures_count: int | None = None,
    min_images: int | None = None,
) -> CoreResult:
    try:
        finalize_step(
            client=client,
            run_id=run_id,
            step_id=step_id,
            status="FAILED",
            finished_at=datetime.now(timezone.utc).isoformat(),
            error=error,
        )
    except Exception:
        log_event(logger, "finalize_failed", runId=run_id, stepId=step_id, error=error.code)

    return CoreResult(
        status="FAILED",
        run_id=run_id,
        step_id=step_id,
        outputs_manifest_gcs_uri=outputs_manifest_gcs_uri,
        items_count=items_count,
        failures_count=failures_count,
        min_images=min_images,
        error_code=error.code,
    )
