from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .orchestration import StepError


@dataclass(frozen=True, slots=True)
class ChartTemplate:
    chart_template_id: str
    description: str
    chart_img_symbol_template: str
    request: dict[str, Any]


@dataclass(frozen=True, slots=True)
class BuiltChartRequest:
    chart_template_id: str
    kind: str
    chart_img_symbol: str
    interval: str
    request: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RequestFailure:
    chart_template_id: str
    error: StepError


@dataclass(frozen=True, slots=True)
class BuildRequestsResult:
    items: list[BuiltChartRequest]
    failures: list[RequestFailure]
    validation_error: StepError | None = None


class ChartTemplateStore(Protocol):
    def get(self, chart_template_id: str) -> Mapping[str, Any] | None:  # pragma: no cover
        raise NotImplementedError


class FirestoreChartTemplateStore:
    def __init__(self, client: Any) -> None:
        self._client = client

    def get(self, chart_template_id: str) -> Mapping[str, Any] | None:
        doc = self._client.collection("chart_templates").document(chart_template_id).get()
        if getattr(doc, "exists", True) is False:
            return None
        data = doc.to_dict() if doc is not None else None
        return data if isinstance(data, Mapping) else None


def validate_requests(
    *, requests: list[Mapping[str, Any]], min_images: int | None
) -> StepError | None:
    if min_images is not None and min_images > len(requests):
        return StepError(
            code="VALIDATION_FAILED",
            message="minImages cannot exceed number of requests",
            details={"minImages": min_images, "requestsCount": len(requests)},
        )

    seen: set[str] = set()
    duplicates: set[str] = set()
    for req in requests:
        chart_template_id = req.get("chartTemplateId") if isinstance(req, Mapping) else None
        if isinstance(chart_template_id, str):
            if chart_template_id in seen:
                duplicates.add(chart_template_id)
            seen.add(chart_template_id)
    if duplicates:
        return StepError(
            code="VALIDATION_FAILED",
            message="Duplicate chartTemplateId values in requests",
            details={"chartTemplateIds": sorted(duplicates)},
        )

    return None


def build_chart_requests(
    *,
    requests: list[Mapping[str, Any]],
    scope_symbol: str,
    timeframe: str,
    default_timezone: str,
    template_store: ChartTemplateStore,
    min_images: int | None = None,
) -> BuildRequestsResult:
    validation_error = validate_requests(requests=requests, min_images=min_images)
    if validation_error is not None:
        return BuildRequestsResult(items=[], failures=[], validation_error=validation_error)

    if not _is_valid_scope_symbol(scope_symbol):
        return BuildRequestsResult(
            items=[],
            failures=[],
            validation_error=StepError(
                code="VALIDATION_FAILED",
                message="scope.symbol must be a non-empty base symbol without '/'",
                details={"scopeSymbol": scope_symbol},
            ),
        )

    items: list[BuiltChartRequest] = []
    failures: list[RequestFailure] = []

    for req in requests:
        chart_template_id = _extract_chart_template_id(req)
        if chart_template_id is None:
            failures.append(
                RequestFailure(
                    chart_template_id="",
                    error=StepError(
                        code="VALIDATION_FAILED",
                        message="chartTemplateId is required",
                    ),
                )
            )
            continue

        template_data = template_store.get(chart_template_id)
        if template_data is None:
            failures.append(
                RequestFailure(
                    chart_template_id=chart_template_id,
                    error=StepError(
                        code="VALIDATION_FAILED",
                        message="Chart template not found",
                        details={"chartTemplateId": chart_template_id},
                    ),
                )
            )
            continue

        parsed = parse_chart_template(template_data, chart_template_id)
        if isinstance(parsed, StepError):
            failures.append(RequestFailure(chart_template_id=chart_template_id, error=parsed))
            continue

        chart_img_symbol = render_chart_img_symbol(
            parsed.chart_img_symbol_template, scope_symbol
        )
        if chart_img_symbol is None:
            failures.append(
                RequestFailure(
                    chart_template_id=chart_template_id,
                    error=StepError(
                        code="VALIDATION_FAILED",
                        message="chartImgSymbolTemplate must include {symbol}",
                        details={"chartTemplateId": chart_template_id},
                    ),
                )
            )
            continue

        request_payload = copy.deepcopy(parsed.request)
        request_payload["symbol"] = chart_img_symbol
        request_payload["interval"] = timeframe
        request_payload["timezone"] = default_timezone

        items.append(
            BuiltChartRequest(
                chart_template_id=chart_template_id,
                kind=parsed.description,
                chart_img_symbol=chart_img_symbol,
                interval=timeframe,
                request=request_payload,
            )
        )

    return BuildRequestsResult(items=items, failures=failures)


def parse_chart_template(
    raw: Mapping[str, Any], chart_template_id: str
) -> ChartTemplate | StepError:
    description = raw.get("description")
    if not isinstance(description, str) or description.strip() == "":
        return StepError(
            code="VALIDATION_FAILED",
            message="Template description must be a non-empty string",
            details={"chartTemplateId": chart_template_id},
        )

    symbol_template = raw.get("chartImgSymbolTemplate")
    if not isinstance(symbol_template, str) or symbol_template.strip() == "":
        return StepError(
            code="VALIDATION_FAILED",
            message="chartImgSymbolTemplate is required",
            details={"chartTemplateId": chart_template_id},
        )

    request = raw.get("request")
    if not isinstance(request, Mapping):
        return StepError(
            code="VALIDATION_FAILED",
            message="Template request must be an object",
            details={"chartTemplateId": chart_template_id},
        )

    return ChartTemplate(
        chart_template_id=chart_template_id,
        description=description,
        chart_img_symbol_template=symbol_template,
        request=dict(request),
    )


def render_chart_img_symbol(symbol_template: str, scope_symbol: str) -> str | None:
    if "{symbol}" not in symbol_template:
        return None
    return symbol_template.replace("{symbol}", scope_symbol)


def _extract_chart_template_id(req: Mapping[str, Any]) -> str | None:
    chart_template_id = req.get("chartTemplateId")
    if not isinstance(chart_template_id, str) or chart_template_id.strip() == "":
        return None
    return chart_template_id


def _is_valid_scope_symbol(scope_symbol: str) -> bool:
    if not isinstance(scope_symbol, str):
        return False
    stripped = scope_symbol.strip()
    if stripped == "":
        return False
    if "/" in stripped:
        return False
    if any(ch.isspace() for ch in stripped):
        return False
    return True
