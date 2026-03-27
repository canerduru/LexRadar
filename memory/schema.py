"""
Pydantic schemas for the Memory Engine.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClientWatchlist(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: UUID
    client_name: str
    company_name: str
    sector: Literal['TEKNOLOJI', 'FINANS', 'INSAAT', 'ILAC', 'ENERJI', 'DIGER']
    legal_areas: List[Literal['REKABET', 'VERGI', 'IS_HUKUKU', 'KVKK', 'IHALE', 'SIRKETLER', 'CEZA', 'IDARE']]
    case_references: List[str] = Field(default_factory=list)
    watchlist_keywords: List[str] = Field(default_factory=list)
    alert_threshold: float = 0.75
    notes: str = ""
    created_at: datetime


class IntelligenceEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str  # Maps to FinalReport.doc_id
    gazette_date: str
    overall_signal: str
    executive_summary_en: str
    key_locations: List[str] = Field(default_factory=list)
    opportunities: List[dict] = Field(default_factory=list)
    risks: List[dict] = Field(default_factory=list)
    source_url: str = ""
    raw_json_path: str = ""
    legal_area: str = ""
    affected_sectors: List[str] = Field(default_factory=list)
    case_references: List[str] = Field(default_factory=list)
    court_name: Optional[str] = None
    decision_type: Literal['KARAR', 'KANUN', 'YONETMELIK', 'TEBLIG', 'IHALE', 'OTHER'] = 'OTHER'


class SearchResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    score: float
    document: str
    metadata: dict


class MatchResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    portfolio_item: ClientWatchlist
    intelligence_entry: IntelligenceEntry
    similarity_score: float
    match_reasons: List[str] = Field(default_factory=list)
    match_type: Literal['KEYWORD', 'SECTOR', 'LEGAL_AREA', 'CASE_REF', 'ENTITY', 'SEMANTIC'] = 'SEMANTIC'
    urgency_level: str = ""
    recommended_action: str = ""
