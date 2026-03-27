"""
Vector Store component using ChromaDB.
"""

from __future__ import annotations

import os
from typing import Dict, List, Any

import chromadb
import structlog
from chromadb.config import Settings as ChromaSettings

from brain.reduce_synthesizer import FinalReport
from config.settings import Settings
from memory.embedder import TextEmbedder
from memory.schema import IntelligenceEntry, MatchResult, PortfolioItem, SearchResult


class ChromaMemory:
    """
    ChromaDB-powered dual-memory system for Intelligence and Portfolio entries.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._logger = structlog.get_logger()
        self._embedder = TextEmbedder(settings)

        os.makedirs(self._settings.CHROMA_DB_DIR, exist_ok=True)
        
        self._client = chromadb.PersistentClient(
            path=self._settings.CHROMA_DB_DIR,
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # Get or create collections with cosine distance
        self._intel_collection = self._client.get_or_create_collection(
            name=self._settings.INTELLIGENCE_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )

        self._portfolio_collection = self._client.get_or_create_collection(
            name=self._settings.PORTFOLIO_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )

        n_intel = self._intel_collection.count()
        n_port = self._portfolio_collection.count()
        self._logger.info(f"🧠 Memory online: {n_intel} intelligence entries, {n_port} portfolio items")

    async def upsert_intelligence(self, report: FinalReport) -> None:
        """
        Adds or updates an intelligence entry.
        """
        entry = IntelligenceEntry(
            id=report.doc_id,
            gazette_date=report.gazette_date,
            overall_signal=report.overall_signal,
            executive_summary_en=report.executive_summary_en,
            key_locations=report.key_locations,
            opportunities=[opp.model_dump() for opp in report.opportunities],
            risks=[rsk.model_dump() for rsk in report.risks],
            source_url=report.source_url,
            raw_json_path=""
        )

        text = self._embedder.build_intelligence_text(entry)
        embedding = await self._embedder.embed(text)

        metadata = entry.model_dump()
        # ChromaDB metadata values must be str, int, float, or bool. Serialize lists/dicts.
        for k, v in metadata.items():
            if isinstance(v, (list, dict)):
                import json
                metadata[k] = json.dumps(v, ensure_ascii=False)

        self._intel_collection.upsert(
            ids=[entry.id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )

    async def upsert_portfolio_item(self, item: PortfolioItem) -> None:
        """
        Adds or updates a portfolio entry.
        """
        text = self._embedder.build_portfolio_text(item)
        embedding = await self._embedder.embed(text)

        metadata = item.model_dump()
        metadata["id"] = str(metadata["id"])
        # Serialize lists/dicts
        for k, v in metadata.items():
            if isinstance(v, (list, dict)):
                import json
                metadata[k] = json.dumps(v, ensure_ascii=False)
            elif v is None:
                metadata[k] = ""
            elif hasattr(v, "isoformat"):
                metadata[k] = v.isoformat()

        self._portfolio_collection.upsert(
            ids=[str(item.id)],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )

    def _parse_chroma_results(self, results: Dict[str, Any]) -> List[SearchResult]:
        search_results = []
        if not results["ids"] or not results["ids"][0]:
            return search_results

        ids = results["ids"][0]
        distances = results["distances"][0] if "distances" in results and results["distances"] else [0.0]*len(ids)
        documents = results["documents"][0] if "documents" in results and results["documents"] else [""]*len(ids)
        metadatas = results["metadatas"][0] if "metadatas" in results and results["metadatas"] else [{}]*len(ids)

        for i in range(len(ids)):
            # Convert cosine distance to similarity (1 - distance)
            similarity = 1.0 - distances[i]
            search_results.append(SearchResult(
                id=ids[i],
                score=similarity,
                document=documents[i],
                metadata=metadatas[i]
            ))
        return search_results

    async def query_intelligence(self, query_text: str, n: int = None) -> List[SearchResult]:
        if n is None:
            n = self._settings.TOP_K_MATCHES
            
        embedding = await self._embedder.embed(query_text)
        results = self._intel_collection.query(
            query_embeddings=[embedding],
            n_results=n
        )
        return self._parse_chroma_results(results)

    async def query_portfolio(self, query_text: str, n: int = None) -> List[SearchResult]:
        if n is None:
            n = self._settings.TOP_K_MATCHES
            
        embedding = await self._embedder.embed(query_text)
        results = self._portfolio_collection.query(
            query_embeddings=[embedding],
            n_results=n
        )
        return self._parse_chroma_results(results)

    def _deserialize_metadata(self, metadata: dict, model_cls: Any) -> Any:
        import json
        clean_meta = dict(metadata)
        for k, v in clean_meta.items():
            if isinstance(v, str) and (v.startswith("[") or v.startswith("{")):
                try:
                    clean_meta[k] = json.loads(v)
                except:
                    pass
        return model_cls.model_validate(clean_meta)

    async def find_portfolio_matches_for_report(self, report: FinalReport) -> List[MatchResult]:
        """
        Smart matching: embed report's key details to query portfolio,
        and embed portfolio's watchlist_keywords to query intelligence.
        Returns union of match sets above SIMILARITY_THRESHOLD.
        """
        # Convert report to IntelligenceEntry
        entry = IntelligenceEntry(
            id=report.doc_id,
            gazette_date=report.gazette_date,
            overall_signal=report.overall_signal,
            executive_summary_en=report.executive_summary_en,
            key_locations=report.key_locations,
            opportunities=[opp.model_dump() for opp in report.opportunities],
            risks=[rsk.model_dump() for rsk in report.risks],
            source_url=report.source_url,
            raw_json_path=""
        )

        all_matches: Dict[str, MatchResult] = {}
        
        # 1. Report queries Portfolio
        locs = ", ".join(report.key_locations)
        opps = ", ".join([o.description for o in report.opportunities])
        risks = ", ".join([r.description for r in report.risks])
        query_text = f"Locations: {locs}. Opportunities: {opps}. Risks: {risks}"
        
        port_results = await self.query_portfolio(query_text, n=self._settings.TOP_K_MATCHES)
        
        for res in port_results:
            if res.score >= self._settings.SIMILARITY_THRESHOLD:
                portfolio_item = self._deserialize_metadata(res.metadata, PortfolioItem)
                
                # Determine match reasons heuristically
                reasons = []
                for loc in report.key_locations:
                    if loc.lower() in portfolio_item.district.lower() or loc.lower() in portfolio_item.city.lower():
                        reasons.append(f"Location overlap: {loc}")
                for kw in portfolio_item.watchlist_keywords:
                    if kw.lower() in query_text.lower():
                        reasons.append(f"Keyword match: {kw}")
                if not reasons:
                    reasons.append("Semantic semantic overlap found in descriptions.")
                
                match = MatchResult(
                    portfolio_item=portfolio_item,
                    intelligence_entry=entry,
                    similarity_score=res.score,
                    match_reasons=reasons
                )
                all_matches[str(portfolio_item.id)] = match

        # 2. Portfolio items query Intelligence
        all_portfolios = await self.get_all_portfolio()
        for p_item in all_portfolios:
            if str(p_item.id) in all_matches:
                continue # Already found a high-quality match
                
            if p_item.watchlist_keywords:
                kw_query = ", ".join(p_item.watchlist_keywords)
                # Embed keys and query intel
                embedding = await self._embedder.embed(kw_query)
                intel_results = self._intel_collection.query(
                    query_embeddings=[embedding],
                    n_results=self._settings.TOP_K_MATCHES
                )
                parsed_intel = self._parse_chroma_results(intel_results)
                
                for i_res in parsed_intel:
                    if i_res.score >= self._settings.SIMILARITY_THRESHOLD and i_res.id == entry.id:
                        reasons = [f"Watchlist keyword match: {kw}" for kw in p_item.watchlist_keywords if kw.lower() in i_res.document.lower()]
                        if not reasons:
                            reasons.append("Semantic keyword overlap found.")
                            
                        match = MatchResult(
                            portfolio_item=p_item,
                            intelligence_entry=entry,
                            similarity_score=i_res.score,
                            match_reasons=reasons
                        )
                        all_matches[str(p_item.id)] = match

        return list(all_matches.values())

    async def get_all_portfolio(self) -> List[PortfolioItem]:
        results = self._portfolio_collection.get()
        items = []
        if "metadatas" in results and results["metadatas"]:
            for meta in results["metadatas"]:
                if meta:
                    items.append(self._deserialize_metadata(meta, PortfolioItem))
        return items

    async def delete_portfolio_item(self, item_id: str) -> None:
        self._portfolio_collection.delete(ids=[item_id])
