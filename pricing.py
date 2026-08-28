"""Marketplace fee tables and net-profit math for GAME4ALL listings.

Defaults are seller-side rates commonly published by each marketplace.
Operators can override commission % and extra fees in the calculator.
"""

from __future__ import annotations

import re
from typing import Any

# Marketplace IDs used across inventory, calculator, and sales copy.
PLATFORMS = (
    "G2G",
    "Eldorado",
    "PlayerAuctions",
    "PlayHub (PlayOkay)",
    "EpicNPC",
    "U7BUY",
)

# commission_pct: percentage of the listing/sale price taken by the marketplace.
# extra_fees: fixed extras (payment processing, payout fees) in the same currency.
PLATFORM_FEES: dict[str, dict[str, Any]] = {
    "G2G": {
        "commission_pct": 8.9,
        "extra_fees": 0.0,
        "note": "Seller service fee on most game-account categories (editable).",
        "copy_format": "html",
    },
    "Eldorado": {
        "commission_pct": 8.0,
        "extra_fees": 0.0,
        "note": "Standard Eldorado seller commission on account offers.",
        "copy_format": "html",
    },
    "PlayerAuctions": {
        "commission_pct": 8.0,
        "extra_fees": 0.30,
        "note": "Final-value fee plus a small payout/processing buffer.",
        "copy_format": "html",
    },
    "PlayHub (PlayOkay)": {
        "commission_pct": 8.0,
        "extra_fees": 0.0,
        "note": "PlayOkay / PlayHub seller rate on digital offers.",
        "copy_format": "html",
    },
    "EpicNPC": {
        "commission_pct": 0.0,
        "extra_fees": 0.0,
        "note": "Forum listing has no site cut; add PayPal/Wise fees as extras if used.",
        "copy_format": "bbcode",
    },
    "U7BUY": {
        "commission_pct": 8.0,
        "extra_fees": 0.0,
        "note": "U7BUY seller commission on account/item offers.",
        "copy_format": "plain",
    },
}

HOT_MARGIN_PCT = 20.0
THIN_MARGIN_PCT = 8.0


def get_platform_profile(platform: str) -> dict[str, Any]:
    """Return fee defaults for a marketplace, or a conservative 8% fallback."""
    key = (platform or "").strip()
    if key in PLATFORM_FEES:
        profile = dict(PLATFORM_FEES[key])
        profile["platform"] = key
        return profile
    return {
        "platform": key or "G2G",
        "commission_pct": 8.0,
        "extra_fees": 0.0,
        "note": "Unknown marketplace — using an 8% placeholder.",
        "copy_format": "plain",
    }


def calculate_deal(
    cost_price: float,
    sell_price: float,
    commission_pct: float | None = None,
    extra_fees: float | None = None,
    platform: str = "",
    hot_margin_pct: float = HOT_MARGIN_PCT,
) -> dict[str, Any]:
    """Net payout, profit, ROI, and deal heat after marketplace fees.

    ROI is profit / cost. Margin-on-sale is profit / sell price.
    """
    profile = get_platform_profile(platform) if platform else None
    if commission_pct is None:
        commission_pct = float(profile["commission_pct"]) if profile else 0.0
    if extra_fees is None:
        extra_fees = float(profile["extra_fees"]) if profile else 0.0

    cost = float(cost_price or 0)
    sell = float(sell_price or 0)
    rate = float(commission_pct or 0) / 100.0
    commission_amount = sell * rate
    fees = float(extra_fees or 0)
    net_received = sell - commission_amount - fees
    net_profit = net_received - cost
    roi_pct = (net_profit / cost * 100.0) if cost > 0 else 0.0
    margin_on_sale = (net_profit / sell * 100.0) if sell > 0 else 0.0

    if net_profit < 0:
        heat = "loss"
    elif roi_pct >= float(hot_margin_pct):
        heat = "hot"
    elif roi_pct < THIN_MARGIN_PCT:
        heat = "thin"
    else:
        heat = "ok"

    return {
        "platform": (profile or {}).get("platform") or platform or "",
        "cost_price": round(cost, 4),
        "sell_price": round(sell, 4),
        "commission_pct": round(float(commission_pct or 0), 4),
        "extra_fees": round(fees, 4),
        "commission_amount": round(commission_amount, 4),
        "net_received": round(net_received, 4),
        "net_profit": round(net_profit, 4),
        "roi_pct": round(roi_pct, 2),
        "margin_on_sale": round(margin_on_sale, 2),
        "heat": heat,
        "note": (profile or {}).get("note") or "",
    }


def required_sell_price(
    cost_price: float,
    target_profit: float,
    commission_pct: float = 0.0,
    extra_fees: float = 0.0,
) -> float:
    """Lowest list price that still yields ``target_profit`` after fees."""
    denom = 1.0 - (float(commission_pct or 0) / 100.0)
    if denom <= 0:
        return float("nan")
    raw = (float(cost_price or 0) + float(target_profit or 0) + float(extra_fees or 0)) / denom
    return round(raw, 2)


def compare_platforms(cost_price: float, sell_price: float) -> list[dict[str, Any]]:
    """Run the same cost/sell pair through every supported marketplace."""
    rows = []
    for name in PLATFORMS:
        rows.append(calculate_deal(cost_price, sell_price, platform=name))
    return rows


