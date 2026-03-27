"""
LlamaParse-backed PDF parsing pipeline with batch CLI.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import structlog

from config.settings import Settings, get_settings


@dataclass(frozen=True)
class PageContent:
    """Content extracted for a single page."""

    page_num: int
    text: str
    tables: List[str]
    has_images: bool


@dataclass(frozen=True)
class ParseResult:
    """Full parse output from LlamaParse wrapper."""

    source_path: str
    pages: List[PageContent]
    total_pages: int
    language_detected: str
    parse_duration_s: float
    raw_markdown: str


class LlamaParseWrapper:
    """Async wrapper around LlamaParse with retries and markdown persistence."""

    def __init__(self, settings: Settings) -> None:
        """Initialize parser wrapper from app settings."""

        self._settings = settings
        self._logger = structlog.get_logger()
        os.makedirs(self._settings.PARSED_MARKDOWN_DIR, exist_ok=True)

    async def parse(self, pdf_path: str) -> ParseResult:
        """
        Parse PDF into markdown and page-wise structure.

        Args:
            pdf_path: Local PDF file path.
        """

        if not self._settings.LLAMA_CLOUD_API_KEY:
            raise ValueError("LLAMA_CLOUD_API_KEY is required in environment")

        parser = self._create_parser()
        started = time.perf_counter()
        last_error: Optional[Exception] = None

        for attempt in range(1, 4):
            try:
                self._logger.info("🔍 Parsing PDF", pdf_path=pdf_path, attempt=attempt)
                docs = await asyncio.to_thread(parser.load_data, pdf_path)

                raw_markdown = self._extract_raw_markdown(docs)
                pages = self._extract_pages(raw_markdown)
                total_pages = len(pages)
                duration = time.perf_counter() - started

                # Cost estimate requested: pages x $0.003
                cost_estimate = round(total_pages * 0.003, 4)
                self._logger.info(
                    "✅ Parse complete",
                    pdf_path=pdf_path,
                    total_pages=total_pages,
                    parse_duration_s=round(duration, 3),
                    cost_estimate_usd=cost_estimate,
                )

                stem = Path(pdf_path).stem
                md_path = os.path.join(self._settings.PARSED_MARKDOWN_DIR, f"{stem}.md")
                await self._save_markdown(md_path, raw_markdown)

                return ParseResult(
                    source_path=pdf_path,
                    pages=pages,
                    total_pages=total_pages,
                    language_detected=self._settings.PARSER_LANGUAGE,
                    parse_duration_s=duration,
                    raw_markdown=raw_markdown,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                self._logger.warning(
                    "❌ Parse attempt failed",
                    pdf_path=pdf_path,
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt < 3:
                    await asyncio.sleep(float(2 ** (attempt - 1)))

        raise RuntimeError(f"Failed to parse {pdf_path}: {last_error}")

    def _create_parser(self) -> Any:
        """Create and configure LlamaParse client."""

        try:
            from llama_parse import LlamaParse
        except Exception as exc:  # noqa: BLE001
            raise ImportError(
                "llama-parse package is required. Install dependencies from requirements.txt"
            ) from exc

        return LlamaParse(
            api_key=self._settings.LLAMA_CLOUD_API_KEY,
            result_type="markdown",
            language=self._settings.PARSER_LANGUAGE,
            skip_diagonal_text=True,
            do_not_unroll_columns=True,
        )

    def _extract_raw_markdown(self, docs: List[Any]) -> str:
        """Extract markdown text from LlamaParse document objects."""

        parts: List[str] = []
        for doc in docs:
            # Typical llama-index Document has `text`.
            text = getattr(doc, "text", None)
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
                continue

            # Fallback for dict-like payloads.
            if isinstance(doc, dict):
                maybe_text = doc.get("text") or doc.get("markdown")
                if isinstance(maybe_text, str) and maybe_text.strip():
                    parts.append(maybe_text.strip())

        return "\n\n".join(parts).strip()

    def _extract_pages(self, raw_markdown: str) -> List[PageContent]:
        """
        Build page list from markdown.

        If explicit page delimiters do not exist, pages are approximated from
        markdown content boundaries and capped by max pages per chunk heuristic.
        """

        if not raw_markdown.strip():
            return []

        # Heuristic split on common page markers emitted by OCR/parsers.
        splits = [
            part.strip()
            for part in __import__("re").split(r"\n(?:(?:---\s*)?Page\s+\d+|Sayfa\s+\d+)\s*\n", raw_markdown)
            if part.strip()
        ]

        if not splits:
            splits = [raw_markdown.strip()]

        pages: List[PageContent] = []
        for idx, part in enumerate(splits, start=1):
            table_snippets = self._extract_table_snippets(part)
            has_images = bool(__import__("re").search(r"!\[[^\]]*\]\([^)]+\)", part))
            pages.append(
                PageContent(
                    page_num=idx,
                    text=part,
                    tables=table_snippets,
                    has_images=has_images,
                )
            )
        return pages

    def _extract_table_snippets(self, text: str) -> List[str]:
        """Extract markdown table-like snippets from text."""

        lines = text.splitlines()
        snippets: List[str] = []
        current: List[str] = []
        for line in lines:
            if "|" in line:
                current.append(line)
            else:
                if len(current) >= 2:
                    snippets.append("\n".join(current))
                current = []
        if len(current) >= 2:
            snippets.append("\n".join(current))
        return snippets

    async def _save_markdown(self, path: str, markdown: str) -> None:
        """Persist raw markdown output."""

        import aiofiles

        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(markdown)


async def _process_pdf(
    pdf_path: str,
    source_url: str,
    parser: LlamaParseWrapper,
    settings: Settings,
    semaphore: asyncio.Semaphore,
) -> Optional[str]:
    """Parse one PDF, extract metadata, normalize and save JSON."""

    from parser.metadata_extractor import MetadataExtractor
    from parser.normalizer import DocumentNormalizer

    stem = Path(pdf_path).stem
    output_json = os.path.join(settings.PARSED_JSON_DIR, f"{stem}.json")
    logger = structlog.get_logger()
    if os.path.exists(output_json):
        logger.info("✅ Skipping already-parsed PDF", pdf_path=pdf_path, output_json=output_json)
        return output_json

    async with semaphore:
        result = await parser.parse(pdf_path)
        metadata = MetadataExtractor().extract(result)
        normalizer = DocumentNormalizer(settings)
        json_path = await normalizer.normalize_and_save(result, metadata, source_url=source_url)
        logger.info("✅ Normalized JSON saved", pdf_path=pdf_path, json_path=json_path)
        return json_path


def _load_source_map(queue_file: str) -> Dict[str, str]:
    """Map local PDF path to source URL from download queue file."""

    import json

    if not os.path.exists(queue_file):
        return {}
    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return {}
        out: Dict[str, str] = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            local_path = item.get("local_path")
            url = item.get("url")
            if isinstance(local_path, str) and isinstance(url, str):
                out[os.path.abspath(local_path)] = url
        return out
    except Exception:
        return {}


async def run_batch(input_dir: str, output_dir: str) -> None:
    """
    Process the entire raw_pdfs directory in async batch mode.
    """

    settings = get_settings()
    settings.PARSED_JSON_DIR = output_dir
    os.makedirs(settings.PARSED_JSON_DIR, exist_ok=True)

    parser = LlamaParseWrapper(settings)
    source_map = _load_source_map(settings.QUEUE_FILE)
    logger = structlog.get_logger()

    pdfs = sorted(str(p) for p in Path(input_dir).glob("*.pdf"))
    if not pdfs:
        click.echo("No PDFs found to parse.")
        return

    semaphore = asyncio.Semaphore(3)
    tasks = []
    for pdf in pdfs:
        source_url = source_map.get(os.path.abspath(pdf), "")
        tasks.append(
            asyncio.create_task(
                _process_pdf(
                    pdf_path=pdf,
                    source_url=source_url,
                    parser=parser,
                    settings=settings,
                    semaphore=semaphore,
                )
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)
    success = 0
    failed = 0
    for result in results:
        if isinstance(result, Exception):
            failed += 1
            logger.error("❌ Batch parse failure", error=str(result))
        elif result:
            success += 1

    click.echo(f"Batch parse summary: {len(pdfs)} files, {success} succeeded, {failed} failed")


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--input", "input_dir", default="data/raw_pdfs/", show_default=True, help="Input PDF directory.")
@click.option("--output", "output_dir", default="data/parsed_json/", show_default=True, help="Output normalized JSON directory.")
def main(input_dir: str, output_dir: str) -> None:
    """CLI entrypoint: parse raw PDFs and emit normalized JSON."""

    asyncio.run(run_batch(input_dir=input_dir, output_dir=output_dir))


if __name__ == "__main__":
    main()

