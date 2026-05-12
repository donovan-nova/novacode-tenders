import os
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_PATH = os.getenv("DB_PATH", "/tmp/tenders.db")

USE_POSTGRES = bool(DATABASE_URL and DATABASE_URL.startswith("postgres"))

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS tenders (
    id SERIAL PRIMARY KEY,
    external_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    department TEXT,
    country TEXT DEFAULT 'ZA',
    category TEXT,
    value_raw TEXT,
    value_zar REAL,
    deadline TEXT,
    published TEXT,
    reference TEXT,
    source TEXT,
    portal_url TEXT,
    description TEXT,
    status TEXT DEFAULT 'active',
    score INTEGER DEFAULT 50,
    score_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    keywords TEXT NOT NULL,
    email TEXT,
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_TABLES_SQLITE = """
CREATE TABLE IF NOT EXISTS tenders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    department TEXT,
    country TEXT DEFAULT 'ZA',
    category TEXT,
    value_raw TEXT,
    value_zar REAL,
    deadline TEXT,
    published TEXT,
    reference TEXT,
    source TEXT,
    portal_url TEXT,
    description TEXT,
    status TEXT DEFAULT 'active',
    score INTEGER DEFAULT 50,
    score_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keywords TEXT NOT NULL,
    email TEXT,
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

async def init_db():
    if USE_POSTGRES:
        import asyncpg
        # Fix Railway postgres URL format
        url = DATABASE_URL.replace("postgres://", "postgresql://")
        conn = await asyncpg.connect(url)
        try:
            await conn.execute(CREATE_TABLES_SQL)
            logger.info("PostgreSQL database initialised successfully.")
        finally:
            await conn.close()
    else:
        import aiosqlite
        os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.executescript(CREATE_TABLES_SQLITE)
            await db.commit()
        logger.info("SQLite database initialised successfully.")

async def get_db():
    if USE_POSTGRES:
        import asyncpg
        url = DATABASE_URL.replace("postgres://", "postgresql://")
        return await asyncpg.connect(url)
    else:
        import aiosqlite
        return await aiosqlite.connect(DB_PATH)
