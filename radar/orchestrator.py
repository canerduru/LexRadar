"""
Master Orchestrator pulling together Hunter, Parser, Brain, Memory, and Radar.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import structlog

from config.settings import Settings
from hunter.gazette_hunter import GazetteHunter
from hunter.yargitay_hunter import YargitayHunter
from hunter.danistay_hunter import DanistayHunter
from hunter.kik_hunter import KIKHunter
from parser.pdf_parser import LlamaParseWrapper
from parser.metadata_extractor import MetadataExtractor
from parser.normalizer import DocumentNormalizer
from brain.intelligence_engine import IntelligenceEngine
from memory.vector_store import ChromaMemory
from radar.alert_engine import AlertEngine


class PipelineOrchestrator:
    """
    THE MASTER Orchestrator coordinating all modules safely.
    """
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._logger = structlog.get_logger()
        
        # Instantiate all sub-modules
        self._gazette_hunter = GazetteHunter(settings)
        self._yargitay_hunter = YargitayHunter()
        self._danistay_hunter = DanistayHunter()
        self._kik_hunter = KIKHunter()
        self._parser = LlamaParseWrapper(settings)
        self._normalizer = DocumentNormalizer(settings)
        self._metadata_extractor = MetadataExtractor()
        
        self._brain = IntelligenceEngine(settings)
        self._memory = ChromaMemory(settings)
        self._alert_engine = AlertEngine(settings)

        os.makedirs("data", exist_ok=True)
        self._runs_log_path = "data/pipeline_runs.jsonl"

    async def _write_run_log(self, record: dict) -> None:
        with open(self._runs_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def run_full_pipeline(self, days_back: int = 1) -> None:
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        self._logger.info("🚀 Starting Master Pipeline Run", run_id=run_id, days_back=days_back)
        
        summary = {
            "run_id": run_id,
            "started_at": started_at.isoformat(),
            "finished_at": "",
            "pdfs_found": 0,
            "pdfs_parsed": 0,
            "reports_generated": 0,
            "matches_found": 0,
            "alerts_sent": 0,
            "errors": []
        }
        
        # 1. HUNTER PHASE
        try:
            results = await asyncio.gather(
                self._gazette_hunter.run(days_back=days_back),
                self._yargitay_hunter.run(days_back=days_back),
                self._danistay_hunter.run(days_back=days_back),
                self._kik_hunter.run(days_back=days_back),
                return_exceptions=True
            )
            
            all_downloads = []
            source_counts = {"GAZETTE": 0, "YARGITAY": 0, "DANISTAY": 0, "KIK": 0}
            
            for res_list in results:
                if isinstance(res_list, Exception):
                    self._logger.error(f"A hunter failed: {str(res_list)}")
                    summary["errors"].append(str(res_list))
                    continue
                
                # Flatten lists
                for item in res_list:
                    if item.status == "downloaded" and item.path:
                        all_downloads.append(item)
                    if item.path:
                        source_counts[item.source] = source_counts.get(item.source, 0) + 1
            
            # Log exact counts per source requested by user
            self._logger.info(f"📰 Gazette: {source_counts.get('GAZETTE', 0)} PDFs")
            self._logger.info(f"⚖️ Yargıtay: {source_counts.get('YARGITAY', 0)} kararlar")
            self._logger.info(f"🏛️ Danıştay: {source_counts.get('DANISTAY', 0)} kararlar")
            self._logger.info(f"📋 KİK: {source_counts.get('KIK', 0)} ihaleler")
            
            downloads = all_downloads
            summary["pdfs_found"] = len(downloads)
        except Exception as e:
            msg = f"Hunter phase failed: {str(e)}"
            self._logger.error(msg)
            summary["errors"].append(msg)
            downloads = []

        # Process each PDF safely
        for item in downloads:
            pdf_path = item.path
            source_url = item.url
            
            try:
                # 2. PARSER PHASE
                parse_result = await self._parser.parse(pdf_path)
                metadata = self._metadata_extractor.extract(parse_result)
                metadata["source"] = item.source  # Inject source into metadata
                json_path = await self._normalizer.normalize_and_save(parse_result, metadata, source_url)
                summary["pdfs_parsed"] += 1
                
                # 3. BRAIN PHASE
                report = await self._brain.process_document(json_path)
                if not report:
                    continue
                summary["reports_generated"] += 1
                
                # 4. MEMORY / STORE PHASE
                await self._memory.upsert_intelligence(report)
                
                # 5. MATCH PHASE
                matches = await self._memory.find_portfolio_matches_for_report(report)
                summary["matches_found"] += len(matches)
                
                # 6. ALERT PHASE
                if matches:
                    await self._alert_engine.process_and_alert(report, matches)
                    # We estimate 1 alert triggered per report for this metric
                    summary["alerts_sent"] += 1

            except Exception as e:
                msg = f"Pipeline failed for {pdf_path}: {str(e)}"
                self._logger.error(msg)
                summary["errors"].append(msg)

        # 7. LOG SUMMARY
        finished_at = datetime.now(timezone.utc)
        summary["finished_at"] = finished_at.isoformat()
        
        duration = finished_at - started_at
        summary["duration_secs"] = round(duration.total_seconds(), 2)
        self._logger.info(
            "🏁 Pipeline Run Complete",
            **summary
        )
        
        await self._write_run_log(summary)
