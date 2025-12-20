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


class ClaimContentionError(Exception):
    pass


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
        try:
            result = _try_claim_account(client=client, account=account, now=now)
        except ClaimContentionError:
            if logger is not None:
                payload = {"accountId": account.id}
                if log_context:
                    payload.update(log_context)
                log_event(logger, "chart_api_usage_claim_conflict", **payload)
            continue
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
    logger = logging.getLogger("worker-chart-export")
    max_attempts = 3
    base_backoff = 0.2
    for attempt in range(max_attempts):
        snapshot = doc_ref.get()
        raw = snapshot.to_dict() if snapshot is not None else None
        data = raw if isinstance(raw, Mapping) else {}
        exists = isinstance(raw, Mapping)

        usage_today, window_start = _reset_window_if_needed(data, now)
        daily_limit = _resolve_daily_limit(account, data)
        update = {"windowStart": window_start, "usageToday": daily_limit}
        try:
            _write_usage_update(
                client=client,
                doc_ref=doc_ref,
                snapshot=snapshot,
                update=update,
                create_if_missing=not exists,
            )
            return AccountUsage(
                account_id=account.id,
                usage_today=daily_limit,
                daily_limit=daily_limit,
                window_start=window_start,
            )
        except Exception as exc:
            if _is_precondition_error(exc) or _is_aborted_error(exc):
                if attempt < max_attempts - 1:
                    time.sleep(base_backoff * (2**attempt))
                    continue
                log_event(
                    logger,
                    "usage_mark_exhausted_precondition_failed",
                    accountId=account.id,
                )
                return AccountUsage(
                    account_id=account.id,
                    usage_today=daily_limit,
                    daily_limit=daily_limit,
                    window_start=window_start,
                )
            raise
    return AccountUsage(
        account_id=account.id,
        usage_today=0,
        daily_limit=account.daily_limit or DEFAULT_CHART_IMG_DAILY_LIMIT,
        window_start=_utc_day_start(now),
    )


def _try_claim_account(
    *,
    client: Any,
    account: ChartImgAccount,
    now: datetime,
) -> AccountUsage | None:
    doc_ref = client.collection("chart_img_accounts_usage").document(account.id)
    max_attempts = 3
    base_backoff = 0.2
    for attempt in range(max_attempts):
        snapshot = doc_ref.get()
        raw = snapshot.to_dict() if snapshot is not None else None
        data = raw if isinstance(raw, Mapping) else {}
        exists = isinstance(raw, Mapping)

        usage_today, window_start = _reset_window_if_needed(data, now)
        daily_limit = _resolve_daily_limit(account, data)

        if usage_today >= daily_limit:
            if data.get("windowStart") != window_start or data.get("usageToday") != usage_today:
                update = {"windowStart": window_start, "usageToday": usage_today}
                try:
                    _write_usage_update(
                        client=client,
                        doc_ref=doc_ref,
                        snapshot=snapshot,
                        update=update,
                        create_if_missing=not exists,
                    )
                except Exception as exc:
                    if _is_precondition_error(exc) or _is_aborted_error(exc):
                        if attempt < max_attempts - 1:
                            time.sleep(base_backoff * (2**attempt))
                            continue
                    # Best-effort update for exhausted path.
            return None

        next_usage = usage_today + 1
        update = {"windowStart": window_start, "usageToday": next_usage}
        try:
            _write_usage_update(
                client=client,
                doc_ref=doc_ref,
                snapshot=snapshot,
                update=update,
                create_if_missing=not exists,
            )
            return AccountUsage(
                account_id=account.id,
                usage_today=next_usage,
                daily_limit=daily_limit,
                window_start=window_start,
            )
        except Exception as exc:
            if _is_precondition_error(exc) or _is_aborted_error(exc):
                if attempt < max_attempts - 1:
                    time.sleep(base_backoff * (2**attempt))
                    continue
                raise ClaimContentionError("usage claim precondition failed") from exc
            raise

    raise ClaimContentionError("usage claim precondition failed")


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


def _is_aborted_error(exc: Exception) -> bool:
    try:
        from google.api_core import exceptions as gax_exceptions
    except Exception:
        gax_exceptions = None
    if gax_exceptions is not None and isinstance(exc, gax_exceptions.Aborted):
        return True
    return exc.__class__.__name__ == "Aborted"


def _is_precondition_error(exc: Exception) -> bool:
    try:
        from google.api_core import exceptions as gax_exceptions
    except Exception:
        gax_exceptions = None
    if gax_exceptions is not None and isinstance(
        exc, (gax_exceptions.FailedPrecondition, gax_exceptions.Conflict)
    ):
        return True
    return exc.__class__.__name__ in ("FailedPrecondition", "PreconditionFailed", "Conflict")


def _write_usage_update(
    *,
    client: Any,
    doc_ref: Any,
    snapshot: Any,
    update: dict[str, Any],
    create_if_missing: bool,
) -> None:
    if create_if_missing:
        if hasattr(client, "write_option"):
            option = client.write_option(exists=False)
            doc_ref.set(update, merge=False, option=option)
        else:
            doc_ref.set(update, merge=False)
        return

    update_time = getattr(snapshot, "update_time", None)
    if update_time is not None and hasattr(client, "write_option"):
        option = client.write_option(last_update_time=update_time)
        doc_ref.update(update, option=option)
    else:
        doc_ref.update(update)
