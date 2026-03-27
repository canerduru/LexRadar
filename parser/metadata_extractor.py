"""
Metadata extraction for parsed Official Gazette documents.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Set

import regex as re

from parser.pdf_parser import ParseResult

DocumentType = Literal["KAMULAŞTIRMA", "İMAR", "İHALE", "TAPU", "KANUN", "YÖNETMELİK", "OTHER"]


@dataclass(frozen=True)
class DocumentMetadata:
    """Structured metadata extracted from parsed markdown."""

    gazette_date: str
    gazette_number: str
    document_type: DocumentType
    affected_districts: List[str]
    land_parcel_ids: List[str]
    monetary_values: List[str]
    involved_entities: List[str]


class MetadataExtractor:
    """Extract domain metadata from ParseResult using regex and heuristics."""

    _CITY_NAMES: Set[str] = {
        "adana", "adiyaman", "afyonkarahisar", "agri", "amasya", "ankara", "antalya", "artvin",
        "aydin", "balikesir", "bilecik", "bingol", "bitlis", "bolu", "burdur", "bursa",
        "canakkale", "cankiri", "corum", "denizli", "diyarbakir", "edirne", "elazig", "erzincan",
        "erzurum", "eskisehir", "gaziantep", "giresun", "gumushane", "hakkari", "hatay", "isparta",
        "mersin", "istanbul", "izmir", "kars", "kastamonu", "kayseri", "kirklareli", "kirsehir",
        "kocaeli", "konya", "kutahya", "malatya", "manisa", "kahramanmaras", "mardin", "mugla",
        "mus", "nevsehir", "nigde", "ordu", "rize", "sakarya", "samsun", "siirt", "sinop",
        "sivas", "tekirdag", "tokat", "trabzon", "tunceli", "sanliurfa", "usak", "van", "yozgat",
        "zonguldak", "aksaray", "bayburt", "karaman", "kirikkale", "batman", "sirnak", "bartin",
        "ardahan", "igdir", "yalova", "karabuk", "kilis", "osmaniye", "duzce",
        # common major districts
        "cankaya", "kecioren", "yenimahalle", "kadikoy", "besiktas", "uskudar", "fatih",
        "bornova", "konak", "karsiyaka", "sahinbey", "seyhan",
    }

    _TYPE_PATTERNS = {
        "KAMULAŞTIRMA": re.compile(r"\bkamulastirma|kamula[sş]t[ıi]rma|acele kamulastirma\b", re.IGNORECASE),
        "İMAR": re.compile(r"\bimar|nazim imar|uygulama imar|zoning\b", re.IGNORECASE),
        "İHALE": re.compile(r"\bihale|tender|ihale ilan[ıi]\b", re.IGNORECASE),
        "TAPU": re.compile(r"\btapu|kadastro|land registry\b", re.IGNORECASE),
        "KANUN": re.compile(r"\bkanun\b", re.IGNORECASE),
        "YÖNETMELİK": re.compile(r"\byonetmelik|y[öo]netmelik\b", re.IGNORECASE),
    }

    _DATE_RE = re.compile(r"\b([0-3]?\d)\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})\b", re.IGNORECASE)
    _NUMBER_RE = re.compile(r"(Sayi|Sayı)\s*[:\-]?\s*(\d{4,6})", re.IGNORECASE)
    _PARCEL_RE = re.compile(
        r"\b(?:Ada\s*No[:\s]*)?(\d{1,5})\s*(?:Ada)?\s*[\/\-]?\s*(?:Parsel\s*No[:\s]*)?(\d{1,6})\b",
        re.IGNORECASE,
    )
    _MONEY_RE = re.compile(
        r"\b(?:\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?)\s*(?:TL|TRY|Turk Lirasi|Türk Liras[ıi])\b",
        re.IGNORECASE,
    )
    _ENTITY_RE = re.compile(
        r"\b([A-ZİIĞÜŞÖÇ][\p{L}\s\-']+(?:Bakanligi|Bakanlığı|Belediyesi|Valiligi|Valiliği|Mudurlugu|Müdürlüğü))\b"
    )

    def extract(self, parse_result: ParseResult) -> DocumentMetadata:
        """
        Extract metadata fields from parse result text.

        Args:
            parse_result: Parsed PDF output.
        """

        text = parse_result.raw_markdown or "\n".join(page.text for page in parse_result.pages)
        text_ascii = self._normalize_for_match(text)

        gazette_date = self._extract_gazette_date(text)
        gazette_number = self._extract_gazette_number(text)
        document_type = self._extract_document_type(text_ascii)
        affected_districts = self._extract_districts(text_ascii)
        land_parcel_ids = self._extract_land_parcels(text)
        monetary_values = self._extract_monetary_values(text)
        involved_entities = self._extract_entities(text)

        return DocumentMetadata(
            gazette_date=gazette_date,
            gazette_number=gazette_number,
            document_type=document_type,
            affected_districts=affected_districts,
            land_parcel_ids=land_parcel_ids,
            monetary_values=monetary_values,
            involved_entities=involved_entities,
        )

    def _normalize_for_match(self, text: str) -> str:
        """Normalize Turkish characters for robust matching."""

        tr_map = str.maketrans(
            {"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c"}
        )
        return text.translate(tr_map)

    def _extract_gazette_date(self, text: str) -> str:
        """Extract gazette date in Turkish date format."""

        months = {
            "ocak",
            "subat",
            "şubat",
            "mart",
            "nisan",
            "mayis",
            "mayıs",
            "haziran",
            "temmuz",
            "agustos",
            "ağustos",
            "eylul",
            "eylül",
            "ekim",
            "kasim",
            "kasım",
            "aralik",
            "aralık",
        }
        for m in self._DATE_RE.finditer(text):
            month = self._normalize_for_match(m.group(2)).lower()
            if month in months:
                return m.group(0)
        return ""

    def _extract_gazette_number(self, text: str) -> str:
        """Extract gazette issue number."""

        m = self._NUMBER_RE.search(text)
        return m.group(2) if m else ""

    def _extract_document_type(self, text: str) -> DocumentType:
        """Classify document into predefined document type enum."""

        for doc_type, pattern in self._TYPE_PATTERNS.items():
            if pattern.search(text):
                return doc_type  # type: ignore[return-value]
        return "OTHER"

    def _extract_districts(self, text: str) -> List[str]:
        """Extract city/district names from curated Turkish list."""

        found = [name for name in self._CITY_NAMES if re.search(rf"\b{re.escape(name)}\b", text, re.IGNORECASE)]
        return sorted(set(found))

    def _extract_land_parcels(self, text: str) -> List[str]:
        """Extract cadastral Ada/Parsel references."""

        out: List[str] = []
        for m in self._PARCEL_RE.finditer(text):
            ada, parsel = m.group(1), m.group(2)
            out.append(f"Ada {ada} Parsel {parsel}")
        return sorted(set(out))

    def _extract_monetary_values(self, text: str) -> List[str]:
        """Extract TRY monetary values."""

        return sorted(set(m.group(0) for m in self._MONEY_RE.finditer(text)))

    def _extract_entities(self, text: str) -> List[str]:
        """Extract ministry/municipality/administrative entities."""

        return sorted(set(m.group(1).strip() for m in self._ENTITY_RE.finditer(text)))

