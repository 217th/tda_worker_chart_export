from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

try:  # pragma: no cover - optional dependency for runtime HTTP
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

from .config import ChartImgAccount, ChartsApiMode
from .logging import log_event


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
NON_RETRIABLE_STATUSES = {400, 401, 403, 404, 409, 422}
RETRIABLE_STATUSES = {500, 504}


DEFAULT_FIXTURES_DIR = Path(
    "docs-worker-chart-export/fixtures/chart-api/chart-img/advanced-chart-v2"
)


@dataclass(frozen=True, slots=True)
class ChartImgRequest:
    chart_template_id: str
    chart_img_symbol: str
    timeframe: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ChartApiError:
    code: str
    message: str
    http_status: int | None = None
    retriable: bool = False
    details: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ChartApiResult:
    ok: bool
    png_bytes: bytes | None = None
    error: ChartApiError | None = None
    http_status: int | None = None
    from_fixture: bool = False
    fixture_path: str | None = None


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status_code: int
    headers: dict[str, str]
    content: bytes


class HttpRequestError(Exception):
    def __init__(self, message: str, *, is_timeout: bool = False) -> None:
        super().__init__(message)
        self.is_timeout = is_timeout


class HttpRequester(Protocol):
    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json_body: Mapping[str, Any],
        timeout: float,
    ) -> HttpResponse:  # pragma: no cover - protocol
        raise NotImplementedError


class HttpxRequester:
    def __init__(self, client: httpx.Client | None = None) -> None:
        if httpx is None:
            raise RuntimeError("httpx is required for HttpxRequester")
        self._client = client or httpx.Client()

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json_body: Mapping[str, Any],
        timeout: float,
    ) -> HttpResponse:
        try:
            response = self._client.post(
                url, headers=dict(headers), json=json_body, timeout=timeout
            )
        except httpx.TimeoutException as exc:
            raise HttpRequestError("Chart-IMG request timed out", is_timeout=True) from exc
        except httpx.HTTPError as exc:
            raise HttpRequestError("Chart-IMG request failed") from exc

        headers_out = {k.lower(): v for k, v in response.headers.items()}
        return HttpResponse(
            status_code=response.status_code,
            headers=headers_out,
            content=response.content,
        )


class ChartImgClient:
    def __init__(
        self,
        *,
        mode: ChartsApiMode,
        base_url: str = "https://api.chart-img.com",
        fixtures_dir: Path | None = None,
        http: HttpRequester | None = None,
        timeout_sec: float = 30.0,
    ) -> None:
        self._mode = mode
        self._base_url = base_url.rstrip("/")
        self._fixtures_dir = fixtures_dir or DEFAULT_FIXTURES_DIR
        self._http = http
        self._timeout = timeout_sec

    @property
    def fixtures_dir(self) -> Path:
        return self._fixtures_dir

    def fetch(
        self,
        *,
        account: ChartImgAccount,
        request: ChartImgRequest,
        logger: logging.Logger | None = None,
        log_context: Mapping[str, Any] | None = None,
    ) -> ChartApiResult:
        if self._mode == "mock":
            return _load_fixture(
                request=request,
                fixtures_dir=self._fixtures_dir,
                logger=logger,
                log_context=log_context,
            )

        if self._mode == "record":
            existing = _load_fixture(
                request=request,
                fixtures_dir=self._fixtures_dir,
                logger=logger,
                log_context=log_context,
                allow_missing=True,
            )
            if existing is not None:
                return existing

        result = self._fetch_real(account=account, request=request)
        if self._mode == "record":
            _record_fixture(request=request, result=result, fixtures_dir=self._fixtures_dir)
        return result

    def _fetch_real(
        self,
        *,
        account: ChartImgAccount,
        request: ChartImgRequest,
    ) -> ChartApiResult:
        if self._http is None:
            raise RuntimeError("HttpRequester is required for real/record modes")

        url = f"{self._base_url}/v2/tradingview/advanced-chart"
        headers = {"x-api-key": account.api_key}

        try:
            response = self._http.post(
                url,
                headers=headers,
                json_body=request.payload,
                timeout=self._timeout,
            )
        except HttpRequestError as exc:
            error = ChartApiError(
                code="CHART_API_FAILED",
                message=str(exc),
                retriable=True,
                details={"reason": "timeout"} if exc.is_timeout else {"reason": "network"},
            )
            return ChartApiResult(ok=False, error=error)

        return _handle_http_response(
            response=response,
            chart_template_id=request.chart_template_id,
            chart_img_symbol=request.chart_img_symbol,
        )


