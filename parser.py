"""Batch listing parser and marketplace sales-copy generator.

Reads TXT/CSV inventory packs (game, rank, skins, prices, email, password).
email:password combo lines are imported as stock logins for delivery, not checked online.
"""

from __future__ import annotations

import csv
import io
import re
from html import escape as _html_escape
from typing import Any

from pricing import PLATFORMS, get_platform_profile

# email:password (and close variants) — imported as delivery logins, never authenticated here.
# The local part (before @) also stops at | ; , so a compact pipe/semicolon-delimited line
# like "League of Legends|EUW|Smurf|Full Access|buyer@mail.com:pass" never bleeds the
# previous field ("...Access") into the email, corrupting game/rank/extras downstream.
# Password stops at whitespace / | / ; / / so listing fields after a combo stay separate.
COMBO_IN_TEXT = re.compile(
    r"([^\s@|;,]+@[^\s@]+\.[A-Za-z0-9.-]+)[:|;/\t]([^\s|;/]+)",
    re.IGNORECASE,
)
CREDENTIAL_LINE = re.compile(
    rf"^\s*{COMBO_IN_TEXT.pattern}",
    re.IGNORECASE,
)

COLUMN_ALIASES = {
    "sku": {"sku", "id", "ref", "code"},
    "title": {"title", "name", "item", "listing", "account"},
    "game": {"game", "jeu", "title_game"},
    "rank": {"rank", "tier", "elo", "rr"},
    "level": {"level", "lvl", "niveau"},
    "skins": {"skins", "skin", "items", "loadout", "cosmetics"},
    "emotes": {"emotes", "emote", "dances", "dance"},
    "extras": {"extras", "extra", "notes_extra", "features"},
    "server": {"server", "region", "realm"},
    "cost": {"cost", "buy", "buy_price", "cost_price", "prix_achat"},
    "list_price": {"list_price", "sell", "sell_price", "price", "prix"},
    "platform": {"platform", "marketplace", "market", "site"},
    "status": {"status", "state", "stock"},
    "notes": {"notes", "note", "desc", "description", "raw"},
    "login_email": {"email", "mail", "e_mail", "login_email", "user", "username", "login", "account_email"},
    "login_password": {"password", "pass", "passwd", "pwd", "pass_word", "login_password", "account_password"},
    "combo": {"combo", "login_combo", "ep", "userpass", "email_password"},
}

GAMES = (
    "Valorant",
    "Fortnite",
    "League of Legends",
    "LoL",
    "Rocket League",
    "GTA V",
    "GTA",
    "FC 25",
    "FC 26",
    "FIFA",
    "Roblox",
    "CS2",
    "CS:GO",
    "Counter-Strike",
    "Dota 2",
    "Overwatch",
    "Apex Legends",
    "Warzone",
    "Call of Duty",
    "Rainbow Six",
    "Minecraft",
    "PUBG",
    "Mobile Legends",
    "Clash of Clans",
    "Brawl Stars",
    "Steam",
    "Riot",
    "Destiny 2",
    "Lost Ark",
    "Path of Exile",
    "World of Warcraft",
)

RANKS = (
    "Radiant",
    "Immortal",
    "Ascendant",
    "Diamond",
    "Platinum",
    "Gold",
    "Silver",
    "Bronze",
    "Iron",
    "Unreal",
    "Champion",
    "Champion League",
    "Unranked",
    "Fresh",
    "Smurf",
    "Predator",
    "Master",
    "Grandmaster",
    "Challenger",
    "Mythic",
    "Legendary",
    "High Rank",
    "Rank Ready",
)

SERVERS = (
    "EUW",
    "EUNE",
    "NAE",
    "NAW",
    "EU",
    "NA",
    "LATAM",
    "LAN",
    "LAS",
    "BR",
    "AP",
    "KR",
    "JP",
    "OCE",
    "TR",
    "MENA",
    "SEA",
    "RU",
)

