from fastapi import APIRouter
router = APIRouter()

@router.get("/")
@router.get("")
async def list_sources():
    return []
