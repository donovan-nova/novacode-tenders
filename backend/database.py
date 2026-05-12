import os
import aiosqlite
import os
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "tenders.db")


async def get_db():
    return await aiosqlite.connect(DB_PATH)


async def init_db():
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)`n    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS tenders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                department TEXT,
                country TEXT NOT NULL,
                category TEXT,
                value_raw TEXT,
                value_zar REAL,
                deadline TEXT,
                published TEXT,
                reference TEXT,
                source TEXT NOT NULL,
                portal_url TEXT,
                description TEXT,
                score INTEGER DEFAULT 0,
                score_reason TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                country TEXT NOT NULL,
                portal_url TEXT,
                scraper_type TEXT,
                last_synced TEXT,
                tender_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                error_log TEXT
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT (datetime('now')),
                active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                started_at TEXT DEFAULT (datetime('now')),
                completed_at TEXT,
                tenders_found INTEGER DEFAULT 0,
                tenders_new INTEGER DEFAULT 0,
                error TEXT,
                status TEXT DEFAULT 'running'
            );

            CREATE INDEX IF NOT EXISTS idx_tenders_country ON tenders(country);
            CREATE INDEX IF NOT EXISTS idx_tenders_score ON tenders(score DESC);
            CREATE INDEX IF NOT EXISTS idx_tenders_deadline ON tenders(deadline);
            CREATE INDEX IF NOT EXISTS idx_tenders_status ON tenders(status);
            CREATE INDEX IF NOT EXISTS idx_tenders_category ON tenders(category);
        """)
        await db.commit()

        # Seed default sources
        await db.execute("""
            INSERT OR IGNORE INTO sources (name, country, portal_url, scraper_type, status)
            VALUES
                ('SA National Treasury (OCDS API)', 'ZA', 'https://ocds-api.etenders.gov.za', 'ocds_api', 'active'),
                ('PPRA Kenya', 'KE', 'https://tenders.go.ke', 'html_scraper', 'active'),
                ('Zambia ZPPA', 'ZM', 'https://www.zppa.org.zm', 'html_scraper', 'active'),
                ('Nigeria BPP', 'NG', 'https://www.bpp.gov.ng', 'html_scraper', 'active'),
                ('Ghana PPA', 'GH', 'https://www.ppaghana.org', 'html_scraper', 'scheduled'),
                ('PPDA Uganda', 'UG', 'https://www.ppda.go.ug', 'html_scraper', 'scheduled'),
                ('Tanzania PPRA', 'TZ', 'https://www.ppra.go.tz', 'html_scraper', 'coming_soon'),
                ('Eskom Tender Portal', 'ZA', 'https://www.eskom.co.za/procurement', 'html_scraper', 'scheduled'),
                ('Transnet Procurement', 'ZA', 'https://www.transnet.net', 'html_scraper', 'scheduled')
        """)

        # Seed default alerts
        default_alerts = [
            "AI automation", "artificial intelligence", "machine learning",
            "fintech", "digital transformation", "ICT consulting",
            "data analytics", "software development", "fraud detection",
            "loan origination", "credit scoring", "automation"
        ]
        for keyword in default_alerts:
            await db.execute(
                "INSERT OR IGNORE INTO alerts (keyword) VALUES (?)", (keyword,)
            )

        await db.commit()
        logger.info("Database initialised successfully.")

