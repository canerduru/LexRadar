"""
Prompts for the Map-Reduce RAG analysis engine.
"""

from __future__ import annotations

MAP_SYSTEM_PROMPT = """You are a Turkish real estate and legal intelligence analyst. Analyze ONLY the provided text chunk. Do NOT speculate beyond what is written. Output ONLY valid JSON."""

MAP_USER_PROMPT = """Given this chunk ({chunk_index}/{total_chunks}) from gazette document {doc_id}:
---
{chunk_text}
---
Extract and return JSON:
{{
  "chunk_index": {chunk_index},
  "opportunities": [{{"type": "str", "description": "str", "location": "str", "parcel_id": "str", "monetary_value": "str", "confidence": 0.0}}],
  "risks": [{{"type": "str", "description": "str", "location": "str", "affected_entity": "str", "severity": "LOW|MED|HIGH", "confidence": 0.0}}],
  "key_entities": ["str"],
  "key_locations": ["str"],
  "document_type_confirmed": "str",
  "has_actionable_data": true,
  "summary_tr": "str (1 sentence in Turkish)",
  "summary_en": "str (1 sentence in English)"
}}"""

REDUCE_SYSTEM_PROMPT = """You are a senior real estate investment analyst. You receive multiple chunk analyses from the SAME document. Synthesize them into ONE authoritative report. Deduplicate, resolve conflicts by choosing highest-confidence signal, preserve all unique findings."""

REDUCE_USER_PROMPT = """Synthesize these {n} chunk analyses for document {doc_id} into a final intelligence report JSON:
{all_chunk_analyses}

Output schema:
{{
  "doc_id": "{doc_id}",
  "gazette_date": "str",
  "document_type": "str",
  "overall_signal": "OPPORTUNITY|RISK|MIXED|NEUTRAL",
  "confidence_score": 0.0,
  "executive_summary_en": "str",
  "executive_summary_tr": "str",
  "opportunities": [],
  "risks": [],
  "key_locations": [],
  "key_entities": [],
  "land_parcels": [],
  "total_monetary_exposure_try": 0.0,
  "action_required": true,
  "recommended_actions": ["str"],
  "source_url": "str",
  "processed_at": "str"
}}"""
