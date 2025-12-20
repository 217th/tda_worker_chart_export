from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .config import ChartImgAccount, DEFAULT_CHART_IMG_DAILY_LIMIT
from .logging import log_event


@dataclass(frozen=True, slots=True)
class AccountUsage:
    account_id: str
    usage_today: int
    daily_limit: int
    window_start: str


@dataclass(frozen=True, slots=True)
class AccountSelectionResult:
    account: ChartImgAccount | None
    usage: AccountUsage | None
    exhausted_accounts: list[str]


def select_account_for_request(
    *,
    client: Any,
    accounts: Sequence[ChartImgAccount],
    now: datetime | None = None,
    logger: logging.Logger | None = None,
    log_context: Mapping[str, Any] | None = None,
) -> AccountSelectionResult:
    now = now or datetime.now(timezone.utc)
    exhausted: list[str] = []

    for account in accounts:
        result = _try_claim_account(client=client, account=account, now=now)
        if result is None:
            exhausted.append(account.id)
            continue
        return AccountSelectionResult(account=account, usage=result, exhausted_accounts=exhausted)

    if exhausted and logger is not None:
        payload = {
            "error": {"code": "CHART_API_LIMIT_EXCEEDED"},
            "exhaustedAccounts": exhausted,
        }
        if log_context:
            payload.update(log_context)
        log_event(logger, "chart_api_limit_exceeded", **payload)
    return AccountSelectionResult(account=None, usage=None, exhausted_accounts=exhausted)


def mark_account_exhausted(
    *,
    client: Any,
    account: ChartImgAccount,
    now: datetime | None = None,
) -> AccountUsage:
    now = now or datetime.now(timezone.utc)
    doc_ref = client.collection("chart_img_accounts_usage").document(account.id)

    def _mark(transaction: Any) -> AccountUsage:
        snapshot = doc_ref.get(transaction=transaction)
        data = snapshot.to_dict() if snapshot is not None else None
        data = data if isinstance(data, Mapping) else {}

        usage_today, window_start = _reset_window_if_needed(data, now)
        daily_limit = _resolve_daily_limit(account, data)

        update = {
            "windowStart": window_start,
            "usageToday": daily_limit,
        }
        _transaction_set(transaction, doc_ref, update)
        return AccountUsage(
            account_id=account.id,
            usage_today=daily_limit,
            daily_limit=daily_limit,
            window_start=window_start,
        )

    return _run_transaction(client, _mark)


def _try_claim_account(
    *,
    client: Any,
    account: ChartImgAccount,
    now: datetime,
) -> AccountUsage | None:
    doc_ref = client.collection("chart_img_accounts_usage").document(account.id)

    def _claim(transaction: Any) -> AccountUsage | None:
        snapshot = doc_ref.get(transaction=transaction)
        data = snapshot.to_dict() if snapshot is not None else None
        data = data if isinstance(data, Mapping) else {}

        usage_today, window_start = _reset_window_if_needed(data, now)
        daily_limit = _resolve_daily_limit(account, data)

        if usage_today >= daily_limit:
            if data.get("windowStart") != window_start or data.get("usageToday") != usage_today:
                update = {"windowStart": window_start, "usageToday": usage_today}
                _transaction_set(transaction, doc_ref, update)
            return None

        usage_today += 1
        update = {"windowStart": window_start, "usageToday": usage_today}
        _transaction_set(transaction, doc_ref, update)
        return AccountUsage(
            account_id=account.id,
            usage_today=usage_today,
            daily_limit=daily_limit,
            window_start=window_start,
        )

    return _run_transaction(client, _claim)


def _resolve_daily_limit(account: ChartImgAccount, data: Mapping[str, Any]) -> int:
    doc_limit = data.get("dailyLimit")
    if isinstance(doc_limit, int) and doc_limit > 0:
        return doc_limit
    return account.daily_limit or DEFAULT_CHART_IMG_DAILY_LIMIT


def _reset_window_if_needed(data: Mapping[str, Any], now: datetime) -> tuple[int, str]:
    window_start_raw = data.get("windowStart")
    usage_today_raw = data.get("usageToday")
    usage_today = usage_today_raw if isinstance(usage_today_raw, int) and usage_today_raw >= 0 else 0

    window_start = _parse_rfc3339(window_start_raw)
    today_start = _utc_day_start(now)

    if window_start is None or window_start.date() != now.date():
        return 0, today_start

    return usage_today, window_start_raw if isinstance(window_start_raw, str) else today_start


def _parse_rfc3339(value: Any) -> datetime | None:
    if not isinstance(value, str) or value.strip() == "":
        return None
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _utc_day_start(now: datetime) -> str:
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    return start.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _transaction_set(transaction: Any, doc_ref: Any, update: dict[str, Any]) -> None:
    setter = getattr(transaction, "set", None)
    if callable(setter):
        setter(doc_ref, update, merge=True)
    else:
        transaction.update(doc_ref, update)


def _is_aborted_error(exc: Exception) -> bool:
    try:
        from google.api_core import exceptions as gax_exceptions
    except Exception:
        gax_exceptions = None
    if gax_exceptions is not None and isinstance(exc, gax_exceptions.Aborted):
        return True
    return exc.__class__.__name__ == "Aborted"


def _run_transaction(client: Any, fn: Any) -> Any:
    max_attempts = 5
    base_backoff = 0.2
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        transaction = client.transaction()
        begin = getattr(transaction, "_begin", None)
        try:
            if callable(begin):
                begin()
            result = fn(transaction)
            commit = getattr(transaction, "commit", None)
            if callable(commit):
                commit()
            return result
        except Exception as exc:
            last_exc = exc
            rollback = getattr(transaction, "_rollback", None)
            if callable(rollback):
                try:
                    rollback()
                except Exception:
                    pass
            if _is_aborted_error(exc) and attempt < max_attempts - 1:
                time.sleep(base_backoff * (2**attempt))
                continue
            raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("transaction failed without exception")
