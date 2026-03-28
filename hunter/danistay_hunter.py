"""
Hunter module for scraping decisions from the Danıştay (Council of State) databases.
"""

from __future__ import annotations

import asyncio
import os
from datetime import date, datetime, timedelta
from typing import List

import httpx
import structlog
from bs4 import BeautifulSoup

from config.settings import get_settings
from hunter.downloader import AsyncPDFDownloader, DownloadResult


class DanistayHunter:
    """
    Scrapes Danistay decisions based on keywords and queues them.
    Output is identical to GazetteHunter for pipeline continuity.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._logger = structlog.get_logger()
        self._search_url = "https://www.danistay.gov.tr/karar-arama"
        self._base_url = "https://www.danistay.gov.tr"

    async def run(self, days_back: int = 1) -> List[DownloadResult]:
        self._logger.info(f"⚖️ Starting Danıştay Hunter", days_back=days_back)
        results: List[DownloadResult] = []
        target_date = date.today() - timedelta(days=days_back)
        
        # Disable SSL verification minimally since gov sites sometimes have certificate chain issues.
        async with httpx.AsyncClient(timeout=3.0, verify=False) as client:
            downloader = AsyncPDFDownloader(self._settings.RAW_PDF_DIR)
            try:
                for keyword in self._settings.KEYWORDS[:3]:
                    self._logger.info("🔍 Searching Danıştay", keyword=keyword)
                    
                    # Assume a POST endpoint mimicking common search portals
                    payload = {
                        "aranan_kelime": keyword,
                        "sayfa_no": 1,
                        "limit": 20
                    }
                    
                    try:
                        response = await client.post(self._search_url, data=payload)
                        response.raise_for_status()
                    except Exception as e:
                        self._logger.error("Failed to query Danıştay", keyword=keyword, error=str(e))
                        continue
                        
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    # Extract rows; depending on Danistay portal HTML structure
                    # Expected extraction: esas_no, karar_no, tarih, daire, konu, pdf_url
                    rows = soup.find_all("tr")
                    for row in rows:
                        cells = row.find_all("td")
                        
                        # Requires at least 5 columns for expected data shape
                        if len(cells) < 5:
                            continue
                            
                        esas_no = cells[0].get_text(strip=True)
                        karar_no = cells[1].get_text(strip=True)
                        tarih_str = cells[2].get_text(strip=True)
                        daire = cells[3].get_text(strip=True)
                        konu = cells[4].get_text(strip=True)
                        
                        try:
                            # Standard Turkish dates parsing
                            tarih_str = tarih_str.replace("/", ".")
                            karar_tarihi = datetime.strptime(tarih_str, "%d.%m.%Y").date()
                        except ValueError:
                            continue
                            
                        # Filter by date limitation
                        if karar_tarihi < target_date:
                            continue
                            
                        link = row.find("a")
                        pdf_url = link["href"] if link else ""
                        if not pdf_url:
                            continue
                        
                        if not pdf_url.startswith("http"):
                            pdf_url = f"{self._base_url}/{pdf_url.lstrip('/')}"
                            
                        title = f"Danıştay {daire} - Esas: {esas_no} Karar: {karar_no}"
                        sanitized_karar = karar_no.replace("/", "_").replace("\\", "_").replace(" ", "")
                        filename_base = f"danistay_{karar_tarihi.isoformat()}_{sanitized_karar}"
                        
                        # Use AsyncPDFDownloader for standardized saving & idempotency
                        if pdf_url.lower().endswith(".pdf"):
                            res = await downloader.download_pdf(
                                url=pdf_url,
                                title=title,
                                published_date=karar_tarihi
                            )
                            # Override the source tag since the downloader defaults to 'GAZETTE'
                            res = DownloadResult(
                                path=res.path,
                                url=res.url,
                                title=res.title,
                                date=res.date,
                                file_size_kb=res.file_size_kb,
                                status=res.status,
                                source="DANISTAY"
                            )
                            results.append(res)
                        else:
                            # HTML fallback downloading mechanism
                            path = os.path.join(self._settings.RAW_PDF_DIR, f"{filename_base}.html")
                            if not os.path.exists(path):
                                try:
                                    html_resp = await client.get(pdf_url)
                                    html_resp.raise_for_status()
                                    with open(path, "w", encoding="utf-8") as f:
                                        f.write(html_resp.text)
                                    status = "downloaded"
                                except Exception as e:
                                    self._logger.error("Failed to download Danıştay HTML payload", url=pdf_url, error=str(e))
                                    status = "failed"
                            else:
                                status = "skipped"
                                
                            size_kb = os.path.getsize(path) / 1024.0 if os.path.exists(path) else 0.0
                            results.append(
                                DownloadResult(
                                    path=path,
                                    url=pdf_url,
                                    title=title,
                                    date=karar_tarihi,
                                    file_size_kb=size_kb,
                                    status=status,
                                    source="DANISTAY"
                                )
                            )
                            
            finally:
                await downloader.aclose()
                
        return results

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Danistay Hunter CLI")
    parser.add_argument("--days-back", type=int, default=1, help="Number of days to look back")
    args = parser.parse_args()
    
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ]
    )
    
    hunter = DanistayHunter()
    results = asyncio.run(hunter.run(days_back=args.days_back))
    
    print(f"Total processed: {len(results)}")
    for r in results:
        print(f"[{r.source}] {r.status}: {r.path}")
