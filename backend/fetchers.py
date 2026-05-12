"""
Fetchers for each procurement source.
SA uses the official OCDS API — structured, legal, no scraping needed.
Other African portals use lightweight HTML scraping (BeautifulSoup).
"""
import httpx
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "NovaCode-TenderMonitor/1.0 (contact@nova-code.co)",
    "Accept": "application/json",
}


# ─────────────────────────────────────────────
# SOUTH AFRICA — Official OCDS API
# ─────────────────────────────────────────────

async def fetch_sa_ocds(days_back: int = 30) -> list[dict]:
    tenders = []
    try:
        async with httpx.AsyncClient(timeout=30, headers=HEADERS, verify=False) as client:
            resp = await client.post(
                "https://www.etenders.gov.za/Home/GetFilteredTenders",
                data={"id": "1", "pageNumber": "1", "pageSize": "100", "searchText": "", "category": "", "province": "", "organOfState": ""},
            )
            if resp.status_code != 200:
                logger.warning(f"SA eTenders portal returned {resp.status_code}")
                return tenders
            data = resp.json()
            items = data if isinstance(data, list) else data.get("data", data.get("tenders", data.get("results", [])))
            if not isinstance(items, list):
                logger.warning(f"SA eTenders unexpected format: {type(data)}")
                return tenders
            for item in items:
                title = item.get("Description") or item.get("TenderDescription") or item.get("title") or "Untitled"
                dept = item.get("Department") or item.get("OrganOfState") or item.get("department") or "Unknown"
                ref = item.get("TenderNo") or item.get("ReferenceNumber") or item.get("tenderNo") or ""
                tender = {
                    "external_id": f"ZA-ET-{ref or title[:30]}",
                    "title": title, "department": dept, "country": "ZA",
                    "category": _map_sa_category("services"),
                    "value_raw": None, "value_zar": None,
                    "deadline": _parse_date(item.get("ClosingDate") or item.get("closingDate") or ""),
                    "published": _parse_date(item.get("AdvertisedDate") or item.get("advertisedDate") or ""),
                    "reference": ref, "source": "SA National Treasury OCDS API",
                    "portal_url": "https://www.etenders.gov.za/Home/opportunities?id=1",
                    "description": item.get("description") or "", "status": "active",
                }
                tenders.append(tender)
    except Exception as e:
        logger.error(f"SA eTenders fetch error: {e}")
    logger.info(f"SA OCDS: fetched {len(tenders)} tenders")
    return tenders

def _map_sa_category(ocds_cat: str) -> str:
    mapping = {
        "goods": "Goods & Supply",
        "services": "Consulting",
        "works": "Construction",
        "consultingServices": "Consulting",
    }
    return mapping.get(ocds_cat, "ICT & Services")


def _map_sa_status(ocds_status: str) -> str:
    mapping = {
        "active": "active", "cancelled": "cancelled",
        "complete": "awarded", "unsuccessful": "cancelled",
    }
    return mapping.get(ocds_status, "active")


# ─────────────────────────────────────────────
# KENYA — PPRA (tenders.go.ke)
# ─────────────────────────────────────────────

async def fetch_kenya_tenders() -> list[dict]:
    tenders = []
    url = "https://tenders.go.ke/website/tenders/index"
    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": HEADERS["User-Agent"]}, verify=False) as client:
            resp = await client.get(url, follow_redirects=True)
            soup = BeautifulSoup(resp.text, "html.parser")

            rows = soup.select("table tbody tr")
            for row in rows[:50]:
                cols = row.find_all("td")
                if len(cols) < 4:
                    continue
                title = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                if not title:
                    continue
                tenders.append({
                    "external_id": f"KE-PPRA-{_slugify(title)[:40]}",
                    "title": title,
                    "department": cols[0].get_text(strip=True) if cols else "",
                    "country": "KE",
                    "category": _classify_category(title),
                    "value_raw": cols[3].get_text(strip=True) if len(cols) > 3 else "N/A",
                    "deadline": _parse_date(cols[2].get_text(strip=True) if len(cols) > 2 else ""),
                    "published": datetime.now().strftime("%Y-%m-%d"),
                    "reference": cols[0].get_text(strip=True)[:30] if cols else "",
                    "source": "PPRA Kenya",
                    "portal_url": "https://tenders.go.ke",
                    "description": "",
                    "status": "active",
                })
    except Exception as e:
        logger.error(f"Kenya scraper error: {e}")

    logger.info(f"Kenya: fetched {len(tenders)} tenders")
    return tenders


# ─────────────────────────────────────────────
# ZAMBIA — ZPPA
# ─────────────────────────────────────────────

