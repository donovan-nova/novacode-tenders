from fastapi import APIRouter
from database import get_db

router = APIRouter()

@router.get("/")
async def get_stats():
    db = await get_db()
    try:
        stats = {}
        r = await db.fetchrow("SELECT COUNT(*) FROM tenders WHERE status='active'")
        stats["total_active"] = r[0]
        r = await db.fetchrow("SELECT COUNT(*) FROM tenders WHERE score >= 80 AND status='active'")
        stats["high_matches"] = r[0]
        r = await db.fetchrow("""
            SELECT COUNT(*) FROM tenders WHERE status='active'
            AND deadline >= CURRENT_DATE AND deadline <= CURRENT_DATE + INTERVAL '7 days'
        """)
        stats["closing_this_week"] = r[0]
        r = await db.fetchrow("SELECT SUM(value_zar) FROM tenders WHERE status='active' AND country='ZA' AND value_zar IS NOT NULL")
        stats["total_value_zar"] = round(float(r[0] or 0))
        rows = await db.fetch("SELECT country, COUNT(*) as count FROM tenders WHERE status='active' GROUP BY country ORDER BY count DESC")
        stats["by_country"] = [{"country": r["country"], "count": r["count"]} for r in rows]
        return stats
    except Exception as e:
        return {"error": str(e)}
    finally:
        await db.close()
