with open('backend/routers/tenders.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the INSERT OR IGNORE line
insert_line = None
for i, line in enumerate(lines):
    if 'INSERT OR IGNORE INTO tenders' in line:
        insert_line = i
        break

if insert_line is None:
    print('INSERT OR IGNORE not found')
    exit()

print(f'Found INSERT at line {insert_line}')

# Find the end of this block (await db.commit())
commit_line = None
for i in range(insert_line, len(lines)):
    if 'await db.commit()' in lines[i]:
        commit_line = i
        break

print(f'Found commit at line {commit_line}')

# Replace lines from INSERT to commit (inclusive)
new_block = '''            INSERT INTO tenders
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
        )
'''

new_lines = lines[:insert_line] + [new_block] + lines[commit_line+1:]

with open('backend/routers/tenders.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Done!')
# Verify
with open('backend/routers/tenders.py', 'r', encoding='utf-8') as f:
    content = f.read()
print('Has $1:', '$1' in content)
print('Has ON CONFLICT:', 'ON CONFLICT' in content)
print('Has INSERT OR IGNORE:', 'INSERT OR IGNORE' in content)
