"""
Fetchers for each procurement source.
SA uses the eTenders portal POST endpoint.
Kenya uses the PPIP OCDS API with PPRA fallback.
Others use HTML scraping with multiple URL fallbacks.
"""
import httpx
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
}


# ─────────────────────────────────────────────
# SOUTH AFRICA — eTenders Portal POST endpoint
# ─────────────────────────────────────────────

async def fetch_sa_ocds(days_back: int = 30) -> list[dict]:
    """Fetch live tenders from SA eTenders portal via the GetFilteredTenders endpoint."""
    tenders = []
    try:
        async with httpx.AsyncClient(timeout=30, headers=HEADERS, verify=False) as client:
            resp = await client.post(
                "https://www.etenders.gov.za/Home/GetFilteredTenders",
                data={
                    "id": "1",
                    "pageNumber": "1",
                    "pageSize": "100",
                    "searchText": "",
                    "category": "",
                    "province": "",
                    "organOfState": "",
                },
            )
            logger.info(f"SA eTenders: status {resp.status_code}, length {len(resp.text)}")
            if resp.status_code != 200:
                logger.warning(f"SA eTenders returned {resp.status_code}: {resp.text[:300]}")
                return tenders

            data = resp.json()
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = (
                    data.get("data")
                    or data.get("tenders")
                    or data.get("results")
                    or data.get("Data")
                    or data.get("Tenders")
                    or []
                )
            else:
                logger.warning(f"SA eTenders unexpected format: {type(data)}, raw: {str(data)[:300]}")
                return tenders

            logger.info(f"SA eTenders: {len(items)} items in response")

            for item in items:
                title = (
                    item.get("Description")
                    or item.get("TenderDescription")
                    or item.get("title")
                    or item.get("Title")
                    or "Untitled"
                )
                dept = (
                    item.get("Department")
                    or item.get("OrganOfState")
                    or item.get("department")
                    or item.get("Institution")
                    or "Unknown"
                )
                ref = (
                    item.get("TenderNo")
                    or item.get("ReferenceNumber")
                    or item.get("tenderNo")
                    or item.get("Reference")
                    or ""
                )
                closing = (
                    item.get("ClosingDate")
                    or item.get("closingDate")
                    or item.get("Closing")
                    or ""
                )
                advertised = (
                    item.get("AdvertisedDate")
                    or item.get("advertisedDate")
                    or item.get("Published")
                    or ""
                )
                tenders.append({
                    "external_id": f"ZA-ET-{ref or _slugify(title)[:40]}",
                    "title": title,
                    "department": dept,
                    "country": "ZA",
                    "category": _classify_category(title),
                    "value_raw": None,
                    "value_zar": None,
                    "deadline": _parse_date(closing),
                    "published": _parse_date(advertised) or datetime.now().strftime("%Y-%m-%d"),
                    "reference": ref,
                    "source": "SA eTenders (National Treasury)",
                    "portal_url": "https://www.etenders.gov.za/Home/opportunities?id=1",
                    "description": item.get("description") or item.get("Description") or "",
                    "status": "active",
                })

    except Exception as e:
        logger.error(f"SA eTenders fetch error: {e}")

    logger.info(f"SA eTenders: fetched {len(tenders)} tenders")
    return tenders


# ─────────────────────────────────────────────
# KENYA — PPIP API with PPRA fallback
# ─────────────────────────────────────────────