EMAIL_LABELS = {
    "full_access": {
        "en": "Full Access",
        "fr": "Full Access (accès complet)",
        "ar": "Full Access",
    },
    "original_email": {
        "en": "Original Email",
        "fr": "Original Email",
        "ar": "Original Email",
    },
    "full_and_original": {
        "en": "Full Access + Original Email",
        "fr": "Full Access + Original Email",
        "ar": "Full Access + Original Email",
    },
}

COPY_PACKS = {
    "en": {
        "hook": {
            "G2G": "INSTANT DELIVERY • TRUSTED SELLER",
            "Eldorado": "FAST DELIVERY • FULL ACCESS",
            "PlayerAuctions": "READY TO PLAY • WARRANTY INCLUDED",
            "FanPay": "SECURE PAYOUT • FAST HANDOFF",
            "PlayHub (PlayOkay)": "QUICK HANDOFF • CLEAN LISTING",
            "EpicNPC": "SERIOUS SELLER • INSTANT INFO",
            "U7BUY": "FAST DELIVERY • CLEAN ACCOUNT",
        },
        "intro": "<strong>{title}</strong> — ready for {platform}. GAME4ALL: Trust, Security, Speed.",
        "status": "Status",
        "server": "Server",
        "email": "Email access",
        "skins": "Skins / items",
        "emotes": "Emotes",
        "level": "Level",
        "extras": "Extras",
        "warranty": "Warranty",
        "warranty_text": "{hours}h replacement if the listing details do not match + active seller support",
        "footer": "Buy with confidence from GAME4ALL Accounts Store. Screenshots on request.",
        "rank_fallback": "Rank ready",
    },
    "fr": {
        "hook": {
            "G2G": "LIVRAISON INSTANTANÉE • VENDEUR FIABLE",
            "Eldorado": "LIVRAISON RAPIDE • FULL ACCESS",
            "PlayerAuctions": "PRÊT À JOUER • GARANTIE INCLUSE",
            "FanPay": "PAIEMENT SÉCURISÉ • REMISE RAPIDE",
            "PlayHub (PlayOkay)": "REMISE RAPIDE • ANNONCE PROPRE",
            "EpicNPC": "VENDEUR SÉRIEUX • INFOS IMMÉDIATES",
            "U7BUY": "LIVRAISON RAPIDE • COMPTE CLEAN",
        },
        "intro": "<strong>{title}</strong> — prêt pour {platform}. GAME4ALL : Confiance, Sécurité, Vitesse.",
        "status": "Statut",
        "server": "Serveur",
        "email": "Accès e-mail",
        "skins": "Skins / items",
        "emotes": "Emotes",
        "level": "Niveau",
        "extras": "Extras",
        "warranty": "Garantie",
        "warranty_text": "Remplacement sous {hours}h si l’annonce ne correspond pas + support vendeur",
        "footer": "Achetez en confiance chez GAME4ALL Accounts Store. Captures sur demande.",
        "rank_fallback": "Rank ready",
    },
    "ar": {
        "hook": {
            "G2G": "تسليم فوري • بائع موثوق",
            "Eldorado": "تسليم سريع • Full Access",
            "PlayerAuctions": "جاهز للعب • ضمان مضمّن",
            "FanPay": "دفع آمن • تسليم سريع",
            "PlayHub (PlayOkay)": "تسليم سريع • إعلان نظيف",
            "EpicNPC": "بائع جاد • معلومات فورية",
            "U7BUY": "تسليم سريع • حساب نظيف",
        },
        "intro": "<strong>{title}</strong> — جاهز لمنصة {platform}. GAME4ALL: ثقة، أمان، سرعة.",
        "status": "الحالة",
        "server": "السيرفر",
        "email": "وصول الإيميل",
        "skins": "السكينات / الأيتمات",
        "emotes": "الإيموتات",
        "level": "المستوى",
        "extras": "إضافات",
        "warranty": "الضمان",
        "warranty_text": "استبدال خلال {hours} ساعة إذا لم تطابق التفاصيل + دعم البائع",
        "footer": "اشترِ بثقة من GAME4ALL Accounts Store. لقطات الشاشة عند الطلب.",
        "rank_fallback": "جاهز للرانك",
    },
}


