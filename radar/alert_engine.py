"""
Alert Engine module for processing match results, deduplicating, and firing notifications.
"""

from __future__ import annotations

import json
import os
from typing import List

import aiosmtplib
import structlog
from email.message import EmailMessage

from brain.reduce_synthesizer import FinalReport
from config.settings import Settings
from memory.schema import MatchResult
from radar.email_formatter import AlertEmailFormatter, EmailPayload
from radar.whatsapp_notifier import WhatsAppNotifier


class AlertEngine:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._logger = structlog.get_logger()
        self._email_formatter = AlertEmailFormatter(settings)
        self._whatsapp_notifier = WhatsAppNotifier(settings)
        
        os.makedirs("data", exist_ok=True)
        self._log_path = "data/alert_log.jsonl"
        self._sent_alerts = set()
        self._load_alert_history()

    def _load_alert_history(self) -> None:
        if os.path.exists(self._log_path):
            with open(self._log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            record = json.loads(line)
                            if "doc_id" in record:
                                self._sent_alerts.add(record["doc_id"])
                        except Exception:
                            pass

    async def _log_alert(self, doc_id: str, email_recipients: int, whatsapp_messages: int) -> None:
        """Write alert record to data/alert_log.jsonl (append-only)"""
        record = {
            "doc_id": doc_id,
            "email_recipients": email_recipients,
            "whatsapp_messages": whatsapp_messages,
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        }
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._sent_alerts.add(doc_id)

    async def _send_email(self, payload: EmailPayload) -> None:
        if not self._settings.SMTP_HOST or not self._settings.ALERT_TO_EMAILS:
            self._logger.warning("SMTP configuration missing. Skipping email.")
            return

        msg = EmailMessage()
        msg["Subject"] = payload.subject
        msg["From"] = self._settings.ALERT_FROM_EMAIL
        msg["To"] = self._settings.ALERT_TO_EMAILS

        msg.set_content(payload.text_body)
        msg.add_alternative(payload.html_body, subtype="html")

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._settings.SMTP_HOST,
                port=self._settings.SMTP_PORT,
                username=self._settings.SMTP_USER,
                password=self._settings.SMTP_PASSWORD,
                use_tls=True if self._settings.SMTP_PORT == 465 else False, # Typically TLS on 465 or StartTLS on 587
                start_tls=True if self._settings.SMTP_PORT == 587 else False
            )
        except Exception as e:
            self._logger.error("Failed to send email", error=str(e))
            raise

    async def process_and_alert(self, report: FinalReport, matches: List[MatchResult]) -> None:
        if report.doc_id in self._sent_alerts:
            self._logger.info("Alert already sent for document", doc_id=report.doc_id)
            return

        # 1. Filter matches based on thresholds
        valid_matches = []
        for match in matches:
            if match.similarity_score >= self._settings.MIN_SIMILARITY_FOR_ALERT and report.confidence_score >= self._settings.MIN_CONFIDENCE_FOR_ALERT:
                valid_matches.append(match)

        # 2. If no matches pass threshold
        if not valid_matches:
            self._logger.info(f"📭 No alertable matches for {report.doc_id}")
            return

        # Prepare metrics to log at the end
        emails_sent_count = len(self._settings.ALERT_TO_EMAILS.split(",")) if self._settings.ALERT_TO_EMAILS else 0
        whatsapp_messages_sent = 0

        # Send Emails FIRST
        try:
            payload = self._email_formatter.format(valid_matches, report)
            await self._send_email(payload)
        except Exception as e:
            self._logger.error("Email processing failed.", error=str(e))

        # Check conditions for WhatsApp (HIGH severity risks or OPPORTUNITY)
        overall = str(report.overall_signal).upper()
        high_risk = any(rsk.severity.upper() == "HIGH" for rsk in report.risks)
        
        if overall == "OPPORTUNITY" or (overall in ("RISK", "MIXED") and high_risk):
            seen_items = set()
            for match in valid_matches:
                pid = str(match.portfolio_item.id)
                if pid not in seen_items:
                    await self._whatsapp_notifier.send_alert(match, report)
                    seen_items.add(pid)
                    whatsapp_messages_sent += 1

        self._logger.info(f"🚨 Alert fired: {emails_sent_count} email recipients, {whatsapp_messages_sent} WhatsApp messages for {report.doc_id}")
        await self._log_alert(report.doc_id, emails_sent_count, whatsapp_messages_sent)
