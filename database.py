"""SQLite inventory, sales, settings, and license store for GAME4ALL Manager Pro.

Listings are product rows (title, game, features, prices, delivery logins).
License keys live in ``licenses``; workstation activation is persisted in ``settings``.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "data" / "game4all_manager.db"

STATUSES = ("Available", "Listed", "Sold")

INVENTORY_COLUMNS = [
    "id",
    "pack_id",
    "sku",
    "title",
    "game",
    "rank",
    "level",
    "skins",
    "emotes",
    "extras",
    "server",
    "cost",
    "list_price",
    "platform",
    "status",
    "login_email",
    "login_password",
    "security_status",
    "sessions_revoked_at",
    "notes",
    "created_at",
    "updated_at",
]

SALES_COLUMNS = [
    "id",
    "inventory_id",
    "title",
    "game",
    "platform",
    "cost",
    "sold_price",
    "commission_pct",
    "extra_fees",
    "net_profit",
    "roi_pct",
    "sold_at",
    "month_key",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _month_key(when: str | None = None) -> str:
    if when:
        return when[:7]
    return datetime.now(timezone.utc).strftime("%Y-%m")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# Older builds of this app auto-seeded a demo pack (12 rows from
# sample_data/batch_pack_example.csv) tagged with one of these pack_id spellings the very
# first time the app ran. That auto-seeding code has been removed, but any database file
# created before the removal still has those rows sitting on disk. This module now never
# inserts sample/mock inventory itself; _purge_legacy_sample_inventory() only ever deletes
# rows matching the old seeder's own tags so a pre-existing install ends up just as empty
# as a brand new one.
_LEGACY_SAMPLE_PACK_PATTERNS = ("%SAMPLE-PACK%", "%SAMPLE_PACK%")


def _purge_legacy_sample_inventory(conn: sqlite3.Connection) -> int:
    """Delete any inventory rows left over from the removed auto-seeded demo pack.

    Safe to run on every startup: it is a no-op once a database has already been cleaned,
    and it never touches rows that were genuinely imported by a user (those use pack ids
    like ``PACK-<timestamp>`` or a custom name, never ``SAMPLE-PACK``/``G4A-SAMPLE-PACK-…``).

    A real sale can end up referencing one of these legacy demo rows via
    ``sales.inventory_id`` (recorded before this cleanup existed). With
    ``PRAGMA foreign_keys = ON`` a plain DELETE on the parent row would then raise
    ``sqlite3.IntegrityError: FOREIGN KEY constraint failed`` and crash the app on every
    startup, so any such sale is first unlinked (``inventory_id`` set to NULL) — the sale
    record itself, and its profit/ROI numbers, are kept intact.
    """
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    removed = 0
    for pattern in _LEGACY_SAMPLE_PACK_PATTERNS:
        ids = [row[0] for row in conn.execute("SELECT id FROM inventory WHERE UPPER(pack_id) LIKE ?", (pattern,)).fetchall()]
        if not ids:
            continue
        placeholders = ",".join("?" for _ in ids)
        if "sales" in tables:
            conn.execute(f"UPDATE sales SET inventory_id = NULL WHERE inventory_id IN ({placeholders})", ids)
        cursor = conn.execute(f"DELETE FROM inventory WHERE id IN ({placeholders})", ids)
        removed += cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0
    return removed


def _backfill_missing_features(conn: sqlite3.Connection) -> int:
    """Re-derive game/rank/level/server/extras for rows that were saved with a blank
    ``game`` — e.g. imported before a parser fix mangled a compact pipe-delimited combo
    line. Runs the same smart-text extraction the parser uses on the row's own
    title/notes, so a previously-corrupted import self-heals without a re-upload, and the
    listing generator never has to fall back to a generic placeholder.
    """
    from parser import extract_features

    rows = conn.execute(
        "SELECT id, title, game, rank, level, skins, emotes, extras, server, notes FROM inventory WHERE TRIM(game) = ''"
    ).fetchall()
    updated = 0
    for row in rows:
        seed = dict(row)
        features = extract_features(str(seed.get("notes") or seed.get("title") or ""), seed)
        game = str(features.get("game") or "").strip()
        if not game:
            continue
        conn.execute(
            """
            UPDATE inventory SET
                game = ?,
                rank = CASE WHEN TRIM(rank) = '' THEN ? ELSE rank END,
                level = CASE WHEN TRIM(level) = '' THEN ? ELSE level END,
                server = CASE WHEN TRIM(server) = '' THEN ? ELSE server END,
                extras = CASE WHEN TRIM(extras) = '' THEN ? ELSE extras END
            WHERE id = ?
            """,
            (
                game,
                str(features.get("rank") or ""),
                str(features.get("level") or ""),
                str(features.get("server") or ""),
                str(features.get("extras") or ""),
                seed["id"],
            ),
        )
        updated += 1
    return updated


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pack_id TEXT NOT NULL DEFAULT '',
                sku TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                game TEXT NOT NULL DEFAULT '',
                rank TEXT NOT NULL DEFAULT '',
                level TEXT NOT NULL DEFAULT '',
                skins TEXT NOT NULL DEFAULT '',
                emotes TEXT NOT NULL DEFAULT '',
                extras TEXT NOT NULL DEFAULT '',
                server TEXT NOT NULL DEFAULT '',
                cost REAL NOT NULL DEFAULT 0,
                list_price REAL NOT NULL DEFAULT 0,
                platform TEXT NOT NULL DEFAULT 'G2G',
                status TEXT NOT NULL DEFAULT 'Available',
                login_email TEXT NOT NULL DEFAULT '',
                login_password TEXT NOT NULL DEFAULT '',
                security_status TEXT NOT NULL DEFAULT 'Unlocked',
                sessions_revoked_at TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        existing = {row[1] for row in conn.execute("PRAGMA table_info(inventory)").fetchall()}
        if "login_email" not in existing:
            conn.execute("ALTER TABLE inventory ADD COLUMN login_email TEXT NOT NULL DEFAULT ''")
        if "login_password" not in existing:
            conn.execute("ALTER TABLE inventory ADD COLUMN login_password TEXT NOT NULL DEFAULT ''")
        if "security_status" not in existing:
            conn.execute("ALTER TABLE inventory ADD COLUMN security_status TEXT NOT NULL DEFAULT 'Unlocked'")
        if "sessions_revoked_at" not in existing:
            conn.execute("ALTER TABLE inventory ADD COLUMN sessions_revoked_at TEXT NOT NULL DEFAULT ''")
        _purge_legacy_sample_inventory(conn)
        _backfill_missing_features(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER,
                title TEXT NOT NULL DEFAULT '',
                game TEXT NOT NULL DEFAULT '',
                platform TEXT NOT NULL DEFAULT '',
                cost REAL NOT NULL DEFAULT 0,
                sold_price REAL NOT NULL DEFAULT 0,
                commission_pct REAL NOT NULL DEFAULT 0,
                extra_fees REAL NOT NULL DEFAULT 0,
                net_profit REAL NOT NULL DEFAULT 0,
                roi_pct REAL NOT NULL DEFAULT 0,
                sold_at TEXT NOT NULL,
                month_key TEXT NOT NULL,
                FOREIGN KEY (inventory_id) REFERENCES inventory(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT NOT NULL UNIQUE,
                key_hash TEXT NOT NULL DEFAULT '',
                plan TEXT NOT NULL DEFAULT 'lifetime',
                status TEXT NOT NULL DEFAULT 'active',
                note TEXT NOT NULL DEFAULT '',
                issued_at TEXT NOT NULL,
                expires_at TEXT,
                activated_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.commit()
    seed_demo_licenses()


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def inventory_frame(status: str | None = None, pack_id: str | None = None, game: str | None = None) -> pd.DataFrame:
    clauses: list[str] = []
    params: list[Any] = []
    if status and status != "All":
        clauses.append("status = ?")
        params.append(status)
    if pack_id and pack_id != "All":
        clauses.append("pack_id = ?")
        params.append(pack_id)
    if game and game != "All":
        clauses.append("game = ?")
        params.append(game)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_connection() as conn:
        df = pd.read_sql_query(
            f"SELECT * FROM inventory {where} ORDER BY id DESC",
            conn,
            params=params,
        )
    if df.empty:
        return pd.DataFrame(columns=INVENTORY_COLUMNS)
    return df


def inventory_counts() -> dict[str, int]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM inventory GROUP BY status"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) AS n FROM inventory").fetchone()["n"]
    counts = {row["status"]: int(row["n"]) for row in rows}
    return {
        "total": int(total),
        "Available": int(counts.get("Available", 0)),
        "Listed": int(counts.get("Listed", 0)),
        "Sold": int(counts.get("Sold", 0)),
    }


def list_packs() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT pack_id FROM inventory WHERE pack_id != '' ORDER BY pack_id"
        ).fetchall()
    return [row["pack_id"] for row in rows]


def list_games() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT game FROM inventory WHERE game != '' ORDER BY game"
        ).fetchall()
    return [row["game"] for row in rows]


def list_delivery_accounts() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, sku, title, game, platform, status, login_email, login_password
            FROM inventory
            ORDER BY CASE status
                WHEN 'Sold' THEN 0
                WHEN 'Listed' THEN 1
                ELSE 2
            END, id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_item(item_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM inventory WHERE id = ?", (item_id,)).fetchone()
    return _row_to_dict(row)


def insert_listings(rows: list[dict[str, Any]], pack_id: str) -> int:
    now = _utc_now()
    inserted = 0
    with get_connection() as conn:
        for raw in rows:
            sku = str(raw.get("sku") or "").strip() or f"G4A-{pack_id}-{inserted + 1:03d}"
            platform = str(raw.get("platform") or "G2G").strip() or "G2G"
            cost = float(raw.get("cost") or 0)
            list_price = float(raw.get("list_price") or 0)
            if list_price <= 0 and cost > 0:
                from pricing import suggested_list_price

                list_price = suggested_list_price(raw, platform)
            conn.execute(
                """
                INSERT INTO inventory (
                    pack_id, sku, title, game, rank, level, skins, emotes, extras,
                    server, cost, list_price, platform, status, login_email, login_password,
                    notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pack_id,
                    sku,
                    str(raw.get("title") or "").strip(),
                    str(raw.get("game") or "").strip(),
                    str(raw.get("rank") or "").strip(),
                    str(raw.get("level") or "").strip(),
                    str(raw.get("skins") or "").strip(),
                    str(raw.get("emotes") or "").strip(),
                    str(raw.get("extras") or "").strip(),
                    str(raw.get("server") or "").strip(),
                    cost,
                    list_price,
                    platform,
                    str(raw.get("status") or "Available").strip() or "Available",
                    str(raw.get("login_email") or "").strip(),
                    str(raw.get("login_password") or "").strip(),
                    str(raw.get("notes") or "").strip(),
                    now,
                    now,
                ),
            )
            inserted += 1
        conn.commit()
    return inserted