async def fetch_kenya_tenders() -> list[dict]:
    tenders = []
    try:
        async with httpx.AsyncClient(timeout=20, headers=HEADERS, verify=False) as client:
            # Try PPIP JSON API
            try:
                resp = await client.get("https://tenders.go.ke/api/tenders", follow_redirects=True)
                logger.info(f"Kenya PPIP API: {resp.status_code}, {len(resp.text)} bytes")
                if resp.status_code == 200 and resp.text.strip().startswith("{"):
                    data = resp.json()
                    items = data.get("data", data.get("tenders", data.get("results", [])))
                    if isinstance(items, list) and items:
                        for item in items[:50]:
                            title = item.get("title") or item.get("description") or "Untitled"
                            tenders.append({
                                "external_id": f"KE-PPIP-{item.get('id', _slugify(title)[:40])}",
                                "title": title,
                                "department": item.get("procuringEntity") or item.get("entity") or "",
                                "country": "KE",
                                "category": _classify_category(title),
                                "value_raw": str(item.get("value") or "N/A"),
                                "value_zar": None,
                                "deadline": _parse_date(item.get("closingDate") or ""),
                                "published": _parse_date(item.get("publishedDate") or ""),
                                "reference": item.get("tenderNo") or "",
                                "source": "PPIP Kenya",
                                "portal_url": "https://tenders.go.ke",
                                "description": item.get("description") or "",
                                "status": "active",
                            })
                        logger.info(f"Kenya PPIP API: {len(tenders)} tenders")
                        return tenders
            except Exception as e:
                logger.warning(f"Kenya PPIP API failed: {e}")

            # Fallback: PPRA static site
            resp2 = await client.get("https://ppra.go.ke/category/tenders/", follow_redirects=True)
            logger.info(f"Kenya PPRA: {resp2.status_code}, {len(resp2.text)} bytes")
            if resp2.status_code == 200:
                soup = BeautifulSoup(resp2.text, "html.parser")
                for art in soup.select("article, h2.entry-title, .post")[:30]:
                    title_el = art.select_one("h1, h2, h3, a")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    if len(title) < 10:
                        continue
                    tenders.append({
                        "external_id": f"KE-PPRA-{_slugify(title)[:40]}",
                        "title": title,
                        "department": "PPRA Kenya",
                        "country": "KE",
                        "category": _classify_category(title),
                        "value_raw": "N/A",
                        "value_zar": None,
                        "deadline": "",
                        "published": datetime.now().strftime("%Y-%m-%d"),
                        "reference": "",
                        "source": "PPRA Kenya",
                        "portal_url": "https://ppra.go.ke/category/tenders/",
                        "description": "",
                        "status": "active",
                    })

    except Exception as e:
        logger.error(f"Kenya scraper error: {e}")

    logger.info(f"Kenya: fetched {len(tenders)} tenders")
    return tenders


# ─────────────────────────────────────────────
# ZAMBIA — ZPPA with multiple URL fallbacks
# ─────────────────────────────────────────────

async def fetch_zambia_tenders() -> list[dict]:
    tenders = []
    urls_to_try = [
        "https://www.zppa.org.zm/open-tenders",
        "https://www.zppa.org.zm/procurement-notices",
        "https://zppa.org.zm/tenders",
    ]
    try:
        async with httpx.AsyncClient(timeout=20, headers=HEADERS, verify=False) as client:
            for url in urls_to_try:
                try:
                    resp = await client.get(url, follow_redirects=True)
                    logger.info(f"Zambia {url}: {resp.status_code}, {len(resp.text)} bytes")
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")
                    items = soup.select("table tbody tr, article, .tender-item")
                    for item in items[:30]:
                        title_el = item.select_one("h2, h3, td:nth-child(2), td, a")
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
                            "value_zar": None,
                            "deadline": "",
                            "published": datetime.now().strftime("%Y-%m-%d"),
                            "reference": "",
                            "source": "Zambia ZPPA",
                            "portal_url": url,
                            "description": "",
                            "status": "active",
                        })
                    if tenders:
                        break
                except Exception as e:
                    logger.warning(f"Zambia {url} failed: {e}")
    except Exception as e:
        logger.error(f"Zambia scraper error: {e}")

    logger.info(f"Zambia: fetched {len(tenders)} tenders")
    return tenders


# ─────────────────────────────────────────────
# NIGERIA — OCDS open data API with BPP fallback
# ─────────────────────────────────────────────

