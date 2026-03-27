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
        # Subject matching template rule:
        district_list = list(set([m.portfolio_item.district for m in match_results]))
        districts_str = ", ".join(district_list) if district_list else "Unknown District"
        
        signal_badge = report.overall_signal if report.overall_signal else "NEUTRAL"
        doc_type = report.document_type if report.document_type else "Gazette"
        date_str = report.gazette_date if report.gazette_date else "Today"
        
        subject = f"🚨 [{signal_badge}] {districts_str} — {doc_type} | Radar Alert {date_str}"

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

        # Fallback raw text parsing roughly matching HTML outline
        text_body = f"Radar Alert - {signal_badge}\nDate: {date_str}\n" \
                    f"Summary: {report.executive_summary_en}\n\nMatched Items:\n"
                    
        for client, items in matched_groups.items():
            text_body += f"\nClient: {client}\n"
            for match in items:
                text_body += f" - {match.portfolio_item.asset_type} | {match.portfolio_item.address} (Sim: {match.similarity_score:.2f})\n"

        return EmailPayload(
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
