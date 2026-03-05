"""
Async HTTP client for intelliExtract dual-path API.

Supports both:
- /api/v1/spreadsheet/extract/url (JSON body with URL)
- /api/v1/spreadsheet/extract/upload (multipart/form-data file)
"""

import json
import time
import contextlib
from pathlib import Path
from typing import Literal

import aiohttp

from auth import HeaderFactory


# Type for which endpoint was used (for load-balancing and reporting)
EndpointMode = Literal["url", "upload"]

# BASE_URL = "https://vcex9tits4.us-west-2.awsapprunner.com"
BASE_URL = "https://4nbcwkdjru.us-west-2.awsapprunner.com/"
URL_ENDPOINT = "/api/v1/spreadsheet/extract/url"
UPLOAD_ENDPOINT = "/api/v1/spreadsheet/extract/upload"


class ExtractResult:
    """Result of a single extract request (either URL or upload)."""

    __slots__ = ("success", "status_code", "latency_ms", "server_processing_ms", "network_overhead_ms", "response_body", "error", "error_type")

    def __init__(
        self,
        success: bool,
        status_code: int | None,
        latency_ms: float,
        response_body: str,
        server_processing_ms: float | None = None,
        network_overhead_ms: float | None = None,
        error: str | None = None,
        error_type: str | None = None,
    ) -> None:
        self.success = success
        self.status_code = status_code
        self.latency_ms = latency_ms
        self.server_processing_ms = server_processing_ms
        self.network_overhead_ms = network_overhead_ms
        self.response_body = response_body
        self.error = error
        self.error_type = error_type


class IntelliExtractClient:
    """
    Async client for intelliExtract spreadsheet extract API.
    Uses HeaderFactory for authentication on every request.
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        header_factory: HeaderFactory | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._headers = (header_factory or HeaderFactory()).headers()
        self._session = session

    @contextlib.asynccontextmanager
    async def _get_session(self):
        if self._session:
            yield self._session
        else:
            async with aiohttp.ClientSession() as session:
                yield session

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    async def extract_by_url(self, url: str) -> ExtractResult:
        """
        Call the /url endpoint with a JSON body containing the given URL.

        Args:
            url: S3 signed URL or public link to the spreadsheet.

        Returns:
            ExtractResult with status, latency, and response body.
        """
        # Serialize explicitly so long presigned URLs are valid JSON (no unescaped " or \)
        payload = {"url": url}
        try:
            body_bytes = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        except (TypeError, ValueError):
            body_bytes = json.dumps({"url": str(url)}, ensure_ascii=True).encode("utf-8")
        start = time.perf_counter()
        try:
            async with self._get_session() as session:
                async with session.post(
                    self._url(URL_ENDPOINT),
                    data=body_bytes,
                    headers={
                        **self._headers,
                        "Content-Type": "application/json",
                    },
                ) as resp:
                    body = await resp.text()
                    latency_ms = (time.perf_counter() - start) * 1000
                    
                    server_processing_ms = None
                    network_overhead_ms = None
                    envoy_time = resp.headers.get("x-envoy-upstream-service-time")
                    if envoy_time:
                        try:
                            server_processing_ms = float(envoy_time)
                            network_overhead_ms = max(0.0, latency_ms - server_processing_ms)
                        except ValueError:
                            pass
                            
                    return ExtractResult(
                        success=200 <= resp.status < 300,
                        status_code=resp.status,
                        latency_ms=latency_ms,
                        server_processing_ms=server_processing_ms,
                        network_overhead_ms=network_overhead_ms,
                        response_body=body,
                    )
        except Exception as e:  # noqa: BLE001
            latency_ms = (time.perf_counter() - start) * 1000
            return ExtractResult(
                success=False,
                status_code=None,
                latency_ms=latency_ms,
                response_body="",
                error=str(e),
            )

    async def extract_by_upload(
        self,
        file_path: str | Path,
        form_field_name: str = "file",
    ) -> ExtractResult:
        """
        Call the /upload endpoint with multipart/form-data file.

        Args:
            file_path: Path to the local spreadsheet file.
            form_field_name: Form field name for the file (default: file).

        Returns:
            ExtractResult with status, latency, and response body.
        """
        path = Path(file_path)
        if not path.is_file():
            return ExtractResult(
                success=False,
                status_code=None,
                latency_ms=0.0,
                response_body="",
                error=f"File not found: {path}",
            )

        start = time.perf_counter()
        try:
            file_content = path.read_bytes()
            data = aiohttp.FormData()
            data.add_field(
                form_field_name,
                file_content,
                filename=path.name,
                content_type="application/octet-stream",
            )

            async with self._get_session() as session:
                async with session.post(
                    self._url(UPLOAD_ENDPOINT),
                    data=data,
                    headers=self._headers,
                ) as resp:
                    body = await resp.text()
                    latency_ms = (time.perf_counter() - start) * 1000
                    
                    server_processing_ms = None
                    network_overhead_ms = None
                    envoy_time = resp.headers.get("x-envoy-upstream-service-time")
                    if envoy_time:
                        try:
                            server_processing_ms = float(envoy_time)
                            network_overhead_ms = max(0.0, latency_ms - server_processing_ms)
                        except ValueError:
                            pass
                            
                    return ExtractResult(
                        success=200 <= resp.status < 300,
                        status_code=resp.status,
                        latency_ms=latency_ms,
                        server_processing_ms=server_processing_ms,
                        network_overhead_ms=network_overhead_ms,
                        response_body=body,
                    )
        except Exception as e:  # noqa: BLE001
            latency_ms = (time.perf_counter() - start) * 1000
            return ExtractResult(
                success=False,
                status_code=None,
                latency_ms=latency_ms,
                response_body="",
                error=str(e),
            )

    async def extract(
        self,
        mode: EndpointMode,
        *,
        url: str | None = None,
        file_path: str | Path | None = None,
    ) -> ExtractResult:
        """
        Single entry point: run extract via 'url' or 'upload' based on mode.

        Args:
            mode: 'url' or 'upload'
            url: Required when mode is 'url' (S3 signed or public URL).
            file_path: Required when mode is 'upload' (local file path).

        Returns:
            ExtractResult for the chosen endpoint.
        """
        if mode == "url":
            if not url:
                return ExtractResult(
                    success=False,
                    status_code=None,
                    latency_ms=0.0,
                    response_body="",
                    error="url is required when mode is 'url'",
                )
            return await self.extract_by_url(url)
        if mode == "upload":
            if not file_path:
                return ExtractResult(
                    success=False,
                    status_code=None,
                    latency_ms=0.0,
                    response_body="",
                    error="file_path is required when mode is 'upload'",
                )
            return await self.extract_by_upload(file_path)
        return ExtractResult(
            success=False,
            status_code=None,
            latency_ms=0.0,
            response_body="",
            error=f"Invalid mode: {mode}",
        )
