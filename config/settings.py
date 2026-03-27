"""
Central application settings loaded from environment variables.
"""

from __future__ import annotations

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration.

    Values are loaded from `.env` (when present) and from process environment.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    GAZETTE_BASE_URL: str = "https://www.resmigazete.gov.tr"
    RAW_PDF_DIR: str = "data/raw_pdfs"
    QUEUE_FILE: str = "data/download_queue.json"
    LOG_LEVEL: str = "INFO"
    LLAMA_CLOUD_API_KEY: str = ""
    PARSED_MARKDOWN_DIR: str = "data/parsed_markdown"
    PARSED_JSON_DIR: str = "data/parsed_json"
    MAX_PAGES_PER_CHUNK: int = 20
    PARSER_LANGUAGE: str = "tr"

    # Map-Reduce Brain Settings
    GOOGLE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    MAP_MODEL: str = "gemini-1.5-flash"
    REDUCE_MODEL: str = "gpt-4o-mini"
    INTELLIGENCE_REPORTS_DIR: str = "data/intelligence_reports"
    MAP_TEMPERATURE: float = 0.1
    REDUCE_TEMPERATURE: float = 0.2

    # Memory Engine Settings
    CHROMA_DB_DIR: str = "data/chroma_db"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    INTELLIGENCE_COLLECTION: str = "gazette_intelligence"
    PORTFOLIO_COLLECTION: str = "b2b_portfolio"
    TOP_K_MATCHES: int = 5
    SIMILARITY_THRESHOLD: float = 0.75

    # Radar & Alerts Settings
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ALERT_FROM_EMAIL: str = ""
    ALERT_TO_EMAILS: str = ""
    
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_FROM: str = ""
    TWILIO_WHATSAPP_TO: str = ""
    
    SCHEDULE_HOUR: int = 7
    SCHEDULE_TIMEZONE: str = "Europe/Istanbul"
    MIN_CONFIDENCE_FOR_ALERT: float = 0.7
    MIN_SIMILARITY_FOR_ALERT: float = 0.75

    KEYWORDS: List[str] = [
        "imar",
        "kamulaştırma",
        "ihale",
        "tapu",
        "yapı ruhsatı",
        "kıyı kanunu",
        "mera",
        "orman",
        "gayrimenkul",
        "arazi",
        "expropriation",
        "tender",
        "zoning",
        "real estate",
        "land registry",
    ]


def get_settings() -> Settings:
    """Create and return settings from environment."""

    return Settings()

