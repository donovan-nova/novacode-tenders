with open('backend/fetchers.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_func = """async def fetch_sa_ocds(days_back: int = 30) -> list[dict]:
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

"""

start = content.find('async def fetch_sa_ocds')
end = content.find('def _map_sa_category')
new_content = content[:start] + new_func + content[end:]
with open('backend/fetchers.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
print(f'Done - replaced {end-start} chars')
