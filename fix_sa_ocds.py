with open('backend/fetchers.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_func = """async def fetch_sa_ocds(days_back: int = 30) -> list[dict]:
    \"\"\"Fetch tenders from SA National Treasury OCDS API using releaseDate parameter.\"\"\"
    tenders = []
    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    base_url = "https://ocds-api.etenders.gov.za/api/OCDSReleasePackage"
    params = {
        "releaseDate": date_from,
        "pageSize": 100,
        "pageNumber": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=30, headers=HEADERS, verify=False) as client:
            while True:
                resp = await client.get(base_url, params=params)
                logger.info(f"SA OCDS API: {resp.url} -> {resp.status_code}")
                if resp.status_code != 200:
                    logger.warning(f"SA OCDS API returned {resp.status_code}: {resp.text[:200]}")
                    break
                data = resp.json()
                releases = data.get("releases", [])
                if not releases:
                    logger.info(f"SA OCDS: no releases in response. Keys: {list(data.keys())}")
                    break
                for release in releases:
                    tender_obj = release.get("tender", {})
                    buyer = release.get("buyer", {})
                    planning = release.get("planning", {})
                    budget = planning.get("budget", {})
                    tender = {
                        "external_id": f"ZA-OCDS-{release.get('ocid', '')}",
                        "title": tender_obj.get("title", "Untitled"),
                        "department": buyer.get("name", "Unknown Department"),
                        "country": "ZA",
                        "category": _map_sa_category(tender_obj.get("mainProcurementCategory", "")),
                        "value_raw": _format_value(budget.get("amount", {}).get("amount"), "ZAR"),
                        "value_zar": budget.get("amount", {}).get("amount"),
                        "deadline": _parse_date(tender_obj.get("tenderPeriod", {}).get("endDate")),
                        "published": _parse_date(release.get("date")),
                        "reference": tender_obj.get("id", ""),
                        "source": "SA National Treasury (OCDS API)",
                        "portal_url": "https://www.etenders.gov.za/Home/opportunities?id=1",
                        "description": tender_obj.get("description", ""),
                        "status": _map_sa_status(tender_obj.get("status", "")),
                    }
                    tenders.append(tender)
                if len(releases) < params["pageSize"]:
                    break
                params["pageNumber"] += 1
    except Exception as e:
        logger.error(f"SA OCDS fetch error: {e}")
    logger.info(f"SA OCDS: fetched {len(tenders)} tenders")
    return tenders

"""

start = content.find('async def fetch_sa_ocds')
end = content.find('def _map_sa_category')
new_content = content[:start] + new_func + content[end:]
with open('backend/fetchers.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
print(f'Done - replaced {end-start} chars')
