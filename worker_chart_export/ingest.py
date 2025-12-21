from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class FlowRunEvent:
    run_id: str
    flow_run: dict[str, Any]
    event_id: str | None
    event_type: str | None
    subject: str | None


def get_cloud_event_attr(cloud_event: Any, key: str, default: Any = None) -> Any:
    if cloud_event is None:
        return default
    if isinstance(cloud_event, dict):
        return cloud_event.get(key, default)
    getter = getattr(cloud_event, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(cloud_event, key, default)


def is_firestore_update_event(event_type: str | None) -> bool:
    if not event_type:
        return False
    return event_type.endswith(".updated")


def parse_flow_run_event(cloud_event: Any) -> FlowRunEvent | None:
    event_id = get_cloud_event_attr(cloud_event, "id")
    event_type = get_cloud_event_attr(cloud_event, "type")
    subject = get_cloud_event_attr(cloud_event, "subject")
    data = get_cloud_event_attr(cloud_event, "data")
    data = _normalize_event_data(data)

    if not isinstance(data, Mapping):
        return None

    doc_path = _extract_doc_path(subject, data)
    if not doc_path:
        return None

    run_id = _extract_run_id(doc_path)
    if not run_id:
        return None

    value = data.get("value")
    fields = value.get("fields") if isinstance(value, Mapping) else None
    flow_run = decode_firestore_fields(fields) if isinstance(fields, Mapping) else {}

    return FlowRunEvent(
        run_id=run_id,
        flow_run=flow_run,
        event_id=event_id,
        event_type=event_type,
        subject=subject,
    )


def extract_run_id_from_subject(subject: str | None) -> str | None:
    doc_path = _extract_doc_path(subject, {})
    if not doc_path:
        return None
    return _extract_run_id(doc_path)


def _normalize_event_data(data: Any) -> Any:
    if isinstance(data, (bytes, bytearray)):
        try:
            return json.loads(data.decode("utf-8"))
        except Exception:
            return data
    if isinstance(data, str):
        try:
            return json.loads(data)
        except Exception:
            return data
    return data


def pick_ready_chart_export_step(flow_run: Mapping[str, Any]) -> str | None:
    steps = flow_run.get("steps")
    if not isinstance(steps, Mapping):
        return None

    ready_steps: list[str] = []
    for step_id, step in steps.items():
        if not isinstance(step_id, str):
            continue
        if not isinstance(step, Mapping):
            continue
        if step.get("stepType") != "CHART_EXPORT":
            continue
        if step.get("status") != "READY":
            continue
        ready_steps.append(step_id)

    if not ready_steps:
        return None

    return sorted(ready_steps)[0]


def decode_firestore_fields(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {key: decode_firestore_value(value) for key, value in fields.items()}


def decode_firestore_value(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    if "stringValue" in value:
        return value["stringValue"]
    if "integerValue" in value:
        try:
            return int(value["integerValue"])
        except Exception:
            return value["integerValue"]
    if "doubleValue" in value:
        try:
            return float(value["doubleValue"])
        except Exception:
            return value["doubleValue"]
    if "booleanValue" in value:
        return bool(value["booleanValue"])
    if "nullValue" in value:
        return None
    if "timestampValue" in value:
        return value["timestampValue"]
    if "bytesValue" in value:
        return value["bytesValue"]
    if "mapValue" in value:
        map_value = value.get("mapValue") or {}
        fields = map_value.get("fields")
        if isinstance(fields, Mapping):
            return decode_firestore_fields(fields)
        return {}
    if "arrayValue" in value:
        array_value = value.get("arrayValue") or {}
        values = array_value.get("values")
        if isinstance(values, list):
            return [decode_firestore_value(item) for item in values]
        return []
    return dict(value)


def _extract_doc_path(subject: str | None, data: Mapping[str, Any]) -> str | None:
    if isinstance(subject, str):
        if "/documents/flow_runs/" in subject:
            return subject
        if "documents/flow_runs/" in subject:
            return f"/{subject}"
    value = data.get("value")
    name = value.get("name") if isinstance(value, Mapping) else None
    if isinstance(name, str) and "/documents/flow_runs/" in name:
        return name
    return None


def _extract_run_id(doc_path: str) -> str | None:
    marker = "/documents/flow_runs/"
    if marker not in doc_path:
        return None
    tail = doc_path.split(marker, 1)[1]
    run_id = tail.split("/", 1)[0]
    return run_id or None
