with open('.github/scripts/scrape_tenders.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the etenders scraper to search multiple keywords
old_etenders = '''async def scrape_etenders(page) -> list[dict]:
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
    return tenders'''

new_etenders = '''async def scrape_etenders(page) -> list[dict]:
    """Scrape SA eTenders portal - search for IT/software/AI tenders."""
    all_tenders = {}
    search_terms = ["software", "ICT", "data", "digital", "system", "AI", "technology", "analytics", "platform", "consulting"]
    print("Scraping etenders.gov.za...")
    try:
        for term in search_terms:
            try:
                await page.goto(f"https://www.etenders.gov.za/Home/opportunities?id=1", timeout=30000)
                await page.wait_for_timeout(3000)
                # Try to find and fill search box
                search_box = await page.query_selector("input[type='search'], input[placeholder*='earch'], #searchText, input[name='search']")
                if search_box:
                    await search_box.fill(term)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(3000)
                rows = await page.query_selector_all("table tbody tr")
                print(f"  '{term}': {len(rows)} rows")
                for row in rows[:100]:
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
                        key = ref.strip() or title[:50]
                        if key in all_tenders:
                            continue
                        all_tenders[key] = {
                            "external_id": f"ZA-ET-{key[:40]}",
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
                        }
                    except Exception:
                        continue
            except Exception as e:
                print(f"  '{term}' error: {e}")
                continue
    except Exception as e:
        print(f"etenders error: {e}")
    tenders = list(all_tenders.values())
    print(f"etenders: scraped {len(tenders)} unique tenders")
    return tenders'''

content = content.replace(old_etenders, new_etenders)
with open('.github/scripts/scrape_tenders.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done" if new_etenders[:50] in open('.github/scripts/scrape_tenders.py').read() else "Pattern not found")
