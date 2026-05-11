from fastapi import APIRouter
from database import get_db

router = APIRouter()


@router.get("/")
async def get_stats():
    db = await get_db()
    try:
        stats = {}
        c = await db.execute("SELECT COUNT(*) FROM tenders WHERE status='active'")
        stats["total_active"] = (await c.fetchone())[0]

        c = await db.execute("SELECT COUNT(*) FROM tenders WHERE score >= 80 AND status='active'")
        stats["high_matches"] = (await c.fetchone())[0]

        c = await db.execute(
            "SELECT COUNT(*) FROM tenders WHERE status='active' AND deadline BETWEEN date('now') AND date('now', '+7 days')"
        )
        stats["closing_this_week"] = (await c.fetchone())[0]

        c = await db.execute(
            "SELECT SUM(value_zar) FROM tenders WHERE status='active' AND country='ZA' AND value_zar IS NOT NULL"
        )
        val = (await c.fetchone())[0]
        stats["total_value_zar"] = round(val or 0)

        c = await db.execute(
            "SELECT country, COUNT(*) FROM tenders WHERE status='active' GROUP BY country ORDER BY COUNT(*) DESC"
        )
        rows = await c.fetchall()
        stats["by_country"] = [{"country": r[0], "count": r[1]} for r in rows]

        return stats
    finally:
        await db.close()
