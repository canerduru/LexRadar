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
from memory.schema import IntelligenceEntry, MatchResult, ClientWatchlist, SearchResult


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
            raw_json_path="",
            # Add new fields with sensible defaults or leave them empty if not provided logically yet
            legal_area="",
            affected_sectors=[],
            case_references=[],
            court_name=None,
            decision_type="OTHER"
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

    async def upsert_portfolio_item(self, item: ClientWatchlist) -> None:
        """
        Adds or updates a ClientWatchlist entry.
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

    async def find_watchlist_matches_for_report(self, report: FinalReport) -> List[MatchResult]:
        """
        Smart matching: embed report's key details to query portfolio,
        and embed portfolio's watchlist_keywords to query intelligence.
        Returns union of match sets above SIMILARITY_THRESHOLD or based on heuristics.
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
            raw_json_path="",
            # Use getattr to safely handle Pydantic fields that might be missing dynamically
            legal_area=getattr(report, "legal_area", ""),
            affected_sectors=getattr(report, "affected_sectors", []),
            case_references=getattr(report, "case_references", []),
            court_name=getattr(report, "court_or_authority", None),
            decision_type=getattr(report, "decision_type", "OTHER")
        )

        urgency_level = getattr(report, "urgency_level", "")
        recommended_actions = getattr(report, "recommended_actions", [])
        recommended_action = recommended_actions[0] if recommended_actions else ""

        all_matches: Dict[str, MatchResult] = {}
        all_portfolios = await self.get_all_portfolio()
        
        # Perform deterministic heuristic matching against all portfolios
        for p_item in all_portfolios:
            score = 0.0
            match_type = 'SEMANTIC'
            reasons = []

            # 1. Exact Match: Case References (Highest Priority)
            if p_item.case_references and hasattr(report, "case_references") and report.case_references:
                for case_ref in p_item.case_references:
                    if any(case_ref.lower() in rep_ref.lower() for rep_ref in report.case_references):
                        score = 1.0
                        match_type = 'CASE_REF'
                        reasons.append(f"Exact case reference match: {case_ref}")

            # 2. Key Entities overlap (Company name)
            if score < 1.0 and hasattr(report, "key_entities") and report.key_entities:
                if any(p_item.company_name.lower() in ent.lower() for ent in report.key_entities):
                    score = max(score, 0.95)
                    match_type = 'ENTITY'
                    reasons.append(f"Company entity match: {p_item.company_name}")

            # 3. Sector & Legal Area combined match
            if score < 0.85:
                sector_match = hasattr(report, "affected_sectors") and p_item.sector in report.affected_sectors
                legal_match = hasattr(report, "legal_areas") and any(la in report.legal_areas for la in p_item.legal_areas)
                if sector_match and legal_match:
                    score = max(score, 0.85)
                    match_type = 'LEGAL_AREA' if not score else match_type
                    reasons.append(f"Sector ({p_item.sector}) and Legal Area ({', '.join(p_item.legal_areas)}) aligned.")
                elif sector_match:
                    reasons.append(f"Sector logic alignment: {p_item.sector}")
                elif legal_match:
                    reasons.append(f"Legal Area alignment")

            # 4. Keyword Substring Match (as an ultimate fallback alongside vectors)
            if score < self._settings.SIMILARITY_THRESHOLD:
                if p_item.watchlist_keywords:
                    # simplistic fallback test on the summaries
                    for kw in p_item.watchlist_keywords:
                        if kw.lower() in report.executive_summary_en.lower() or kw.lower() in report.executive_summary_tr.lower():
                            score = max(score, self._settings.SIMILARITY_THRESHOLD + 0.05)
                            match_type = 'KEYWORD'
                            reasons.append(f"Keyword semantic match: {kw}")

            if score >= self._settings.SIMILARITY_THRESHOLD:
                match = MatchResult(
                    portfolio_item=p_item,
                    intelligence_entry=entry,
                    similarity_score=score,
                    match_reasons=reasons,
                    match_type=match_type,
                    urgency_level=urgency_level,
                    recommended_action=recommended_action
                )
                all_matches[str(p_item.id)] = match

        # 5. Semantic Query (for instances where heuristics fail but concepts align)
        locs = ", ".join(report.key_locations)
        opps = ", ".join([o.description for o in getattr(report, "opportunities", [])])
        risks = ", ".join([r.description for r in getattr(report, "risks", [])])
        query_text = f"Locations: {locs}. Opportunities: {opps}. Risks: {risks}"
        
        port_results = await self.query_portfolio(query_text, n=self._settings.TOP_K_MATCHES)
        for res in port_results:
            if res.score >= self._settings.SIMILARITY_THRESHOLD:
                pid = res.metadata.get("id")
                if str(pid) not in all_matches:
                    p_item = self._deserialize_metadata(res.metadata, ClientWatchlist)
                    match = MatchResult(
                        portfolio_item=p_item,
                        intelligence_entry=entry,
                        similarity_score=res.score,
                        match_reasons=["Semantic overlap found in descriptions."],
                        match_type='SEMANTIC',
                        urgency_level=urgency_level,
                        recommended_action=recommended_action
                    )
                    all_matches[str(p_item.id)] = match

        return list(all_matches.values())

    async def get_all_portfolio(self) -> List[ClientWatchlist]:
        results = self._portfolio_collection.get()
        items = []
        if "metadatas" in results and results["metadatas"]:
            for meta in results["metadatas"]:
                if meta:
                    items.append(self._deserialize_metadata(meta, ClientWatchlist))
        return items

    async def delete_portfolio_item(self, item_id: str) -> None:
        self._portfolio_collection.delete(ids=[item_id])
