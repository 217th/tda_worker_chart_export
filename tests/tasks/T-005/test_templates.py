import unittest
from typing import Any, Mapping

from worker_chart_export.templates import (
    BuildRequestsResult,
    ChartTemplateStore,
    build_chart_requests,
    parse_chart_template,
)


class DictTemplateStore(ChartTemplateStore):
    def __init__(self, templates: dict[str, Mapping[str, Any]]):
        self._templates = templates

    def get(self, chart_template_id: str) -> Mapping[str, Any] | None:
        return self._templates.get(chart_template_id)


class TestTemplates(unittest.TestCase):
    def test_valid_template_builds_request(self) -> None:
        store = DictTemplateStore(
            {
                "ctpl_ok": {
                    "id": "ctpl_ok",
                    "description": "Price + Volume",
                    "chartImgSymbolTemplate": "BINANCE:{symbol}",
                    "request": {"theme": "dark", "style": "baseline"},
                }
            }
        )
        result = build_chart_requests(
            requests=[{"chartTemplateId": "ctpl_ok"}],
            scope_symbol="BTCUSDT",
            timeframe="1h",
            default_timezone="UTC",
            template_store=store,
            min_images=1,
        )
        self.assertIsNone(result.validation_error)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(len(result.items), 1)
        item = result.items[0]
        self.assertEqual(item.kind, "Price + Volume")
        self.assertEqual(item.chart_img_symbol, "BINANCE:BTCUSDT")
        self.assertEqual(item.interval, "1h")
        self.assertEqual(item.request["symbol"], "BINANCE:BTCUSDT")
        self.assertEqual(item.request["interval"], "1h")
        self.assertEqual(item.request["timezone"], "UTC")
        self.assertEqual(item.request["theme"], "dark")

    def test_template_overrides_symbol_interval_timezone(self) -> None:
        store = DictTemplateStore(
            {
                "ctpl_override": {
                    "id": "ctpl_override",
                    "description": "Override test",
                    "chartImgSymbolTemplate": "BYBIT:{symbol}.P",
                    "request": {
                        "symbol": "SHOULD_NOT_LEAK",
                        "interval": "99m",
                        "timezone": "Europe/Paris",
                        "style": "candle",
                    },
                }
            }
        )
        result = build_chart_requests(
            requests=[{"chartTemplateId": "ctpl_override"}],
            scope_symbol="ETHUSDT",
            timeframe="4h",
            default_timezone="UTC",
            template_store=store,
        )
        item = result.items[0]
        self.assertEqual(item.request["symbol"], "BYBIT:ETHUSDT.P")
        self.assertEqual(item.request["interval"], "4h")
        self.assertEqual(item.request["timezone"], "UTC")

    def test_missing_template_records_failure(self) -> None:
        store = DictTemplateStore({})
        result = build_chart_requests(
            requests=[{"chartTemplateId": "missing"}],
            scope_symbol="BTCUSDT",
            timeframe="1h",
            default_timezone="UTC",
            template_store=store,
        )
        self.assertEqual(len(result.items), 0)
        self.assertEqual(len(result.failures), 1)
        failure = result.failures[0]
        self.assertEqual(failure.chart_template_id, "missing")
        self.assertEqual(failure.error.code, "VALIDATION_FAILED")

    def test_invalid_template_schema_records_failure(self) -> None:
        store = DictTemplateStore({"bad": {"id": "bad", "description": "Bad"}})
        result = build_chart_requests(
            requests=[{"chartTemplateId": "bad"}],
            scope_symbol="BTCUSDT",
            timeframe="1h",
            default_timezone="UTC",
            template_store=store,
        )
        self.assertEqual(len(result.items), 0)
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(result.failures[0].error.code, "VALIDATION_FAILED")

    def test_partial_success_across_requests(self) -> None:
        store = DictTemplateStore(
            {
                "ctpl_ok": {
                    "id": "ctpl_ok",
                    "description": "Ok",
                    "chartImgSymbolTemplate": "BINANCE:{symbol}",
                    "request": {"theme": "light"},
                }
            }
        )
        result = build_chart_requests(
            requests=[
                {"chartTemplateId": "ctpl_ok"},
                {"chartTemplateId": "missing"},
            ],
            scope_symbol="BTCUSDT",
            timeframe="1d",
            default_timezone="UTC",
            template_store=store,
            min_images=1,
        )
        self.assertEqual(len(result.items), 1)
        self.assertEqual(len(result.failures), 1)
        self.assertIsNone(result.validation_error)

    def test_duplicate_chart_template_id_is_validation_error(self) -> None:
        store = DictTemplateStore(
            {
                "dup": {
                    "id": "dup",
                    "description": "Dup",
                    "chartImgSymbolTemplate": "BINANCE:{symbol}",
                    "request": {"theme": "dark"},
                }
            }
        )
        result = build_chart_requests(
            requests=[{"chartTemplateId": "dup"}, {"chartTemplateId": "dup"}],
            scope_symbol="BTCUSDT",
            timeframe="1h",
            default_timezone="UTC",
            template_store=store,
            min_images=1,
        )
        self.assertIsNotNone(result.validation_error)
        assert result.validation_error is not None
        self.assertEqual(result.validation_error.code, "VALIDATION_FAILED")

    def test_min_images_greater_than_requests_validation_error(self) -> None:
        store = DictTemplateStore(
            {
                "ctpl_ok": {
                    "id": "ctpl_ok",
                    "description": "Ok",
                    "chartImgSymbolTemplate": "BINANCE:{symbol}",
                    "request": {"theme": "dark"},
                }
            }
        )
        result = build_chart_requests(
            requests=[{"chartTemplateId": "ctpl_ok"}],
            scope_symbol="BTCUSDT",
            timeframe="1h",
            default_timezone="UTC",
            template_store=store,
            min_images=2,
        )
        self.assertIsNotNone(result.validation_error)
        assert result.validation_error is not None
        self.assertEqual(result.validation_error.code, "VALIDATION_FAILED")

    def test_description_with_spaces_plus_preserved_as_kind(self) -> None:
        store = DictTemplateStore(
            {
                "ctpl_kind": {
                    "id": "ctpl_kind",
                    "description": "Price + Volume",
                    "chartImgSymbolTemplate": "BINANCE:{symbol}",
                    "request": {},
                }
            }
        )
        result = build_chart_requests(
            requests=[{"chartTemplateId": "ctpl_kind"}],
            scope_symbol="BTCUSDT",
            timeframe="1h",
            default_timezone="UTC",
            template_store=store,
        )
        self.assertEqual(result.items[0].kind, "Price + Volume")

    def test_parse_template_requires_chart_img_symbol_template(self) -> None:
        error = parse_chart_template({"description": "X", "request": {}}, "ctpl")
        self.assertEqual(error.code, "VALIDATION_FAILED")


if __name__ == "__main__":
    unittest.main()
