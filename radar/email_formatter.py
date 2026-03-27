"""
Email Formatter for building Alert Payload structures.
"""

from __future__ import annotations

from typing import Dict, List

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

from brain.reduce_synthesizer import FinalReport
from config.settings import Settings
from memory.schema import MatchResult


class EmailPayload(BaseModel):
    subject: str
    html_body: str
    text_body: str


class AlertEmailFormatter:
    """
    Builds the formatted HTML/Text strings required to send email outputs mapping against the provided Jinja template.
    """
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.env = Environment(loader=FileSystemLoader("templates"))

    def format(self, match_results: List[MatchResult], report: FinalReport) -> EmailPayload:
        signal_badge = report.overall_signal if report.overall_signal else "NEUTRAL"
        legal_area = getattr(report, "legal_area", "Genel")
        court = getattr(report, "court_or_authority", "Bilinmiyor")
        date_str = report.gazette_date if report.gazette_date else "Today"
        
        subject = f"⚖️ [{signal_badge}] {legal_area} — {court} | Legal Radar {date_str}"

        # Group matches by client
        matched_groups: Dict[str, List[MatchResult]] = {}
        for match in match_results:
            client = match.portfolio_item.client_name
            if client not in matched_groups:
                matched_groups[client] = []
            matched_groups[client].append(match)

        template = self.env.get_template("alert_email.html")
        html_body = template.render(
            report=report,
            matched_groups=matched_groups
        )

        # Fallback raw text parsing representing the 9 sections
        text_body = "1. Legal Intelligence Radar — Hukuki Uyarı\n\n"
        text_body += f"2. Tür: {getattr(report, 'decision_type', 'OTHER')}\n\n"
        text_body += f"3. Özet (TR): {report.executive_summary_tr}\n"
        text_body += f"   Özet (EN): {report.executive_summary_en}\n\n"
        text_body += f"4. Etkilenen Hukuki Alanlar: {', '.join(getattr(report, 'legal_areas', []))}\n"
        text_body += f"5. Etkilenen Sektörler: {', '.join(getattr(report, 'affected_sectors', []))}\n\n"
        text_body += "6. Matched Client Watchlist:\n"
        
        for client, items in matched_groups.items():
            text_body += f"   - {client}\n"
            for match in items:
                text_body += f"     > {match.portfolio_item.company_name} (Uyumluluk: {match.similarity_score:.2f})\n"
                
        text_body += f"\n7. Önerilen Aksiyonlar: {', '.join(report.recommended_actions)}\n"
        text_body += f"8. Aciliyet Seviyesi: {getattr(report, 'urgency_level', 'LOW')}\n"
        text_body += f"9. Kaynak: {report.source_url}\n"

        return EmailPayload(
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
