"""
Prompts for the Map-Reduce RAG analysis engine.
"""

from __future__ import annotations

MAP_SYSTEM_PROMPT = """You are a Turkish legal intelligence analyst specializing in corporate law, regulatory changes, and court decisions. Analyze ONLY the provided text chunk. Output ONLY valid JSON."""

MAP_USER_PROMPT = """Given this chunk ({chunk_index}/{total_chunks}) from document {doc_id}:
This document is from source: {source} 
(GAZETTE=Resmi Gazete, YARGITAY=Court of Cassation, DANISTAY=Council of State, KIK=Public Procurement Authority)
---
{chunk_text}
---
Extract and return JSON:
{{
  "chunk_index": {chunk_index},
  "decision_type": "KARAR|KANUN|YONETMELIK|TEBLIG|IHALE|YARGITAY_KARARI|DANISTAY_KARARI|KIK_KARARI|OTHER",
  "court_or_authority": "str",
  "legal_areas": ["REKABET|VERGI|IS_HUKUKU|KVKK|IHALE|SIRKETLER|CEZA|IDARE"],
  "affected_sectors": ["str"],
  "opportunities": [{{"type": "str", "description": "str", "affected_sector": "str", "confidence": 0.0}}],
  "risks": [{{"type": "str", "description": "str", "affected_sector": "str", "severity": "LOW|MED|HIGH", "confidence": 0.0}}],
  "case_references": ["str"],
  "key_entities": ["str"],
  "has_actionable_data": true,
  "summary_tr": "str",
  "summary_en": "str"
}}"""

REDUCE_SYSTEM_PROMPT = """You are a senior Turkish legal counsel. Synthesize chunk analyses into one authoritative legal intelligence report. Focus on actionable insights for corporate clients.
If multiple chunks reference the same legal matter from different sources (e.g. a Gazette announcement AND a Yargıtay decision), synthesize them as ONE unified finding with higher confidence score."""

REDUCE_USER_PROMPT = """Synthesize these {n} chunk analyses for document {doc_id} into a final intelligence report JSON:
{all_chunk_analyses}

Output schema:
{{
  "doc_id": "{doc_id}",
  "gazette_date": "str",
  "decision_type": "str",
  "court_or_authority": "str",
  "legal_areas": ["str"],
  "affected_sectors": ["str"],
  "overall_signal": "OPPORTUNITY|RISK|MIXED|NEUTRAL",
  "confidence_score": 0.0,
  "executive_summary_en": "str",
  "executive_summary_tr": "str",
  "opportunities": [],
  "risks": [],
  "case_references": [],
  "key_entities": [],
  "action_required": true,
  "recommended_actions": ["str"],
  "urgency_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "source_url": "str",
  "processed_at": "str"
}}"""
