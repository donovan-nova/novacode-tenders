from fastapi import APIRouter
router = APIRouter()

@router.get("/")
@router.get("")
async def list_alerts():
    return []

@router.post("/")
@router.post("")
async def create_alert(alert: dict):
    return {"id": 1, **alert}

@router.delete("/{alert_id}")
async def delete_alert(alert_id: int):
    return {"deleted": True}
