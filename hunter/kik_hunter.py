"""
Hunter module for scraping public procurement decisions from EKAP (Kamu İhale Kurumu).
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


class KIKHunter:
    """
    Scrapes EKAP (KIK) procurement decisions and tender notices based on keywords.
    Output is identical to GazetteHunter for pipeline continuity.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._logger = structlog.get_logger()
        self._search_url = "https://ekap.kik.gov.tr/EKAP/common/ilanSorgulama.aspx"
        self._base_url = "https://ekap.kik.gov.tr"

    async def run(self, days_back: int = 1) -> List[DownloadResult]:
        self._logger.info(f"⚖️ Starting KIK (EKAP) Hunter", days_back=days_back)
        results: List[DownloadResult] = []
        target_date = date.today() - timedelta(days=days_back)
        
        # We disable SSL verification minimally since gov sites sometimes have certificate chain issues.
        async with httpx.AsyncClient(timeout=3.0, verify=False) as client:
            downloader = AsyncPDFDownloader(self._settings.RAW_PDF_DIR)
            try:
                for keyword in self._settings.KEYWORDS[:3]:
                    self._logger.info("🔍 Searching EKAP", keyword=keyword)
                    
                    # Conceptual payload targeting EKAP tender search form fields
                    payload = {
                        "arananTasinmazKelime": keyword,
                        "sayfaNo": 1,
                        "kayitSayisi": 20
                    }
                    
                    try:
                        response = await client.post(self._search_url, data=payload)
                        response.raise_for_status()
                    except Exception as e:
                        self._logger.error("Failed to query EKAP", keyword=keyword, error=str(e))
                        continue
                        
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    # Depending on EKAP portal HTML structure.
                    # Expected extraction: ihale_no, idare_adi, ihale_konusu, tarih, bedel, belge_url
                    rows = soup.find_all("tr")
                    for row in rows:
                        cells = row.find_all("td")
                        
                        # Assuming at least 6 columns based on the extraction requested
                        if len(cells) < 6:
                            continue
                            
                        ihale_no = cells[0].get_text(strip=True)
                        idare_adi = cells[1].get_text(strip=True)
                        ihale_konusu = cells[2].get_text(strip=True)
                        tarih_str = cells[3].get_text(strip=True)
                        bedel = cells[4].get_text(strip=True)
                        
                        try:
                            # Standard Turkish dates parsing
                            tarih_str = tarih_str.replace("/", ".")
                            ihale_tarihi = datetime.strptime(tarih_str, "%d.%m.%Y").date()
                        except ValueError:
                            continue
                            
                        # Filter by date limitation
                        if ihale_tarihi < target_date:
                            continue
                            
                        link = cells[5].find("a")
                        belge_url = link["href"] if link else ""
                        if not belge_url:
                            continue
                        
                        if not belge_url.startswith("http"):
                            belge_url = f"{self._base_url}/{belge_url.lstrip('/')}"
                            
                        title = f"KIK - İhale No: {ihale_no} ({idare_adi})"
                        sanitized_ihale = ihale_no.replace("/", "_").replace("\\", "_").replace(" ", "")
                        filename_base = f"kik_{ihale_tarihi.isoformat()}_{sanitized_ihale}"
                        
                        if belge_url.lower().endswith(".pdf"):
                            res = await downloader.download_pdf(
                                url=belge_url,
                                title=title,
                                published_date=ihale_tarihi
                            )
                            res = DownloadResult(
                                path=res.path,
                                url=res.url,
                                title=res.title,
                                date=res.date,
                                file_size_kb=res.file_size_kb,
                                status=res.status,
                                source="KIK"
                            )
                            results.append(res)
                        else:
                            # Save HTML fallback
                            path = os.path.join(self._settings.RAW_PDF_DIR, f"{filename_base}.html")
                            if not os.path.exists(path):
                                try:
                                    html_resp = await client.get(belge_url)
                                    html_resp.raise_for_status()
                                    with open(path, "w", encoding="utf-8") as f:
                                        f.write(html_resp.text)
                                    status = "downloaded"
                                except Exception as e:
                                    self._logger.error("Failed to download HTML", url=belge_url, error=str(e))
                                    status = "failed"
                            else:
                                status = "skipped"
                                
                            size_kb = os.path.getsize(path) / 1024.0 if os.path.exists(path) else 0.0
                            results.append(
                                DownloadResult(
                                    path=path,
                                    url=belge_url,
                                    title=title,
                                    date=ihale_tarihi,
                                    file_size_kb=size_kb,
                                    status=status,
                                    source="KIK"
                                )
                            )
                            
            finally:
                await downloader.aclose()
                
        return results

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="KIK Hunter CLI")
    parser.add_argument("--days-back", type=int, default=1, help="Number of days to look back")
    args = parser.parse_args()
    
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ]
    )
    
    hunter = KIKHunter()
    results = asyncio.run(hunter.run(days_back=args.days_back))
    
    print(f"Total processed: {len(results)}")
    for r in results:
        print(f"[{r.source}] {r.status}: {r.path}")