async def fetch_zambia_tenders() -> list[dict]:
    tenders = []
    url = "https://www.zppa.org.zm/tenders"
    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": HEADERS["User-Agent"]}, verify=False) as client:
            resp = await client.get(url, follow_redirects=True)
            soup = BeautifulSoup(resp.text, "html.parser")

            # ZPPA uses article/list patterns — adapt selectors if portal changes
            items = soup.select(".tender-item, article.tender, .procurement-notice, table tbody tr")
            for item in items[:40]:
                title_el = item.select_one("h3, h2, .tender-title, td:nth-child(2)")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                if len(title) < 10:
                    continue
                tenders.append({
                    "external_id": f"ZM-ZPPA-{_slugify(title)[:40]}",
                    "title": title,
                    "department": "",
                    "country": "ZM",
                    "category": _classify_category(title),
                    "value_raw": "N/A",
                    "deadline": "",
                    "published": datetime.now().strftime("%Y-%m-%d"),
                    "reference": "",
                    "source": "Zambia ZPPA",
                    "portal_url": "https://www.zppa.org.zm/tenders",
                    "description": "",
                    "status": "active",
                })
    except Exception as e:
        logger.error(f"Zambia scraper error: {e}")

    logger.info(f"Zambia: fetched {len(tenders)} tenders")
    return tenders


# ─────────────────────────────────────────────
# NIGERIA — BPP
# ─────────────────────────────────────────────

async def fetch_nigeria_tenders() -> list[dict]:
    tenders = []
    url = "https://www.bpp.gov.ng/tender-opportunities/"
    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": HEADERS["User-Agent"]}, verify=False) as client:
            resp = await client.get(url, follow_redirects=True)
            soup = BeautifulSoup(resp.text, "html.parser")

            for item in soup.select("article, .tender-post, .entry, table tbody tr")[:40]:
                title_el = item.select_one("h1, h2, h3, .entry-title, td")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                if len(title) < 10:
                    continue
                tenders.append({
                    "external_id": f"NG-BPP-{_slugify(title)[:40]}",
                    "title": title,
                    "department": "",
                    "country": "NG",
                    "category": _classify_category(title),
                    "value_raw": "N/A",
                    "deadline": "",
                    "published": datetime.now().strftime("%Y-%m-%d"),
                    "reference": "",
                    "source": "Nigeria BPP",
                    "portal_url": url,
                    "description": "",
                    "status": "active",
                })
    except Exception as e:
        logger.error(f"Nigeria scraper error: {e}")

    logger.info(f"Nigeria: fetched {len(tenders)} tenders")
    return tenders


# ─────────────────────────────────────────────
# GHANA — PPA
# ─────────────────────────────────────────────

async def fetch_ghana_tenders() -> list[dict]:
    tenders = []
    url = "https://www.ppaghana.org/PpaGhana/advertised-tenders"
    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": HEADERS["User-Agent"]}, verify=False) as client:
            resp = await client.get(url, follow_redirects=True)
            soup = BeautifulSoup(resp.text, "html.parser")

            for row in soup.select("table tbody tr")[:40]:
                cols = row.find_all("td")
                if len(cols) < 2:
                    continue
                title = cols[1].get_text(strip=True) if len(cols) > 1 else cols[0].get_text(strip=True)
                if len(title) < 10:
                    continue
                tenders.append({
                    "external_id": f"GH-PPA-{_slugify(title)[:40]}",
                    "title": title,
                    "department": cols[0].get_text(strip=True) if cols else "",
                    "country": "GH",
                    "category": _classify_category(title),
                    "value_raw": "N/A",
                    "deadline": _parse_date(cols[-1].get_text(strip=True) if cols else ""),
                    "published": datetime.now().strftime("%Y-%m-%d"),
                    "reference": "",
                    "source": "Ghana PPA",
                    "portal_url": url,
                    "description": "",
                    "status": "active",
                })
    except Exception as e:
        logger.error(f"Ghana scraper error: {e}")

    logger.info(f"Ghana: fetched {len(tenders)} tenders")
    return tenders


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _classify_category(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ["ai ", "artificial intelligence", "machine learning", "ml ", "predictive"]):
        return "AI & Automation"
    if any(k in t for k in ["fintech", "lending", "loan", "credit", "banking", "payment", "reconcil"]):
        return "Fintech"
    if any(k in t for k in ["software", "system", "platform", "app ", "application", "saas", "erp"]):
        return "ICT & Software"
    if any(k in t for k in ["data", "analytics", "business intelligence", "bi ", "dashboard", "reporting"]):
        return "Data & Analytics"
    if any(k in t for k in ["consult", "advisory", "strateg", "digital transform"]):
        return "Consulting"
    if any(k in t for k in ["ict", "it ", "technology", "cyber", "network", "cloud", "infrastruc"]):
        return "ICT & Software"
    return "General"


def _format_value(amount, currency: str) -> str:
    if not amount:
        return "N/A"
    try:
        val = float(amount)
        if val >= 1_000_000:
            return f"{currency} {val/1_000_000:.1f}M"
        elif val >= 1_000:
            return f"{currency} {val/1_000:.0f}K"
        return f"{currency} {val:.0f}"
    except Exception:
        return str(amount)


def _parse_date(date_str) -> str:
    if not date_str:
        return ""
    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%B %d, %Y"]:
        try:
            return datetime.strptime(date_str[:19], fmt[:len(date_str[:19])]).strftime("%Y-%m-%d")
        except Exception:
            continue
    return date_str[:10] if len(date_str) >= 10 else ""


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")