def _norm(value: Any) -> str:
    return str(value or "").strip()


def is_credential_line(text: str) -> bool:
    """True when a line looks like an email:password combo."""
    return bool(split_login_combo(text or "")[0])


def split_login_combo(text: str) -> tuple[str, str]:
    """Return (email, password) from a combo anywhere in the text, or empty strings."""
    match = COMBO_IN_TEXT.search(text or "")
    if match:
        return match.group(1).strip(), match.group(2).strip()
    raw = _norm(text)
    if not raw:
        return "", ""
    parts = re.split(r"[:|;/\t]", raw, maxsplit=1)
    if len(parts) == 2 and "@" in parts[0]:
        return parts[0].strip(), parts[1].strip()
    return "", ""


def _map_header(header: str) -> str | None:
    key = re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_")
    for field, aliases in COLUMN_ALIASES.items():
        if key in aliases:
            return field
    return None


def _money(value: Any) -> float:
    raw = str(value or "").strip().replace(",", ".")
    raw = re.sub(r"[^0-9.\-]", "", raw)
    if not raw or raw in {".", "-", "-."}:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _blank_listing() -> dict[str, Any]:
    return {
        "sku": "",
        "title": "",
        "game": "",
        "rank": "",
        "level": "",
        "skins": "",
        "emotes": "",
        "extras": "",
        "server": "",
        "cost": 0.0,
        "list_price": 0.0,
        "platform": "G2G",
        "status": "Available",
        "notes": "",
        "login_email": "",
        "login_password": "",
    }


def extract_features(text: str, seed: dict[str, Any] | None = None) -> dict[str, str]:
    """Pull rank / skins / emotes / level / region out of free text."""
    if seed:
        blob = " | ".join(
            _norm(seed.get(k))
            for k in ("title", "game", "rank", "level", "skins", "emotes", "extras", "server", "notes")
            if _norm(seed.get(k))
        )
        source = f"{blob} | {text}" if text else blob
    else:
        source = text or ""

    game = _norm((seed or {}).get("game"))
    if not game:
        for name in GAMES:
            if re.search(rf"\b{re.escape(name)}\b", source, re.IGNORECASE):
                game = "League of Legends" if name.lower() == "lol" else name
                break

    rank = _norm((seed or {}).get("rank"))
    if not rank:
        for name in RANKS:
            if re.search(rf"\b{re.escape(name)}\b", source, re.IGNORECASE):
                rank = name
                break

    level = _norm((seed or {}).get("level"))
    if not level:
        level_match = re.search(r"\b(?:lvl|level|lv)\s*[:\-]?\s*(\d{1,4})\b", source, re.IGNORECASE)
        if level_match:
            level = level_match.group(1)

    server = _norm((seed or {}).get("server")).upper()
    if not server:
        for name in SERVERS:
            if re.search(rf"\b{re.escape(name)}\b", source, re.IGNORECASE):
                server = name
                break

    skins = _norm((seed or {}).get("skins"))
    if not skins:
        skin_bits = re.findall(
            r"\b(?:\d+\s+)?(?:skins?|knives?|knife|karambit|heirloom|reaper|champion|reaver|rgx|phantom|vandal|pickaxe|glider)s?\b[^,;|/]*",
            source,
            re.IGNORECASE,
        )
        count_match = re.search(r"(\d+)\s+skins?\b", source, re.IGNORECASE)
        skins = ", ".join(dict.fromkeys(bit.strip(" -") for bit in skin_bits if bit.strip()))
        if count_match and count_match.group(0).lower() not in skins.lower():
            skins = ", ".join(part for part in (count_match.group(0), skins) if part)

    emotes = _norm((seed or {}).get("emotes"))
    if not emotes:
        emote_match = re.search(r"(\d+\s+)?(?:emotes?|dances?|icons?)\b[^,;|/]*", source, re.IGNORECASE)
        if emote_match:
            emotes = emote_match.group(0).strip()

    extras = _norm((seed or {}).get("extras"))
    extra_hits = re.findall(
        r"\b(?:battle pass|vbucks|v-bucks|rp|points|unlinked|no ban|no bans|full access|"
        r"original email|unverified email|verified email|instant delivery|manual delivery|"
        r"2fa|warranty|rank ready|smurf)\b",
        source,
        re.IGNORECASE,
    )
    extra_joined = ", ".join(dict.fromkeys(hit.strip() for hit in extra_hits))
    if extra_joined:
        extras = ", ".join(part for part in (extras, extra_joined) if part)

    title = _norm((seed or {}).get("title"))
    if not title:
        bits = [part for part in (game, rank, skins and "loaded") if part]
        title = " ".join(bits) if bits else source[:80].strip()

    return {
        "title": title,
        "game": game,
        "rank": rank,
        "level": level,
        "skins": skins,
        "emotes": emotes,
        "server": server,
        "extras": extras,
        "raw": source[:4000],
    }


