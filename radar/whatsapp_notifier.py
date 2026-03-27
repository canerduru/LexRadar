"""
WhatsApp Notifier using Twilio.
"""

from __future__ import annotations

import structlog
from twilio.rest import Client

from brain.reduce_synthesizer import FinalReport
from config.settings import Settings
from memory.schema import MatchResult


class WhatsAppNotifier:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._logger = structlog.get_logger()
        
        sid = self._settings.TWILIO_ACCOUNT_SID
        token = self._settings.TWILIO_AUTH_TOKEN
        
        if sid and token:
            self._client = Client(sid, token)
        else:
            self._client = None
            self._logger.warning("Twilio credentials not found, WhatsApp notifications disabled.")

    async def send_alert(self, match_result: MatchResult, report: FinalReport) -> None:
        if not self._client:
            return

        reasons = ", ".join(match_result.match_reasons)
        score = match_result.similarity_score
        port_item = match_result.portfolio_item
        
        # Build the structured message
        message_body = (
            f"🏗️ *RADAR ALERT*\n"
            f"📍 *{report.overall_signal}* — {port_item.district}\n"
            f"📋 {report.executive_summary_en}\n\n"
            f"🎯 *Matched Asset:* {port_item.client_name} — {port_item.address}\n"
            f"📊 *Confidence:* {score:.0%}\n"
            f"💡 *Why:* {reasons}\n\n"
            f"🔗 Source: {report.source_url}"
        )
        
        # Keep under 1600 characters max limit of Twilio Whatsapp text chunk.
        if len(message_body) > 1600:
            message_body = message_body[:1595] + "..."

        try:
            await self._client.messages.create_async(
                body=message_body,
                from_=self._settings.TWILIO_WHATSAPP_FROM,
                to=self._settings.TWILIO_WHATSAPP_TO
            )
            self._logger.info("Sent WhatsApp alert", to=self._settings.TWILIO_WHATSAPP_TO, match_id=str(port_item.id))
        except Exception as e:
            self._logger.error("Failed to send WhatsApp alert", error=str(e), match_id=str(port_item.id))
