import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from worker_chart_export.gcs_artifacts import (
    GeneratedAt,
    PngUploadInput,
    build_manifest,
    build_manifest_object_path,
    build_png_object_path,
    format_generated_at,
    gs_uri,
    upload_pngs,
    validate_manifest,
    write_manifest,
)


@dataclass
class FakeUploader:
    bucket_gs: str
    fail_paths: set[str]
    uploads: list[str]

    def upload_bytes(self, *, object_path: str, data: bytes, content_type: str) -> None:
        _ = data
        _ = content_type
        if object_path in self.fail_paths:
            raise RuntimeError("boom")
        self.uploads.append(object_path)


class TestGcsArtifacts(unittest.TestCase):
    def test_png_path_and_gs_uri(self) -> None:
        generated = GeneratedAt(rfc3339="2025-12-18T12:34:56Z", filename_stamp="20251218-123456")
        path = build_png_object_path(
            run_id="20251218-123456_BTCUSDT_abcd",
            timeframe="1h",
            chart_template_id="ctpl_price_psar_adi_v1",
            generated_at_filename=generated.filename_stamp,
            symbol_slug="BTCUSDT",
        )
        self.assertEqual(
            path,
            "runs/20251218-123456_BTCUSDT_abcd/charts/1h/ctpl_price_psar_adi_v1/"
            "20251218-123456_BTCUSDT_1h_ctpl_price_psar_adi_v1.png",
        )
        uri = gs_uri(bucket_gs="gs://charts-bucket", object_path=path)
        self.assertEqual(
            uri,
            "gs://charts-bucket/runs/20251218-123456_BTCUSDT_abcd/charts/1h/"
            "ctpl_price_psar_adi_v1/20251218-123456_BTCUSDT_1h_ctpl_price_psar_adi_v1.png",
        )

    def test_upload_pngs_partial_failure(self) -> None:
        generated = GeneratedAt(rfc3339="2025-12-18T12:34:56Z", filename_stamp="20251218-123456")
        inputs = [
            PngUploadInput(
                chart_template_id="ctpl_a",
                kind="kind-a",
                png_bytes=b"png-a",
                generated_at=generated,
                symbol_slug="BTCUSDT",
                timeframe="1h",
            ),
            PngUploadInput(
                chart_template_id="ctpl_b",
                kind="kind-b",
                png_bytes=b"png-b",
                generated_at=generated,
                symbol_slug="BTCUSDT",
                timeframe="1h",
            ),
        ]
        fail_path = build_png_object_path(
            run_id="run-1",
            timeframe="1h",
            chart_template_id="ctpl_b",
            generated_at_filename=generated.filename_stamp,
            symbol_slug="BTCUSDT",
        )
        uploader = FakeUploader(bucket_gs="gs://charts", fail_paths={fail_path}, uploads=[])
        result = upload_pngs(uploader=uploader, run_id="run-1", inputs=inputs)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(len(result.failures), 1)
        failure = result.failures[0]
        self.assertEqual(failure["error"]["code"], "GCS_WRITE_FAILED")
        self.assertEqual(failure["request"]["chartTemplateId"], "ctpl_b")

    def test_manifest_validation_failure(self) -> None:
        manifest = {
            "schemaVersion": 1,
            "stepId": "step1",
            "createdAt": "2025-12-18T12:34:56Z",
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "minImages": 1,
            "requested": [{"chartTemplateId": "ctpl_a"}],
            "items": [],
        }
        error = validate_manifest(manifest=manifest)
        self.assertIsNotNone(error)
        self.assertEqual(error.code, "VALIDATION_FAILED")

    def test_manifest_write_failure(self) -> None:
        manifest = build_manifest(
            run_id="run-1",
            step_id="step1",
            created_at="2025-12-18T12:34:56Z",
            symbol="BTCUSDT",
            timeframe="1h",
            min_images=1,
            requested=[{"chartTemplateId": "ctpl_a"}],
            items=[],
            failures=[],
        )
        object_path = build_manifest_object_path(run_id="run-1", step_id="step1")
        uploader = FakeUploader(bucket_gs="gs://charts", fail_paths={object_path}, uploads=[])
        uri, error = write_manifest(
            uploader=uploader, run_id="run-1", step_id="step1", manifest=manifest
        )
        self.assertIsNone(uri)
        self.assertIsNotNone(error)
        self.assertEqual(error.code, "MANIFEST_WRITE_FAILED")

    def test_manifest_does_not_include_signed_fields(self) -> None:
        generated = format_generated_at(datetime(2025, 12, 18, 12, 34, 56, tzinfo=timezone.utc))
        uploader = FakeUploader(bucket_gs="gs://charts", fail_paths=set(), uploads=[])
        result = upload_pngs(
            uploader=uploader,
            run_id="run-1",
            inputs=[
                PngUploadInput(
                    chart_template_id="ctpl_a",
                    kind="kind-a",
                    png_bytes=b"png",
                    generated_at=generated,
                    symbol_slug="BTCUSDT",
                    timeframe="1h",
                )
            ],
        )
        item = result.items[0]
        self.assertNotIn("signed_url", item)
        self.assertNotIn("expires_at", item)

    def test_manifest_overwrite_path_stable(self) -> None:
        manifest = build_manifest(
            run_id="run-1",
            step_id="step1",
            created_at="2025-12-18T12:34:56Z",
            symbol="BTCUSDT",
            timeframe="1h",
            min_images=1,
            requested=[{"chartTemplateId": "ctpl_a"}],
            items=[],
            failures=[],
        )
        uploader = FakeUploader(bucket_gs="gs://charts", fail_paths=set(), uploads=[])
        write_manifest(uploader=uploader, run_id="run-1", step_id="step1", manifest=manifest)
        write_manifest(uploader=uploader, run_id="run-1", step_id="step1", manifest=manifest)
        expected_path = build_manifest_object_path(run_id="run-1", step_id="step1")
        self.assertEqual(uploader.uploads.count(expected_path), 2)


if __name__ == "__main__":
    unittest.main()
