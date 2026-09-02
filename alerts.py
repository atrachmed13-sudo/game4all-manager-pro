"""Discord / Telegram sale alerts.

Credentials are read from, in order:

    1. Environment variables (system env or a local .env via python-dotenv)
    2. Streamlit Secrets (st.secrets) — used automatically on Streamlit Cloud

    DISCORD_WEBHOOK_URL
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID

If those are empty everywhere, notify_sale() returns a skipped result — the UI shows a
placeholder instead of failing the sale save.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

import requests

REQUEST_TIMEOUT = 12
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
DISCORD_PREFIXES = (
    "https://discord.com/api/webhooks/",
    "https://discordapp.com/api/webhooks/",
)
# A real Discord webhook is https://discord(app).com/api/webhooks/<numeric id>/<token>. Any
# URL that doesn't match this shape (missing id/token, typo'd host, copy-pasted channel link,
# etc.) will always 404/400 at Discord, so it's rejected locally with a clear reason instead.
DISCORD_WEBHOOK_RE = re.compile(r"^https://(?:discord|discordapp)\.com/api/webhooks/\d+/[\w-]+/?$")
# Telegram chat_id is either a plain/negative integer (users, groups, supergroups start with
# -100…) or an "@channelusername". Anything else is guaranteed to come back as HTTP 400.
TELEGRAM_CHAT_ID_RE = re.compile(r"^-?\d+$|^@[A-Za-z0-9_]{5,32}$")
DISCORD_MAX_MESSAGE_LEN = 2000
TELEGRAM_MAX_MESSAGE_LEN = 4096


def _strip_wrapping_quotes(value: str) -> str:
    """Undo the common copy/paste mistake of keeping the quotes around a .env value."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1].strip()
    return value


def _read_secret(name: str) -> str:
    """Read a config value from the environment first, then Streamlit Secrets as a fallback.

    This lets the Discord/Telegram dispatcher work out of the box on Streamlit Cloud (where
    secrets.toml is the standard way to store credentials) as well as with a local .env file,
    without changing any call site.
    """
    value = (os.getenv(name) or "").strip()
    if not value:
        try:
            import streamlit as st  # local import: keep this module usable without a live Streamlit runtime

            value = str(st.secrets.get(name, "") or "").strip()
        except Exception:
            value = ""
    return _strip_wrapping_quotes(value)


@dataclass
class AlertResult:
    ok: bool
    channel: str
    skipped: bool = False
    error: str = ""
    status_code: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "channel": self.channel,
            "skipped": self.skipped,
            "error": self.error,
            "status_code": self.status_code,
        }


@dataclass
class AlertSummary:
    results: list[AlertResult] = field(default_factory=list)

    @property
    def configured(self) -> bool:
        return any(not r.skipped for r in self.results) or False

    @property
    def any_ok(self) -> bool:
        return any(r.ok for r in self.results)

    @property
    def skipped_all(self) -> bool:
        sent = [r for r in self.results if r.channel != "none"]
        return not sent or all(r.skipped for r in sent)

    def error_text(self) -> str:
        return "; ".join(f"{r.channel}: {r.error}" for r in self.results if r.error)


def webhook_status() -> dict[str, bool]:
    discord = _read_secret("DISCORD_WEBHOOK_URL")
    telegram_chat = _read_secret("TELEGRAM_CHAT_ID")
    telegram = bool(_read_secret("TELEGRAM_BOT_TOKEN") and _telegram_chat_id_ok(telegram_chat))
    discord_ok = _discord_ok(discord)
    return {
        "discord": discord_ok,
        "telegram": telegram,
        "any": bool(discord_ok or telegram),
    }


def _discord_ok(url: str) -> bool:
    """Loose prefix check (any Discord host) used for quick UI status, not for sending."""
    return url.startswith(DISCORD_PREFIXES)


def _discord_webhook_valid(url: str) -> bool:
    """Strict shape check — catches truncated/garbled URLs before Discord ever sees them."""
    return bool(DISCORD_WEBHOOK_RE.match(url))


