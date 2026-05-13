import asyncio
import logging
from datetime import datetime

from database import get_db
from fetchers import (
    fetch_sa_ocds,
    fetch_kenya_tenders,
    fetch_zambia_tenders,
    fetch_nigeria_tenders,
    fetch_ghana_tenders,
)
from scorer import score_tender

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SECONDS = 6 * 60 * 60  # Every 6 hours


async def sync_source(name: str, fetch_fn, *args):
    """Fetch tenders from one source, score them, and upsert into DB."""
    logger.info(f"Syncing {name}...")
    db = await get_db()
    tenders_new = 0
    tenders_found = 0

    try:
        tenders = await fetch_fn(*args)
        tenders_found = len(tenders)
        logger.info(f"{name}: fetcher returned {tenders_found} tenders")

        for t in tenders:
            try:
                # Check if tender already exists
                existing = await db.fetchrow(
                    "SELECT id FROM tenders WHERE external_id = $1",
                    t["external_id"]
                )

                if existing is None:
                    # New tender — score it
                    score, reason = await score_tender(t)
                    t["score"] = score
                    t["score_reason"] = reason

                    await db.execute("""
                        INSERT INTO tenders
                            (external_id, title, department, country, category,
                             value_raw, value_zar, deadline, published, reference,
                             source, portal_url, description, score, score_reason, status)
                        VALUES
                            ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                        ON CONFLICT (external_id) DO NOTHING
                    """,
                        t.get("external_id", ""),
                        t.get("title", "Untitled"),
                        t.get("department", "Unknown"),
                        t.get("country", "ZA"),
                        t.get("category", "General"),
                        t.get("value_raw"),
                        t.get("value_zar"),
                        t.get("deadline") or None,
                        t.get("published") or datetime.now().strftime("%Y-%m-%d"),
                        t.get("reference", ""),
                        t.get("source", ""),
                        t.get("portal_url", ""),
                        t.get("description", ""),
                        score,
                        reason,
                        t.get("status", "active"),
                    )
                    tenders_new += 1
                else:
                    # Update deadline and status
                    await db.execute("""
                        UPDATE tenders
                        SET deadline = $1, status = $2
                        WHERE external_id = $3
                    """,
                        t.get("deadline") or None,
                        t.get("status", "active"),
                        t["external_id"],
                    )
            except Exception as row_err:
                logger.error(f"{name}: error inserting tender '{t.get('title','?')}': {row_err}")
                continue

        logger.info(f"{name}: {tenders_found} found, {tenders_new} new")

    except Exception as e:
        logger.error(f"{name} sync failed: {e}")
    finally:
        await db.close()

    return tenders_new


async def run_all_syncs():
    """Run all source syncs."""
    logger.info("Starting full sync cycle...")
    total_new = 0
    sources = [
        ("SA National Treasury (OCDS API)", fetch_sa_ocds, 30),
        ("PPRA Kenya", fetch_kenya_tenders),
        ("Zambia ZPPA", fetch_zambia_tenders),
        ("Nigeria BPP", fetch_nigeria_tenders),
        ("Ghana PPA", fetch_ghana_tenders),
    ]
    for item in sources:
        name = item[0]
        fn = item[1]
        args = item[2:] if len(item) > 2 else ()
        try:
            n = await sync_source(name, fn, *args)
            total_new += n
        except Exception as e:
            logger.error(f"Sync error for {name}: {e}")

    logger.info(f"Sync cycle complete — {total_new} new tenders total")
    return total_new


async def start_scheduler():
    """Background task: sync immediately on startup, then every 6 hours."""
    await asyncio.sleep(5)
    while True:
        try:
            await run_all_syncs()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)
