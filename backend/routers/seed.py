from fastapi import APIRouter
from database import get_db
from scorer import score_tender

router = APIRouter()

SEED_TENDERS = []

@router.post("/seed")
async def seed_data():
    """Seed endpoint disabled - using live data from GitHub Actions scraper."""
    return {"seeded": 0, "message": "Seed data disabled. Use GitHub Actions scraper for live tenders."}
