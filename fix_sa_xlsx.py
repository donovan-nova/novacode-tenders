with open('backend/fetchers.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_func = """async def fetch_sa_ocds(days_back: int = 30) -> list[dict]:
    \"\"\"Download and parse SA National Treasury monthly XLSX tender data.\"\"\"
    import io
    from datetime import datetime, timedelta
    tenders = []
    try:
        async with httpx.AsyncClient(timeout=60, headers=HEADERS, verify=False, follow_redirects=True) as client:
            # Try current month and previous month
            for months_back in range(0, 3):
                target = datetime.now() - timedelta(days=30 * months_back)
                filename = target.strftime("%m%Y") + ".xlsx"
                url = f"https://data.etenders.gov.za/Home/DownloadFile/?fileName={filename}"
                logger.info(f"SA OCDS: trying {url}")
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning(f"SA OCDS: {filename} returned {resp.status_code}")
                    continue
                # Parse XLSX
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(io.BytesIO(resp.content), read_only=True, data_only=True)
                    ws = wb.active
                    headers = []
                    for i, row in enumerate(ws.iter_rows(values_only=True)):
                        if i == 0:
                            headers = [str(c).strip() if c else "" for c in row]
                            continue
                        if not any(row):
                            continue
                        row_dict = dict(zip(headers, row))
                        title = str(row_dict.get("Description") or row_dict.get("TenderDescription") or row_dict.get("description") or "Untitled")
                        dept = str(row_dict.get("Department") or row_dict.get("OrganOfState") or row_dict.get("institution") or "Unknown")
                        ref = str(row_dict.get("TenderNo") or row_dict.get("ReferenceNumber") or row_dict.get("tender_no") or "")
                        deadline = row_dict.get("ClosingDate") or row_dict.get("closing_date") or ""
                        published = row_dict.get("AdvertisedDate") or row_dict.get("published") or ""
                        status = str(row_dict.get("Status") or row_dict.get("status") or "active").lower()
                        if status not in ("active", "advertised", "open", ""):
                            continue
                        if title == "Untitled" or title == "None":
                            continue
                        tender = {
                            "external_id": f"ZA-XLSX-{ref or title[:40]}",
                            "title": title[:500],
                            "department": dept[:200],
                            "country": "ZA",
                            "category": _map_sa_category("services"),
                            "value_raw": None,
                            "value_zar": None,
                            "deadline": _parse_date(str(deadline)) if deadline else None,
                            "published": _parse_date(str(published)) if published else None,
                            "reference": ref[:100],
                            "source": "SA National Treasury (OCDS API)",
                            "portal_url": "https://www.etenders.gov.za/Home/opportunities?id=1",
                            "description": title[:500],
                            "status": "active",
                        }
                        tenders.append(tender)
                    if tenders:
                        logger.info(f"SA OCDS: loaded {len(tenders)} tenders from {filename}")
                        break
                except Exception as xe:
                    logger.error(f"SA OCDS: XLSX parse error for {filename}: {xe}")
                    continue
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
