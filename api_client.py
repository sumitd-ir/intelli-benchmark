"""
Async HTTP logic for intelliExtract API with custom headers.

Thin wrapper around the core client and auth; provides the public API
used by the orchestrator (main.py). Includes jittered exponential backoff
for 429 (Rate Limit) and 5xx errors so the framework stays stable under load.
"""

import asyncio
import random
from pathlib import Path
from typing import Literal

from auth import HeaderFactory
from client import (
    BASE_URL,
    ExtractResult,
    IntelliExtractClient as _Client,
)

# Re-export for orchestrator and reporter
__all__ = [
    "IntelliExtractClient",
    "ExtractResult",
    "EndpointMode",
    "BASE_URL",
]

EndpointMode = Literal["url", "upload"]

# Backoff config for 429 and 5xx
DEFAULT_MAX_RETRIES = 5
DEFAULT_BASE_DELAY_SEC = 1.0
DEFAULT_MAX_DELAY_SEC = 60.0


def _should_retry(status_code: int | None) -> bool:
    """True if 429 or 5xx."""
    if status_code is None:
        return False
    if status_code == 429:
        return True
    return 500 <= status_code < 600


def _jittered_delay(attempt: int, base_sec: float = DEFAULT_BASE_DELAY_SEC, max_sec: float = DEFAULT_MAX_DELAY_SEC) -> float:
    """Exponential backoff with jitter: base * 2^attempt + random jitter, capped."""
    delay = base_sec * (2 ** attempt)
    jitter = random.uniform(0, min(delay, base_sec * 2))
    return min(delay + jitter, max_sec)


class IntelliExtractClient(_Client):
    """
    Async HTTP client for both extract endpoints with custom X-headers.
    Uses HeaderFactory for every request. Retries on 429 and 5xx with
    jittered exponential backoff so one App Runner instance under heavy
    load does not crash the framework.
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        header_factory: HeaderFactory | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base_sec: float = DEFAULT_BASE_DELAY_SEC,
        backoff_max_sec: float = DEFAULT_MAX_DELAY_SEC,
    ) -> None:
        super().__init__(base_url=base_url, header_factory=header_factory or HeaderFactory())
        self._max_retries = max_retries
        self._backoff_base = backoff_base_sec
        self._backoff_max = backoff_max_sec

    async def extract(
        self,
        mode: EndpointMode,
        *,
        url: str | None = None,
        file_path: str | Path | None = None,
    ) -> ExtractResult:
        """Run extract via 'url' or 'upload' endpoint with retry on 429/5xx."""
        last_result: ExtractResult | None = None
        for attempt in range(self._max_retries + 1):
            last_result = await super().extract(mode, url=url, file_path=file_path)
            if last_result.success:
                return last_result
            if not _should_retry(last_result.status_code):
                return last_result
            if attempt < self._max_retries:
                delay = _jittered_delay(attempt, self._backoff_base, self._backoff_max)
                await asyncio.sleep(delay)
        return last_result or ExtractResult(
            success=False,
            status_code=None,
            latency_ms=0.0,
            response_body="",
            error="Max retries exceeded",
            error_type="MaxRetries",
        )
