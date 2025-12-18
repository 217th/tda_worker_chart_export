import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping

from worker_chart_export.chart_img import (
    ChartImgClient,
    ChartImgRequest,
    HttpRequestError,
    HttpRequester,
    HttpResponse,
    fetch_with_retries,
)
from worker_chart_export.config import ChartImgAccount, WorkerConfig
from worker_chart_export.errors import ConfigError


PNG_BYTES = b"\x89PNG\r\n\x1a\nTEST"


class FakeRequester(HttpRequester):
    def __init__(self, response: HttpResponse | None = None, *, raise_error: Exception | None = None) -> None:
        self._response = response
        self._raise_error = raise_error
        self.calls: list[dict[str, Any]] = []

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json_body: Mapping[str, Any],
        timeout: float,
    ) -> HttpResponse:
        self.calls.append(
            {"url": url, "headers": dict(headers), "json": dict(json_body), "timeout": timeout}
        )
        if self._raise_error is not None:
            raise self._raise_error
        assert self._response is not None
        return self._response


class TestChartImgClient(unittest.TestCase):
    def setUp(self) -> None:
        self.account = ChartImgAccount(id="acc1", api_key="secret")
        self.request = ChartImgRequest(
            chart_template_id="price_psar_adi_v1",
            chart_img_symbol="BINANCE:BTCUSDT",
            timeframe="1h",
            payload={"symbol": "BINANCE:BTCUSDT", "interval": "1h"},
        )

    def _fixture_stem(self) -> str:
        symbol = self.request.chart_img_symbol.replace(":", "_")
        return f"{symbol}__{self.request.timeframe}__{self.request.chart_template_id}"

    def test_mock_fixture_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixtures_dir = Path(tmp)
            png_path = fixtures_dir / f"{self._fixture_stem()}.png"
            png_path.write_bytes(PNG_BYTES)
            client = ChartImgClient(mode="mock", fixtures_dir=fixtures_dir)
            result = client.fetch(account=self.account, request=self.request)
            self.assertTrue(result.ok)
            self.assertEqual(result.png_bytes, PNG_BYTES)
            self.assertTrue(result.from_fixture)

    def test_mock_missing_fixture_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixtures_dir = Path(tmp)
            client = ChartImgClient(mode="mock", fixtures_dir=fixtures_dir)
            result = client.fetch(account=self.account, request=self.request)
            self.assertFalse(result.ok)
            self.assertEqual(result.error.code, "CHART_API_MOCK_MISSING")

    def test_mock_mode_does_not_call_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixtures_dir = Path(tmp)
            png_path = fixtures_dir / f"{self._fixture_stem()}.png"
            png_path.write_bytes(PNG_BYTES)
            requester = FakeRequester(
                raise_error=HttpRequestError("network should not be called")
            )
            client = ChartImgClient(mode="mock", fixtures_dir=fixtures_dir, http=requester)
            result = client.fetch(account=self.account, request=self.request)
            self.assertTrue(result.ok)
            self.assertEqual(len(requester.calls), 0)

    def test_http_200_non_png_is_failed(self) -> None:
        response = HttpResponse(
            status_code=200,
            headers={"content-type": "text/plain"},
            content=b"not-png",
        )
        requester = FakeRequester(response=response)
        client = ChartImgClient(mode="real", http=requester)
        result = client.fetch(account=self.account, request=self.request)
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "CHART_API_FAILED")
        self.assertFalse(result.error.retriable)

    def test_429_limit_exceeded(self) -> None:
        response = HttpResponse(
            status_code=429,
            headers={"content-type": "application/json"},
            content=b'{"message":"Limit Exceeded"}',
        )
        requester = FakeRequester(response=response)
        client = ChartImgClient(mode="real", http=requester)
        result = client.fetch(account=self.account, request=self.request)
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "CHART_API_LIMIT_EXCEEDED")
        self.assertTrue(result.error.retriable)

    def test_500_is_retriable(self) -> None:
        response = HttpResponse(
            status_code=500,
            headers={"content-type": "application/json"},
            content=b'{"message":"Something Went Wrong"}',
        )
        requester = FakeRequester(response=response)
        client = ChartImgClient(mode="real", http=requester)
        result = client.fetch(account=self.account, request=self.request)
        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "CHART_API_FAILED")
        self.assertTrue(result.error.retriable)

    def test_record_mode_saves_fixture(self) -> None:
        response = HttpResponse(
            status_code=200,
            headers={"content-type": "image/png"},
            content=PNG_BYTES,
        )
        requester = FakeRequester(response=response)
        with tempfile.TemporaryDirectory() as tmp:
            fixtures_dir = Path(tmp)
            client = ChartImgClient(mode="record", fixtures_dir=fixtures_dir, http=requester)
            result = client.fetch(account=self.account, request=self.request)
            self.assertTrue(result.ok)
            png_path = fixtures_dir / f"{self._fixture_stem()}.png"
            self.assertTrue(png_path.exists())
            self.assertEqual(len(requester.calls), 1)

    def test_record_mode_uses_fixture_if_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixtures_dir = Path(tmp)
            png_path = fixtures_dir / f"{self._fixture_stem()}.png"
            png_path.write_bytes(PNG_BYTES)
            requester = FakeRequester(
                raise_error=HttpRequestError("network should not be called")
            )
            client = ChartImgClient(mode="record", fixtures_dir=fixtures_dir, http=requester)
            result = client.fetch(account=self.account, request=self.request)
            self.assertTrue(result.ok)
            self.assertTrue(result.from_fixture)
            self.assertEqual(len(requester.calls), 0)

    def test_record_mode_not_allowed_in_prod(self) -> None:
        env = os.environ.copy()
        try:
            os.environ["CHARTS_BUCKET"] = "gs://test-bucket"
            os.environ["CHARTS_API_MODE"] = "record"
            os.environ["CHARTS_DEFAULT_TIMEZONE"] = "Etc/UTC"
            os.environ["CHART_IMG_ACCOUNTS_JSON"] = '[{"id":"acc1","apiKey":"k1"}]'
            os.environ["TDA_ENV"] = "prod"
            with self.assertRaises(ConfigError):
                WorkerConfig.from_env()
        finally:
            os.environ.clear()
            os.environ.update(env)


