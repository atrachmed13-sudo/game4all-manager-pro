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
# Password stops at whitespace / | / ; / , / so listing fields after a combo stay separate.
# Separator itself accepts : | ; / or , — covers "email:pass", "email;pass", "email,pass"
# and spaced variants like "email | pass" alike (the loose fallback in split_login_combo()
# below also catches spaced separators the strict regex here doesn't sit right next to).
COMBO_IN_TEXT = re.compile(
    r"([^\s@|;,]+@[^\s@]+\.[A-Za-z0-9.-]+)[:|;/,\t]([^\s|;/,]+)",
    re.IGNORECASE,
)
CREDENTIAL_LINE = re.compile(
    rf"^\s*{COMBO_IN_TEXT.pattern}",
    re.IGNORECASE,
)

COLUMN_ALIASES = {
    "account_no": {
        "account_no",
        "account_number",
        "account_num",
        "account",
        "acct_no",
        "acct",
        "no",
        "num",
        "number",
        "n",
        "#",
    },
    "sku": {"sku", "id", "ref", "code"},
    "title": {"title", "name", "item", "listing"},
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
    "login_password": {
        "password",
        "pass",
        "passwd",
        "pwd",
        "pass_word",
        "login_password",
        "account_password",
        "epic_password",
        "epic_pass",
    },
    "mail_password": {"mail_password", "mail_pass", "inbox_password"},
    "old_password": {"old_password", "old_pass", "previous_password", "former_password"},
    "secret_answer": {"secret_answer", "security_answer", "sa", "sqa", "answer"},
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


# Strict decode order for uploaded TXT/combo packs (Arabic Windows exports are usually cp1256).
_DECODE_ORDER = ("utf-8-sig", "utf-8", "cp1256", "latin1")
# Replacement chars and long "?" runs usually mean the wrong code page was picked.
_MOJIBAKE_CHAR = "\ufffd"
_GARBLED_RUN = re.compile(r"\?{2,}")
_GARBLED_FIELD_PREFIX = re.compile(r"^[\?\ufffd�\s=\-*_~#|:،]+")
_GARBLED_LINE = re.compile(r"^[\?\ufffd�\s=\-*_~#|]+$")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def _decode_quality_score(text: str) -> int:
    """Higher is better — penalise replacement chars and long question-mark runs."""
    if not text:
        return 0
    bad = text.count(_MOJIBAKE_CHAR) + text.count("�")
    bad += sum(len(match.group(0)) for match in _GARBLED_RUN.finditer(text))
    return len(text) - bad * 12


def _sanitize_decoded_text(text: str) -> str:
    """Drop lines that are pure mojibake noise; collapse blank lines."""
    cleaned_lines: list[str] = []
    blank_run = 0
    for raw_line in (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = _clean_display_line(raw_line)
        if not line:
            blank_run += 1
            if blank_run <= 1:
                cleaned_lines.append("")
            continue
        blank_run = 0
        if _GARBLED_LINE.match(line):
            continue
        cleaned_lines.append(line)
    while cleaned_lines and not cleaned_lines[-1]:
        cleaned_lines.pop()
    return "\n".join(cleaned_lines)


def decode_upload_bytes(raw: bytes) -> str:
    """Decode an uploaded TXT/CSV/combo file using a fixed encoding order.

    Order: ``utf-8-sig`` → ``utf-8`` → ``cp1256`` (Arabic Windows) → ``latin1``.
    The candidate with the fewest replacement / ``??`` artefacts wins. A final
    ``latin1`` + ``errors='replace'`` pass strips damaged bytes instead of
    leaving them in Titles / grid cells.
    """
    if not raw:
        return ""

    best_text = ""
    best_score = -10**9
    for encoding in _DECODE_ORDER:
        try:
            candidate = raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
        score = _decode_quality_score(candidate)
        if score > best_score:
            best_score = score
            best_text = candidate

    if best_text:
        return _sanitize_decoded_text(best_text)

    fallback = raw.decode("latin1", errors="replace")
    fallback = fallback.replace(_MOJIBAKE_CHAR, "").replace("�", "")
    fallback = _GARBLED_RUN.sub("", fallback)
    fallback = _CONTROL_CHARS.sub("", fallback)
    return _sanitize_decoded_text(fallback)


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
    # Loose fallback for separators the strict regex above doesn't sit right next to —
    # e.g. "email@x.com | pass123" (spaces around the pipe) or a trailing/odd separator.
    parts = re.split(r"[:|;/,\t]", raw, maxsplit=1)
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
        "mail_password": "",
        "old_password": "",
        "secret_answer": "",
    }


def extract_features(text: str, seed: dict[str, Any] | None = None) -> dict[str, str]:
    """Pull rank / skins / emotes / level / region out of an active account's own stored
    attributes first; fall back to free-typed text only when there's no account context.

    When ``seed`` (a picked inventory row) is present, every regex fallback below scans
    the seed's *own* blob only — never the raw ``text`` box. This is deliberate: the raw
    paste box may still contain stale or unrelated text left over from a previously
    picked account (or the seller's own scratch notes), and mixing it into the scan would
    let a leftover match (e.g. a different account's rank/skins) silently override the
    real, trusted details of the account that's actually active. With no seed at all
    (pure manual paste), the raw text is the only source there is.
    """
    if seed:
        source = " | ".join(
            _norm(seed.get(k))
            for k in ("title", "game", "rank", "level", "skins", "emotes", "extras", "server", "notes")
            if _norm(seed.get(k))
        )
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
    # Only append a regex hit if it isn't already covered by the seed's own extras text —
    # otherwise a keyword the account already lists (e.g. "Smurf") gets tacked on a second
    # time just because the same word also appears in the blob it was pulled from.
    existing_lower = extras.lower()
    seen_lower: set[str] = set()
    new_hits: list[str] = []
    for hit in extra_hits:
        clean = hit.strip()
        clean_lower = clean.lower()
        if not clean or clean_lower in seen_lower or clean_lower in existing_lower:
            continue
        seen_lower.add(clean_lower)
        new_hits.append(clean)
    extra_joined = ", ".join(new_hits)
    if extra_joined:
        extras = ", ".join(part for part in (extras, extra_joined) if part)

    title = _norm((seed or {}).get("title"))
    if not title:
        bits = [part for part in (game, rank, skins and "loaded") if part]
        if bits:
            title = " ".join(bits)
        else:
            # A line with nothing else to go on but a bare "email:password" combo should
            # never surface the raw combo (password included) as the visible title — fall
            # back to just the email instead of leaking the credential into the UI.
            combo_email, combo_password = split_login_combo(source)
            clean_source = source
            if combo_email and combo_password:
                combo_needle = re.compile(re.escape(combo_email) + r"\s*[:|;/,\t]?\s*" + re.escape(combo_password))
                clean_source = combo_needle.sub(" ", source, count=1).strip(" |;,:\t")
            title = clean_source[:80].strip() or combo_email

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


_LISTING_TEXT_FIELDS = (
    "sku",
    "title",
    "game",
    "rank",
    "level",
    "skins",
    "emotes",
    "extras",
    "server",
    "notes",
    "login_email",
    "login_password",
    "mail_password",
    "old_password",
    "secret_answer",
)


def _sanitize_listing_row(item: dict[str, Any]) -> dict[str, Any]:
    """Blank any grid field that is still mojibake after decoding/cleaning."""
    for key in _LISTING_TEXT_FIELDS:
        if key not in item:
            continue
        clean = _sanitize_field_value(str(item.get(key) or ""))
        if key == "title":
            clean = _clean_title(clean)
        item[key] = clean
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
    item = _sanitize_listing_row(item)
    if not item["title"]:
        item["title"] = item["game"] or item["login_email"] or "GAME4ALL listing"
    return item


def listing_from_csv_cells(
    row_cells: dict[str, Any],
    header_map: dict[str, str | None],
) -> dict[str, Any]:
    """Map one CSV/Excel row (header → cell value) into a normalized inventory listing."""
    mapped = _blank_listing()
    notes_bits: list[str] = []
    account_no = ""
    for src, value in row_cells.items():
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        field = header_map.get(src)
        if field == "account_no":
            account_no = text
            continue
        if field and field != "combo":
            mapped[field] = value
        else:
            notes_bits.append(f"{src}: {text}")
    if account_no:
        notes_bits.insert(0, f"Account #: {account_no}")
        if not _norm(mapped.get("sku")):
            mapped["sku"] = f"ACC-{account_no}"
    if notes_bits:
        mapped["notes"] = " | ".join(part for part in (mapped.get("notes"), *notes_bits) if part)
    item = _finalize_listing(mapped)
    if account_no and account_no not in (item.get("notes") or ""):
        item["notes"] = " | ".join(part for part in (item.get("notes"), f"Account #: {account_no}") if part)
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
    header_map = {src: _map_header(src) for src in reader.fieldnames}
    rows: list[dict[str, Any]] = []
    for raw in reader:
        if not any(str(value or "").strip() for value in raw.values()):
            continue
        item = listing_from_csv_cells(raw, header_map)
        if item["login_email"] and item["login_password"]:
            imported += 1
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
        # Strip out the matched "email <sep> password" chunk as one unit so neither the
        # credentials nor a stray leftover separator (":" / "|" ...) pollute the
        # "notes"/"title" leftover text below. Matching literal values (not just the
        # strict-regex .sub()) also covers combos only found via split_login_combo()'s
        # looser fallback — e.g. "email@x.com | pass123" with spaces around the separator,
        # which the strict COMBO_IN_TEXT regex doesn't match but the fallback does.
        combo_needle = re.compile(re.escape(email) + r"\s*[:|;/,\t]?\s*" + re.escape(password))
        line_for_parts, count = combo_needle.subn(" ", line, count=1)
        if not count:
            line_for_parts = line.replace(email, " ", 1).replace(password, " ", 1)
    parts = [part.strip() for part in re.split(r"[|/;,]+", line_for_parts) if part.strip()]
    leftover = []
    kv_prefix_re = re.compile(
        r"^(cost|buy|sell|price|lvl|level|rank|game|server|skins|emotes|platform|email|password|combo)\s*[=:]",
        re.IGNORECASE,
    )
    bare_email_re = re.compile(r"^[^\s@]+@[^\s@]+\.[A-Za-z0-9.-]+$")
    idx = 0
    while idx < len(parts):
        part = parts[idx]
        email, password = split_login_combo(part)
        if email and password:
            mapped["login_email"] = mapped["login_email"] or email
            mapped["login_password"] = mapped["login_password"] or password
            idx += 1
            continue
        # A fully pipe/comma-delimited row where every column — including the login —
        # shares the same delimiter (e.g. "Fortnite | EU | buyer@mail.com | Pass123!") has
        # no distinct separator tying email to password, so split_login_combo() alone can't
        # see it: the email and password simply land as two consecutive plain fields. Pair
        # a bare email field with whatever immediately follows it, unless that next field is
        # clearly a labeled key=value pair for something else.
        if (
            not mapped["login_password"]
            and bare_email_re.match(part)
            and idx + 1 < len(parts)
            and " " not in parts[idx + 1]
            and not kv_prefix_re.match(parts[idx + 1])
        ):
            mapped["login_email"] = mapped["login_email"] or part
            mapped["login_password"] = parts[idx + 1]
            idx += 2
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
            idx += 1
            continue
        leftover.append(part)
        idx += 1
    if leftover:
        mapped["title"] = leftover[0]
        mapped["notes"] = " | ".join(leftover)
    return _finalize_listing(mapped)


def _is_noise_line(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("#")


EMAIL_ONLY = re.compile(r"^[^\s@]+@[^\s@]+\.[A-Za-z0-9.-]+$", re.IGNORECASE)
BLOCK_SEPARATOR = re.compile(r"^\s*(?:[=\-*_~.]{3,}|[=\-*_~\s]{8,})\s*$")
ACCOUNT_HEADER = re.compile(
    r"""^\s*(?:[=\-*_~#\[\] ]*)
    (?:
        (?:account|acc|item|listing|n[o°]|رقم|الحساب|compte)\s*[#.:\-]*\s*\d+
        | (?:account|acc)\s*[#.:\-]+\s*\d+
        | (?:account|acc)\b
        | \[\s*\d+\s*\]
        | \#\s*\d+
        | \d{1,4}\s*[.)\-](?:\s+\S+)?
        | \d{1,4}\s*:\s+\S+
    )
    .*$
    """,
    re.IGNORECASE | re.VERBOSE,
)
# More specific labels are tried first so "Mail Password" never becomes the email field
# and "Epic Password" never falls through to the generic password matcher.
_LABELED_SPECS: tuple[tuple[str, str], ...] = (
    ("title", r"title|name|account\s*name|listing|العنوان|titre"),
    ("game", r"game|jeu|اللعبة|لعبة"),
    ("login_email", r"e[-_]?mail(?:\s*address)?|mail(?:\s*address)?|login|username|user|الإيميل|الايميل|الميل|البريد"),
    (
        "login_password",
        r"epic(?:\s+games)?(?:\s*(?:password|pass|pwd))?|(?:password|pass|pwd)\s*(?:epic|game)|"
        r"كلمة\s*سر(?:ة)?(?:\s*ال)?(?:[اأإآ]?يبك|epic)|باسورد\s*(?:ال)?(?:[اأإآ]?يبك|epic)",
    ),
    (
        "mail_password",
        r"(?:mail|email|inbox)\s*(?:password|pass|pwd)|(?:password|pass|pwd)\s*(?:mail|email|inbox)|"
        r"كلمة\s*سر(?:ة)?(?:\s*ال)?(?:ميل|بريد)|باسورد\s*(?:ال)?(?:ميل|بريد)",
    ),
    (
        "old_password",
        r"old\s*(?:password|pass|pwd)|(?:password|pass|pwd)\s*old|previous\s*(?:password|pass|pwd)|"
        r"former\s*(?:password|pass|pwd)|كلمة\s*سر(?:ة)?\s*قديم(?:ة)?|باسورد\s*قديم",
    ),
    (
        "secret_answer",
        r"secret\s*answer|security\s*answer|(?:secret|security)\s*ans|\bsqa\b|\bsa\b|answer|"
        r"الإجابة\s*السرية|الجواب\s*(?:السري)?",
    ),
    ("secret_question", r"secret\s*question|security\s*question|\bsq\b|question|السؤال\s*السري"),
    ("rank", r"rank|tier|elo|الرانك"),
    ("level", r"level|lvl|niveau|المستوى"),
    ("skins", r"skins?|cosmetics?|السكينات"),
    ("emotes", r"emotes?|dances?"),
    ("server", r"server|region|السيرفر|المنطقة"),
    ("cost", r"cost|buy(?:_?price)?|prix_achat"),
    ("list_price", r"list_price|sell(?:_?price)?|price|prix"),
    ("platform", r"platform|marketplace|market|site"),
    (
        "login_password",
        r"password|pass|passwd|pwd|mot\s*de\s*passe|كلمة\s*(?:ال)?سر(?:ة)?|باسورد",
    ),
)
_LABEL_ONLY_RES: list[tuple[str, re.Pattern[str]]] = [
    (field, re.compile(rf"^(?:{label_re})\s*$", re.IGNORECASE))
    for field, label_re in _LABELED_SPECS
]
_ACCOUNT_DUMP_NAME = re.compile(r"(?:account|acc|fortnite|epic|valorant|combo|pack)", re.IGNORECASE)


def _clean_display_line(line: str) -> str:
    """Strip control characters / mojibake junk from a source line."""
    text = (line or "").replace("\ufeff", "").replace("\u200b", "").replace("\xa0", " ")
    text = _CONTROL_CHARS.sub("", text)
    text = text.replace(_MOJIBAKE_CHAR, "").replace("�", "")
    text = _GARBLED_RUN.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _is_garbled_value(text: str) -> bool:
    """True when a field is mostly corrupted encoding noise (???? / replacement chars)."""
    value = _norm(text)
    if not value:
        return False
    if _GARBLED_LINE.match(value):
        return True
    if re.match(r"^\?{2,}", value):
        return True
    if value.count("?") >= 3 and value.count("?") / len(value) >= 0.45:
        return True
    damaged = value.count(_MOJIBAKE_CHAR) + value.count("�")
    return damaged >= max(1, len(value) // 2)


def _sanitize_field_value(value: str) -> str:
    """Remove leading ``?`` / odd symbols; blank the field if it is still garbled."""
    text = _clean_display_line(value)
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'", "`"}:
        text = text[1:-1].strip()
    text = _GARBLED_FIELD_PREFIX.sub("", text).strip()
    if _is_garbled_value(text):
        return ""
    return text


def _clean_field_value(value: str) -> str:
    return _sanitize_field_value(value)


def _clean_title(value: str) -> str:
    text = _clean_field_value(value)
    text = re.sub(r"^[=\-*_~#\[\]\s]+", "", text)
    text = re.sub(r"[=\-*_~#\[\]\s]+$", "", text)
    text = re.sub(r"\s+", " ", text).strip(" -:|")
    return text


def _game_from_filename(filename: str) -> str:
    """Infer the game from names like C.FORTNITE.txt / fortnite_pack.txt."""
    name = _norm(filename)
    if not name:
        return ""
    stem = re.sub(r"\.[^.]+$", "", name)
    stem = re.sub(r"^[A-Za-z]\.", "", stem)
    blob = f"{stem} {name}".replace("_", " ").replace("-", " ")
    for game in GAMES:
        if re.search(rf"\b{re.escape(game)}\b", blob, re.IGNORECASE):
            return "League of Legends" if game.lower() == "lol" else game
    compact = re.sub(r"[^a-z0-9]+", "", stem.lower())
    for game in GAMES:
        key = re.sub(r"[^a-z0-9]+", "", game.lower())
        if key and compact == key:
            return "League of Legends" if game.lower() == "lol" else game
    return ""


def _labeled_match(line: str) -> tuple[str, str] | None:
    stripped = _clean_display_line(line)
    if not stripped:
        return None
    for field, label_re in _LABELED_SPECS:
        match = re.match(rf"^(?:{label_re})\s*[:：=\-]\s*(.+)$", stripped, re.IGNORECASE)
        if match:
            return field, _clean_field_value(match.group(1))
    return None


def _is_label_only_line(line: str) -> str | None:
    """Return the field name when a line is ONLY a label (value on the next line)."""
    stripped = _clean_display_line(line)
    if not stripped:
        return None
    for field, pattern in _LABEL_ONLY_RES:
        if pattern.match(stripped):
            return field
    return None


def _assign_block_field(mapped: dict[str, Any], field: str, value: str) -> None:
    value = _clean_field_value(value)
    if not value:
        return
    if field == "login_email":
        combo_email, combo_password = split_login_combo(value)
        mapped["login_email"] = mapped["login_email"] or combo_email or value
        if combo_password:
            mapped["login_password"] = mapped["login_password"] or combo_password
    elif field == "login_password":
        mapped["login_password"] = mapped["login_password"] or value
    elif field == "mail_password":
        mapped["mail_password"] = mapped["mail_password"] or value
    elif field == "old_password":
        mapped["old_password"] = mapped["old_password"] or value
    elif field == "secret_answer":
        mapped["secret_answer"] = mapped["secret_answer"] or value
    elif field == "title":
        mapped["title"] = mapped["title"] or _clean_title(value)
    elif field in mapped and not _norm(mapped.get(field)):
        mapped[field] = value


def _is_comment_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("#"):
        return False
    return not ACCOUNT_HEADER.match(stripped)


def _is_account_header(line: str) -> bool:
    stripped = _clean_display_line(line)
    if not stripped or _labeled_match(stripped):
        return False
    if EMAIL_ONLY.match(stripped) or ("@" in stripped and "." in stripped):
        return False
    return bool(ACCOUNT_HEADER.match(stripped))


def _header_title(line: str) -> str:
    stripped = _clean_display_line(line)
    rest = re.sub(
        r"^\s*(?:[=\-*_~#\[\] ]*)(?:account|acc|item|listing|n[o°]|رقم|الحساب|compte)?\s*[#.:\-]*\s*\d+\s*[.):\-]?\s*",
        "",
        stripped,
        flags=re.IGNORECASE,
    )
    rest = re.sub(r"^\[\s*\d+\s*\]\s*", "", rest)
    return _clean_title(rest)


def _looks_like_feature_text(text: str) -> bool:
    lowered = text.lower()
    if re.search(r"\d+\s+(?:skins?|emotes?|dances?|items?)", lowered):
        return True
    if any(game.lower() == lowered or game.lower() in lowered for game in GAMES):
        return len(text.split()) >= 2
    return False


def _looks_like_one_line_pack(lines: list[str]) -> bool:
    """True when almost every line is already a self-contained listing/combo row."""
    if len(lines) <= 1:
        return True
    compact = 0
    for ln in lines:
        if "|" in ln or ";" in ln:
            compact += 1
            continue
        email, password = split_login_combo(ln)
        if email and password:
            compact += 1
            continue
        if re.match(r"^(cost|buy|sell|price|lvl|level|rank|game|server|platform)\s*[=:]", ln, re.IGNORECASE):
            compact += 1
            continue
    # Do NOT treat per-field labeled lines (Email : … / Epic Password : …) as compact rows —
    # those are block-dump lines and must be grouped, not parsed one line = one table row.
    return compact >= max(1, int(len(lines) * 0.65))


def _looks_like_account_blocks(text: str, filename: str = "") -> bool:
    """True when the file is a multi-line account dump (C.FORTNITE.txt style), not one row per line."""
    if filename.lower().endswith(".csv"):
        return False
    lines = [_clean_display_line(ln) for ln in (text or "").splitlines()]
    lines = [ln for ln in lines if ln and not _is_comment_line(ln)]
    if len(lines) < 2:
        return False
    if _looks_like_one_line_pack(lines):
        return False

    headers = sum(1 for ln in lines if _is_account_header(ln))
    label_only = sum(1 for ln in lines if _is_label_only_line(ln))
    inline_labels = sum(1 for ln in lines if _labeled_match(ln))
    emails = len(re.findall(r"[^\s@|;,]+@[^\s@]+\.[A-Za-z0-9.-]+", text or ""))
    seps = sum(1 for ln in lines if BLOCK_SEPARATOR.match(ln))

    if headers >= 1:
        return True
    if label_only >= 2:
        return True
    if inline_labels >= 2 and emails >= 1:
        return True
    if seps >= 1 and emails >= 1:
        return True
    if emails >= 1 and len(lines) >= emails * 3:
        return True
    if _ACCOUNT_DUMP_NAME.search(filename) and emails >= 1:
        return True
    # Any non-compact multiline TXT with at least one email is treated as a block dump —
    # prevents "Email" / "Epic Password" label lines becoming separate table rows.
    return emails >= 1


def _should_use_block_parser(text: str, filename: str = "") -> bool:
    """Decide whether a TXT upload must go through the block parser (never one-line-per-row)."""
    if filename.lower().endswith(".csv"):
        return False
    payload = _sanitize_decoded_text((text or "").replace("\ufeff", "").strip())
    lines = [_clean_display_line(ln) for ln in payload.splitlines()]
    lines = [ln for ln in lines if ln and not _is_comment_line(ln)]
    if len(lines) < 2:
        return False
    if _looks_like_one_line_pack(lines):
        return False

    # Files like C.FORTNITE.txt / fortnite_combo.txt are always block dumps.
    if _ACCOUNT_DUMP_NAME.search(filename):
        return True

    return _looks_like_account_blocks(payload, filename)


def _resplit_chunk_on_headers(lines: list[str]) -> list[list[str]]:
    """If several ACCOUNT headers landed in one chunk, split again on each header."""
    if sum(1 for ln in lines if _is_account_header(ln)) <= 1:
        return [lines]
    groups: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if current and _is_account_header(line):
            groups.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        groups.append(current)
    return groups or [lines]


def _split_account_blocks(text: str) -> list[str]:
    """Cut a dump into one text blob per account."""
    raw_lines = (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    chunks: list[list[str]] = []
    current: list[str] = []
    current_has_email = False

    def flush() -> None:
        nonlocal current, current_has_email
        kept = [_clean_display_line(ln) for ln in current if not _is_comment_line(ln)]
        kept = [ln for ln in kept if ln and not BLOCK_SEPARATOR.match(ln)]
        if kept:
            for group in _resplit_chunk_on_headers(kept):
                if group:
                    chunks.append(group)
        current = []
        current_has_email = False

    for raw in raw_lines:
        line = _clean_display_line(raw)
        if _is_comment_line(raw):
            continue
        if not line:
            continue
        if BLOCK_SEPARATOR.match(line):
            flush()
            continue
        labeled = _labeled_match(line)
        is_email_label = bool(labeled and labeled[0] == "login_email")
        is_bare_email = bool(EMAIL_ONLY.match(line))
        is_label_only_email = _is_label_only_line(line) == "login_email"
        starts_new_account = current and (
            _is_account_header(line)
            or (current_has_email and (is_email_label or is_bare_email or is_label_only_email))
        )
        if starts_new_account:
            flush()
        current.append(line)
        if is_email_label or is_bare_email or is_label_only_email or split_login_combo(line)[0]:
            current_has_email = True
    flush()

    if len(chunks) == 1:
        emails_in_first = len(
            re.findall(r"[^\s@|;,]+@[^\s@]+\.[A-Za-z0-9.-]+", "\n".join(chunks[0]))
        )
        if emails_in_first > 1:
            chunks = _resplit_block_on_emails(chunks[0])

    return ["\n".join(lines) for lines in chunks if any(lines)]


def _resplit_block_on_emails(lines: list[str]) -> list[list[str]]:
    """If one blob still holds several emails, start a new account at each extra email line."""
    groups: list[list[str]] = []
    current: list[str] = []
    seen_email = False
    for line in lines:
        if _is_account_header(line):
            if current:
                groups.append(current)
            current = [line]
            seen_email = False
            continue
        labeled = _labeled_match(line)
        is_email = (
            (labeled and labeled[0] == "login_email")
            or _is_label_only_line(line) == "login_email"
            or bool(EMAIL_ONLY.match(line))
            or bool(split_login_combo(line)[0])
        )
        if seen_email and is_email:
            if current:
                groups.append(current)
            current = [line]
            seen_email = bool(is_email)
            continue
        current.append(line)
        if is_email:
            seen_email = True
    if current:
        groups.append(current)
    return groups or [lines]


def _account_header_title(line: str) -> str:
    rest = _header_title(line)
    if rest:
        return rest
    cleaned = _clean_title(line)
    if cleaned:
        return cleaned
    num = re.search(r"\d+", line or "")
    return f"Account {num.group(0)}" if num else "Account"


def _is_valid_account_row(item: dict[str, Any]) -> bool:
    """Drop junk rows produced when a label line was parsed alone (Email, Epic Password, …)."""
    if _norm(item.get("login_email")):
        return True
    if _norm(item.get("login_password")) and _norm(item.get("title")) and not _is_label_only_line(item["title"]):
        return True
    return False


def _parse_account_block(block: str, filename: str = "") -> dict[str, Any]:
    """Turn one multi-line account dump into a single inventory row."""
    mapped = _blank_listing()
    leftover: list[str] = []
    unlabeled: list[str] = []
    secret_question = ""
    raw_lines = [
        _clean_display_line(raw_line)
        for raw_line in (block or "").splitlines()
        if _clean_display_line(raw_line) and not BLOCK_SEPARATOR.match(_clean_display_line(raw_line))
    ]

    idx = 0
    while idx < len(raw_lines):
        line = raw_lines[idx]
        if _is_account_header(line):
            if not mapped["title"]:
                mapped["title"] = _account_header_title(line)
            idx += 1
            continue

        labeled = _labeled_match(line)
        if labeled:
            field, value = labeled
            if field == "secret_question":
                secret_question = secret_question or value
            else:
                _assign_block_field(mapped, field, value)
            idx += 1
            continue

        label_only = _is_label_only_line(line)
        if label_only:
            nxt_idx = idx + 1
            while nxt_idx < len(raw_lines) and not raw_lines[nxt_idx].strip():
                nxt_idx += 1
            if nxt_idx < len(raw_lines):
                nxt = raw_lines[nxt_idx]
                if not _is_account_header(nxt) and not _is_label_only_line(nxt) and not _labeled_match(nxt):
                    if label_only == "secret_question":
                        secret_question = secret_question or nxt
                    else:
                        _assign_block_field(mapped, label_only, nxt)
                    idx = nxt_idx + 1
                    continue
            idx += 1
            continue

        combo_email, combo_password = split_login_combo(line)
        if combo_email:
            mapped["login_email"] = mapped["login_email"] or combo_email
            mapped["login_password"] = mapped["login_password"] or combo_password
            idx += 1
            continue
        if EMAIL_ONLY.match(line):
            mapped["login_email"] = mapped["login_email"] or line
            idx += 1
            continue

        unlabeled.append(line)
        idx += 1

    for item in unlabeled:
        if not mapped["title"] and (_looks_like_feature_text(item) or len(item.split()) >= 2):
            mapped["title"] = _clean_title(item)
            continue
        if not mapped["title"]:
            mapped["title"] = _clean_title(item)
            continue
        if _looks_like_feature_text(item):
            leftover.append(item)
            continue
        if not mapped["login_password"]:
            mapped["login_password"] = item
            continue
        if not mapped["mail_password"]:
            mapped["mail_password"] = item
            continue
        if not mapped["old_password"]:
            mapped["old_password"] = item
            continue
        if not mapped["secret_answer"]:
            mapped["secret_answer"] = item
            continue
        leftover.append(item)

    if not mapped["login_email"]:
        found = re.search(r"[^\s@|;,]+@[^\s@]+\.[A-Za-z0-9.-]+", block or "")
        if found:
            mapped["login_email"] = found.group(0)

    if not mapped["game"]:
        mapped["game"] = _game_from_filename(filename)

    if leftover:
        mapped["notes"] = " | ".join(dict.fromkeys(_clean_title(part) for part in leftover if _clean_title(part)))
    if secret_question and secret_question.lower() not in (mapped.get("notes") or "").lower():
        mapped["notes"] = " | ".join(part for part in (mapped.get("notes"), f"SQ: {secret_question}") if part)

    item = _finalize_listing(mapped)
    if item.get("login_email") and item["login_email"] in (item.get("notes") or ""):
        item["notes"] = " | ".join(
            part for part in (item.get("notes") or "").split(" | ") if item["login_email"] not in part
        )
    return item


def parse_batch_text(text: str, filename: str = "") -> dict[str, Any]:
    """Parse uploaded pack contents into listing dicts, including login combos and block dumps."""
    payload = _sanitize_decoded_text((text or "").replace("\ufeff", "").strip())
    if _should_use_block_parser(payload, filename):
        rows = []
        for block in _split_account_blocks(payload):
            item = _parse_account_block(block, filename)
            if _is_valid_account_row(item):
                rows.append(item)
        imported = sum(1 for row in rows if _norm(row.get("login_email")) and _norm(row.get("login_password")))
        return {"rows": rows, "imported_logins": imported, "filename": filename}

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
