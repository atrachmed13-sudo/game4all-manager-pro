"""Local license-key generation and activation for GAME4ALL Manager Pro.

Keys live in the SQLite ``licenses`` table. A successful activation is stored
in ``settings`` so the desk stays unlocked across Streamlit reruns.

Generate keys from the hidden admin panel (PIN in .env) or:

    python -m license generate lifetime --note "shop-pc"
    python -m license generate annual --note "reseller-a"
    python -m license generate monthly --note "trial"
    python -m license list
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import database as db

load_dotenv(Path(__file__).resolve().parent / ".env")

PLANS = ("lifetime", "annual", "monthly")
PLAN_DAYS = {"lifetime": None, "annual": 365, "monthly": 30}
PLAN_CODE = {"lifetime": "LIFE", "annual": "YR", "monthly": "MO"}
CODE_PLAN = {code: plan for plan, code in PLAN_CODE.items()}
KEY_PATTERN = re.compile(
    r"^GAME4ALL-PRO-20\d{2}-(?:LIFE|YR|MO)-[A-Z0-9]{4}$",
    re.IGNORECASE,
)
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
DEMO_KEYS = (
    ("GAME4ALL-PRO-2026-LIFE-K7M2", "lifetime", "Seeded lifetime demo"),
    ("GAME4ALL-PRO-2026-YR-N4QP", "annual", "Seeded annual demo"),
    ("GAME4ALL-PRO-2026-MO-T8RX", "monthly", "Seeded monthly demo"),
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_stamp(when: datetime | None = None) -> str:
    return (when or _utc_now()).strftime("%Y-%m-%d %H:%M:%S")


def _parse_stamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc)


def normalize_key(raw: str) -> str:
    compact = re.sub(r"\s+", "", (raw or "")).upper().replace("_", "-")
    return compact.strip()


def key_hash(license_key: str) -> str:
    secret = os.getenv("LICENSE_HMAC_SECRET", "game4all-manager-pro")
    payload = f"{secret}:{normalize_key(license_key)}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def mask_key(license_key: str) -> str:
    key = normalize_key(license_key)
    if len(key) < 8:
        return "••••"
    return f"{key[:18]}••••{key[-4:]}"


def expires_for_plan(plan: str, issued_at: datetime | None = None) -> str | None:
    days = PLAN_DAYS.get(plan)
    if days is None:
        return None
    return _utc_stamp((issued_at or _utc_now()) + timedelta(days=days))


def generate_key_string(plan: str = "lifetime") -> str:
    code = PLAN_CODE.get(plan, "LIFE")
    year = _utc_now().year
    body = "".join(secrets.choice(ALPHABET) for _ in range(4))
    return f"GAME4ALL-PRO-{year}-{code}-{body}"


def issue_license(plan: str = "lifetime", note: str = "") -> dict[str, Any]:
    """Create a new key in the database and return the plaintext key once."""
    if plan not in PLANS:
        raise ValueError(f"Unknown plan: {plan}")
    for _ in range(12):
        key = generate_key_string(plan)
        if not db.get_license(key):
            break
    else:
        raise RuntimeError("Could not allocate a unique license key.")
    issued = _utc_now()
    record = {
        "license_key": key,
        "key_hash": key_hash(key),
        "plan": plan,
        "status": "active",
        "note": (note or "").strip(),
        "issued_at": _utc_stamp(issued),
        "expires_at": expires_for_plan(plan, issued),
        "activated_at": "",
    }
    db.insert_license(record)
    return record


def license_status(row: dict[str, Any] | None) -> str:
    if not row:
        return "invalid"
    if str(row.get("status") or "") == "revoked":
        return "revoked"
    expires = _parse_stamp(str(row.get("expires_at") or ""))
    if expires and expires < _utc_now():
        return "expired"
    return "ok"


def validate_key(raw: str) -> tuple[bool, str, dict[str, Any] | None]:
    key = normalize_key(raw)
    if not key:
        return False, "empty", None
    if not KEY_PATTERN.match(key):
        return False, "format", None
    row = db.get_license(key)
    state = license_status(row)
    if state == "expired" and row:
        db.set_license_status(key, "expired")
        row = {**row, "status": "expired"}
    if state != "ok":
        return False, state, row
    return True, "ok", row


def activate_key(raw: str) -> tuple[bool, str, dict[str, Any] | None]:
    ok, reason, row = validate_key(raw)
    if not ok or not row:
        return False, reason, row
    key = normalize_key(raw)
    now = _utc_stamp()
    db.mark_license_activated(key, now)
    db.set_setting("license_key", key)
    db.set_setting("license_hash", key_hash(key))
    db.set_setting("license_plan", str(row.get("plan") or "lifetime"))
    db.set_setting("license_expires_at", str(row.get("expires_at") or ""))
    db.set_setting("license_activated_at", now)
    return True, "ok", {**row, "license_key": key, "activated_at": now}


def clear_activation() -> None:
    for key in ("license_key", "license_hash", "license_plan", "license_expires_at", "license_activated_at"):
        db.set_setting(key, "")


def current_activation() -> dict[str, Any] | None:
    stored = db.get_setting("license_key", "")
    if not stored:
        return None
    ok, reason, row = validate_key(stored)
    if not ok:
        if reason in {"expired", "revoked", "invalid"}:
            clear_activation()
        return {"valid": False, "reason": reason, "license_key": stored}
    assert row is not None
    return {
        "valid": True,
        "reason": "ok",
        "license_key": stored,
        "masked": mask_key(stored),
        "plan": row.get("plan") or "lifetime",
        "expires_at": row.get("expires_at") or "",
        "activated_at": db.get_setting("license_activated_at", "") or row.get("activated_at") or "",
        "note": row.get("note") or "",
    }


def is_unlocked() -> bool:
    status = current_activation()
    return bool(status and status.get("valid"))


def admin_pin() -> str:
    return (os.getenv("LICENSE_ADMIN_PIN") or "g4a-royal-admin").strip()


def check_admin_pin(raw: str) -> bool:
    offered = (raw or "").strip()
    expected = admin_pin()
    if not offered or not expected:
        return False
    return secrets.compare_digest(offered, expected)


def _cli() -> int:
    db.init_db()
    parser = argparse.ArgumentParser(description="GAME4ALL license key manager")
    sub = parser.add_subparsers(dest="cmd", required=True)
    gen = sub.add_parser("generate", help="Issue a new license key")
    gen.add_argument("plan", choices=PLANS)
    gen.add_argument("--note", default="")
    sub.add_parser("list", help="Print stored licenses")
    args = parser.parse_args()
    if args.cmd == "generate":
        record = issue_license(args.plan, args.note)
        print(record["license_key"])
        print(f"plan={record['plan']} expires={record['expires_at'] or 'never'}")
        return 0
    for row in db.list_licenses():
        print(
            f"{row['license_key']}\t{row['plan']}\t{row['status']}\t"
            f"exp={row['expires_at'] or 'never'}\t{row['note']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