class TestChartImgRetries(unittest.TestCase):
    def setUp(self) -> None:
        self.account_a = ChartImgAccount(id="acc1", api_key="k1")
        self.account_b = ChartImgAccount(id="acc2", api_key="k2")
        self.request = ChartImgRequest(
            chart_template_id="price_psar_adi_v1",
            chart_img_symbol="BINANCE:BTCUSDT",
            timeframe="1h",
            payload={"symbol": "BINANCE:BTCUSDT", "interval": "1h"},
        )

    def test_max_attempts_across_accounts(self) -> None:
        response = HttpResponse(
            status_code=500,
            headers={"content-type": "application/json"},
            content=b'{"message":"Something Went Wrong"}',
        )
        requester = FakeRequester(response=response)
        client = ChartImgClient(mode="real", http=requester)

        accounts = [self.account_a, self.account_b]
        index = {"value": 0}

        def select_account() -> ChartImgAccount | None:
            if index["value"] >= len(accounts):
                return accounts[-1]
            acc = accounts[index["value"]]
            index["value"] += 1
            return acc

        result = fetch_with_retries(
            client=client,
            request=self.request,
            select_account=select_account,
            max_attempts=2,
            backoff_base_seconds=0,
            sleep_fn=lambda _: None,
        )
        self.assertFalse(result.ok)
        self.assertEqual(len(requester.calls), 2)

    def test_limit_exceeded_switches_account(self) -> None:
        responses = [
            HttpResponse(
                status_code=429,
                headers={"content-type": "application/json"},
                content=b'{"message":"Limit Exceeded"}',
            ),
            HttpResponse(
                status_code=200,
                headers={"content-type": "image/png"},
                content=PNG_BYTES,
            ),
        ]
        requester = FakeRequester(response=responses[0])
        client = ChartImgClient(mode="real", http=requester)

        accounts = [self.account_a, self.account_b]
        index = {"value": 0}
        exhausted: list[str] = []

        def select_account() -> ChartImgAccount | None:
            if index["value"] >= len(accounts):
                return None
            acc = accounts[index["value"]]
            index["value"] += 1
            return acc

        def mark_exhausted(account: ChartImgAccount) -> None:
            exhausted.append(account.id)
            requester._response = responses[1]

        result = fetch_with_retries(
            client=client,
            request=self.request,
            select_account=select_account,
            mark_account_exhausted=mark_exhausted,
            max_attempts=3,
            backoff_base_seconds=0,
            sleep_fn=lambda _: None,
        )
        self.assertTrue(result.ok)
        self.assertEqual(exhausted, ["acc1"])


if __name__ == "__main__":
    unittest.main()
