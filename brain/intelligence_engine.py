"""
Intelligence Engine Orchestrator.
Coordinates the Map (Gemini) and Reduce (OpenAI) phases.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import structlog

from brain.map_analyzer import ChunkMapAnalyzer
from brain.reduce_synthesizer import FinalReport, ReportReduceSynthesizer
from config.settings import Settings, get_settings


class IntelligenceEngine:
    """
    Main orchestrator for the Map-Reduce RAG Analysis Engine.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._logger = structlog.get_logger()
        self._map_analyzer = ChunkMapAnalyzer(settings)
        self._reduce_synthesizer = ReportReduceSynthesizer(settings)
        os.makedirs(self._settings.INTELLIGENCE_REPORTS_DIR, exist_ok=True)

    def _estimate_cost(self, map_input_chars: int, reduce_input_chars: int) -> float:
        """
        Estimate API cost based on character counts.
        Rough estimate: 4 chars per token.
        Gemini Flash ($0.075 / 1M tokens)
        GPT-4o-mini ($0.150 / 1M tokens)
        """
        map_tokens = map_input_chars / 4
        reduce_tokens = reduce_input_chars / 4

        map_cost = (map_tokens / 1_000_000) * 0.075
        reduce_cost = (reduce_tokens / 1_000_000) * 0.150

        return map_cost + reduce_cost

    async def process_document(self, normalized_doc_path: str) -> FinalReport | None:
        """
        Process a single normalized JSON document through the Map-Reduce pipeline.
        """
        doc_path = Path(normalized_doc_path)
        if not doc_path.exists():
            self._logger.error("Document not found", path=normalized_doc_path)
            return None

        try:
            with open(doc_path, "r", encoding="utf-8") as f:
                doc_data = json.load(f)
        except Exception as e:
            self._logger.error("Failed to read JSON document", path=normalized_doc_path, error=str(e))
            return None

        metadata = doc_data  # full doc is the metadata context
        doc_id = doc_data.get("id", doc_path.stem)
        chunks = doc_data.get("chunks", [])

        if not chunks:
            self._logger.warning("No chunks found in document", doc_id=doc_id)
            return None

        self._logger.info("Starting Map-Reduce pipeline", doc_id=doc_id, total_chunks=len(chunks))

        # 1. MAP PHASE
        map_tasks = []
        map_input_chars = 0
        for chunk in chunks:
            text = chunk.get("text", "")
            map_input_chars += len(text)
            
            # Adapt chunk format from parser output to required input
            adapted_chunk = {
                "index": chunk.get("page_num", 1),
                "text": text,
            }
            # Adding total chunks to metadata for the map prompt
            metadata["total_chunks"] = len(chunks)
            
            map_tasks.append(self._map_analyzer.analyze_chunk(adapted_chunk, metadata))

        self._logger.info("Executing Map Phase concurrently", doc_id=doc_id)
        chunk_analyses = await asyncio.gather(*map_tasks, return_exceptions=True)

        valid_analyses = []
        for i, res in enumerate(chunk_analyses):
            if isinstance(res, Exception):
                self._logger.error("Chunk analysis failed", doc_id=doc_id, chunk_index=i+1, error=str(res))
            else:
                valid_analyses.append(res)

        if not valid_analyses:
            self._logger.error("All chunk analyses failed", doc_id=doc_id)
            return None

        # 2. REDUCE PHASE
        self._logger.info("Executing Reduce Phase", doc_id=doc_id)
        
        # Estimate reduce chars
        reduce_input_chars = sum(len(c.model_dump_json()) for c in valid_analyses)
        
        try:
            final_report = await self._reduce_synthesizer.synthesize(valid_analyses, metadata)
        except Exception as e:
            self._logger.error("Reduce phase failed", doc_id=doc_id, error=str(e))
            return None

        # Add processing timestamp
        final_report.processed_at = datetime.now(timezone.utc).isoformat()
        
        # Pull gazette_date and url if available
        if not final_report.gazette_date and "tarih" in metadata:
            final_report.gazette_date = metadata["tarih"]
        if not final_report.source_url and "source_url" in metadata:
            final_report.source_url = metadata["source_url"]

        # 3. SAVE REPORT
        output_path = os.path.join(self._settings.INTELLIGENCE_REPORTS_DIR, f"{doc_id}.json")
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_report.model_dump_json(indent=2))
            self._logger.info("Final Report saved", doc_id=doc_id, path=output_path)
        except Exception as e:
            self._logger.error("Failed to save final report", doc_id=doc_id, error=str(e))

        # 4. LOG COST
        estimated_cost = self._estimate_cost(map_input_chars, reduce_input_chars)
        self._logger.info("💰 Orchestration complete", doc_id=doc_id, estimated_cost_usd=round(estimated_cost, 4))
        
        return final_report

    async def process_all(self) -> None:
        """
        Process all normalized JSON documents in the parsed_json directory.
        """
        parsed_dir = Path(self._settings.PARSED_JSON_DIR)
        if not parsed_dir.exists() or not parsed_dir.is_dir():
            self._logger.error("Parsed JSON directory not found", path=str(parsed_dir))
            return

        json_files = sorted(parsed_dir.glob("*.json"))
        if not json_files:
            self._logger.info("No documents found to process", path=str(parsed_dir))
            return

        self._logger.info("Processing all documents", count=len(json_files))

        for file_path in json_files:
            # We process sequentially to avoid aggressive rate limiting across documents
            try:
                await self.process_document(str(file_path))
            except Exception as e:
                self._logger.error("Unexpected error processing document", path=str(file_path), error=str(e))
                # Never crash on a single bad document
                continue


async def main() -> None:
    parser = argparse.ArgumentParser(description="Map-Reduce RAG Intelligence Engine")
    parser.add_argument("--doc", type=str, help="Path to a specific normalized JSON document to process", default=None)
    parser.add_argument("--all", action="store_true", help="Process all documents in the parsed_json directory")
    args = parser.parse_args()

    # Configure logging
    import logging
    settings = get_settings()
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
    )

    engine = IntelligenceEngine(settings)
    
    if args.doc:
        await engine.process_document(args.doc)
    elif args.all:
        await engine.process_all()
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
