from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker

from .orchestration import StepError


MANIFEST_SCHEMA_PATH = Path(
    "docs-worker-chart-export/contracts/charts_outputs_manifest.schema.json"
)


@dataclass(frozen=True, slots=True)
class GeneratedAt:
    rfc3339: str
    filename_stamp: str


@dataclass(frozen=True, slots=True)
class PngUploadInput:
    chart_template_id: str
    kind: str
    png_bytes: bytes
    generated_at: GeneratedAt
    symbol_slug: str
    timeframe: str


@dataclass(frozen=True, slots=True)
class PngUploadResult:
    items: list[dict[str, Any]]
    failures: list[dict[str, Any]]


class GcsUploader:
    def __init__(self, *, client: Any, bucket_gs: str) -> None:
        self._bucket_name = _parse_gs_bucket(bucket_gs)
        self._client = client

    @property
    def bucket_gs(self) -> str:
        return f"gs://{self._bucket_name}"

    def upload_bytes(self, *, object_path: str, data: bytes, content_type: str) -> None:
        bucket = self._client.bucket(self._bucket_name)
        blob = bucket.blob(object_path)
        blob.upload_from_string(data, content_type=content_type)


def build_png_object_path(
    *,
    run_id: str,
    timeframe: str,
    chart_template_id: str,
    generated_at_filename: str,
    symbol_slug: str,
) -> str:
    return (
        f"runs/{run_id}/charts/{timeframe}/{chart_template_id}/"
        f"{generated_at_filename}_{symbol_slug}_{timeframe}_{chart_template_id}.png"
    )


def build_manifest_object_path(*, run_id: str, step_id: str) -> str:
    return f"runs/{run_id}/steps/{step_id}/charts/manifest.json"


def gs_uri(*, bucket_gs: str, object_path: str) -> str:
    bucket = _parse_gs_bucket(bucket_gs)
    return f"gs://{bucket}/{object_path}"


def format_generated_at(dt: datetime) -> GeneratedAt:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    rfc3339 = dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    filename_stamp = dt.strftime("%Y%m%d-%H%M%S")
    return GeneratedAt(rfc3339=rfc3339, filename_stamp=filename_stamp)


def upload_pngs(
    *,
    uploader: GcsUploader,
    run_id: str,
    inputs: Sequence[PngUploadInput],
) -> PngUploadResult:
    items: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for entry in inputs:
        object_path = build_png_object_path(
            run_id=run_id,
            timeframe=entry.timeframe,
            chart_template_id=entry.chart_template_id,
            generated_at_filename=entry.generated_at.filename_stamp,
            symbol_slug=entry.symbol_slug,
        )
        try:
            uploader.upload_bytes(
                object_path=object_path,
                data=entry.png_bytes,
                content_type="image/png",
            )
        except Exception as exc:
            failures.append(
                {
                    "request": {"chartTemplateId": entry.chart_template_id},
                    "error": {
                        "code": "GCS_WRITE_FAILED",
                        "message": "Failed to write PNG to GCS",
                        "details": {
                            "objectPath": object_path,
                            "error": type(exc).__name__,
                        },
                    },
                }
            )
            continue

        items.append(
            {
                "chartTemplateId": entry.chart_template_id,
                "kind": entry.kind,
                "generatedAt": entry.generated_at.rfc3339,
                "png_gcs_uri": gs_uri(bucket_gs=uploader.bucket_gs, object_path=object_path),
            }
        )

    return PngUploadResult(items=items, failures=failures)


def build_manifest(
    *,
    run_id: str,
    step_id: str,
    created_at: str,
    symbol: str,
    timeframe: str,
    min_images: int,
    requested: Sequence[Mapping[str, Any]],
    items: Sequence[Mapping[str, Any]],
    failures: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "schemaVersion": 1,
        "runId": run_id,
        "stepId": step_id,
        "createdAt": created_at,
        "symbol": symbol,
        "timeframe": timeframe,
        "minImages": min_images,
        "requested": [dict(r) for r in requested],
        "items": [dict(item) for item in items],
    }
    if failures:
        manifest["failures"] = [dict(failure) for failure in failures]
    return manifest


def validate_manifest(
    *, manifest: Mapping[str, Any], schema_path: Path | None = None
) -> StepError | None:
    schema = _load_manifest_schema(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(manifest), key=lambda e: list(e.path))
    if not errors:
        return None
    error = errors[0]
    return StepError(
        code="VALIDATION_FAILED",
        message=error.message,
        details={"path": list(error.path)},
    )


def write_manifest(
    *,
    uploader: GcsUploader,
    run_id: str,
    step_id: str,
    manifest: Mapping[str, Any],
) -> tuple[str | None, StepError | None]:
    object_path = build_manifest_object_path(run_id=run_id, step_id=step_id)
    try:
        payload = json.dumps(manifest, ensure_ascii=False).encode("utf-8")
        uploader.upload_bytes(
            object_path=object_path,
            data=payload,
            content_type="application/json",
        )
    except Exception as exc:
        return None, StepError(
            code="MANIFEST_WRITE_FAILED",
            message="Failed to write manifest to GCS",
            details={"objectPath": object_path, "error": type(exc).__name__},
        )
    return gs_uri(bucket_gs=uploader.bucket_gs, object_path=object_path), None


def _load_manifest_schema(schema_path: Path | None) -> dict[str, Any]:
    path = schema_path or MANIFEST_SCHEMA_PATH
    raw = path.read_text("utf-8")
    return json.loads(raw)


def _parse_gs_bucket(value: str) -> str:
    bucket = value.strip()
    if bucket.startswith("gs://"):
        bucket = bucket.removeprefix("gs://")
    if bucket == "" or "/" in bucket:
        raise ValueError("Expected bucket name or gs://<bucket>")
    return bucket
