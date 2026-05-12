"""
NovaCode Tender Scraper
Runs on GitHub Actions every 6 hours.
Scrapes SA eTenders and other African portals using Playwright (real browser).
Posts results to Railway backend API.
"""

import asyncio
import json
import os
import re
import httpx
from datetime import datetime
from playwright.async_api import async_playwright

RAILWAY_API_URL = os.environ.get("RAILWAY_API_URL", "https://novacode-tenders-api-production.up.railway.app")

NOVACODE_KEYWORDS = [
    "software", "digital", "technology", "IT ", "ICT", "system", "platform",
    "data", "analytics", "artificial intelligence", "AI ", "machine learning",
    "automation", "fintech", "financial technology", "banking", "credit",
    "loan", "lending", "debt", "collection", "debtors", "payment",
    "development", "application", "mobile", "web", "portal", "integration",
    "cloud", "database", "API", "cybersecurity", "security", "compliance",
    "consulting", "advisory", "management information", "ERP", "CRM",
    "business intelligence", "reporting", "dashboard", "monitoring",
]

def score_relevance(title: str, description: str = "") -> int:
    """Quick relevance score 0-100 based on keywords."""
    text = (title + " " + description).lower()
    matches = sum(1 for kw in NOVACODE_KEYWORDS if kw.lower() in text)
    return min(100, matches * 15)

def parse_date(date_str: str) -> str | None:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %B %Y", "%B %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None

async def scrape_etenders(page) -> list[dict]:
    """Scrape SA eTenders portal using real browser."""
    tenders = []
    print("Scraping etenders.gov.za...")
    try:
        await page.goto("https://www.etenders.gov.za/Home/opportunities?id=1", timeout=30000)
        await page.wait_for_timeout(5000)  # Wait for JS to load

        # Try to find tender rows
        rows = await page.query_selector_all("table tbody tr, .tender-row, .opportunity-row, tr[data-id]")
        print(f"Found {len(rows)} rows on etenders")

        if not rows:
            # Try alternative: search for IT/software tenders specifically
            await page.fill("input[type='search'], input[placeholder*='search'], #searchText", "software")
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(3000)
            rows = await page.query_selector_all("table tbody tr")
            print(f"After search: {len(rows)} rows")

        for row in rows[:50]:
            try:
                cells = await row.query_selector_all("td")
                if len(cells) < 2:
                    continue
                title = await cells[1].inner_text() if len(cells) > 1 else await cells[0].inner_text()
                title = title.strip()
                if not title or len(title) < 5:
                    continue
                dept = await cells[0].inner_text() if cells else ""
                deadline = await cells[3].inner_text() if len(cells) > 3 else ""
                ref = await cells[2].inner_text() if len(cells) > 2 else ""

                score = score_relevance(title)
                if score < 5:  # Skip irrelevant tenders
                    continue

                tenders.append({
                    "external_id": f"ZA-ET-{ref.strip()[:30] or title[:30]}",
                    "title": title[:500],
                    "department": dept.strip()[:200],
                    "country": "ZA",
                    "category": "ICT & Services",
                    "value_raw": None,
                    "value_zar": None,
                    "deadline": parse_date(deadline.strip()),
                    "published": datetime.now().strftime("%Y-%m-%d"),
                    "reference": ref.strip()[:100],
                    "source": "SA National Treasury (OCDS API)",
                    "portal_url": "https://www.etenders.gov.za/Home/opportunities?id=1",
                    "description": title[:500],
                    "status": "active",
                })
            except Exception as e:
                print(f"Row error: {e}")
                continue

    except Exception as e:
        print(f"etenders error: {e}")
    print(f"etenders: scraped {len(tenders)} relevant tenders")
    return tenders


