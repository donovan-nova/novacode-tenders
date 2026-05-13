from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from database import get_db
from scheduler import run_all_syncs
from scorer import score_tender
import json

router = APIRouter()


@router.get("/")
async def list_tenders(
    country: str = Query(None),
    category: str = Query(None),
    min_score: int = Query(0),
    status: str = Query("active"),
    search: str = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
):
    db = await get_db()
    try:
        conditions = ["status = ?"]
        params = [status]

        if country:
            conditions.append("country = ?")
            params.append(country)
        if category:
            conditions.append("category = ?")
            params.append(category)
        if min_score:
            conditions.append("score >= ?")
            params.append(min_score)
        if search:
            conditions.append("(title LIKE ? OR department LIKE ? OR description LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like, like])

        where = " AND ".join(conditions)
        params.extend([limit, offset])

        cursor = await db.execute(
            f"""SELECT id, external_id, title, department, country, category,
                value_raw, value_zar, deadline, published, reference, source,
                portal_url, score, score_reason, status, created_at
            FROM tenders WHERE {where}
            ORDER BY score DESC, deadline ASC
            LIMIT ? OFFSET ?""",
            params,
        )
        rows = await cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        tenders = [dict(zip(cols, row)) for row in rows]

        # Total count
        count_cursor = await db.execute(
            f"SELECT COUNT(*) FROM tenders WHERE {where}",
            params[:-2],
        )
        total = (await count_cursor.fetchone())[0]

        return {"tenders": tenders, "total": total, "limit": limit, "offset": offset}
    finally:
        await db.close()


@router.get("/stats/summary")
async def tender_summary():
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
            "SELECT country, COUNT(*) as cnt FROM tenders WHERE status='active' GROUP BY country ORDER BY cnt DESC"
        )
        rows = await c.fetchall()
        stats["by_country"] = [{"country": r[0], "count": r[1]} for r in rows]

        c = await db.execute(
            "SELECT category, COUNT(*) as cnt FROM tenders WHERE status='active' GROUP BY category ORDER BY cnt DESC LIMIT 8"
        )
        rows = await c.fetchall()
        stats["by_category"] = [{"category": r[0], "count": r[1]} for r in rows]

        c = await db.execute("SELECT completed_at, tenders_new, source FROM sync_log WHERE status='success' ORDER BY completed_at DESC LIMIT 1")
        row = await c.fetchone()
        stats["last_sync"] = {"at": row[0], "new": row[1], "source": row[2]} if row else None

        return stats
    finally:
        await db.close()


@router.get("/{tender_id}")
async def get_tender(tender_id: int):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM tenders WHERE id = ?", (tender_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Tender not found")
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))
    finally:
        await db.close()


@router.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks):
    """Manually trigger a full sync cycle."""
    background_tasks.add_task(run_all_syncs)
    return {"message": "Sync triggered", "status": "running"}


@router.post("/{tender_id}/rescore")
async def rescore_tender(tender_id: int):
    """Re-run AI scoring on a specific tender."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM tenders WHERE id = ?", (tender_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Tender not found")
        cols = [d[0] for d in cursor.description]
        tender = dict(zip(cols, row))

        score, reason = await score_tender(tender)
        await db.execute(
            "UPDATE tenders SET score=?, score_reason=? WHERE id=?",
            (score, reason, tender_id)
        )
        await db.commit()
        return {"score": score, "reason": reason}
    finally:
        await db.close()

@router.post("/import")
async def import_tender(tender: dict):
    """Accept a tender from external scraper (GitHub Actions)."""
    from datetime import datetime
    db = await get_db()
    try:
        await db.execute("""
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
        )
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.close()

