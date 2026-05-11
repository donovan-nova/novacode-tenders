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

    # Log sync start
    cursor = await db.execute(
        "INSERT INTO sync_log (source, status) VALUES (?, 'running')", (name,)
    )
    log_id = cursor.lastrowid
    await db.commit()

    tenders_new = 0
    tenders_found = 0
    error_msg = None

    try:
        tenders = await fetch_fn(*args)
        tenders_found = len(tenders)

        for t in tenders:
            # Check if we already have this tender
            existing = await db.execute(
                "SELECT id, score FROM tenders WHERE external_id = ?", (t["external_id"],)
            )
            row = await existing.fetchone()

            if row is None:
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
                        (:external_id, :title, :department, :country, :category,
                         :value_raw, :value_zar, :deadline, :published, :reference,
                         :source, :portal_url, :description, :score, :score_reason, :status)
                """, t)
                tenders_new += 1
            else:
                # Update status/deadline if changed
                await db.execute("""
                    UPDATE tenders SET updated_at = datetime('now'),
                    deadline = :deadline, status = :status
                    WHERE external_id = :external_id
                """, t)

        # Update source record
        await db.execute("""
            UPDATE sources SET last_synced = datetime('now'), tender_count = tender_count + ?
            WHERE name = ?
        """, (tenders_new, name))

        await db.execute("""
            UPDATE sync_log SET completed_at = datetime('now'),
            tenders_found = ?, tenders_new = ?, status = 'success'
            WHERE id = ?
        """, (tenders_found, tenders_new, log_id))

        await db.commit()
        logger.info(f"{name}: {tenders_found} found, {tenders_new} new")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"{name} sync failed: {e}")
        await db.execute("""
            UPDATE sync_log SET status = 'error', error = ?, completed_at = datetime('now')
            WHERE id = ?
        """, (error_msg, log_id))
        await db.commit()
    finally:
        await db.close()

    return tenders_new


async def run_all_syncs():
    """Run all source syncs concurrently."""
    logger.info("Starting full sync cycle...")
    tasks = [
        sync_source("SA National Treasury (OCDS API)", fetch_sa_ocds, 7),
        sync_source("PPRA Kenya", fetch_kenya_tenders),
        sync_source("Zambia ZPPA", fetch_zambia_tenders),
        sync_source("Nigeria BPP", fetch_nigeria_tenders),
        sync_source("Ghana PPA", fetch_ghana_tenders),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_new = sum(r for r in results if isinstance(r, int))
    logger.info(f"Sync cycle complete — {total_new} new tenders total")
    return total_new


async def start_scheduler():
    """Background task: sync immediately on startup, then every 6 hours."""
    # Small delay to let the DB initialise
    await asyncio.sleep(5)
    while True:
        try:
            await run_all_syncs()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)
