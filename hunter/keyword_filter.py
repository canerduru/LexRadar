"""
Keyword filtering utilities for gazette article titles.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List

from unidecode import unidecode


def _turkish_normalize(text: str) -> str:
    """
    Normalize text to be robust to Turkish characters.

    This function:
    - maps Turkish-specific letters to their ASCII equivalents
    - lowercases the result
    - runs `unidecode` as a fallback for any remaining diacritics
    """

    translation = str.maketrans(
        {
            "ı": "i",
            "İ": "i",
            "ş": "s",
            "Ş": "s",
            "ğ": "g",
            "Ğ": "g",
            "ü": "u",
            "Ü": "u",
            "ö": "o",
            "Ö": "o",
            "ç": "c",
            "Ç": "c",
        }
    )

    normalized = text.translate(translation).lower()
    normalized = unidecode(normalized)

    # Collapse whitespace to make phrase matching more stable.
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


@dataclass(frozen=True)
class KeywordMatch:
    """Represents a matched keyword and its frequency."""

    keyword: str
    count: int


class KeywordFilter:
    """
    Filter gazette content by real-estate/legal/tender-related keywords.

    Matching is case-insensitive and robust to Turkish locale characters via
    normalization with unidecode fallback.
    """

    def __init__(self, keywords: List[str]) -> None:
        """
        Initialize the keyword filter.

        Args:
            keywords: List of keyword strings to match.
        """

        if not keywords:
            raise ValueError("keywords must be a non-empty list")

        self._keywords: List[str] = list(dict.fromkeys(keywords))  # de-dupe while preserving order
        self._keywords_norm: Dict[str, str] = {kw: _turkish_normalize(kw) for kw in self._keywords}

    def matches(self, text: str) -> bool:
        """
        Return True if any keyword is found in the given text.

        Args:
            text: Text to scan (typically an article title).
        """

        return any(self._count_keyword(kw, text) > 0 for kw in self._keywords)

    def score(self, text: str) -> Dict[str, int]:
        """
        Compute keyword frequency map for the given text.

        Args:
            text: Text to score.

        Returns:
            Dict mapping each matched keyword (original form) to its occurrence count.
            Keywords with count == 0 are omitted.
        """

        text_norm = _turkish_normalize(text)
        counts: Dict[str, int] = {}

        for kw in self._keywords:
            kw_norm = self._keywords_norm[kw]
            if not kw_norm:
                continue
            count = text_norm.count(kw_norm)
            if count > 0:
                counts[kw] = count

        return counts

    def _count_keyword(self, keyword: str, text: str) -> int:
        """Count keyword occurrences using the normalized matching strategy."""

        text_norm = _turkish_normalize(text)
        keyword_norm = self._keywords_norm.get(keyword, "")
        if not keyword_norm:
            return 0
        return text_norm.count(keyword_norm)

