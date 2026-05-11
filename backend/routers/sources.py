from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_db

# ── Sources ──────────────────────────────────
router = APIRouter()


@router.get("/")
async def list_sources():
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM sources ORDER BY status, country"
        )
        rows = await cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        await db.close()
