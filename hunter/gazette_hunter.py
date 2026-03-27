"""
Gazette hunter orchestrator.

Scrapes Turkey's Official Gazette and downloads PDFs matching real-estate/
legal/tender keywords, maintaining a persistent download queue.
"""

from __future__ import annotations

import json
import logging
import os
import re
import asyncio
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Set
from urllib.parse import urljoin

import aiofiles
import click
import httpx
import structlog
from bs4 import BeautifulSoup

from config.settings import Settings, get_settings
from hunter.downloader import AsyncPDFDownloader, DownloadResult, _sanitize_filename
from hunter.keyword_filter import KeywordFilter


_DATE_DMY_RE = re.compile(r"(?P<d>\d{2})\.(?P<m>\d{2})\.(?P<y>\d{4})")


def _configure_logging(log_level: str) -> None:
    """
    Configure structlog + standard logging once per process.

    Args:
        log_level: Logging level name (e.g. "INFO", "DEBUG").
    """

    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        cache_logger_on_first_use=True,
    )


def _today_utc_date() -> Date:
    """Return today's date in UTC."""

    return datetime.now(timezone.utc).date()


def _date_range_back(days_back: int) -> List[Date]:
    """
    Return a list of dates including today and going back `days_back - 1`.

    Args:
        days_back: Number of days to include, where 1 means "today only".
    """

    if days_back < 1:
        raise ValueError("days_back must be >= 1")

    end = _today_utc_date()
    start = end - timedelta(days=days_back - 1)
    out: List[Date] = []
    cur = start
    while cur <= end:
        out.append(cur)
        cur += timedelta(days=1)
    return out


async def _fetch_html(
    client: httpx.AsyncClient,
    url: str,
    *,
    timeout_s: float = 30.0,
    retries: int = 3,
) -> Optional[str]:
    """
    Fetch HTML from a URL with retries and error handling.

    Returns:
        HTML string on success, otherwise None.
    """

    last_err: Optional[str] = None

    for attempt in range(1, retries + 1):
        try:
            resp = await client.get(url, timeout=timeout_s)
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "")
            if "text/html" not in ctype and "application/xhtml+xml" not in ctype and "<html" not in resp.text[:2000].lower():
                # Some pages might be served differently; still attempt parsing.
                return resp.text
            return resp.text
        except httpx.HTTPStatusError as e:
            last_err = f"HTTP {e.response.status_code}"
            # Don't retry 404/400.
            if e.response.status_code in (400, 401, 403, 404):
                return None
        except httpx.RequestError as e:
            last_err = str(e)

        if attempt < retries:
            backoff_s = float(2 ** (attempt - 1))
            await asyncio.sleep(backoff_s)

    _ = last_err
    return None


def _extract_dmy_date_from_href(href: str) -> Optional[Date]:
    """Extract and parse a D.M.YYYY date from an href string."""

    m = _DATE_DMY_RE.search(href)
    if not m:
        return None
    try:
        return Date(int(m.group("y")), int(m.group("m")), int(m.group("d")))
    except ValueError:
        return None


def _extract_title_from_anchor(a_tag: Any) -> str:
    """
    Extract a best-effort title from a PDF anchor element.

    Args:
        a_tag: BeautifulSoup anchor tag.
    """

    title = a_tag.get_text(" ", strip=True) if a_tag else ""
    if not title:
        title = a_tag.get("title") or ""
    if not title:
        parent_text = getattr(a_tag.parent, "get_text", None)
        if callable(parent_text):
            title = parent_text(" ", strip=True)  # type: ignore[misc]
    title = re.sub(r"\s+", " ", title).strip()
    # Remove obvious file-name remnants.
    title = re.sub(r"\.pdf$", "", title, flags=re.IGNORECASE).strip()
    return title[:220] if len(title) > 220 else title


def _iter_issue_urls_from_listing(html: str, base_url: str) -> List[str]:
    """
    Parse issue URLs from a listing HTML page.

    This uses heuristic matching on links that contain `dd.mm.yyyy`.
    """

    soup = BeautifulSoup(html, "lxml")
    issue_urls: List[str] = []

    for a in soup.find_all("a"):
        href = a.get("href")
        if not href or not isinstance(href, str):
            continue
        # Typical issue pages use `/dd.mm.yyyy` style paths.
        if _DATE_DMY_RE.search(href):
            issue_urls.append(urljoin(base_url, href))

    # De-dupe while preserving order.
    seen: Set[str] = set()
    unique: List[str] = []
    for u in issue_urls:
        if u in seen:
            continue
        seen.add(u)
        unique.append(u)
    return unique