def _apply_login_fields(item: dict[str, Any], source: str = "") -> dict[str, Any]:
    combo = _norm(item.pop("combo", "") if "combo" in item else "")
    email = _norm(item.get("login_email"))
    password = _norm(item.get("login_password"))
    if combo and (not email or not password):
        combo_email, combo_password = split_login_combo(combo)
        email = email or combo_email
        password = password or combo_password
    if (not email or not password) and source:
        src_email, src_password = split_login_combo(source)
        email = email or src_email
        password = password or src_password
    if (not email or not password) and _norm(item.get("notes")):
        note_email, note_password = split_login_combo(_norm(item.get("notes")))
        email = email or note_email
        password = password or note_password
    item["login_email"] = email
    item["login_password"] = password
    if email and not _norm(item.get("title")):
        item["title"] = email
    return item


def _finalize_listing(row: dict[str, Any]) -> dict[str, Any]:
    item = _blank_listing()
    item.update({k: row.get(k, item[k]) for k in item if k in row or k in item})
    if "combo" in row:
        item["combo"] = row.get("combo")
    item["cost"] = _money(item["cost"])
    item["list_price"] = _money(item["list_price"])
    platform = _norm(item["platform"])
    item["platform"] = platform if platform in PLATFORMS else "G2G"
    status = _norm(item["status"]).title()
    item["status"] = status if status in {"Available", "Listed", "Sold"} else "Available"
    features = extract_features(item.get("notes") or "", item)
    for key in ("title", "game", "rank", "level", "skins", "emotes", "server", "extras"):
        if not _norm(item.get(key)):
            item[key] = features.get(key) or ""
    item = _apply_login_fields(item, _norm(item.get("notes")))
    if not item["title"]:
        item["title"] = item["game"] or item["login_email"] or "GAME4ALL listing"
    return item


