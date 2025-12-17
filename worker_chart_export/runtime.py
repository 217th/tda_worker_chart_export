from __future__ import annotations

from functools import lru_cache

from .config import WorkerConfig


@lru_cache(maxsize=1)
def get_config() -> WorkerConfig:
    return WorkerConfig.from_env()

