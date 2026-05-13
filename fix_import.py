with open('backend/routers/tenders.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the import endpoint body
old = '''        await db.execute("""
            INSERT OR IGNORE INTO tenders
            (external_id, title, department, country, category, value_raw, value_zar,
             deadline, published, reference, source, portal_url, description, status, score, score_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tender.get("external_id", ""),
            tender.get("title", "Untitled"),
            tender.get("department", "Unknown"),
            tender.get("country", "ZA"),
            tender.get("category", "ICT & Services"),
            tender.get("value_raw"),
            tender.get("value_zar"),
            tender.get("deadline"),
            tender.get("published", datetime.now().strftime("%Y-%m-%d")),
            tender.get("reference", ""),
            tender.get("source", "External"),
            tender.get("portal_url", ""),
            tender.get("description", ""),
            tender.get("status", "active"),
            tender.get("score", 50),
            tender.get("score_reason", "Imported from scraper"),
        ))
        await db.commit()'''

new = '''        await db.execute("""
            INSERT INTO tenders
            (external_id, title, department, country, category, value_raw, value_zar,
             deadline, published, reference, source, portal_url, description, status, score, score_reason)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            ON CONFLICT (external_id) DO NOTHING
        """,
            tender.get("external_id", ""),
            tender.get("title", "Untitled"),
            tender.get("department", "Unknown"),
            tender.get("country", "ZA"),
            tender.get("category", "ICT & Services"),
            tender.get("value_raw"),
            tender.get("value_zar"),
            tender.get("deadline"),
            tender.get("published", datetime.now().strftime("%Y-%m-%d")),
            tender.get("reference", ""),
            tender.get("source", "External"),
            tender.get("portal_url", ""),
            tender.get("description", ""),
            tender.get("status", "active"),
            tender.get("score", 50),
            tender.get("score_reason", "Imported from scraper"),
        )'''

if old in content:
    content = content.replace(old, new)
    with open('backend/routers/tenders.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed!')
else:
    # Try with Windows line endings
    old_win = old.replace('\n', '\r\n')
    if old_win in content:
        content = content.replace(old_win, new)
        with open('backend/routers/tenders.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print('Fixed (CRLF)!')
    else:
        print('Pattern not found')
        # Show what the end of the file looks like
        lines = content.split('\n')
        for i, line in enumerate(lines[-25:], len(lines)-25):
            print(f"{i}: {repr(line)}")
