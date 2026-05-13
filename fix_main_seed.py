with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the auto_seed function and its call
# Replace the entire auto_seed function with a no-op
content = content.replace(
    'async def auto_seed():\n    from database import get_db\n    db = await get_db()\n    try:\n        cursor = await db.execute("SELECT COUNT(*) FROM tenders")\n        count = (await cursor.fetchone())[0]\n        db_empty = count == 0\n    finally:\n        await db.close()\n    if db_empty:\n        logger.info("DB empty - auto-seeding...")\n        from routers.seed import seed_tenders\n        await seed_tenders()',
    'async def auto_seed():\n    logger.info("Auto-seed disabled - using GitHub Actions scraper for live data.")'
)

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
with open('backend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines[12:30], start=13):
    print(f"{i}: {line}", end='')