def update_inventory_row(item_id: int, fields: dict[str, Any]) -> None:
    allowed = {
        "pack_id",
        "sku",
        "title",
        "game",
        "rank",
        "level",
        "skins",
        "emotes",
        "extras",
        "server",
        "cost",
        "list_price",
        "platform",
        "status",
        "notes",
        "login_email",
        "login_password",
    }
    assignments = []
    values: list[Any] = []
    for key, value in fields.items():
        if key not in allowed:
            continue
        assignments.append(f"{key} = ?")
        values.append(value)
    if not assignments:
        return
    assignments.append("updated_at = ?")
    values.append(_utc_now())
    values.append(item_id)
    with get_connection() as conn:
        conn.execute(
            f"UPDATE inventory SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        conn.commit()


def bulk_set_status(item_ids: list[int], status: str) -> int:
    if status not in STATUSES or not item_ids:
        return 0
    now = _utc_now()
    with get_connection() as conn:
        conn.executemany(
            "UPDATE inventory SET status = ?, updated_at = ? WHERE id = ?",
            [(status, now, item_id) for item_id in item_ids],
        )
        conn.commit()
    return len(item_ids)


def clear_inventory() -> int:
    """Wipe every inventory row so the seller can start a batch pack import from zero.

    Powers the "🔄 Reset / Clear All" button in the Upload section. Any ``sales`` record
    referencing a row being deleted is first unlinked (``inventory_id`` set to NULL,
    mirroring ``_purge_legacy_sample_inventory``) instead of blocked by the foreign key —
    the sale history itself is intentionally kept; only the *inventory* table is reset.
    """
    with get_connection() as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "sales" in tables:
            conn.execute("UPDATE sales SET inventory_id = NULL WHERE inventory_id IS NOT NULL")
        cursor = conn.execute("DELETE FROM inventory")
        conn.commit()
        return cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0


def secure_and_revoke_sessions(item_ids: list[int]) -> int:
    """Lock the security flag and stamp a session-revocation timestamp for the given accounts.

    Used by the "تأمين وفصل الجلسات الأمنية" (Secure & Unlink Sessions) action so an account's
    old device sessions are marked as cut off after handover to a new owner.
    """
    if not item_ids:
        return 0
    now = _utc_now()
    with get_connection() as conn:
        conn.executemany(
            """
            UPDATE inventory
            SET security_status = 'Secured', sessions_revoked_at = ?, updated_at = ?
            WHERE id = ?
            """,
            [(now, now, item_id) for item_id in item_ids],
        )
        conn.commit()
    return len(item_ids)


def record_sale(
    *,
    inventory_id: int | None,
    title: str,
    game: str,
    platform: str,
    cost: float,
    sold_price: float,
    commission_pct: float,
    extra_fees: float,
    net_profit: float,
    roi_pct: float,
) -> int:
    now = _utc_now()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO sales (
                inventory_id, title, game, platform, cost, sold_price,
                commission_pct, extra_fees, net_profit, roi_pct, sold_at, month_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                inventory_id,
                title,
                game,
                platform,
                float(cost or 0),
                float(sold_price or 0),
                float(commission_pct or 0),
                float(extra_fees or 0),
                float(net_profit or 0),
                float(roi_pct or 0),
                now,
                _month_key(now),
            ),
        )
        sale_id = int(cur.lastrowid)
        if inventory_id:
            conn.execute(
                "UPDATE inventory SET status = 'Sold', updated_at = ? WHERE id = ?",
                (now, inventory_id),
            )
        conn.commit()
    return sale_id


