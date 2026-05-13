"""
NovaCode Tender Scraper - OCP Data Registry Edition
Tries 2026 files first, falls back to 2025. Filters for last 180 days only.
"""

import asyncio
import gzip
import json
import os
import httpx
from datetime import datetime, timedelta

RAILWAY_API_URL = os.environ.get("RAILWAY_API_URL", "https://novacode-tenders-api-production.up.railway.app")

SOURCES = [
    {"country": "ZA", "name": "SA National Treasury", "source": "SA National Treasury (OCDS API)",
     "portal_url": "https://www.etenders.gov.za/Home/opportunities?id=1",
     "urls": [
         "https://data.open-contracting.org/en/publication/143/download?name=2026.jsonl.gz",
         "https://data.open-contracting.org/en/publication/143/download?name=2025.jsonl.gz",
     ]},
    {"country": "KE", "name": "Kenya PPRA", "source": "PPRA Kenya",
     "portal_url": "https://tenders.go.ke",
     "urls": [
         "https://data.open-contracting.org/en/publication/147/download?name=2026.jsonl.gz",
         "https://data.open-contracting.org/en/publication/147/download?name=2025.jsonl.gz",
     ]},
    {"country": "NG", "name": "Nigeria BPP", "source": "Nigeria BPP",
     "portal_url": "https://www.bpp.gov.ng",
     "urls": [
         "https://data.open-contracting.org/en/publication/64/download?name=2026.jsonl.gz",
         "https://data.open-contracting.org/en/publication/64/download?name=2025.jsonl.gz",
     ]},
    {"country": "GH", "name": "Ghana PPA", "source": "Ghana PPA",
     "portal_url": "https://www.ppaghana.org",
     "urls": [
         "https://data.open-contracting.org/en/publication/85/download?name=2026.jsonl.gz",
         "https://data.open-contracting.org/en/publication/85/download?name=2025.jsonl.gz",
     ]},
    {"country": "RW", "name": "Rwanda RPPA", "source": "Rwanda RPPA",
     "portal_url": "https://www.rppa.gov.rw",
     "urls": [
         "https://data.open-contracting.org/en/publication/88/download?name=2026.jsonl.gz",
         "https://data.open-contracting.org/en/publication/88/download?name=2025.jsonl.gz",
     ]},
]

NOVACODE_KEYWORDS = [
    "software", "digital", "technology", "information technology",
    "ICT", "system", "platform", "application", "data", "analytics",
    "artificial intelligence", "machine learning", "automation",
    "fintech", "financial technology", "banking", "credit", "loan",
    "lending", "debt", "collection", "payment", "mobile", "web",
    "portal", "integration", "cloud", "database", "cybersecurity",
    "security", "compliance", "consulting", "advisory",
    "management information", "ERP", "CRM", "business intelligence",
    "reporting", "dashboard", "monitoring", "digital transformation",
]

CUTOFF_DATE = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
TODAY = datetime.now().strftime("%Y-%m-%d")


def is_relevant(title, description="", category=""):
    text = (title + " " + description + " " + category).lower()
    return any(kw.lower() in text for kw in NOVACODE_KEYWORDS)


def parse_date(date_str):
    if not date_str:
        return None
    return str(date_str)[:10]


def is_recent(published, deadline):
    if deadline and deadline >= TODAY:
        return True
    if published and published >= CUTOFF_DATE:
        return True
    return False


def extract_tender(release, country, source, portal_url):
    tender_obj = release.get("tender", {})
    buyer = release.get("buyer", {})
    planning = release.get("planning", {})
    budget = planning.get("budget", {})

    title = tender_obj.get("title", "") or ""
    if not title or len(title) < 5:
        return None

    description = tender_obj.get("description", "") or ""
    category = tender_obj.get("mainProcurementCategory", "") or ""

    if not is_relevant(title, description, category):
        return None

    published = parse_date(release.get("date"))
    deadline = parse_date(tender_obj.get("tenderPeriod", {}).get("endDate"))

    if not is_recent(published, deadline):
        return None

    budget_amount = budget.get("amount", {})
    if isinstance(budget_amount, dict):
        value = budget_amount.get("amount")
        currency = budget_amount.get("currency", "")
    else:
        value = None
        currency = ""

    value_raw = f"{currency} {value:,.0f}" if value and currency else None
    value_zar = float(value) if value and country == "ZA" else None

    ocid = release.get("ocid", "")
    ref = tender_obj.get("id", "") or ocid
    dept = buyer.get("name", "Unknown")

    return {
        "external_id": f"{country}-OCP-{(ocid or ref)[:40]}",
        "title": title[:500],
        "department": dept[:200],
        "country": country,
        "category": "ICT & Services",
        "value_raw": value_raw,
        "value_zar": value_zar,
        "deadline": deadline,
        "published": published,
        "reference": ref[:100],
        "source": source,
        "portal_url": portal_url,
        "description": description[:500] or title[:500],
        "status": "active",
    }


async def download_and_parse(source):
    tenders = []
    country = source["country"]
    print(f"\nProcessing {source['name']}...")

    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        for url in source["urls"]:
            year = "2026" if "2026" in url else "2025"
            try:
                resp = await client.get(url, headers={"User-Agent": "NovaCode-TenderMonitor/1.0 (contact@nova-code.co)"})
                if resp.status_code != 200:
                    print(f"  {year}: HTTP {resp.status_code}")
                    continue

                content = resp.content
                if len(content) < 100:
                    print(f"  {year}: Empty file, trying next")
                    continue

                print(f"  {year}: Downloaded {len(content)/1024:.0f} KB")
                decompressed = gzip.decompress(content)
                lines = decompressed.decode("utf-8").strip().split("\n")
                print(f"  {year}: Processing {len(lines)} records...")

                found = 0
                for line in lines:
                    if not line.strip():
                        continue
                    try:
                        release = json.loads(line)
                        tender = extract_tender(release, country, source["source"], source["portal_url"])
                        if tender:
                            tenders.append(tender)
                            found += 1
                    except Exception:
                        continue

                print(f"  {year}: {found} relevant recent tenders")
                if found > 0 and year == "2026":
                    break

            except Exception as e:
                print(f"  {year} error: {e}")
                continue

    return tenders


async def post_tenders_to_api(tenders):
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
            except Exception:
                continue
    return added


async def main():
    all_tenders = []
    for source in SOURCES:
        tenders = await download_and_parse(source)
        all_tenders.extend(tenders)

    seen = {}
    for t in all_tenders:
        seen[t["external_id"]] = t
    unique = list(seen.values())

    print(f"\n{'='*50}")
    print(f"Total relevant recent tenders: {len(unique)}")
    for c in ["ZA", "KE", "NG", "GH", "RW"]:
        count = sum(1 for t in unique if t["country"] == c)
        if count:
            print(f"  {c}: {count}")

    added = await post_tenders_to_api(unique)
    print(f"New tenders added to dashboard: {added}")


if __name__ == "__main__":
    asyncio.run(main())