@dataclass(frozen=True)
class PdfCandidate:
    """Represents a PDF referenced by an article title."""

    url: str
    title: str
    date: Date


def _iter_pdf_candidates(html: str, *, base_url: str, published_date: Date) -> List[PdfCandidate]:
    """
    Extract PDF URLs and associated titles from an issue HTML page.

    Heuristics:
    - consider anchor tags whose `href` contains "pdf"
    - use anchor text/attributes/nearby parent text as the title
    """

    soup = BeautifulSoup(html, "lxml")
    candidates: List[PdfCandidate] = []
    seen_urls: Set[str] = set()

    for a in soup.find_all("a"):
        href = a.get("href")
        if not href or not isinstance(href, str):
            continue

        href_l = href.lower()
        if "pdf" not in href_l:
            continue
        pdf_url = urljoin(base_url, href)
        if pdf_url in seen_urls:
            continue

        title = _extract_title_from_anchor(a)
        if not title:
            title = "resmi gazete pdf"

        # Optional: if href contains a date different from the page, ignore.
        extracted = _extract_dmy_date_from_href(href)
        if extracted is not None and extracted != published_date:
            continue

        seen_urls.add(pdf_url)
        candidates.append(PdfCandidate(url=pdf_url, title=title, date=published_date))

    return candidates


def _expected_local_path(raw_pdf_dir: str, published_date: Date, title: str) -> str:
    """Compute the expected local path using the downloader naming scheme."""

    sanitized = _sanitize_filename(title)
    filename = f"{published_date.isoformat()}_{sanitized}.pdf"
    return os.path.join(raw_pdf_dir, filename)


async def _load_queue(queue_file: str) -> List[Dict[str, Any]]:
    """Load the queue JSON file."""

    if not os.path.exists(queue_file):
        return []

    try:
        async with aiofiles.open(queue_file, "r", encoding="utf-8") as f:
            raw = await f.read()
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            return data["items"]
        if isinstance(data, dict):
            return list(data.values())
    except Exception:
        # Corrupt queue should not crash the scraper; start fresh.
        return []

    return []


async def _save_queue(queue_file: str, items: Sequence[Dict[str, Any]]) -> None:
    """Persist queue items to disk."""

    os.makedirs(os.path.dirname(queue_file) or ".", exist_ok=True)
    tmp_path = f"{queue_file}.tmp"
    async with aiofiles.open(tmp_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(list(items), ensure_ascii=False, indent=2))
    os.replace(tmp_path, queue_file)