def _parse_csv(text: str) -> tuple[list[dict[str, Any]], int]:
    imported = 0
    sample = text.lstrip()[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        return [], 0
    mapping = {src: _map_header(src) for src in reader.fieldnames}
    rows: list[dict[str, Any]] = []
    for raw in reader:
        mapped: dict[str, Any] = _blank_listing()
        notes_bits = []
        for src, value in raw.items():
            field = mapping.get(src)
            if field:
                mapped[field] = value
            elif value:
                notes_bits.append(f"{src}: {value}")
        if notes_bits:
            mapped["notes"] = " | ".join(part for part in (mapped.get("notes"), *notes_bits) if part)
        item = _finalize_listing(mapped)
        if item["login_email"] and item["login_password"]:
            imported += 1
        if item["game"] or item["title"] or item["login_email"]:
            rows.append(item)
    return rows, imported


def _parse_pipe_line(line: str) -> dict[str, Any]:
    mapped = _blank_listing()
    mapped["notes"] = line
    email, password = split_login_combo(line)
    line_for_parts = line
    if email and password:
        mapped["login_email"] = email
        mapped["login_password"] = password
        line_for_parts = COMBO_IN_TEXT.sub(" ", line, count=1)
    parts = [part.strip() for part in re.split(r"[|/;]+", line_for_parts) if part.strip()]
    leftover = []
    for part in parts:
        email, password = split_login_combo(part)
        if email and password:
            mapped["login_email"] = mapped["login_email"] or email
            mapped["login_password"] = mapped["login_password"] or password
            continue
        kv = re.match(r"^(cost|buy|sell|price|lvl|level|rank|game|server|skins|emotes|platform|email|password|combo)\s*[=:]\s*(.+)$", part, re.IGNORECASE)
        if not kv:
            # "cost 16" / "sell 29" — space separator is only safe when the value is a number.
            kv = re.match(r"^(cost|buy|sell|price|lvl|level)\s+([\d.,]+)$", part, re.IGNORECASE)
        if kv:
            key = kv.group(1).lower()
            val = kv.group(2).strip()
            if key in {"cost", "buy"}:
                mapped["cost"] = val
            elif key in {"sell", "price"}:
                mapped["list_price"] = val
            elif key in {"lvl", "level"}:
                mapped["level"] = val
            elif key == "rank":
                mapped["rank"] = val
            elif key == "game":
                mapped["game"] = val
            elif key == "server":
                mapped["server"] = val
            elif key == "skins":
                mapped["skins"] = val
            elif key == "emotes":
                mapped["emotes"] = val
            elif key == "platform":
                mapped["platform"] = val
            elif key == "email":
                mapped["login_email"] = val
            elif key == "password":
                mapped["login_password"] = val
            elif key == "combo":
                mapped["combo"] = val
            continue
        leftover.append(part)
    if leftover:
        mapped["title"] = leftover[0]
        mapped["notes"] = " | ".join(leftover)
    return _finalize_listing(mapped)


def _is_noise_line(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("#")


def parse_batch_text(text: str, filename: str = "") -> dict[str, Any]:
    """Parse uploaded pack contents into listing dicts, including login combos."""
    payload = (text or "").replace("\ufeff", "").strip()
    body_lines = [line for line in payload.splitlines() if not _is_noise_line(line)]
    body = "\n".join(body_lines)
    header = body_lines[0] if body_lines else ""
    # A header only counts as CSV when several of its comma fields are real column names,
    # so prose or a combo line with a stray comma is never mistaken for a CSV header.
    header_fields = [part for part in header.split(",") if part.strip()]
    mapped_fields = sum(1 for part in header_fields if _map_header(part) is not None)
    looks_csv = filename.lower().endswith(".csv") or (len(header_fields) >= 2 and mapped_fields >= 2)
    imported = 0
    rows: list[dict[str, Any]] = []
    if looks_csv and body:
        rows, imported = _parse_csv(body)
    if not rows:
        # Every TXT line goes through the same parser: the combo becomes the delivery login
        # and the remaining pipe fields still fill game / rank / prices.
        for line in body_lines:
            item = _parse_pipe_line(line)
            if item["game"] or item["title"] or item["login_email"]:
                rows.append(item)
    imported = sum(1 for row in rows if _norm(row.get("login_email")) and _norm(row.get("login_password")))
    return {"rows": rows, "imported_logins": imported, "filename": filename}


def feature_cards(features: dict[str, str]) -> list[dict[str, str]]:
    """Turn extracted fields into bold bullet cards for the UI."""
    order = (
        ("game", "feat_game"),
        ("rank", "feat_rank"),
        ("level", "feat_level"),
        ("skins", "feat_skins"),
        ("emotes", "feat_emotes"),
        ("server", "feat_server"),
        ("extras", "feat_extras"),
    )
    cards = []
    for field, label_key in order:
        value = _norm(features.get(field))
        if value:
            cards.append({"field": field, "label_key": label_key, "value": value})
    return cards


def _bullets(features: dict[str, str], pack: dict[str, Any], email_label: str, warranty_h: int) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    rank = _norm(features.get("rank")) or pack["rank_fallback"]
    items.append((pack["status"], rank))
    if _norm(features.get("server")):
        items.append((pack["server"], features["server"]))
    items.append((pack["email"], email_label))
    if _norm(features.get("level")):
        items.append((pack["level"], features["level"]))
    if _norm(features.get("skins")):
        items.append((pack["skins"], features["skins"]))
    if _norm(features.get("emotes")):
        items.append((pack["emotes"], features["emotes"]))
    if _norm(features.get("extras")):
        items.append((pack["extras"], features["extras"]))
    items.append((pack["warranty"], pack["warranty_text"].format(hours=int(warranty_h))))
    return items


def generate_sales_copy(
    features: dict[str, str],
    *,
    platform: str = "G2G",
    lang: str = "en",
    email_key: str = "full_access",
    warranty_h: int = 12,
) -> dict[str, str]:
    """Return HTML, plain text, and BBCode optimized for the target marketplace."""
    lang_key = lang if lang in COPY_PACKS else "en"
    pack = COPY_PACKS[lang_key]
    market = platform if platform in PLATFORMS else "G2G"
    title = _norm(features.get("title")) or _norm(features.get("game")) or "GAME4ALL listing"
    hook = pack["hook"].get(market) or pack["hook"]["G2G"]
    email_label = EMAIL_LABELS.get(email_key, EMAIL_LABELS["full_access"]).get(lang_key, "Full Access")
    bullets = _bullets(features, pack, email_label, warranty_h)
    intro = pack["intro"].format(title=title, platform=market)

    html_lines = [
        f"<h3>{hook} — {features.get('game') or 'Premium listing'}</h3>",
        f"<p>{intro}</p>",
        "<ul>",
    ]
    for label, value in bullets:
        html_lines.append(f"  <li><strong>{label}:</strong> {value}</li>")
    html_lines.extend(["</ul>", f"<p>{pack['footer']}</p>"])
    html = "\n".join(html_lines)

    plain_lines = [f"{hook} — {features.get('game') or 'Premium listing'}", intro.replace("<strong>", "").replace("</strong>", ""), ""]
    for label, value in bullets:
        plain_lines.append(f"• {label}: {value}")
    plain_lines.extend(["", pack["footer"]])
    plain = "\n".join(plain_lines)

    bb_lines = [
        f"[b][color=#3b82f6]{hook}[/color] — {features.get('game') or 'Premium listing'}[/b]",
        intro.replace("<strong>", "[b]").replace("</strong>", "[/b]"),
        "",
    ]
    for label, value in bullets:
        bb_lines.append(f"[*] [b]{label}:[/b] {value}")
    bb_lines.extend(["", pack["footer"]])
    bbcode = "\n".join(bb_lines)

    preferred = get_platform_profile(market).get("copy_format") or "html"
    primary = {"html": html, "plain": plain, "bbcode": bbcode}.get(preferred, html)
    return {
        "html": html,
        "plain": plain,
        "bbcode": bbcode,
        "primary": primary,
        "format": preferred,
        "platform": market,
        "lang": lang_key,
    }


LISTING_PLATFORMS = ("G2G", "Eldorado", "PlayerAuctions", "FanPay")
DELIVERY_KEYS = ("instant", "manual", "fast_1h", "hours_12", "hours_24")


def generate_marketplace_listing(
    *,
    game: str,
    rank: str = "",
    server: str = "",
    delivery_label: str = "",
    extras: str = "",
    platform: str = "G2G",
    lang: str = "en",
) -> dict[str, str]:
    """Build a marketplace title and paste-ready description for G2G-style shops."""
    lang_key = lang if lang in COPY_PACKS else "en"
    pack = COPY_PACKS[lang_key]
    market = platform if platform in LISTING_PLATFORMS else "G2G"
    game_name = _norm(game) or "Premium Game Account"
    rank_name = _norm(rank) or pack["rank_fallback"]
    region_name = _norm(server)
    # Reflect the real region/server in the headline whenever it's known (e.g. "League of
    # Legends EUW Smurf") instead of silently dropping it from the generated copy.
    game_region = f"{game_name} {region_name}".strip() if region_name else game_name
    extras_text = _norm(extras) or EMAIL_LABELS["full_access"][lang_key]
    delivery = _norm(delivery_label) or pack["hook"].get(market, pack["hook"]["G2G"]).split("•")[0].strip()
    hook = pack["hook"].get(market) or pack["hook"]["G2G"]
    feature_bit = extras_text.split(",")[0].strip()[:42] or "Full Access"

    if market == "G2G":
        title = f"{game_region} {rank_name} | {delivery} | {feature_bit}"
    elif market == "Eldorado":
        title = f"{game_region} {rank_name} Account — {feature_bit} — {delivery}"
    elif market == "FanPay":
        title = f"{game_region} | {rank_name} | {feature_bit} | GAME4ALL"
    else:
        title = f"{game_region} {rank_name} — {delivery} — Ready to Play"

    title = re.sub(r"\s+", " ", title).strip()[:120]

    labels = {
        "en": ("Game", "Region / server", "Rank / level", "Delivery", "Features", "Email access", "Warranty"),
        "fr": ("Jeu", "Région / serveur", "Rang / niveau", "Livraison", "Extras", "Accès e-mail", "Garantie"),
        "ar": ("اللعبة", "المنطقة / السيرفر", "الرانك / المستوى", "التسليم", "المميزات", "وصول الإيميل", "الضمان"),
    }
    named = labels.get(lang_key, labels["en"])
    values = (game_name, region_name, rank_name, delivery, extras_text, EMAIL_LABELS["full_access"][lang_key], pack["warranty_text"].format(hours=12))
    # Skip the region row entirely when there's nothing to show, rather than printing a
    # blank/placeholder line in the pasted copy.
    labeled = [(label, value) for label, value in zip(named, values) if not (label == named[1] and not value)]

    intro_title = re.sub(r"\s+", " ", f"{game_region} {rank_name}").strip()
    intro = pack["intro"].format(title=intro_title, platform=market)
    html_lines = [
        f"<h3>{hook}</h3>",
        f"<p>{intro}</p>",
        "<ul>",
    ]
    for label, value in labeled:
        html_lines.append(f"  <li><strong>{label}:</strong> {value}</li>")
    html_lines.extend(["</ul>", f"<p>{pack['footer']}</p>"])

    plain_lines = [hook, "", intro.replace("<strong>", "").replace("</strong>", ""), ""]
    for label, value in labeled:
        plain_lines.append(f"• {label}: {value}")
    plain_lines.extend(["", pack["footer"], "", "GAME4ALL Accounts Store — Trust, Security, Speed"])
    description = "\n".join(plain_lines)
    return {
        "title": title,
        "description": description,
        "html": "\n".join(html_lines),
        "platform": market,
        "lang": lang_key,
    }


HYPER_LISTING_LABELS = {
    "en": {
        "banner": "HYPER LISTING",
        "creds": "🔐 Secure Delivery Credentials",
        "email": "Email",
        "password": "Password",
        "stamp_title": "✅ Session Revocation Confirmed",
        "stamp_body": "All old device sessions were revoked and unlinked at {ts} UTC — safe to hand over.",
        "stamp_pending_title": "⏳ Sessions Not Yet Revoked",
        "stamp_pending_body": "Run the Secure & Unlink Sessions action before sharing this card with a buyer.",
        "footer": "GAME4ALL Accounts Store — Trust, Security, Speed",
        "item_tag": "Item",
    },
    "fr": {
        "banner": "HYPER LISTING",
        "creds": "🔐 Identifiants de livraison sécurisés",
        "email": "Email",
        "password": "Mot de passe",
        "stamp_title": "✅ Révocation des sessions confirmée",
        "stamp_body": "Toutes les anciennes sessions ont été révoquées et déconnectées à {ts} UTC — prêt à livrer.",
        "stamp_pending_title": "⏳ Sessions non encore révoquées",
        "stamp_pending_body": "Lancez l'action Sécuriser et déconnecter les sessions avant de partager cette fiche.",
        "footer": "GAME4ALL Accounts Store — Confiance, Sécurité, Rapidité",
        "item_tag": "Article",
    },
    "ar": {
        "banner": "هايبر ليستينغ",
        "creds": "🔐 بيانات تسليم آمنة",
        "email": "الإيميل",
        "password": "كلمة السر",
        "stamp_title": "✅ تم تأكيد فصل الجلسات",
        "stamp_body": "تم فصل جميع جلسات الأجهزة القديمة نهائيًا في {ts} UTC — الحساب جاهز للتسليم بأمان.",
        "stamp_pending_title": "⏳ لم يتم فصل الجلسات بعد",
        "stamp_pending_body": "قم بتشغيل إجراء تأمين وفصل الجلسات الأمنية قبل مشاركة هذه البطاقة مع الزبون.",
        "footer": "GAME4ALL Accounts Store — ثقة، أمان، سرعة",
        "item_tag": "الحساب",
    },
}


def generate_hyper_listing(
    *,
    item_id: int,
    title: str = "",
    game: str = "",
    rank: str = "",
    server: str = "",
    extras: str = "",
    platform: str = "G2G",
    login_email: str = "",
    login_password: str = "",
    secured_at: str = "",
    lang: str = "en",
) -> dict[str, Any]:
    """Hyper-Listing & Secure Telegram Dispatcher.

    Combines a high-converting G2G/Eldorado marketing description with the freshly
    secured delivery credentials, returning both a Streamlit-ready markdown card and an
    HTML-formatted payload safe to push straight to the Telegram Bot API.
    """
    listing = generate_marketplace_listing(
        game=game or title,
        rank=rank,
        server=server,
        extras=extras,
        platform=platform,
        lang=lang,
    )
    lang_key = lang if lang in HYPER_LISTING_LABELS else "en"
    labels = HYPER_LISTING_LABELS[lang_key]
    market = listing["platform"]
    display_title = listing["title"]
    email_value = _norm(login_email) or "—"
    password_value = _norm(login_password) or "—"
    is_secured = bool(_norm(secured_at))

    if is_secured:
        stamp_title = labels["stamp_title"]
        stamp_body = labels["stamp_body"].format(ts=secured_at)
    else:
        stamp_title = labels["stamp_pending_title"]
        stamp_body = labels["stamp_pending_body"]

    card_lines = [
        f"### 🌟 {labels['banner']} — {market} 🌟",
        "",
        f"**{display_title}**",
        "",
        listing["description"],
        "",
        "---",
        "",
        f"**{labels['creds']}**",
        f"- {labels['email']}: `{email_value}`",
        f"- {labels['password']}: `{password_value}`",
        "",
        f"**{stamp_title}**",
        stamp_body,
        "",
        "---",
        f"🆔 {labels['item_tag']} `#{item_id}` · {labels['footer']}",
    ]
    card_markdown = "\n".join(card_lines)

    telegram_lines = [
        f"🌟 <b>{_html_escape(labels['banner'])} — {_html_escape(market)}</b> 🌟",
        "",
        f"<b>{_html_escape(display_title)}</b>",
        "",
        _html_escape(listing["description"]),
        "",
        f"<b>{_html_escape(labels['creds'])}</b>",
        f"{_html_escape(labels['email'])}: <code>{_html_escape(email_value)}</code>",
        f"{_html_escape(labels['password'])}: <code>{_html_escape(password_value)}</code>",
        "",
        f"<b>{_html_escape(stamp_title)}</b>",
        _html_escape(stamp_body),
        "",
        f"🆔 {_html_escape(labels['item_tag'])} <code>#{item_id}</code> · {_html_escape(labels['footer'])}",
    ]
    telegram_html = "\n".join(telegram_lines)

    return {
        "title": display_title,
        "description": listing["description"],
        "card_markdown": card_markdown,
        "telegram_html": telegram_html,
        "platform": market,
        "lang": lang_key,
        "secured": is_secured,
    }
