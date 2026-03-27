"""
Pydantic schemas for the Memory Engine.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PortfolioItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: UUID
    client_name: str
    asset_type: Literal["ARSA", "BINA", "TARLA", "BAHÇE", "DEPO", "OFİS", "PROJE"]
    district: str
    city: str
    ada_parsel: Optional[str] = None
    address: str
    area_sqm: float
    current_value_try: float
    tags: List[str] = Field(default_factory=list)
    notes: str = ""
    created_at: datetime
    watchlist_keywords: List[str] = Field(default_factory=list)


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


class SearchResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    score: float
    document: str
    metadata: dict


class MatchResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    portfolio_item: PortfolioItem
    intelligence_entry: IntelligenceEntry
    similarity_score: float
    match_reasons: List[str] = Field(default_factory=list)
