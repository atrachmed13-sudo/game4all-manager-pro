"""Discord / Telegram sale alerts. Credentials come from the environment only.

    DISCORD_WEBHOOK_URL
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID

If those are empty, notify_sale() returns a skipped result — the UI shows a
placeholder instead of failing the sale save.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import requests

REQUEST_TIMEOUT = 12
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
DISCORD_PREFIXES = (
    "https://discord.com/api/webhooks/",
    "https://discordapp.com/api/webhooks/",
)


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
    discord = (os.getenv("DISCORD_WEBHOOK_URL") or "").strip()
    telegram = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip() and (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    return {
        "discord": discord.startswith(DISCORD_PREFIXES),
        "telegram": bool(telegram),
        "any": bool(discord.startswith(DISCORD_PREFIXES) or telegram),
    }


def _discord_ok(url: str) -> bool:
    return url.startswith(DISCORD_PREFIXES)


def _post_discord(message: str, embed: dict[str, Any] | None = None) -> AlertResult:
    url = (os.getenv("DISCORD_WEBHOOK_URL") or "").strip()
    if not url:
        return AlertResult(ok=False, channel="discord", skipped=True, error="DISCORD_WEBHOOK_URL is empty")
    if not _discord_ok(url):
        return AlertResult(ok=False, channel="discord", skipped=True, error="Discord URL placeholder is invalid")
    payload: dict[str, Any] = {"content": message, "username": "GAME4ALL Manager Pro"}
    if embed:
        payload["embeds"] = [embed]
    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        if 200 <= response.status_code < 300:
            return AlertResult(ok=True, channel="discord", status_code=response.status_code)
        return AlertResult(
            ok=False,
            channel="discord",
            status_code=response.status_code,
            error=f"HTTP {response.status_code}",
        )
    except requests.RequestException as exc:
        return AlertResult(ok=False, channel="discord", error=str(exc))


def _post_telegram(message: str) -> AlertResult:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if not token or not chat_id:
        return AlertResult(ok=False, channel="telegram", skipped=True, error="Telegram token/chat placeholder is empty")
    url = TELEGRAM_API.format(token=token)
    try:
        response = requests.post(
            url,
            json={"chat_id": chat_id, "text": message, "disable_web_page_preview": True},
            timeout=REQUEST_TIMEOUT,
        )
        if 200 <= response.status_code < 300:
            body = response.json() if "application/json" in (response.headers.get("content-type") or "") else {}
            if isinstance(body, dict) and body.get("ok") is False:
                return AlertResult(ok=False, channel="telegram", status_code=response.status_code, error=str(body.get("description") or "Telegram rejected the message"))
            return AlertResult(ok=True, channel="telegram", status_code=response.status_code)
        return AlertResult(ok=False, channel="telegram", status_code=response.status_code, error=f"HTTP {response.status_code}")
    except requests.RequestException as exc:
        return AlertResult(ok=False, channel="telegram", error=str(exc))


def push_telegram_message(message: str, *, parse_mode: str = "HTML") -> AlertResult:
    """Send a rich-formatted (HTML/Markdown) message to Telegram.

    Used by the Hyper-Listing & Secure Telegram Dispatcher to push a listing card
    bundled with fresh delivery credentials and a session-revocation confirmation stamp.
    """
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if not token or not chat_id:
        return AlertResult(ok=False, channel="telegram", skipped=True, error="Telegram token/chat placeholder is empty")
    url = TELEGRAM_API.format(token=token)
    try:
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=REQUEST_TIMEOUT,
        )
        if 200 <= response.status_code < 300:
            body = response.json() if "application/json" in (response.headers.get("content-type") or "") else {}
            if isinstance(body, dict) and body.get("ok") is False:
                return AlertResult(ok=False, channel="telegram", status_code=response.status_code, error=str(body.get("description") or "Telegram rejected the message"))
            return AlertResult(ok=True, channel="telegram", status_code=response.status_code)
        return AlertResult(ok=False, channel="telegram", status_code=response.status_code, error=f"HTTP {response.status_code}")
    except requests.RequestException as exc:
        return AlertResult(ok=False, channel="telegram", error=str(exc))


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
    results = [_post_discord(text, embed), _post_telegram(text)]
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
