"""
NovaCode Tender Scraper
Runs on GitHub Actions every 6 hours.
Scrapes SA eTenders and other African portals using Playwright (real browser).
Posts results to Railway backend API.
"""

import asyncio
import json
import os
import httpx
from datetime import datetime
from playwright.async_api import async_playwright

RAILWAY_API_URL = os.environ.get("RAILWAY_API_URL", "https://novacode-tenders-api-production.up.railway.app")

NOVACODE_KEYWORDS = [
    "software", "digital", "technology", "IT", "ICT", "system", "platform",
    "data", "analytics", "artificial intelligence", "AI", "machine learning",
    "automation", "fintech", "financial technology", "banking", "credit",
    "loan", "lending", "debt", "collection", "debtors", "payment",
    "development", "application", "mobile", "web", "portal", "integration",
    "cloud", "database", "cybersecurity", "security", "compliance",
    "consulting", "advisory", "management information", "ERP", "CRM",
    "business intelligence", "reporting", "dashboard", "monitoring",
]

def score_relevance(title: str, description: str = "") -> int:
    text = (title + " " + description).lower()
    matches = sum(1 for kw in NOVACODE_KEYWORDS if kw.lower() in text)
    return min(100, matches * 15)

def parse_date(date_str: str):
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %B %Y", "%B %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None

def make_tender(external_id, title, dept, deadline, ref, source, portal_url):
    return {
        "external_id": external_id,
        "title": title[:500],
        "department": dept[:200],
        "country": "ZA",
        "category": "ICT & Services",
        "value_raw": None,
        "value_zar": None,
        "deadline": parse_date(deadline),
        "published": datetime.now().strftime("%Y-%m-%d"),
        "reference": ref[:100],
        "source": source,
        "portal_url": portal_url,
        "description": title[:500],
        "status": "active",
    }

async def scrape_etenders(page) -> list[dict]:
    """Scrape SA eTenders by searching multiple keywords."""
    seen = {}
    print("Scraping etenders.gov.za...")
    search_terms = ["software", "ICT", "data", "digital", "technology", "analytics", "system", "platform", "AI", "consulting"]

    for term in search_terms:
        try:
            await page.goto("https://www.etenders.gov.za/Home/opportunities?id=1", timeout=30000)
            await page.wait_for_timeout(3000)

            # Try to fill search box
            search_selectors = [
                "input[placeholder*='earch']",
                "input[type='search']",
                "#searchText",
                "input[name='search']",
                ".search-input",
            ]
            filled = False
            for sel in search_selectors:
                try:
                    box = await page.query_selector(sel)
                    if box:
                        await box.fill(term)
                        await page.keyboard.press("Enter")
                        await page.wait_for_timeout(2000)
                        filled = True
                        break
                except Exception:
                    continue

            rows = await page.query_selector_all("table tbody tr")
            print(f"  '{term}': {len(rows)} rows (search {'applied' if filled else 'not applied'})")

            for row in rows[:100]:
                try:
                    cells = await row.query_selector_all("td")
                    if len(cells) < 2:
                        continue
                    title = (await cells[1].inner_text()).strip() if len(cells) > 1 else (await cells[0].inner_text()).strip()
                    if not title or len(title) < 5:
                        continue
                    dept = (await cells[0].inner_text()).strip() if cells else ""
                    deadline = (await cells[3].inner_text()).strip() if len(cells) > 3 else ""
                    ref = (await cells[2].inner_text()).strip() if len(cells) > 2 else ""
                    key = ref or title[:50]
                    if key not in seen:
                        seen[key] = make_tender(
                            f"ZA-ET-{key[:40]}",
                            title, dept, deadline, ref,
                            "SA National Treasury (OCDS API)",
                            "https://www.etenders.gov.za/Home/opportunities?id=1"
                        )
                except Exception:
                    continue
        except Exception as e:
            print(f"  '{term}' error: {e}")
            continue

    tenders = list(seen.values())
    print(f"etenders: scraped {len(tenders)} unique tenders")
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
                title = (await cells[0].inner_text()).strip()
                if not title or len(title) < 5:
                    continue
                dept = (await cells[1].inner_text()).strip() if len(cells) > 1 else ""
                deadline = (await cells[3].inner_text()).strip() if len(cells) > 3 else ""
                ref = (await cells[2].inner_text()).strip() if len(cells) > 2 else ""
                tenders.append(make_tender(
                    f"ZA-GPW-{ref[:30] or title[:30]}",
                    title, dept, deadline, ref,
                    "SA National Treasury (OCDS API)",
                    "https://www.gpwonline.co.za/Tenders/Pages/Bids-and-Tenders.aspx"
                ))
            except Exception:
                continue
    except Exception as e:
        print(f"GPW error: {e}")
    print(f"GPW: scraped {len(tenders)} tenders")
    return tenders


async def scrape_kenya(page) -> list[dict]:
    """Scrape Kenya PPRA tenders portal."""
    tenders = []
    print("Scraping Kenya PPRA...")
    try:
        await page.goto("https://tenders.go.ke/website/tenders/index", timeout=30000)
        await page.wait_for_timeout(8000)
        rows = await page.query_selector_all("table tbody tr")
        print(f"Kenya: found {len(rows)} rows after JS load")
        for row in rows[:50]:
            try:
                cells = await row.query_selector_all("td")
                if len(cells) < 2:
                    continue
                title = (await cells[1].inner_text()).strip() if len(cells) > 1 else (await cells[0].inner_text()).strip()
                if not title or len(title) < 5:
                    continue
                dept = (await cells[0].inner_text()).strip() if cells else ""
                deadline = (await cells[2].inner_text()).strip() if len(cells) > 2 else ""
                tenders.append(make_tender(
                    f"KE-PPRA-{title[:40]}",
                    title, dept, deadline, "",
                    "PPRA Kenya",
                    "https://tenders.go.ke"
                ))
            except Exception:
                continue
    except Exception as e:
        print(f"Kenya error: {e}")
    print(f"Kenya: scraped {len(tenders)} tenders")
    return tenders


async def post_tenders_to_api(tenders: list[dict]) -> int:
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
                    pass
                else:
                    print(f"API {resp.status_code}: {tender.get('title', '')[:50]}")
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

        etenders = await scrape_etenders(page)
        all_tenders.extend(etenders)

        gpw = await scrape_gpw(page)
        all_tenders.extend(gpw)

        kenya = await scrape_kenya(page)
        all_tenders.extend(kenya)

        await browser.close()

    print(f"\nTotal tenders scraped: {len(all_tenders)}")
    added = await post_tenders_to_api(all_tenders)
    print(f"New tenders added to dashboard: {added}")


if __name__ == "__main__":
    asyncio.run(main())
