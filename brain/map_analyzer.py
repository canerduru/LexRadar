"""
Map Phase: Analyzes individual chunks using Gemini Flash.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Literal

import google.generativeai as genai
import structlog
from pydantic import BaseModel, ConfigDict, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from brain.prompts import MAP_SYSTEM_PROMPT, MAP_USER_PROMPT
from config.settings import Settings


class Opportunity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: str = Field(default="")
    description: str = Field(default="")
    affected_sector: str = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class Risk(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: str = Field(default="")
    description: str = Field(default="")
    affected_sector: str = Field(default="")
    severity: Literal["LOW", "MED", "HIGH", ""] = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ChunkAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")
    chunk_index: int
    decision_type: Literal['KARAR', 'KANUN', 'YONETMELIK', 'TEBLIG', 'IHALE', 'YARGITAY_KARARI', 'DANISTAY_KARARI', 'KIK_KARARI', 'OTHER', ''] = Field(default="")
    court_or_authority: str = Field(default="")
    legal_areas: List[str] = Field(default_factory=list)
    affected_sectors: List[str] = Field(default_factory=list)
    opportunities: List[Opportunity] = Field(default_factory=list)
    risks: List[Risk] = Field(default_factory=list)
    case_references: List[str] = Field(default_factory=list)
    key_entities: List[str] = Field(default_factory=list)
    has_actionable_data: bool = Field(default=False)
    summary_tr: str = Field(default="")
    summary_en: str = Field(default="")


class ChunkMapAnalyzer:
    """
    Analyzer that runs the Map phase on chunks using Gemini Flash.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._logger = structlog.get_logger()
        genai.configure(api_key=self._settings.GOOGLE_API_KEY)
        self._model = genai.GenerativeModel(
            model_name=self._settings.MAP_MODEL,
            system_instruction=MAP_SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=self._settings.MAP_TEMPERATURE,
            ),
        )
        self._semaphore = asyncio.Semaphore(10)

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=5, max=70))
    async def _analyze_with_retry(self, prompt: str) -> str:
        """Call Gemini API with retry logic. Tenacity handles retries on failures."""
        response = await self._model.generate_content_async(prompt)
        text = response.text
        if not text:
            raise ValueError("Empty response received from API")
        return text

    async def analyze_chunk(self, chunk: Dict[str, Any], doc_metadata: Dict[str, Any]) -> ChunkAnalysis:
        """
        Analyze a single chunk and return structured analysis.
        """
        doc_id = doc_metadata.get("id", "unknown_doc")
        chunk_index = chunk.get("index", 1)
        total_chunks = doc_metadata.get("total_chunks", 1)
        chunk_text = chunk.get("text", "")

        self._logger.info(f"🗺️ Mapping chunk {chunk_index}/{total_chunks} for {doc_id}")

        source_name = doc_metadata.get("source", "UNKNOWN")

        prompt = MAP_USER_PROMPT.format(
            source=source_name,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            doc_id=doc_id,
            chunk_text=chunk_text,
        )

        async with self._semaphore:
            for attempt in range(1, 4):
                try:
                    raw_response = await self._analyze_with_retry(prompt)
                    parsed_json = json.loads(raw_response)
                    return ChunkAnalysis.model_validate(parsed_json)
                except json.JSONDecodeError as e:
                    self._logger.warning("Failed to parse JSON response", error=str(e), attempt=attempt)
                    prompt += "\nOutput ONLY valid JSON, no markdown"
                except Exception as e:
                    self._logger.error("Error analyzing chunk", error=str(e), attempt=attempt)
                    if attempt == 3:
                        raise

            # Fallback if parsing fails across all retries
            return ChunkAnalysis(chunk_index=chunk_index)