class GazetteHunter:
    """
    Main orchestrator for scraping and downloading Official Gazette PDFs.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Args:
            settings: Application configuration.
        """

        self._settings = settings
        self._logger = structlog.get_logger()
        self._keyword_filter = KeywordFilter(settings.KEYWORDS)

    async def run(self, days_back: int = 1) -> None:
        """
        Run the scraper for the date range [today - days_back + 1, today].

        Args:
            days_back: Number of days to look back (including today).
        """

        _configure_logging(self._settings.LOG_LEVEL)

        downloader = AsyncPDFDownloader(self._settings.RAW_PDF_DIR)
        await self._run_internal(downloader, days_back=days_back)
        await downloader.aclose()

    async def _run_internal(self, downloader: AsyncPDFDownloader, *, days_back: int) -> None:
        """
        Internal run that accepts an already-created downloader instance.
        """

        dates = _date_range_back(days_back)
        base = self._settings.GAZETTE_BASE_URL.rstrip("/")

        queue_items = await _load_queue(self._settings.QUEUE_FILE)
        queue_by_url: Dict[str, Dict[str, Any]] = {}
        for item in queue_items:
            url = item.get("url")
            if isinstance(url, str):
                queue_by_url[url] = dict(item)

        articles_scanned = 0
        keyword_match_articles = 0
        pdf_downloaded = 0

        semaphore = asyncio.Semaphore(6)

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=30.0),
            headers={"User-Agent": "Mozilla/5.0"},
        ) as client:
            download_tasks: List[asyncio.Task[None]] = []

            async def _download_one(candidate: PdfCandidate, score: Dict[str, int], matched_keywords: List[str]) -> None:
                """Download and update queue for a single matched PDF."""

                nonlocal pdf_downloaded
                async with semaphore:
                    local_path = _expected_local_path(self._settings.RAW_PDF_DIR, candidate.date, candidate.title)

                    entry = queue_by_url.get(candidate.url)
                    if entry is None:
                        entry = {
                            "url": candidate.url,
                            "title": candidate.title,
                            "date": candidate.date.isoformat(),
                            "local_path": local_path,
                            "status": "queued",
                            "keyword_matches": matched_keywords,
                            "score": score,
                        }
                        queue_by_url[candidate.url] = entry
                    else:
                        entry.update(
                            {
                                "url": candidate.url,
                                "title": candidate.title,
                                "date": candidate.date.isoformat(),
                                "local_path": local_path,
                                "status": "queued",
                                "keyword_matches": matched_keywords,
                                "score": score,
                            }
                        )

                    self._logger.info(
                        "📥 Queued download",
                        url=candidate.url,
                        title=candidate.title,
                        date=str(candidate.date),
                        local_path=local_path,
                    )

                    result: DownloadResult = await downloader.download_pdf(
                        candidate.url, candidate.title, candidate.date
                    )

                    if result.status == "downloaded":
                        entry["status"] = "downloaded"
                        self._logger.info(
                            "✅ Download complete",
                            url=candidate.url,
                            title=candidate.title,
                            date=str(candidate.date),
                            local_path=result.path,
                        )
                        pdf_downloaded += 1
                    elif result.status == "skipped":
                        entry["status"] = "downloaded"
                        self._logger.info(
                            "✅ Download already present",
                            url=candidate.url,
                            title=candidate.title,
                            date=str(candidate.date),
                            local_path=result.path,
                        )
                        pdf_downloaded += 1
                    else:
                        entry["status"] = "failed"
                        self._logger.error(
                            "❌ Download failed",
                            url=candidate.url,
                            title=candidate.title,
                            date=str(candidate.date),
                            local_path=result.path,
                        )

            for published_date in dates:
                d_str = published_date.isoformat()
                self._logger.info("🔍 Scanning day listing", date=d_str)

                # Generate likely listing URL(s) for the day.
                fihrist_urls = [
                    f"{base}/fihrist?tarih={d_str}",
                    f"{base}/fihrist?tarih={d_str}&mukerrer=1",
                ]

                issue_pages: List[str] = []
                for listing_url in fihrist_urls:
                    html = await _fetch_html(client, listing_url)
                    if not html:
                        continue
                    issue_pages.extend(_iter_issue_urls_from_listing(html, base))

                # Fallback: direct issue page for that date (dd.mm.yyyy).
                dmy = published_date.strftime("%d.%m.%Y")
                if not issue_pages:
                    issue_pages = [f"{base}/{dmy}"]

                # Fetch each issue page and parse candidate PDFs.
                for issue_url in issue_pages:
                    self._logger.info("🔍 Scanning issue page", date=d_str, issue_url=issue_url)
                    html = await _fetch_html(client, issue_url)
                    if not html:
                        continue

                    candidates = _iter_pdf_candidates(html, base_url=base, published_date=published_date)
                    if not candidates:
                        continue

                    for candidate in candidates:
                        articles_scanned += 1
                        score = self._keyword_filter.score(candidate.title)
                        if not score:
                            continue

                        matched_keywords = list(score.keys())
                        keyword_match_articles += 1

                        download_tasks.append(
                            asyncio.create_task(_download_one(candidate, score, matched_keywords))
                        )

            if download_tasks:
                await asyncio.gather(*download_tasks)

        # Save queue state at the end.
        final_items = list(queue_by_url.values())
        await _save_queue(self._settings.QUEUE_FILE, final_items)

        self._logger.info(
            "Scrape summary",
            articles_scanned=articles_scanned,
            keyword_matches_articles=keyword_match_articles,
            pdf_downloaded=pdf_downloaded,
        )

        click.echo(
            f"Summary: {articles_scanned} articles scanned, "
            f"{keyword_match_articles} keyword matches, {pdf_downloaded} PDFs downloaded"
        )


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--days-back", type=int, default=1, show_default=True, help="Look back N days (including today).")
def main(days_back: int) -> None:
    """CLI entrypoint for the Official Gazette PDF hunter."""

    settings = get_settings()
    hunter = GazetteHunter(settings)
    # Use asyncio.run from sync Click context.
    import asyncio

    asyncio.run(hunter.run(days_back=days_back))


if __name__ == "__main__":
    main()