# Typical retail multiple vs cost, then rank/skins/platform nudge the quote.
_GAME_MARKUP = (
    (("valorant",), 1.48),
    (("fortnite",), 1.52),
    (("league", "lol", "wild rift"), 1.46),
    (("gta",), 1.58),
    (("cs2", "cs:go", "counter-strike", "counter strike"), 1.40),
    (("apex",), 1.50),
    (("roblox",), 1.62),
    (("rocket",), 1.44),
    (("fc 2", "fifa", "ea fc"), 1.42),
    (("minecraft",), 1.38),
    (("pubg",), 1.40),
    (("wow", "warcraft"), 1.50),
)
_RANK_BOOST = (
    (("radiant",), 0.24),
    (("immortal",), 0.18),
    (("unreal",), 0.20),
    (("predator",), 0.22),
    (("champion", "ssl", "supersonic"), 0.12),
    (("ascendant",), 0.11),
    (("master", "grandmaster"), 0.16),
    (("diamond",), 0.10),
    (("platinum", "plat"), 0.06),
    (("gold", "gold nova"), 0.03),
)
_PLATFORM_DEMAND = {
    "G2G": 1.00,
    "Eldorado": 1.03,
    "PlayerAuctions": 1.06,
    "PlayHub (PlayOkay)": 0.97,
    "EpicNPC": 1.05,
    "U7BUY": 0.99,
}
_RARE_TOKENS = (
    "heirloom",
    "reaver",
    "champions",
    "prestige",
    "limited",
    "painted",
    "meta",
    "rgx",
    "vandal",
    "phantom",
    "prime",
)


def _blob(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(key) or "")
        for key in ("title", "game", "rank", "level", "skins", "emotes", "extras", "notes")
    ).lower()


def _first_int(value: Any) -> int:
    match = re.search(r"(\d+)", str(value or ""))
    return int(match.group(1)) if match else 0


def _game_markup(game: str) -> float:
    text = (game or "").lower()
    for needles, markup in _GAME_MARKUP:
        if any(needle in text for needle in needles):
            return markup
    return 1.45


def _category_label(game: str) -> str:
    text = (game or "").strip()
    return text or "General"


def feature_multiplier(item: dict[str, Any]) -> float:
    """Lift from rank, skin/item count, and rare keywords."""
    boost = 0.0
    rank = str(item.get("rank") or "").lower()
    for needles, weight in _RANK_BOOST:
        if any(needle in rank for needle in needles):
            boost = max(boost, weight)
            break
    skins = _first_int(item.get("skins"))
    boost += min(skins, 200) * 0.00055
    emotes = _first_int(item.get("emotes"))
    if emotes >= 20:
        boost += 0.04
    elif emotes >= 8:
        boost += 0.02
    level = _first_int(item.get("level"))
    if level >= 180:
        boost += 0.05
    elif level >= 100:
        boost += 0.03
    blob = _blob(item)
    if any(token in blob for token in _RARE_TOKENS):
        boost += 0.07
    return round(1.0 + boost, 4)


def estimate_market_value(item: dict[str, Any], platform: str) -> float:
    """Buyer-side market quote for one listing on one marketplace."""
    cost = float(item.get("cost") or 0)
    if cost <= 0:
        return 0.0
    demand = _PLATFORM_DEMAND.get(platform, 1.0)
    raw = cost * _game_markup(str(item.get("game") or "")) * feature_multiplier(item) * demand
    listed = float(item.get("list_price") or 0)
    if listed > 0:
        raw = raw * 0.62 + listed * demand * 0.38
    return round(max(raw, 0.0), 2)


def estimate_listing(item: dict[str, Any], platform: str) -> dict[str, Any]:
    """Market estimate, recommended ask, fees, and net profit for one platform."""
    cost = float(item.get("cost") or 0)
    profile = get_platform_profile(platform)
    estimated = estimate_market_value(item, platform)
    target_profit = cost * (HOT_MARGIN_PCT / 100.0) if cost > 0 else 8.0
    floor = required_sell_price(
        cost,
        target_profit,
        float(profile["commission_pct"]),
        float(profile["extra_fees"]),
    )
    if floor != floor:
        floor = estimated or cost
    recommended = round(max(estimated, float(floor or 0)), 2)
    deal = calculate_deal(cost, recommended, platform=platform)
    fees = deal["commission_amount"] + deal["extra_fees"]
    return {
        "item_id": item.get("id"),
        "item_name": str(item.get("title") or item.get("sku") or "Listing").strip() or "Listing",
        "game": str(item.get("game") or "").strip(),
        "category": _category_label(str(item.get("game") or "")),
        "cost_price": round(cost, 2),
        "platform": platform,
        "estimated_market_value": estimated,
        "recommended_price": recommended,
        "marketplace_fees": round(fees, 2),
        "commission_pct": deal["commission_pct"],
        "net_profit": deal["net_profit"],
        "roi_pct": deal["roi_pct"],
        "heat": deal["heat"],
        "note": profile.get("note") or "",
    }


def suggested_list_price(item: dict[str, Any], platform: str | None = None) -> float:
    """Recommended ask for the listing's own marketplace (used on import)."""
    market = (platform or str(item.get("platform") or "G2G")).strip() or "G2G"
    if market not in PLATFORMS:
        market = "G2G"
    return float(estimate_listing(item, market)["recommended_price"])


def estimate_item_platforms(item: dict[str, Any]) -> list[dict[str, Any]]:
    return [estimate_listing(item, name) for name in PLATFORMS]


def pricing_grid(items: list[dict[str, Any]] | Any) -> list[dict[str, Any]]:
    """Expand each inventory row into six marketplace quotes."""
    rows: list[dict[str, Any]] = []
    records = items.to_dict("records") if hasattr(items, "to_dict") else list(items or [])
    for item in records:
        rows.extend(estimate_item_platforms(item))
    return rows


def best_quote(quotes: list[dict[str, Any]]) -> dict[str, Any] | None:
    profitable = [row for row in quotes if float(row.get("net_profit") or 0) > 0]
    pool = profitable or quotes
    if not pool:
        return None
    return max(pool, key=lambda row: (float(row.get("net_profit") or 0), float(row.get("roi_pct") or 0)))
