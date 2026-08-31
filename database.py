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
    """Seed demo licenses with INSERT OR IGNORE to prevent unique constraint crash."""
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