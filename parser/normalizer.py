"""
Normalize parsed markdown and metadata into final JSON schema.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Dict, List

import aiofiles

from config.settings import Settings
from parser.metadata_extractor import DocumentMetadata
from parser.pdf_parser import ParseResult


@dataclass(frozen=True)
class NormalizedChunk:
    """Chunk unit for downstream map-reduce processing."""

    chunk_id: str
    chunk_index: int
    text: str
    page_start: int
    page_end: int


class DocumentNormalizer:
    """Build normalized JSON documents from parse + metadata results."""

    def __init__(self, settings: Settings) -> None:
        """Initialize with application settings."""

        self._settings = settings
        os.makedirs(self._settings.PARSED_JSON_DIR, exist_ok=True)

    async def normalize_and_save(
        self,
        parse_result: ParseResult,
        metadata: DocumentMetadata,
        source_url: str,
    ) -> str:
        """
        Produce and persist normalized JSON representation.

        Args:
            parse_result: Parsed PDF result.
            metadata: Extracted document metadata.
            source_url: Source URL where PDF originated.

        Returns:
            Final JSON file path.
        """

        stem = os.path.splitext(os.path.basename(parse_result.source_path))[0]
        chunks = self._chunk_pages(parse_result)

        normalized: Dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "source_url": source_url,
            "local_pdf_path": parse_result.source_path,
            "gazette_date": metadata.gazette_date,
            "gazette_number": metadata.gazette_number,
            "document_type": metadata.document_type,
            "affected_districts": metadata.affected_districts,
            "land_parcels": metadata.land_parcel_ids,
            "monetary_values": metadata.monetary_values,
            "entities": metadata.involved_entities,
            "total_pages": parse_result.total_pages,
            "chunks": [asdict(chunk) for chunk in chunks],
            "status": "parsed",
        }

        out_path = os.path.join(self._settings.PARSED_JSON_DIR, f"{stem}.json")
        async with aiofiles.open(out_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(normalized, ensure_ascii=False, indent=2))
        return out_path

    def _chunk_pages(self, parse_result: ParseResult) -> List[NormalizedChunk]:
        """
        Split parsed content by MAX_PAGES_PER_CHUNK while preserving headers.
        """

        chunks: List[NormalizedChunk] = []
        pages = parse_result.pages
        if not pages:
            chunks.append(
                NormalizedChunk(
                    chunk_id=str(uuid.uuid4()),
                    chunk_index=0,
                    text=parse_result.raw_markdown,
                    page_start=1,
                    page_end=1,
                )
            )
            return chunks

        max_pages = max(1, self._settings.MAX_PAGES_PER_CHUNK)
        carry_headers: List[str] = []

        for index, start in enumerate(range(0, len(pages), max_pages)):
            batch = pages[start : start + max_pages]
            page_start = batch[0].page_num
            page_end = batch[-1].page_num

            text_blocks: List[str] = []
            if carry_headers:
                text_blocks.append("\n".join(carry_headers))

            for page in batch:
                # Track markdown headers so the next chunk keeps section context.
                current_headers = [
                    line.strip()
                    for line in page.text.splitlines()
                    if line.strip().startswith("#")
                ]
                if current_headers:
                    carry_headers = current_headers[-3:]
                text_blocks.append(page.text.strip())

            chunk_text = "\n\n".join(block for block in text_blocks if block).strip()
            chunks.append(
                NormalizedChunk(
                    chunk_id=str(uuid.uuid4()),
                    chunk_index=index,
                    text=chunk_text,
                    page_start=page_start,
                    page_end=page_end,
                )
            )

        return chunks

