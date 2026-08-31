import sqlite3
import datetime
import hashlib
import os

DB_PATH = "game4all.db"

def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

DEMO_KEYS = [
    ("GAME4ALL-PRO-2026-DEMO-K7M2", "enterprise", "Demo Lifetime License"),
]

def get_setting(key: str, default: str = None) -> str:
    """Retrieve application setting from database."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
        if not cursor.fetchone():
            return default
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

def save_setting(key: str, value: str):
    """Save application setting to database."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
            """,
            (key, value),
        )
        conn.commit()

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT UNIQUE,
                key_hash TEXT,
                plan TEXT,
                status TEXT,
                note TEXT,
                issued_at TEXT
            )
            """
        )
        conn.commit()
    seed_demo_licenses()

def seed_demo_licenses():
    """Seed demo licenses if table is empty or missing them using INSERT OR IGNORE."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        now = _utc_now()
        for key, plan, note in DEMO_KEYS:
            conn.execute(
                """
                INSERT OR IGNORE INTO licenses
                    (license_key, key_hash, plan, status, note, issued_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (key, _hash_key(key), plan, "active", note, now),
            )
        conn.commit()

def seed_sample_if_empty():
    """Seed sample items if tables are empty."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT,
                category TEXT,
                price REAL,
                stock INTEGER,
                updated_at TEXT
            )
            """
        )
        conn.commit()