def sales_frame(month_key: str | None = None) -> pd.DataFrame:
    with get_connection() as conn:
        if month_key and month_key != "All":
            df = pd.read_sql_query(
                "SELECT * FROM sales WHERE month_key = ? ORDER BY id DESC",
                conn,
                params=(month_key,),
            )
        else:
            df = pd.read_sql_query("SELECT * FROM sales ORDER BY id DESC", conn)
    if df.empty:
        return pd.DataFrame(columns=SALES_COLUMNS)
    return df


def list_sale_months() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT month_key FROM sales ORDER BY month_key DESC"
        ).fetchall()
    return [row["month_key"] for row in rows]


def monthly_analytics() -> pd.DataFrame:
    with get_connection() as conn:
        df = pd.read_sql_query(
            """
            SELECT
                month_key,
                COUNT(*) AS sales_count,
                SUM(sold_price) AS gross,
                SUM(net_profit) AS net_profit,
                AVG(roi_pct) AS avg_roi
            FROM sales
            GROUP BY month_key
            ORDER BY month_key
            """,
            conn,
        )
    if df.empty:
        return pd.DataFrame(columns=["month_key", "sales_count", "gross", "net_profit", "avg_roi"])
    return df


def seed_demo_licenses() -> None:
    """Insert starter keys once so the desk can be activated on first launch."""
    from license import DEMO_KEYS, expires_for_plan, key_hash

    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM licenses").fetchone()["n"]
        if count:
            return
        now = _utc_now()
        for key, plan, note in DEMO_KEYS:
            conn.execute(
                """
                INSERT OR IGNORE INTO licenses
                    (license_key, key_hash, plan, status, note, issued_at, expires_at, activated_at)
                VALUES (?, ?, ?, 'active', ?, ?, ?, '')
                """,
                (key, key_hash(key), plan, note, now, expires_for_plan(plan)),
            )
        conn.commit()


def insert_license(record: dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO licenses
                (license_key, key_hash, plan, status, note, issued_at, expires_at, activated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["license_key"],
                record.get("key_hash") or "",
                record.get("plan") or "lifetime",
                record.get("status") or "active",
                record.get("note") or "",
                record["issued_at"],
                record.get("expires_at"),
                record.get("activated_at") or "",
            ),
        )
        conn.commit()


def get_license(license_key: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM licenses WHERE license_key = ?",
            (license_key,),
        ).fetchone()
    return _row_to_dict(row)


def list_licenses() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM licenses ORDER BY id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def mark_license_activated(license_key: str, when: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE licenses
            SET activated_at = CASE WHEN activated_at = '' THEN ? ELSE activated_at END
            WHERE license_key = ?
            """,
            (when, license_key),
        )
        conn.commit()


def set_license_status(license_key: str, status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE licenses SET status = ? WHERE license_key = ?",
            (status, license_key),
        )
        conn.commit()


def get_setting(key: str, default: str = "") -> str:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else default


def set_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()
