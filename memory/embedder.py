"""
Text Embedder for the Memory Engine.
"""

from __future__ import annotations

import asyncio
from typing import List

import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import Settings
from memory.schema import IntelligenceEntry, PortfolioItem


class TextEmbedder:
    """
    Generates embeddings using OpenAI's text-embedding-3-small model.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = openai.AsyncOpenAI(api_key=self._settings.OPENAI_API_KEY)
        self._model = self._settings.EMBEDDING_MODEL
        # Rate limiting: max 100 texts per batch
        self._max_batch_size = 100

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single string.
        """
        response = await self._client.embeddings.create(
            input=[text],
            model=self._model
        )
        return response.data[0].embedding

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _embed_batch_chunk(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a chunk of strings.
        """
        if not texts:
            return []
            
        response = await self._client.embeddings.create(
            input=texts,
            model=self._model
        )
        
        # Sort by index to maintain original order just in case
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of strings, handling max batch size.
        """
        all_embeddings = []
        for i in range(0, len(texts), self._max_batch_size):
            chunk = texts[i:i + self._max_batch_size]
            chunk_embeddings = await self._embed_batch_chunk(chunk)
            all_embeddings.extend(chunk_embeddings)
        return all_embeddings

    def build_portfolio_text(self, item: PortfolioItem) -> str:
        """
        Builds the cohesive text representation of a PortfolioItem for embedding.
        """
        ada = item.ada_parsel if item.ada_parsel else "Bilinmiyor"
        tags = ", ".join(item.tags) if item.tags else "Yok"
        keywords = ", ".join(item.watchlist_keywords) if item.watchlist_keywords else "Yok"
        
        text = (
            f"{item.asset_type} in {item.district}, {item.city}. "
            f"Ada/Parsel: {ada}. "
            f"Tags: {tags}. "
            f"Keywords: {keywords}. "
            f"Notes: {item.notes}"
        )
        return text

    def build_intelligence_text(self, entry: IntelligenceEntry) -> str:
        """
        Builds the cohesive text representation of an IntelligenceEntry for embedding.
        """
        locs = ", ".join(entry.key_locations) if entry.key_locations else "Yok"
        
        # Extract summaries from complex dicts
        opp_summaries = []
        for opp in entry.opportunities:
            desc = opp.get("description", "")
            if desc:
                opp_summaries.append(desc)
        opps_str = " | ".join(opp_summaries) if opp_summaries else "Yok"
        
        risk_summaries = []
        for rsk in entry.risks:
            desc = rsk.get("description", "")
            if desc:
                risk_summaries.append(desc)
        risks_str = " | ".join(risk_summaries) if risk_summaries else "Yok"

        text = (
            f"{entry.overall_signal}: {entry.executive_summary_en}. "
            f"Locations: {locs}. "
            f"Opportunities: {opps_str}. "
            f"Risks: {risks_str}"
        )
        return text