async def scrape_gpw(page) -> list[dict]:
    """Scrape GPW Government Tender Bulletin."""
    tenders = []
    print("Scraping GPW Tender Bulletin...")
    try:
        await page.goto("https://www.gpwonline.co.za/Tenders/Pages/Bids-and-Tenders.aspx", timeout=30000)
        await page.wait_for_timeout(4000)

        rows = await page.query_selector_all("table tr, .ms-listviewtable tr")
        print(f"GPW: found {len(rows)} rows")

        for row in rows[1:100]:
            try:
                cells = await row.query_selector_all("td")
                if len(cells) < 2:
                    continue
                title = await cells[0].inner_text()
                title = title.strip()
                if not title or len(title) < 5:
                    continue

                score = score_relevance(title)
                if score < 15:
                    continue

                dept = await cells[1].inner_text() if len(cells) > 1 else ""
                deadline = await cells[3].inner_text() if len(cells) > 3 else ""
                ref = await cells[2].inner_text() if len(cells) > 2 else ""

                tenders.append({
                    "external_id": f"ZA-GPW-{ref.strip()[:30] or title[:30]}",
                    "title": title[:500],
                    "department": dept.strip()[:200],
                    "country": "ZA",
                    "category": "ICT & Services",
                    "value_raw": None,
                    "value_zar": None,
                    "deadline": parse_date(deadline.strip()),
                    "published": datetime.now().strftime("%Y-%m-%d"),
                    "reference": ref.strip()[:100],
                    "source": "SA National Treasury (OCDS API)",
                    "portal_url": "https://www.gpwonline.co.za/Tenders/Pages/Bids-and-Tenders.aspx",
                    "description": title[:500],
                    "status": "active",
                })
            except Exception as e:
                continue

    except Exception as e:
        print(f"GPW error: {e}")
    print(f"GPW: scraped {len(tenders)} relevant tenders")
    return tenders


async def scrape_kenya(page) -> list[dict]:
    """Scrape Kenya PPRA tenders portal."""
    tenders = []
    print("Scraping Kenya PPRA...")
    try:
        await page.goto("https://tenders.go.ke/website/tenders/index", timeout=30000)
        await page.wait_for_timeout(5000)

        # Kenya uses Vue.js - wait for content
        await page.wait_for_timeout(8000)
        rows = await page.query_selector_all("table tbody tr")
        print(f"Kenya: found {len(rows)} rows after JS load")

        for row in rows[:50]:
            try:
                cells = await row.query_selector_all("td")
                if len(cells) < 2:
                    continue
                title = await cells[1].inner_text() if len(cells) > 1 else await cells[0].inner_text()
                title = title.strip()
                if not title or len(title) < 5:
                    continue
                score = score_relevance(title)
                if score < 5:
                    continue
                dept = await cells[0].inner_text() if cells else ""
                deadline = await cells[2].inner_text() if len(cells) > 2 else ""
                tenders.append({
                    "external_id": f"KE-PPRA-{title[:40]}",
                    "title": title[:500],
                    "department": dept.strip()[:200],
                    "country": "KE",
                    "category": "ICT & Services",
                    "value_raw": None,
                    "value_zar": None,
                    "deadline": parse_date(deadline.strip()),
                    "published": datetime.now().strftime("%Y-%m-%d"),
                    "reference": "",
                    "source": "PPRA Kenya",
                    "portal_url": "https://tenders.go.ke",
                    "description": title[:500],
                    "status": "active",
                })
            except Exception:
                continue

    except Exception as e:
        print(f"Kenya error: {e}")
    print(f"Kenya: scraped {len(tenders)} relevant tenders")
    return tenders


async def post_tenders_to_api(tenders: list[dict]) -> int:
    """POST scraped tenders to Railway backend."""
    if not tenders:
        return 0
    added = 0
    async with httpx.AsyncClient(timeout=30) as client:
        for tender in tenders:
            try:
                resp = await client.post(
                    f"{RAILWAY_API_URL}/api/tenders/import",
                    json=tender,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code in (200, 201):
                    added += 1
                elif resp.status_code == 409:
                    pass  # Already exists
                else:
                    print(f"API error {resp.status_code} for: {tender.get('title', '')[:50]}")
            except Exception as e:
                print(f"POST error: {e}")
    return added


async def main():
    all_tenders = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True,
        )
        page = await context.new_page()

        # Scrape all sources
        etenders = await scrape_etenders(page)
        all_tenders.extend(etenders)

        gpw = await scrape_gpw(page)
        all_tenders.extend(gpw)

        kenya = await scrape_kenya(page)
        all_tenders.extend(kenya)

        await browser.close()

    print(f"\nTotal tenders scraped: {len(all_tenders)}")

    # Post to Railway API
    added = await post_tenders_to_api(all_tenders)
    print(f"New tenders added to dashboard: {added}")


if __name__ == "__main__":
    asyncio.run(main())

