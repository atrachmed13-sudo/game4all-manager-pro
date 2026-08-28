"""Batch listing parser and marketplace sales-copy generator.

Reads TXT/CSV inventory packs (game, rank, skins, prices).
Lines that look like email:password logins are skipped — this module
does not authenticate to any game or marketplace.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Any

from pricing import PLATFORMS, get_platform_profile

# email:password (and close variants) — never imported as stock.
CREDENTIAL_LINE = re.compile(
    r"^\s*[^\s@]+@[^\s@]+\.[^\s@:|;]+(?:[:|;/\t]\S+)",
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

SERVERS = ("EU", "NA", "LATAM", "BR", "AP", "KR", "OCE", "TR", "MENA", "SEA")

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
    """True when a line looks like an email:password combo rather than a listing."""
    return bool(CREDENTIAL_LINE.match(text or ""))


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
        r"\b(?:battle pass|vbucks|v-bucks|rp|points|unlinked|no ban|no bans|full access|original email|2fa|warranty)\b",
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


def _finalize_listing(row: dict[str, Any]) -> dict[str, Any]:
    item = _blank_listing()
    item.update({k: row.get(k, item[k]) for k in item})
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
    if not item["title"]:
        item["title"] = item["game"] or "GAME4ALL listing"
    return item


def _parse_csv(text: str) -> tuple[list[dict[str, Any]], int]:
    skipped = 0
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
        line = " ".join(str(v) for v in raw.values() if v)
        if is_credential_line(line):
            skipped += 1
            continue
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
        if item["game"] or item["title"]:
            rows.append(item)
    return rows, skipped


def _parse_pipe_line(line: str) -> dict[str, Any]:
    parts = [part.strip() for part in re.split(r"[|/;]+", line) if part.strip()]
    mapped = _blank_listing()
    mapped["notes"] = line
    leftover = []
    for part in parts:
        kv = re.match(r"^(cost|buy|sell|price|lvl|level|rank|game|server|skins|emotes|platform)\s*[=:]\s*(.+)$", part, re.IGNORECASE)
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
            continue
        leftover.append(part)
    if leftover:
        mapped["title"] = leftover[0]
        mapped["notes"] = " | ".join(leftover)
    return _finalize_listing(mapped)


def parse_batch_text(text: str, filename: str = "") -> dict[str, Any]:
    """Parse uploaded pack contents into listing dicts."""
    payload = (text or "").replace("\ufeff", "").strip()
    skipped = 0
    kept_lines = []
    for line in payload.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if is_credential_line(line):
            skipped += 1
            continue
        kept_lines.append(line)
    cleaned = "\n".join(kept_lines).strip()
    rows: list[dict[str, Any]] = []
    lower_name = filename.lower()
    looks_csv = lower_name.endswith(".csv") or ("," in cleaned.split("\n", 1)[0] and _map_header(cleaned.split("\n", 1)[0].split(",")[0]) is not None)
    if cleaned and (looks_csv or (cleaned.split("\n", 1)[0].count(",") >= 2 and re.search(r"game|title|rank|skins", cleaned.split("\n", 1)[0], re.I))):
        rows, extra_skip = _parse_csv(cleaned)
        skipped += extra_skip
    if not rows and cleaned:
        for line in kept_lines:
            item = _parse_pipe_line(line)
            if item["game"] or item["title"]:
                rows.append(item)
    return {"rows": rows, "skipped_credentials": skipped, "filename": filename}


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