def fetch_with_retries(
    *,
    client: ChartImgClient,
    request: ChartImgRequest,
    select_account: Callable[[], ChartImgAccount | None],
    mark_account_exhausted: Callable[[ChartImgAccount], None] | None = None,
    max_attempts: int = 3,
    backoff_base_seconds: float = 0.5,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> ChartApiResult:
    last_error: ChartApiError | None = None
    attempts = 0

    while attempts < max_attempts:
        account = select_account()
        if account is None:
            error = ChartApiError(
                code="CHART_API_LIMIT_EXCEEDED",
                message="No Chart-IMG accounts available",
                retriable=False,
            )
            return ChartApiResult(ok=False, error=error)

        attempts += 1
        result = client.fetch(account=account, request=request)
        if result.ok:
            return result

        last_error = result.error
        if last_error is None:
            return result

        if last_error.code == "CHART_API_LIMIT_EXCEEDED":
            if mark_account_exhausted is not None:
                mark_account_exhausted(account)
            continue

        if not last_error.retriable or attempts >= max_attempts:
            return result

        sleep_fn(backoff_base_seconds * (2 ** (attempts - 1)))

    if last_error is not None:
        return ChartApiResult(ok=False, error=last_error)

    return ChartApiResult(
        ok=False,
        error=ChartApiError(
            code="CHART_API_FAILED",
            message="Chart-IMG request failed after retries",
            retriable=False,
        ),
    )


def _handle_http_response(
    *,
    response: HttpResponse,
    chart_template_id: str,
    chart_img_symbol: str,
) -> ChartApiResult:
    status = response.status_code
    headers = response.headers
    content = response.content

    if status == 200:
        if _is_png_bytes(content):
            return ChartApiResult(
                ok=True, png_bytes=content, http_status=status, from_fixture=False
            )
        error = ChartApiError(
            code="CHART_API_FAILED",
            message="Chart-IMG returned HTTP 200 with non-PNG body",
            http_status=status,
            retriable=False,
            details={"contentType": headers.get("content-type")},
        )
        return ChartApiResult(ok=False, error=error, http_status=status)

    body = _parse_json_body(content)
    message = _extract_error_message(body)
    if _is_limit_exceeded(status, message):
        error = ChartApiError(
            code="CHART_API_LIMIT_EXCEEDED",
            message=message or "Chart-IMG limit exceeded",
            http_status=status,
            retriable=True,
            details=_error_details(body, chart_template_id, chart_img_symbol),
        )
        return ChartApiResult(ok=False, error=error, http_status=status)

    retriable = status in RETRIABLE_STATUSES
    error = ChartApiError(
        code="CHART_API_FAILED",
        message=message or "Chart-IMG request failed",
        http_status=status,
        retriable=retriable,
        details=_error_details(body, chart_template_id, chart_img_symbol),
    )
    return ChartApiResult(ok=False, error=error, http_status=status)


def _error_details(
    body: Any, chart_template_id: str, chart_img_symbol: str
) -> dict[str, Any]:
    details: dict[str, Any] = {
        "chartTemplateId": chart_template_id,
        "chartImgSymbol": chart_img_symbol,
    }
    if body is not None:
        details["response"] = body
    return details


def _is_limit_exceeded(status: int, message: str | None) -> bool:
    if status == 429:
        return True
    if message is None:
        return False
    return "limit exceeded" in message.lower()


def _parse_json_body(content: bytes) -> Any:
    if not content:
        return None
    try:
        return json.loads(content.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def _extract_error_message(body: Any) -> str | None:
    if isinstance(body, dict):
        message = body.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
        error = body.get("error")
        if isinstance(error, str) and error.strip():
            return error.strip()
        errors = body.get("errors")
        if isinstance(errors, list):
            parts = []
            for item in errors:
                if isinstance(item, dict):
                    msg = item.get("message") or item.get("error")
                    if isinstance(msg, str) and msg.strip():
                        parts.append(msg.strip())
                elif isinstance(item, str) and item.strip():
                    parts.append(item.strip())
            if parts:
                return "; ".join(parts)
    if isinstance(body, str) and body.strip():
        return body.strip()
    return None


def _is_png_bytes(content: bytes) -> bool:
    return content.startswith(PNG_SIGNATURE)


def _fixture_stem(request: ChartImgRequest) -> str:
    symbol = request.chart_img_symbol.replace(":", "_")
    return f"{symbol}__{request.timeframe}__{request.chart_template_id}"


def _load_fixture(
    *,
    request: ChartImgRequest,
    fixtures_dir: Path,
    logger: logging.Logger | None = None,
    log_context: Mapping[str, Any] | None = None,
    allow_missing: bool = False,
) -> ChartApiResult | None:
    stem = _fixture_stem(request)
    png_path = fixtures_dir / f"{stem}.png"
    if png_path.exists():
        content = png_path.read_bytes()
        if not _is_png_bytes(content):
            error = ChartApiError(
                code="CHART_API_FAILED",
                message="Fixture PNG is invalid",
                retriable=False,
                details={"fixturePath": str(png_path)},
            )
            return ChartApiResult(ok=False, error=error, from_fixture=True)
        return ChartApiResult(
            ok=True,
            png_bytes=content,
            from_fixture=True,
            fixture_path=str(png_path),
        )

    error_fixture = _find_error_fixture(fixtures_dir, stem)
    if error_fixture is None:
        if allow_missing:
            return None
        error = ChartApiError(
            code="CHART_API_MOCK_MISSING",
            message="Chart-IMG fixture is missing",
            retriable=False,
            details={"fixtureStem": stem, "fixturesDir": str(fixtures_dir)},
        )
        if logger is not None:
            payload: dict[str, Any] = {
                "error": {"code": "CHART_API_MOCK_MISSING"},
                "fixtureStem": stem,
                "fixturesDir": str(fixtures_dir),
            }
            if log_context:
                payload.update(log_context)
            log_event(logger, "chart_api_mock_missing", **payload)
        return ChartApiResult(ok=False, error=error, from_fixture=True)

    return _load_error_fixture(
        path=error_fixture,
        chart_template_id=request.chart_template_id,
        chart_img_symbol=request.chart_img_symbol,
    )


def _find_error_fixture(fixtures_dir: Path, stem: str) -> Path | None:
    pattern = f"{stem}__*.json"
    matches = sorted(fixtures_dir.glob(pattern))
    if not matches:
        return None
    return matches[0]


def _load_error_fixture(
    *,
    path: Path,
    chart_template_id: str,
    chart_img_symbol: str,
) -> ChartApiResult:
    try:
        payload = json.loads(path.read_text("utf-8"))
    except (ValueError, UnicodeDecodeError):
        payload = None

    status: int | None = None
    body: Any = payload
    if isinstance(payload, dict) and "status" in payload and "body" in payload:
        raw_status = payload.get("status")
        if isinstance(raw_status, int):
            status = raw_status
        elif isinstance(raw_status, str) and raw_status.isdigit():
            status = int(raw_status)
        body = payload.get("body")

    if status is None:
        status = _parse_status_from_filename(path.name)

    message = _extract_error_message(body)
    if status is not None and _is_limit_exceeded(status, message):
        error = ChartApiError(
            code="CHART_API_LIMIT_EXCEEDED",
            message=message or "Chart-IMG limit exceeded",
            http_status=status,
            retriable=True,
            details=_error_details(body, chart_template_id, chart_img_symbol),
        )
        return ChartApiResult(ok=False, error=error, from_fixture=True, fixture_path=str(path))

    retriable = status in RETRIABLE_STATUSES if status is not None else False
    error = ChartApiError(
        code="CHART_API_FAILED",
        message=message or "Chart-IMG request failed",
        http_status=status,
        retriable=retriable,
        details=_error_details(body, chart_template_id, chart_img_symbol),
    )
    return ChartApiResult(ok=False, error=error, from_fixture=True, fixture_path=str(path))


def _parse_status_from_filename(filename: str) -> int | None:
    parts = filename.rsplit("__", 1)
    if len(parts) != 2:
        return None
    suffix = parts[1]
    if not suffix.endswith(".json"):
        return None
    suffix = suffix[:-5]
    digits = ""
    for ch in suffix:
        if ch.isdigit():
            digits += ch
        else:
            break
    if digits:
        try:
            return int(digits)
        except ValueError:
            return None
    return None


def _record_fixture(
    *,
    request: ChartImgRequest,
    result: ChartApiResult,
    fixtures_dir: Path,
) -> None:
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    stem = _fixture_stem(request)

    if result.ok and result.png_bytes is not None:
        path = fixtures_dir / f"{stem}.png"
        path.write_bytes(result.png_bytes)
        return

    error = result.error
    if error is None:
        return

    status = error.http_status or 0
    message = error.message or "ERROR"
    slug = _slugify_error(message)
    filename = f"{stem}__{status}_{slug}.json"
    path = fixtures_dir / filename
    payload = {
        "status": error.http_status,
        "body": error.details.get("response") if error.details else None,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")


def _slugify_error(message: str) -> str:
    cleaned = []
    last_was_sep = False
    for ch in message.upper():
        if ch.isalnum():
            cleaned.append(ch)
            last_was_sep = False
        else:
            if not last_was_sep:
                cleaned.append("_")
                last_was_sep = True
    slug = "".join(cleaned).strip("_")
    return slug or "ERROR"
