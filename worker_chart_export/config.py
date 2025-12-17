from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Literal
from zoneinfo import ZoneInfo

from .errors import ConfigError


ChartsApiMode = Literal["real", "mock", "record"]


@dataclass(frozen=True, slots=True)
class ChartImgAccount:
    id: str
    api_key: str


@dataclass(frozen=True, slots=True)
class WorkerConfig:
    charts_bucket: str  # gs://<bucket>
    charts_api_mode: ChartsApiMode
    charts_default_timezone: str
    chart_img_accounts: tuple[ChartImgAccount, ...]
    service: str = "worker-chart-export"
    env: str | None = None

    @staticmethod
    def _require_env(name: str) -> str:
        value = os.environ.get(name)
        if value is None or value.strip() == "":
            raise ConfigError(f"Missing required env var: {name}")
        return value

    @staticmethod
    def _normalize_gs_bucket(value: str) -> str:
        v = value.strip()
        if v.startswith("gs://"):
            v = v.removeprefix("gs://")
        if "/" in v:
            raise ConfigError(
                "CHARTS_BUCKET must be a bucket name or gs://<bucket> (no path)"
            )
        if v == "":
            raise ConfigError("CHARTS_BUCKET must not be empty")
        return f"gs://{v}"

    @classmethod
    def from_env(cls) -> "WorkerConfig":
        charts_bucket_raw = os.environ.get("CHARTS_BUCKET", "").strip()
        charts_bucket = cls._normalize_gs_bucket(
            charts_bucket_raw or cls._require_env("CHARTS_BUCKET")
        )

        charts_api_mode = (os.environ.get("CHARTS_API_MODE") or "real").strip()
        if charts_api_mode not in ("real", "mock", "record"):
            raise ConfigError("CHARTS_API_MODE must be one of: real|mock|record")

        charts_default_timezone = (os.environ.get("CHARTS_DEFAULT_TIMEZONE") or "UTC").strip()
        try:
            ZoneInfo(charts_default_timezone)
        except Exception as exc:  # pragma: no cover
            raise ConfigError(
                "CHARTS_DEFAULT_TIMEZONE must be an IANA timezone name (e.g. UTC)"
            ) from exc

        accounts_json = cls._require_env("CHART_IMG_ACCOUNTS_JSON")
        chart_img_accounts = cls._parse_accounts_json(accounts_json)

        env = (os.environ.get("TDA_ENV") or os.environ.get("ENV") or "").strip() or None

        return cls(
            charts_bucket=charts_bucket,
            charts_api_mode=charts_api_mode,  # type: ignore[assignment]
            charts_default_timezone=charts_default_timezone,
            chart_img_accounts=tuple(chart_img_accounts),
            env=env,
        )

    @staticmethod
    def _parse_accounts_json(raw_json: str) -> list[ChartImgAccount]:
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ConfigError("CHART_IMG_ACCOUNTS_JSON must be a valid JSON array") from exc

        if not isinstance(data, list):
            raise ConfigError("CHART_IMG_ACCOUNTS_JSON must be a JSON array")

        accounts: list[ChartImgAccount] = []
        seen_ids: set[str] = set()
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise ConfigError(
                    f"CHART_IMG_ACCOUNTS_JSON[{i}] must be an object with fields id/apiKey"
                )
            account_id = item.get("id")
            api_key = item.get("apiKey")
            if not isinstance(account_id, str) or account_id.strip() == "":
                raise ConfigError(f"CHART_IMG_ACCOUNTS_JSON[{i}].id must be a non-empty string")
            if not isinstance(api_key, str) or api_key.strip() == "":
                raise ConfigError(
                    f"CHART_IMG_ACCOUNTS_JSON[{i}].apiKey must be a non-empty string"
                )
            if account_id in seen_ids:
                raise ConfigError(f"Duplicate Chart-IMG account id: {account_id}")
            seen_ids.add(account_id)
            accounts.append(ChartImgAccount(id=account_id, api_key=api_key))

        if not accounts:
            raise ConfigError("CHART_IMG_ACCOUNTS_JSON must contain at least 1 account")

        return accounts

