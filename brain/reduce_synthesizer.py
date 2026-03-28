"""
Reduce Phase: Synthesizes chunk analyses using GPT-4o-mini.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Literal

import openai
import structlog
from pydantic import BaseModel, ConfigDict, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from brain.map_analyzer import ChunkAnalysis, Opportunity, Risk
from brain.prompts import REDUCE_SYSTEM_PROMPT, REDUCE_USER_PROMPT
from config.settings import Settings


class FinalReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    doc_id: str = Field(default="")
    gazette_date: str = Field(default="")
    document_type: str = Field(default="")
    overall_signal: Literal["OPPORTUNITY", "RISK", "MIXED", "NEUTRAL", ""] = Field(default="")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    executive_summary_en: str = Field(default="")
    executive_summary_tr: str = Field(default="")
    opportunities: List[Opportunity] = Field(default_factory=list)
    risks: List[Risk] = Field(default_factory=list)
    decision_type: str = Field(default="")
    court_or_authority: str = Field(default="")
    legal_areas: List[str] = Field(default_factory=list)
    affected_sectors: List[str] = Field(default_factory=list)
    case_references: List[str] = Field(default_factory=list)
    key_entities: List[str] = Field(default_factory=list)
    urgency_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL", ""] = Field(default="")
    action_required: bool = Field(default=False)
    recommended_actions: List[str] = Field(default_factory=list)
    source_url: str = Field(default="")
    source: str = Field(default="")
    processed_at: str = Field(default="")


class ReportReduceSynthesizer:
    """
    Synthesizer that runs the Reduce phase on chunk analyses using GPT-4o-mini.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._logger = structlog.get_logger()
        self._client = openai.AsyncOpenAI(api_key=self._settings.OPENAI_API_KEY)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _synthesize_with_retry(self, user_prompt: str) -> str:
        """Call OpenAI API with retry logic."""
        response = await self._client.chat.completions.create(
            model=self._settings.REDUCE_MODEL,
            temperature=self._settings.REDUCE_TEMPERATURE,
            messages=[
                {"role": "system", "content": REDUCE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response received from OpenAI API")
        return content

    async def _reduce_batch(self, chunk_analyses: List[ChunkAnalysis], doc_metadata: Dict[str, Any]) -> FinalReport:
        doc_id = doc_metadata.get("id", "unknown_doc")
        
        # Serialize chunks to JSON string
        chunks_str = json.dumps([c.model_dump() for c in chunk_analyses], ensure_ascii=False, indent=2)
        
        prompt = REDUCE_USER_PROMPT.format(
            n=len(chunk_analyses),
            doc_id=doc_id,
            all_chunk_analyses=chunks_str,
        )

        for attempt in range(1, 4):
            try:
                raw_response = await self._synthesize_with_retry(prompt)
                parsed_json = json.loads(raw_response)
                return FinalReport.model_validate(parsed_json)
            except json.JSONDecodeError as e:
                self._logger.warning("Failed to parse JSON response during reduce", error=str(e), attempt=attempt)
                prompt += "\nOutput ONLY valid JSON, no markdown"
            except Exception as e:
                self._logger.error("Error synthesizing chunks", error=str(e), attempt=attempt)
                if attempt == 3:
                    raise

        # Fallback if parsing fails across all retries
        return FinalReport(doc_id=doc_id)

    async def synthesize(self, chunk_analyses: List[ChunkAnalysis], doc_metadata: Dict[str, Any]) -> FinalReport:
        """
        Synthesize chunk analyses into a final report. Handles recursion if too large.
        """
        doc_id = doc_metadata.get("id", "unknown_doc")
        n_chunks = len(chunk_analyses)
        self._logger.info(f"🧬 Reducing {n_chunks} chunks into final report for {doc_id}")

        chunks_str = json.dumps([c.model_dump() for c in chunk_analyses], ensure_ascii=False)

        # Recursively reduce if total text exceeds ~100k characters
        if len(chunks_str) > 100000 and n_chunks > 10:
            self._logger.info("Chunks too large, performing recursive reduction", doc_id=doc_id, total_chars=len(chunks_str))
            
            # Batch in groups of 10
            batch_size = 10
            intermediate_reports = []
            
            for i in range(0, n_chunks, batch_size):
                batch = chunk_analyses[i:i + batch_size]
                intermediate_report = await self._reduce_batch(batch, doc_metadata)
                
                # Convert intermediate report back to a synthetic ChunkAnalysis to pass upwards
                synthetic_chunk = ChunkAnalysis(
                    chunk_index=i // batch_size + 1,
                    opportunities=intermediate_report.opportunities,
                    risks=intermediate_report.risks,
                    decision_type=getattr(intermediate_report, "decision_type", ""),
                    court_or_authority=getattr(intermediate_report, "court_or_authority", ""),
                    legal_areas=getattr(intermediate_report, "legal_areas", []),
                    affected_sectors=getattr(intermediate_report, "affected_sectors", []),
                    case_references=getattr(intermediate_report, "case_references", []),
                    key_entities=intermediate_report.key_entities,
                    has_actionable_data=intermediate_report.action_required,
                    summary_tr=intermediate_report.executive_summary_tr,
                    summary_en=intermediate_report.executive_summary_en,
                )
                intermediate_reports.append(synthetic_chunk)
            
            # Recurse on the intermediate results
            return await self.synthesize(intermediate_reports, doc_metadata)
        else:
            return await self._reduce_batch(chunk_analyses, doc_metadata)
