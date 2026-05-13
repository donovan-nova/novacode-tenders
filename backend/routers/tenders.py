from fastapi import APIRouter, HTTPException, Depends
from database import get_db
from scorer import score_tender
from datetime import datetime

router = APIRouter()


@router.get("")
async def list_tenders(
    search: str = "",
    country: str = "",
    category: str = "",
    match: str = "any",
    limit: int = 50,
    offset: int = 0,
):
    db = await get_db()
    try:
        conditions = ["status = 'active'"]
        params = []
        p = 1

        if search:
            conditions.append(f"(title ILIKE ${p} OR department ILIKE ${p})")
            params.append(f"%{search}%")
            p += 1
        if country:
            conditions.append(f"country = ${p}")
            params.append(country)
            p += 1
        if category:
            conditions.append(f"category = ${p}")
            params.append(category)
            p += 1
        if match == "high":
            conditions.append(f"score >= 70")

        where = " AND ".join(conditions)
        params_with_limit = params + [limit, offset]

        rows = await db.fetch(
            f"""SELECT id, external_id, title, department, country, category,
                value_raw, value_zar, deadline, published, reference, source,
                portal_url, score, score_reason, status, created_at
            FROM tenders WHERE {where}
            ORDER BY score DESC, deadline ASC NULLS LAST
            LIMIT ${p} OFFSET ${p+1}""",
            *params_with_limit,
        )
        tenders = [dict(r) for r in rows]

        count_row = await db.fetchrow(
            f"SELECT COUNT(*) FROM tenders WHERE {where}",
            *params,
        )
        total = count_row[0]

        return {"tenders": tenders, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.close()


@router.get("/stats/summary")
async def tender_summary():
    db = await get_db()
    try:
        c1 = await db.fetchrow("SELECT COUNT(*) FROM tenders WHERE status='active'")
        c2 = await db.fetchrow("SELECT COUNT(*) FROM tenders WHERE score >= 80 AND status='active'")
        c3 = await db.fetchrow("SELECT COALESCE(SUM(value_zar), 0) FROM tenders WHERE country='ZA' AND status='active'")
        c4 = await db.fetchrow("""
            SELECT COUNT(*) FROM tenders 
            WHERE status='active' AND deadline >= CURRENT_DATE AND deadline <= CURRENT_DATE + INTERVAL '7 days'
        """)
        return {
            "active_tenders": c1[0],
            "high_matches": c2[0],
            "total_value_zar": float(c3[0]),
            "closing_this_week": c4[0],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.close()


@router.get("/stats/by-country")
async def tenders_by_country():
    db = await get_db()
    try:
        rows = await db.fetch(
            "SELECT country, COUNT(*) as count FROM tenders WHERE status='active' GROUP BY country ORDER BY count DESC"
        )
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.close()


@router.get("/stats/by-category")
async def tenders_by_category():
    db = await get_db()
    try:
        rows = await db.fetch(
            "SELECT category, COUNT(*) as count FROM tenders WHERE status='active' GROUP BY category ORDER BY count DESC"
        )
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.close()


@router.get("/stats/last-sync")
async def last_sync():
    return {"last_sync": None, "status": "ok"}


@router.get("/{tender_id}")
async def get_tender(tender_id: int):
    db = await get_db()
    try:
        row = await db.fetchrow("SELECT * FROM tenders WHERE id = $1", tender_id)
        if not row:
            raise HTTPException(status_code=404, detail="Tender not found")
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.close()


@router.post("/{tender_id}/score")
async def rescore_tender(tender_id: int):
    db = await get_db()
    try:
        row = await db.fetchrow("SELECT * FROM tenders WHERE id = $1", tender_id)
        if not row:
            raise HTTPException(status_code=404, detail="Tender not found")
        tender = dict(row)
        score, reason = await score_tender(tender)
        await db.execute(
            "UPDATE tenders SET score=$1, score_reason=$2 WHERE id=$3",
            score, reason, tender_id
        )
        return {"score": score, "reason": reason}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.close()


@router.post("/import")
async def import_tender(tender: dict):
    """Accept a tender from external scraper (GitHub Actions)."""
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