async def fetch_nigeria_tenders() -> list[dict]:
    tenders = []
    try:
        async with httpx.AsyncClient(timeout=20, headers=HEADERS, verify=False) as client:
            # Try Nigeria OCDS open data
            try:
                resp = await client.get(
                    "https://ocds.open.nigeria.gov.ng/api/releases/?format=json&page_size=50",
                    follow_redirects=True,
                )
                logger.info(f"Nigeria OCDS: {resp.status_code}, {len(resp.text)} bytes")
                if resp.status_code == 200 and "{" in resp.text:
                    data = resp.json()
                    releases = data.get("results", data.get("releases", []))
                    for r in releases[:40]:
                        tender_obj = r.get("tender", {})
                        title = tender_obj.get("title") or r.get("title") or "Untitled"
                        if len(title) < 5:
                            continue
                        tenders.append({
                            "external_id": f"NG-OCDS-{r.get('ocid', _slugify(title)[:40])}",
                            "title": title,
                            "department": r.get("buyer", {}).get("name") or "",
                            "country": "NG",
                            "category": _classify_category(title),
                            "value_raw": _format_value(
                                tender_obj.get("value", {}).get("amount"), "NGN"
                            ),
                            "value_zar": None,
                            "deadline": _parse_date(
                                tender_obj.get("tenderPeriod", {}).get("endDate") or ""
                            ),
                            "published": _parse_date(r.get("date") or ""),
                            "reference": tender_obj.get("id") or "",
                            "source": "Nigeria BPP (OCDS)",
                            "portal_url": "https://nocopo.bpp.gov.ng",
                            "description": tender_obj.get("description") or "",
                            "status": "active",
                        })
                    if tenders:
                        logger.info(f"Nigeria OCDS: {len(tenders)} tenders")
                        return tenders
            except Exception as e:
                logger.warning(f"Nigeria OCDS failed: {e}")

            # HTML fallback
            for url in [
                "https://nocopo.bpp.gov.ng/Home/TenderOpportunities",
                "https://bpp.gov.ng/procurement-notices/",
            ]:
                try:
                    resp = await client.get(url, follow_redirects=True)
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for item in soup.select("article, .tender-post, table tbody tr")[:30]:
                        title_el = item.select_one("h1, h2, h3, td")
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
                            "value_zar": None,
                            "deadline": "",
                            "published": datetime.now().strftime("%Y-%m-%d"),
                            "reference": "",
                            "source": "Nigeria BPP",
                            "portal_url": url,
                            "description": "",
                            "status": "active",
                        })
                    if tenders:
                        break
                except Exception as e:
                    logger.warning(f"Nigeria {url} failed: {e}")

    except Exception as e:
        logger.error(f"Nigeria scraper error: {e}")

    logger.info(f"Nigeria: fetched {len(tenders)} tenders")
    return tenders


# ─────────────────────────────────────────────
# GHANA — PPA with fallbacks
# ─────────────────────────────────────────────

async def fetch_ghana_tenders() -> list[dict]:
    tenders = []
    urls_to_try = [
        "https://ppaghana.org/PpaGhana/advertised-tenders",
        "https://www.ppaghana.org/tenders",
    ]
    try:
        async with httpx.AsyncClient(timeout=20, headers=HEADERS, verify=False) as client:
            for url in urls_to_try:
                try:
                    resp = await client.get(url, follow_redirects=True)
                    logger.info(f"Ghana {url}: {resp.status_code}, {len(resp.text)} bytes")
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")
                    rows = soup.select("table tbody tr") or soup.select("article, .tender-item")
                    for row in rows[:30]:
                        cols = row.find_all("td")
                        if cols and len(cols) >= 2:
                            title = cols[1].get_text(strip=True)
                        else:
                            title_el = row.select_one("h2, h3, a, td")
                            title = title_el.get_text(strip=True) if title_el else ""
                        if len(title) < 10:
                            continue
                        tenders.append({
                            "external_id": f"GH-PPA-{_slugify(title)[:40]}",
                            "title": title,
                            "department": cols[0].get_text(strip=True) if cols else "",
                            "country": "GH",
                            "category": _classify_category(title),
                            "value_raw": "N/A",
                            "value_zar": None,
                            "deadline": _parse_date(cols[-1].get_text(strip=True) if cols else ""),
                            "published": datetime.now().strftime("%Y-%m-%d"),
                            "reference": "",
                            "source": "Ghana PPA",
                            "portal_url": url,
                            "description": "",
                            "status": "active",
                        })
                    if tenders:
                        break
                except Exception as e:
                    logger.warning(f"Ghana {url} failed: {e}")
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
    if any(k in t for k in ["construction", "build", "civil", "road", "bridge", "works"]):
        return "Construction"
    if any(k in t for k in ["health", "medical", "hospital", "pharma"]):
        return "Health"
    if any(k in t for k in ["security", "guard", "surveillance"]):
        return "Security"
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
    date_str = str(date_str).strip()
    for fmt in [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%B %d, %Y",
        "%d %B %Y",
    ]:
        try:
            return datetime.strptime(date_str[:len(fmt)], fmt).strftime("%Y-%m-%d")
        except Exception:
            continue
    return date_str[:10] if len(date_str) >= 10 else ""


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
