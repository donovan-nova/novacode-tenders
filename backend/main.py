from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from database import init_db
from scheduler import start_scheduler
from proxy import router_proxy
from routers import tenders, sources, alerts, stats, seed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def auto_seed():
    from database import get_db
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM tenders")
        count = (await cursor.fetchone())[0]
        if count == 0:
            logger.info("DB empty - auto-seeding...")
            from routers.seed import seed_tenders
            await seed_tenders()
    finally:
        await db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting NovaCode Tender Intelligence API...")
    await init_db()
    await auto_seed()
    scheduler_task = asyncio.create_task(start_scheduler())
    yield
    scheduler_task.cancel()
    logger.info("Shutting down...")


app = FastAPI(
    title="NovaCode Tender Intelligence API",
    description="Real-time African procurement monitoring for NovaCode Consulting",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_proxy)
app.include_router(tenders.router, prefix="/api/tenders", tags=["Tenders"])
app.include_router(sources.router, prefix="/api/sources", tags=["Sources"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(stats.router, prefix="/api/stats", tags=["Stats"])
app.include_router(seed.router, prefix="/api", tags=["Seed"])


@app.get("/")
async def root():
    return {
        "service": "NovaCode Tender Intelligence",
        "status": "operational",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}




