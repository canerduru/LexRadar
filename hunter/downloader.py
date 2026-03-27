"""
Asynchronous PDF downloader for gazette documents.
"""

from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass
from datetime import date as Date
from typing import Optional

import aiofiles
import httpx
import structlog


@dataclass(frozen=True)
class DownloadResult:
    """Result of a single PDF download attempt."""

    path: str
    url: str
    title: str
    date: Date
    file_size_kb: float
    status: str  # 'downloaded' | 'skipped' | 'failed'


def _sanitize_filename(text: str, max_len: int = 140) -> str:
    """
    Sanitize a title into a filesystem-friendly filename segment.
    """

    # Replace whitespace with underscores and drop unsafe characters.
    s = re.sub(r"\s+", "_", text.strip())
    s = re.sub(r"[^A-Za-z0-9_\-\.]+", "", s)
    s = re.sub(r"_+", "_", s)
    s = s.strip("._-")
    if not s:
        s = "gazette"
    if len(s) > max_len:
        s = s[:max_len].rstrip("._-")
    return s


class AsyncPDFDownloader:
    """
    Async downloader that stores PDFs in a date-prefixed naming scheme.

    Downloading is idempotent: if the destination file already exists,
    the method skips the network call.
    """

    def __init__(self, raw_pdf_dir: str) -> None:
        """
        Args:
            raw_pdf_dir: Directory where PDFs will be saved.
        """

        self._raw_pdf_dir = raw_pdf_dir
        os.makedirs(self._raw_pdf_dir, exist_ok=True)
        self._client: Optional[httpx.AsyncClient] = None
        self._logger = structlog.get_logger()

    def _ensure_client(self) -> httpx.AsyncClient:
        """Lazily create an `httpx.AsyncClient` with configured timeouts."""

        if self._client is None:
            timeout = httpx.Timeout(30.0, connect=30.0)
            self._client = httpx.AsyncClient(timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        return self._client

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""

        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def download_pdf(self, url: str, title: str, published_date: Date) -> DownloadResult:
        """
        Download a PDF if needed.

        Args:
            url: PDF URL.
            title: Title used for filename.
            published_date: Publication date.

        Returns:
            DownloadResult describing the final status.
        """

        sanitized = _sanitize_filename(title)
        filename = f"{published_date.isoformat()}_{sanitized}.pdf"
        path = os.path.join(self._raw_pdf_dir, filename)

        if os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024.0
            self._logger.info(
                "PDF already exists; skipping download",
                url=url,
                title=title,
                date=str(published_date),
                local_path=path,
                file_size_kb=size_kb,
                status="skipped",
            )
            return DownloadResult(
                path=path,
                url=url,
                title=title,
                date=published_date,
                file_size_kb=size_kb,
                status="skipped",
            )

        client = self._ensure_client()

        part_path = f"{path}.part"
        last_error: Optional[str] = None

        for attempt in range(1, 4):
            try:
                self._logger.info(
                    "📥 downloading PDF",
                    url=url,
                    title=title,
                    date=str(published_date),
                    local_path=path,
                    attempt=attempt,
                )

                if os.path.exists(part_path):
                    os.remove(part_path)

                async with client.stream("GET", url, follow_redirects=True) as resp:
                    # Raise for 4xx/5xx to handle gracefully.
                    resp.raise_for_status()

                    async with aiofiles.open(part_path, "wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=1024 * 64):
                            if chunk:
                                await f.write(chunk)

                os.replace(part_path, path)
                size_kb = os.path.getsize(path) / 1024.0
                self._logger.info(
                    "✅ PDF downloaded",
                    url=url,
                    title=title,
                    date=str(published_date),
                    local_path=path,
                    file_size_kb=size_kb,
                    status="downloaded",
                )
                return DownloadResult(
                    path=path,
                    url=url,
                    title=title,
                    date=published_date,
                    file_size_kb=size_kb,
                    status="downloaded",
                )
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                last_error = f"HTTP {status_code}"
                self._logger.warning(
                    "❌ PDF download failed (HTTP status)",
                    url=url,
                    title=title,
                    date=str(published_date),
                    local_path=path,
                    attempt=attempt,
                    http_status=status_code,
                    error=str(e),
                )

                # Don't retry on 404.
                if status_code == 404:
                    return DownloadResult(
                        path=path,
                        url=url,
                        title=title,
                        date=published_date,
                        file_size_kb=0.0,
                        status="failed",
                    )

                if attempt >= 3 or status_code < 500 or status_code == 401 or status_code == 403:
                    return DownloadResult(
                        path=path,
                        url=url,
                        title=title,
                        date=published_date,
                        file_size_kb=0.0,
                        status="failed",
                    )

            except httpx.RequestError as e:
                last_error = str(e)
                self._logger.warning(
                    "❌ PDF download failed (network error)",
                    url=url,
                    title=title,
                    date=str(published_date),
                    local_path=path,
                    attempt=attempt,
                    error=str(e),
                )
            except Exception as e:  # noqa: BLE001 - safety net for malformed responses
                last_error = str(e)
                self._logger.exception(
                    "❌ Unexpected error while downloading PDF",
                    url=url,
                    title=title,
                    date=str(published_date),
                    local_path=path,
                    attempt=attempt,
                )

            # Exponential backoff before retrying.
            if os.path.exists(part_path):
                try:
                    os.remove(part_path)
                except OSError:
                    # Best-effort cleanup; don't crash the scraper.
                    pass
            if attempt < 3:
                backoff_s = float(2 ** (attempt - 1))
                await asyncio.sleep(backoff_s)

        self._logger.error(
            "❌ PDF download failed after retries",
            url=url,
            title=title,
            date=str(published_date),
            local_path=path,
            error=last_error,
            status="failed",
        )
        if os.path.exists(part_path):
            try:
                os.remove(part_path)
            except OSError:
                pass
        return DownloadResult(
            path=path,
            url=url,
            title=title,
            date=published_date,
            file_size_kb=0.0,
            status="failed",
        )

