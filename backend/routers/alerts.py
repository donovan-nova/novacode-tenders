from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_db

router = APIRouter()


class AlertCreate(BaseModel):
    keyword: str


@router.get("/")
async def list_alerts():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM alerts WHERE active=1 ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        await db.close()


@router.post("/")
async def create_alert(alert: AlertCreate):
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR IGNORE INTO alerts (keyword) VALUES (?)", (alert.keyword.strip(),)
        )
        await db.commit()
        return {"message": f"Alert created for: {alert.keyword}"}
    finally:
        await db.close()


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int):
    db = await get_db()
    try:
        await db.execute("UPDATE alerts SET active=0 WHERE id=?", (alert_id,))
        await db.commit()
        return {"message": "Alert removed"}
    finally:
        await db.close()