def _telegram_chat_id_ok(chat_id: str) -> bool:
    return bool(TELEGRAM_CHAT_ID_RE.match(chat_id))


def _extract_json_message(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return ""
    return str(body.get("message") or "") if isinstance(body, dict) else ""


def _post_discord(message: str, embed: dict[str, Any] | None = None) -> AlertResult:
    url = _read_secret("DISCORD_WEBHOOK_URL")
    if not url:
        return AlertResult(ok=False, channel="discord", skipped=True, error="DISCORD_WEBHOOK_URL is empty")
    if not _discord_webhook_valid(url):
        return AlertResult(
            ok=False,
            channel="discord",
            skipped=True,
            error=(
                "DISCORD_WEBHOOK_URL doesn't look like a real Discord webhook link "
                "(expected https://discord.com/api/webhooks/<id>/<token>)."
            ),
        )
    payload: dict[str, Any] = {
        "content": (message or "")[:DISCORD_MAX_MESSAGE_LEN],
        "username": "GAME4ALL Manager Pro",
    }
    if embed:
        payload["embeds"] = [embed]
    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return AlertResult(ok=False, channel="discord", error=f"Network error: {exc}")

    if 200 <= response.status_code < 300:
        return AlertResult(ok=True, channel="discord", status_code=response.status_code)
    if response.status_code == 404:
        return AlertResult(
            ok=False,
            channel="discord",
            status_code=404,
            error=(
                "Discord webhook returned 404 Not Found — it was likely deleted or "
                "regenerated. Open the channel's Integrations settings in Discord, create a "
                "new webhook, and update DISCORD_WEBHOOK_URL."
            ),
        )
    detail = _extract_json_message(response)
    error = f"HTTP {response.status_code}" + (f" — {detail}" if detail else "")
    return AlertResult(ok=False, channel="discord", status_code=response.status_code, error=error)


def _send_telegram(message: str, *, parse_mode: str | None = None) -> AlertResult:
    """Shared sendMessage call for both the plain sale alert and the rich Hyper-Listing push.

    Validates chat_id and text locally first (the two most common causes of Telegram's
    HTTP 400 "Bad Request") and always sends a well-formed JSON body — chat_id and text are
    required fields per the Bot API, and parse_mode is only included when actually needed so
    plain-text alerts can never fail on unescaped HTML/Markdown entities.
    """
    token = _read_secret("TELEGRAM_BOT_TOKEN")
    chat_id = _read_secret("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return AlertResult(ok=False, channel="telegram", skipped=True, error="Telegram token/chat placeholder is empty")
    if not _telegram_chat_id_ok(chat_id):
        return AlertResult(
            ok=False,
            channel="telegram",
            skipped=True,
            error=(
                "TELEGRAM_CHAT_ID is not a valid chat id (expected a numeric id such as "
                "123456789 / -1001234567890, or an @channelusername)."
            ),
        )
    text = (message or "").strip()
    if not text:
        return AlertResult(ok=False, channel="telegram", skipped=True, error="Telegram message text is empty")
    if len(text) > TELEGRAM_MAX_MESSAGE_LEN:
        text = text[: TELEGRAM_MAX_MESSAGE_LEN - 1]

    payload: dict[str, Any] = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    url = TELEGRAM_API.format(token=token)
    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return AlertResult(ok=False, channel="telegram", error=f"Network error: {exc}")

    try:
        body = response.json()
    except ValueError:
        body = {}
    description = str(body.get("description") or "") if isinstance(body, dict) else ""

    if 200 <= response.status_code < 300 and not (isinstance(body, dict) and body.get("ok") is False):
        return AlertResult(ok=True, channel="telegram", status_code=response.status_code)
    if response.status_code == 400:
        hint = description or (
            "Bad Request — check that TELEGRAM_CHAT_ID is correct and that the bot has "
            "actually been started/added to that chat."
        )
        return AlertResult(ok=False, channel="telegram", status_code=400, error=f"HTTP 400 — {hint}")
    error = f"HTTP {response.status_code}" + (f" — {description}" if description else "")
    return AlertResult(ok=False, channel="telegram", status_code=response.status_code, error=error)


def _post_telegram(message: str) -> AlertResult:
    return _send_telegram(message)


def push_telegram_message(message: str, *, parse_mode: str = "HTML") -> AlertResult:
    """Send a rich-formatted (HTML/Markdown) message to Telegram.

    Used by the Hyper-Listing & Secure Telegram Dispatcher to push a listing card
    bundled with fresh delivery credentials and a session-revocation confirmation stamp.
    Wrapped in the same unexpected-error guard as ``notify_sale`` so a bad push can never
    crash the security/dispatch flow in the UI.
    """
    try:
        return _send_telegram(message, parse_mode=parse_mode)
    except Exception as exc:  # pragma: no cover - defensive
        return AlertResult(ok=False, channel="telegram", error=f"Unexpected error: {exc}")


def format_sale_message(
    *,
    title: str,
    game: str,
    platform: str,
    sold_price: float,
    net_profit: float,
    roi_pct: float,
    currency: str = "$",
) -> tuple[str, dict[str, Any]]:
    text = (
        f"GAME4ALL sale closed\n"
        f"{title or game or 'Listing'} · {game}\n"
        f"Platform: {platform}\n"
        f"Sold: {currency}{sold_price:,.2f}\n"
        f"Net profit: {currency}{net_profit:,.2f}  |  ROI {roi_pct:,.1f}%"
    )
    embed = {
        "title": "Successful sale · GAME4ALL",
        "description": title or game or "Listing",
        "color": 0x3B82F6,
        "fields": [
            {"name": "Game", "value": game or "—", "inline": True},
            {"name": "Platform", "value": platform or "—", "inline": True},
            {"name": "Sold", "value": f"{currency}{sold_price:,.2f}", "inline": True},
            {"name": "Net profit", "value": f"{currency}{net_profit:,.2f}", "inline": True},
            {"name": "ROI", "value": f"{roi_pct:,.1f}%", "inline": True},
        ],
        "footer": {"text": "GAME4ALL Accounts Store · Trust, Security, Speed"},
    }
    return text, embed


def _safe_send(channel: str, sender: Any, *args: Any) -> AlertResult:
    """Run a channel sender and guarantee an AlertResult comes back no matter what.

    ``_post_discord``/``_post_telegram`` already turn network/HTTP failures into a result
    object, but this outer guard means a truly unexpected bug (bad credentials shape, a
    library raising something other than ``requests.RequestException``, etc.) still can't
    bubble up and crash the sale-recording flow in the UI — it just shows up as one more
    failed channel with a readable message.
    """
    try:
        return sender(*args)
    except Exception as exc:  # pragma: no cover - defensive: sender() already catches requests errors
        return AlertResult(ok=False, channel=channel, error=f"Unexpected error: {exc}")


def notify_sale(
    *,
    title: str,
    game: str,
    platform: str,
    sold_price: float,
    net_profit: float,
    roi_pct: float,
    currency: str = "$",
    enabled: bool = True,
) -> AlertSummary:
    if not enabled:
        return AlertSummary(results=[AlertResult(ok=False, channel="none", skipped=True, error="Alerts disabled")])
    text, embed = format_sale_message(
        title=title,
        game=game,
        platform=platform,
        sold_price=sold_price,
        net_profit=net_profit,
        roi_pct=roi_pct,
        currency=currency,
    )
    results = [_safe_send("discord", _post_discord, text, embed), _safe_send("telegram", _post_telegram, text)]
    if all(r.skipped for r in results):
        results.append(AlertResult(ok=False, channel="none", skipped=True, error="No webhook configured"))
    return AlertSummary(results=results)


def send_test_alert() -> AlertSummary:
    return notify_sale(
        title="TEST — GAME4ALL Manager Pro",
        game="Valorant",
        platform="G2G",
        sold_price=29.90,
        net_profit=8.40,
        roi_pct=22.5,
        enabled=True,
    )
