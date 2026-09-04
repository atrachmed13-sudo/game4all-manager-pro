"""GAME4ALL Manager Pro — Streamlit command desk for listing stock, copy, fees, and sales.

Run:
    streamlit run app.py
"""

from __future__ import annotations

import importlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import alerts
import database as db
import i18n as i18n_mod
import license as license_mod
import parser as parser_mod
import pricing as pricing_mod

db = importlib.reload(db)
i18n_mod = importlib.reload(i18n_mod)
license_mod = importlib.reload(license_mod)
parser_mod = importlib.reload(parser_mod)
pricing_mod = importlib.reload(pricing_mod)
LANGUAGE_LABELS = i18n_mod.LANGUAGE_LABELS
LANGUAGES = i18n_mod.LANGUAGES
t = i18n_mod.t
PLATFORMS = pricing_mod.PLATFORMS
best_quote = pricing_mod.best_quote
calculate_deal = pricing_mod.calculate_deal
compare_platforms = pricing_mod.compare_platforms
estimate_item_platforms = pricing_mod.estimate_item_platforms
get_platform_profile = pricing_mod.get_platform_profile
pricing_grid = pricing_mod.pricing_grid
required_sell_price = pricing_mod.required_sell_price
suggested_list_price = pricing_mod.suggested_list_price
DELIVERY_KEYS = parser_mod.DELIVERY_KEYS
LISTING_PLATFORMS = parser_mod.LISTING_PLATFORMS
extract_features = parser_mod.extract_features
feature_cards = parser_mod.feature_cards
generate_marketplace_listing = parser_mod.generate_marketplace_listing
generate_hyper_listing = parser_mod.generate_hyper_listing
generate_sales_copy = parser_mod.generate_sales_copy
parse_batch_text = parser_mod.parse_batch_text
decode_upload_bytes = parser_mod.decode_upload_bytes
listing_from_csv_cells = parser_mod.listing_from_csv_cells

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

BOOT_PACK_ID = db.BOOT_PACK_ID
BOOT_PACK_PATHS = tuple(db.discover_default_pack_paths()) or (
    ROOT / "sample_data" / "accounts.csv",
    ROOT / "sample_data" / "batch_pack_example.csv",
    ROOT / "sample_data" / "batch_pack_example.txt",
)

THEMES = ("royal", "cyber", "dark")
DESK_NAV = (
    ("inventory", "nav_inventory"),
    ("parser", "nav_parser"),
    ("pricing", "nav_pricing"),
    ("sales", "nav_sales"),
    ("customers", "nav_customers"),
    ("listing", "nav_listing"),
    ("license", "nav_license"),
)
PRIMARY_NAV = ("inventory", "parser", "pricing", "sales", "customers")
NAV_I18N = {
    "license": "nav_license",
    "listing": "nav_listing",
    "inventory": "nav_inventory",
    "parser": "nav_parser",
    "pricing": "nav_pricing",
    "sales": "nav_sales",
    "customers": "nav_customers",
}
DELIVERY_I18N = {
    "instant": "delivery_instant",
    "manual": "delivery_manual",
    "fast_1h": "delivery_1h",
    "hours_12": "delivery_12h",
    "hours_24": "delivery_24h",
}
CRM_PLATFORMS = ("G2G", "Eldorado", "PlayerAuctions", "FanPay")
ORDER_STATUS_KEYS = ("delivered_pending", "rated_success", "needs_followup")
ORDER_STATUS_I18N = {
    "delivered_pending": "order_status_delivered_pending",
    "rated_success": "order_status_rated_success",
    "needs_followup": "order_status_needs_followup",
}
OTHER_TOOL_PAGES = ("listing", "inventory", "parser", "pricing", "sales", "license")
THEME_LABEL_KEYS = {
    "royal": "theme_royal",
    "cyber": "theme_cyber",
    "dark": "theme_dark",
}
THEME_CHART = {
    "royal": "#d4af37",
    "cyber": "#22d3ee",
    "dark": "#e5e5e5",
}
THEME_VARS = {
    "royal": """
        --g4a-bg:#0d0d0d; --g4a-bg-2:#121212; --g4a-panel:#161411; --g4a-panel-2:#1c1812;
        --g4a-line:#d4af37; --g4a-accent:#d4af37; --g4a-accent-2:#ffd700; --g4a-accent-3:#aa771c;
        --g4a-text:#ffffff; --g4a-muted:#ffffff; --g4a-header:#ffd700; --g4a-btn-text:#ffffff;
        --g4a-hover-text:#ffd700; --g4a-glow:rgba(212,175,55,.32); --g4a-glow-strong:rgba(212,175,55,.5);
        --g4a-shine:rgba(255,215,0,.42); --g4a-success:#ffffff; --g4a-danger:#ffffff; --g4a-ridge:#6b4e12;
        --g4a-font-display:"Cinzel","Times New Roman",serif; --g4a-font-body:"Inter",system-ui,sans-serif;
        --g4a-hero-a:rgba(212,175,55,.22); --g4a-hero-b:rgba(170,119,28,.16);
        --g4a-btn-top:#3a3014; --g4a-btn-mid:#161411; --g4a-btn-bot:#050505; --g4a-tab-idle:#1c1812;
        --g4a-btn-active-top:#5a4716; --primary-color:#d4af37; --background-color:#0d0d0d;
        --secondary-background-color:#121212; --text-color:#ffffff;
    """,
    "cyber": """
        --g4a-bg:#0b0f19; --g4a-bg-2:#070b14; --g4a-panel:#111827; --g4a-panel-2:#0f172a;
        --g4a-line:#3b82f6; --g4a-accent:#3b82f6; --g4a-accent-2:#22d3ee; --g4a-accent-3:#f97316;
        --g4a-text:#ffffff; --g4a-muted:#ffffff; --g4a-header:#22d3ee; --g4a-btn-text:#ffffff;
        --g4a-hover-text:#22d3ee; --g4a-glow:rgba(34,211,238,.34); --g4a-glow-strong:rgba(34,211,238,.5);
        --g4a-shine:rgba(34,211,238,.4); --g4a-success:#34d399; --g4a-danger:#fb7185; --g4a-ridge:#0b1b4a;
        --g4a-font-display:"Inter",system-ui,sans-serif; --g4a-font-body:"Inter",system-ui,sans-serif;
        --g4a-hero-a:rgba(59,130,246,.28); --g4a-hero-b:rgba(249,115,22,.18);
        --g4a-btn-top:#1e3a8a; --g4a-btn-mid:#0b1224; --g4a-btn-bot:#020617; --g4a-tab-idle:#111827;
        --g4a-btn-active-top:#2563eb; --primary-color:#22d3ee; --background-color:#0b0f19;
        --secondary-background-color:#0f172a; --text-color:#ffffff;
    """,
    "dark": """
        --g4a-bg:#0a0a0a; --g4a-bg-2:#111111; --g4a-panel:#141414; --g4a-panel-2:#1a1a1a;
        --g4a-line:#e5e5e5; --g4a-accent:#e5e5e5; --g4a-accent-2:#ffffff; --g4a-accent-3:#737373;
        --g4a-text:#ffffff; --g4a-muted:#ffffff; --g4a-header:#ffffff; --g4a-btn-text:#ffffff;
        --g4a-hover-text:#ffffff; --g4a-glow:rgba(255,255,255,.2); --g4a-glow-strong:rgba(255,255,255,.45);
        --g4a-shine:rgba(255,255,255,.32); --g4a-success:#d4d4d4; --g4a-danger:#f5c2c2; --g4a-ridge:#2a2a2a;
        --g4a-font-display:"Inter",system-ui,sans-serif; --g4a-font-body:"Inter",system-ui,sans-serif;
        --g4a-hero-a:rgba(255,255,255,.06); --g4a-hero-b:rgba(255,255,255,.03);
        --g4a-btn-top:#3a3a3a; --g4a-btn-mid:#161616; --g4a-btn-bot:#050505; --g4a-tab-idle:#141414;
        --g4a-btn-active-top:#525252; --primary-color:#e5e5e5; --background-color:#0a0a0a;
        --secondary-background-color:#141414; --text-color:#ffffff;
    """,
}
LUXURY_UI_CSS = """
.g4a-spacer { height: 1.25rem !important; }
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(1200px 420px at 8% -10%, var(--g4a-hero-a), transparent 55%),
        radial-gradient(900px 380px at 100% 0%, var(--g4a-hero-b), transparent 50%),
        var(--g4a-bg) !important;
    color: var(--g4a-text) !important;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--g4a-bg) 0%, var(--g4a-panel) 100%) !important;
    border-right: 2px solid var(--g4a-accent) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    border: 1px solid var(--g4a-ridge) !important;
    border-radius: 10px !important;
    padding: 0.48rem 0.7rem !important;
    margin-bottom: 0.28rem !important;
    background: var(--g4a-panel-2) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    border-color: var(--g4a-accent) !important;
    box-shadow: 0 0 14px var(--g4a-glow) !important;
    background: linear-gradient(180deg, var(--g4a-btn-top), var(--g4a-bg-2)) !important;
}
[data-testid="stMain"] [data-testid="stRadio"] [role="radiogroup"],
[data-testid="stAppViewContainer"] [data-testid="stRadio"] > div {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 10px !important;
    width: 100% !important;
    align-items: stretch !important;
}
[data-testid="stMain"] [data-testid="stRadio"] label,
[data-testid="stAppViewBlockContainer"] [data-testid="stRadio"] label {
    border: 2px solid var(--g4a-accent) !important;
    border-radius: 14px !important;
    padding: 0.65rem 0.85rem !important;
    background-color: var(--g4a-btn-bot) !important;
    background-image:
        linear-gradient(180deg, var(--g4a-shine) 0%, transparent 34%),
        linear-gradient(180deg, var(--g4a-btn-top) 0%, var(--g4a-btn-mid) 46%, var(--g4a-btn-bot) 100%) !important;
    color: #ffffff !important;
    font-weight: 800 !important;
    white-space: nowrap !important;
    flex: 1 1 0 !important;
    min-height: 3.2rem !important;
    box-shadow: 0 8px 0 var(--g4a-ridge), 0 8px 25px var(--g4a-glow) !important;
}
[data-testid="stMain"] [data-testid="stRadio"] label:has(input:checked),
[data-testid="stMain"] [data-testid="stRadio"] label:has(input:checked) p,
[data-testid="stMain"] [data-testid="stRadio"] label:has(input:checked) span,
[data-testid="stMain"] [data-testid="stRadio"] label:has(input:checked) div {
    border-color: var(--g4a-accent-2) !important;
    color: #ffffff !important;
    background-image:
        linear-gradient(180deg, var(--g4a-shine) 0%, transparent 30%),
        linear-gradient(180deg, var(--g4a-btn-active-top) 0%, var(--g4a-btn-mid) 50%, var(--g4a-btn-bot) 100%) !important;
    box-shadow: 0 0 18px var(--g4a-glow-strong), 0 8px 0 var(--g4a-ridge) !important;
}
[data-testid="stMain"] [data-testid="stRadio"] [data-baseweb="radio"] > div,
[data-testid="stMain"] [data-testid="stRadio"] [data-baseweb="radio"] svg {
    display: none !important;
}
.g4a-listing-box {
    border: 2px solid var(--g4a-accent);
    border-radius: 14px;
    padding: 1rem 1.1rem;
    background: var(--g4a-bg-2);
    box-shadow: 0 8px 25px var(--g4a-glow);
    margin: 0.6rem 0 1.1rem;
}
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span, [data-testid="stCaption"],
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label, label, .stCaption, small,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span,
[data-testid="stSidebar"] label, [data-testid="stAlert"] p, [data-testid="stText"] p {
    color: #ffffff !important;
}
h1, h2, h3, h4, h5, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
[data-testid="stHeading"] * {
    color: var(--g4a-header) !important;
}
div[data-testid="stMetric"] {
    border: 2px solid var(--g4a-accent) !important;
    background: linear-gradient(180deg, var(--g4a-panel-2), var(--g4a-bg-2)) !important;
    box-shadow: 0 8px 25px var(--g4a-glow-strong) !important;
}
div[data-testid="stMetric"] label, div[data-testid="stMetric"] [data-testid="stMetricLabel"] p {
    color: #ffffff !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: var(--g4a-header) !important;
}
input, textarea, [data-baseweb="input"] input, [data-baseweb="textarea"] textarea,
[data-baseweb="select"] *, [data-baseweb="select"] span {
    color: #ffffff !important;
}
.stTextInput input, .stNumberInput input, .stTextArea textarea,
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {
    color: #ffffff !important;
    background-color: var(--g4a-bg-2) !important;
    caret-color: var(--g4a-accent-2) !important;
    border: 2px solid var(--g4a-accent) !important;
}
[data-baseweb="select"] > div {
    background-color: var(--g4a-bg-2) !important;
    color: #ffffff !important;
    border: 2px solid var(--g4a-accent) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    padding: 1.4rem 1.55rem 1.55rem !important;
    margin: 0.4rem 0 1.35rem !important;
    border: 2px solid var(--g4a-accent) !important;
    background: var(--g4a-bg-2) !important;
    border-radius: 16px !important;
    box-shadow: 0 8px 25px var(--g4a-glow) !important;
}
.stTabs [data-testid="stTabContent"] { padding-top: 1.7rem !important; }
.stTabs [data-baseweb="tab-list"], div[data-testid="stTabs"] [role="tablist"] {
    gap: 10px !important;
    row-gap: 12px !important;
    flex-wrap: wrap !important;
    overflow: visible !important;
    background: transparent !important;
    border-bottom: none !important;
    padding: 6px 0 14px !important;
}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { height: 0 !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {
    display: none !important;
    background: transparent !important;
}
html body .stApp [data-testid="stHorizontalBlock"]:has([data-testid="stBaseButton-secondary"]) > div,
html body .stApp [data-testid="stHorizontalBlock"]:has([data-testid="stBaseButton-primary"]) > div {
    display: flex !important;
}
html body .stApp [data-testid="stHorizontalBlock"] .stButton {
    width: 100% !important;
    flex: 1 1 0 !important;
}
html body .stApp [data-testid="stTab"],
html body .stApp [data-testid="stTab"][role="tab"],
html body .stApp .stTabs [data-baseweb="tab"],
html body .stApp .stTabs button[role="tab"],
html body .stApp .stButton > button,
html body .stApp .stDownloadButton > button,
html body .stApp .stFormSubmitButton > button,
html body .stApp button[kind="secondary"],
html body .stApp button[kind="primary"],
html body .stApp [data-testid="stBaseButton-secondary"],
html body .stApp [data-testid="stBaseButton-primary"],
html body .stApp [data-testid="stBaseButton-secondaryFormSubmit"],
html body .stApp [data-testid="stBaseButton-primaryFormSubmit"],
html body [data-testid="stSidebar"] button[kind="secondary"],
html body [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
    background-color: var(--g4a-btn-bot) !important;
    background-image:
        linear-gradient(180deg, var(--g4a-shine) 0%, transparent 34%),
        linear-gradient(180deg, var(--g4a-btn-top) 0%, var(--g4a-btn-mid) 46%, var(--g4a-btn-bot) 100%) !important;
    color: #ffffff !important;
    border: 2px solid var(--g4a-accent) !important;
    border-radius: 14px !important;
    padding: 14px 22px !important;
    min-height: 3.4rem !important;
    white-space: normal !important;
    line-height: 1.25 !important;
    font-weight: 800 !important;
    letter-spacing: 0.04em !important;
    text-shadow: 0 1px 0 #000000, 0 0 10px rgba(0,0,0,.7) !important;
    box-shadow:
        inset 0 2px 0 rgba(255,255,255,.22),
        inset 0 -12px 18px rgba(0,0,0,.62),
        0 1px 0 var(--g4a-accent-2),
        0 8px 0 var(--g4a-ridge),
        0 8px 25px var(--g4a-glow-strong) !important;
    transform: translateY(0);
    transition: transform .12s ease, box-shadow .12s ease, color .12s ease, border-color .12s ease, filter .12s ease !important;
}
html body .stApp [data-testid="stTab"] { margin: 0 6px 10px 0 !important; white-space: nowrap !important; flex: 0 0 auto !important; }
html body .stApp [data-testid="stTab"]:hover,
html body .stApp .stTabs button[role="tab"]:hover,
html body .stApp .stButton > button:hover,
html body .stApp button[kind="secondary"]:hover,
html body .stApp button[kind="primary"]:hover,
html body .stApp [data-testid="stBaseButton-secondary"]:hover,
html body .stApp [data-testid="stBaseButton-primary"]:hover,
html body [data-testid="stSidebar"] button:hover {
    color: var(--g4a-hover-text) !important;
    border-color: var(--g4a-accent-2) !important;
    transform: translateY(-3px);
    filter: brightness(1.08);
    box-shadow:
        inset 0 2px 0 rgba(255,255,255,.28),
        0 1px 0 var(--g4a-accent-2),
        0 11px 0 var(--g4a-ridge),
        0 8px 25px var(--g4a-glow-strong),
        0 16px 36px var(--g4a-glow-strong) !important;
}
html body .stApp [data-testid="stTab"]:active,
html body .stApp .stButton > button:active,
html body .stApp button[kind="secondary"]:active,
html body .stApp button[kind="primary"]:active,
html body .stApp [data-testid="stBaseButton-secondary"]:active,
html body .stApp [data-testid="stBaseButton-primary"]:active {
    transform: translateY(7px) !important;
    box-shadow:
        inset 0 10px 18px rgba(0,0,0,.72),
        0 2px 0 var(--g4a-ridge),
        0 4px 12px rgba(0,0,0,.55) !important;
}
html body .stApp [data-testid="stTab"][aria-selected="true"],
html body .stApp .stTabs [aria-selected="true"] {
    color: #ffffff !important;
    background-image:
        linear-gradient(180deg, var(--g4a-shine) 0%, transparent 30%),
        linear-gradient(180deg, var(--g4a-btn-active-top) 0%, var(--g4a-btn-mid) 50%, var(--g4a-btn-bot) 100%) !important;
    border: 2px solid var(--g4a-accent-2) !important;
    box-shadow:
        inset 0 2px 0 rgba(255,255,255,.3),
        0 0 0 2px var(--g4a-bg),
        0 8px 0 var(--g4a-ridge),
        0 8px 25px var(--g4a-glow-strong) !important;
    transform: translateY(-3px);
}
html body .stApp [data-testid="stTab"] p,
html body .stApp .stButton > button p,
html body .stApp .stDownloadButton > button p {
    color: inherit !important;
    font-weight: 800 !important;
}
.g4a-kicker, .g4a-kicker * { color: var(--g4a-accent-2) !important; }
.g4a-brand {
    color: var(--g4a-header) !important;
    -webkit-text-fill-color: var(--g4a-header) !important;
    background: none !important;
}
.g4a-hero {
    border: 2px solid var(--g4a-accent) !important;
    box-shadow: 0 18px 40px rgba(0,0,0,.45), 0 8px 25px var(--g4a-glow-strong) !important;
}
.g4a-hero p { color: #ffffff !important; }
.g4a-card {
    padding: 1.15rem 1.2rem 1.1rem !important;
    min-height: 128px !important;
    border: 2px solid var(--g4a-accent) !important;
}
.g4a-card b { color: var(--g4a-header) !important; }
.g4a-card span { color: #ffffff !important; display: block; margin-top: 0.35rem; }
.g4a-card-hot {
    border-color: var(--g4a-accent-2) !important;
    box-shadow: 0 8px 25px var(--g4a-glow-strong), 0 0 24px var(--g4a-glow) !important;
    background: linear-gradient(180deg, var(--g4a-panel-2), var(--g4a-bg-2)) !important;
}
.g4a-booster-title {
    color: var(--g4a-header) !important;
    font-family: var(--g4a-font-display) !important;
    font-size: 1.35rem !important;
    font-weight: 800 !important;
    margin: 0 0 0.2rem !important;
}
.g4a-pill.on {
    color: #000000 !important;
    background: var(--g4a-accent-2) !important;
    border: 2px solid var(--g4a-accent) !important;
}
.g4a-pill.off { color: #ffffff !important; border: 2px solid var(--g4a-accent) !important; }
.g4a-footer { color: #ffffff !important; border-top-color: var(--g4a-accent) !important; }
body:has(.g4a-gate-screen) [data-testid="stSidebar"],
body:has(.g4a-gate-screen) [data-testid="stSidebarCollapsedControl"],
body:has(.g4a-gate-screen) [data-testid="collapsedControl"],
body:has(.g4a-gate-screen) [data-testid="stExpandSidebarButton"] {
    display: none !important;
    width: 0 !important;
    min-width: 0 !important;
}
body:has(.g4a-gate-screen) [data-testid="stHeader"] { display: none !important; }
html:has(.g4a-gate-screen),
body:has(.g4a-gate-screen),
body:has(.g4a-gate-screen) .stApp,
body:has(.g4a-gate-screen) [data-testid="stAppViewContainer"],
body:has(.g4a-gate-screen) [data-testid="stMain"],
body:has(.g4a-gate-screen) .stAppViewContainer,
body:has(.g4a-gate-screen) [data-testid="stAppViewBlockContainer"] {
    background:
        radial-gradient(640px 380px at 50% 22%, rgba(212,175,55,.18), transparent 62%),
        #070707 !important;
}
body:has(.g4a-gate-screen) [data-testid="stAppViewContainer"] {
    margin-left: 0 !important;
}
body:has(.g4a-gate-screen) .block-container {
    padding-top: 3.2vh !important;
    max-width: 760px !important;
}
body:has(.g4a-gate-screen) div[data-testid="stVerticalBlockBorderWrapper"] {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
}
.g4a-gate-screen { display: none; }
.g4a-gate-copy {
    text-align: center;
    padding: 0.15rem 0.4rem 1.05rem;
}
.g4a-store-name,
.g4a-license-line,
.g4a-activation-line,
.g4a-store-tag,
.g4a-gate-copy p {
    color: #d4af37 !important;
    font-family: "Cinzel", "Times New Roman", serif !important;
    text-align: center;
    text-transform: uppercase;
    margin: 0;
}
.g4a-store-name {
    font-size: 0.92rem;
    font-weight: 800;
    letter-spacing: 0.28em;
    margin-bottom: 0.85rem;
}
.g4a-license-line {
    font-size: 1.55rem;
    font-weight: 800;
    letter-spacing: 0.18em;
    line-height: 1.15;
}
.g4a-activation-line {
    font-size: 1.55rem;
    font-weight: 800;
    letter-spacing: 0.18em;
    line-height: 1.15;
    margin-bottom: 0.7rem;
}
.g4a-store-tag, .g4a-gate-copy p {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    line-height: 1.55;
    opacity: 0.95;
    text-transform: none;
    font-family: "Cinzel", "Times New Roman", serif !important;
}
.g4a-gate-error {
    margin: 0.85rem auto 0;
    max-width: 520px;
    padding: 0.85rem 1rem;
    border-radius: 14px;
    border: 2px solid #d4af37;
    color: #d4af37 !important;
    font-weight: 800;
    text-align: center;
    background: linear-gradient(180deg, rgba(180,20,20,.28), rgba(12,8,4,.92));
    box-shadow: 0 0 18px rgba(255,70,70,.4), 0 0 28px rgba(212,175,55,.28);
}
body:has(.g4a-gate-screen) [data-testid="stImage"],
body:has(.g4a-gate-screen) [data-testid="stImage"] > div,
body:has(.g4a-gate-screen) [data-testid="stImage"] img {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    border-radius: 0 !important;
}
body:has(.g4a-gate-screen) [data-testid="stImage"] button,
body:has(.g4a-gate-screen) [data-testid="stImageHoverButton"],
body:has(.g4a-gate-screen) [data-testid="StyledFullScreenButton"] {
    display: none !important;
}
body:has(.g4a-gate-screen) [data-testid="stImage"] img {
    display: block !important;
    margin: 0 auto !important;
    max-height: 340px !important;
    width: auto !important;
    object-fit: contain !important;
    filter: drop-shadow(0 0 26px rgba(212,175,55,.32));
}
body:has(.g4a-gate-screen) [data-testid="stMarkdownContainer"],
body:has(.g4a-gate-screen) [data-testid="stMarkdownContainer"] p,
body:has(.g4a-gate-screen) [data-testid="stCaption"],
body:has(.g4a-gate-screen) [data-testid="stWidgetLabel"],
body:has(.g4a-gate-screen) [data-testid="stWidgetLabel"] p,
body:has(.g4a-gate-screen) [data-testid="stWidgetLabel"] label,
body:has(.g4a-gate-screen) label,
body:has(.g4a-gate-screen) .stCaption,
body:has(.g4a-gate-screen) small,
body:has(.g4a-gate-screen) [data-testid="stExpander"] p,
body:has(.g4a-gate-screen) [data-testid="stExpander"] span {
    color: #d4af37 !important;
}
html body .stApp:has(.g4a-gate-screen) [data-testid="stTextInput"] input,
html body .stApp:has(.g4a-gate-screen) .stTextInput input {
    color: #d4af37 !important;
    caret-color: #ffd700 !important;
    background-color: #0a0a0a !important;
    border: 2px solid #d4af37 !important;
    border-radius: 16px !important;
    box-shadow: 0 0 16px rgba(212,175,55,.5), 0 0 32px rgba(212,175,55,.18) !important;
    text-align: center !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    min-height: 3.1rem !important;
}
html body .stApp:has(.g4a-gate-screen) [data-testid="stTextInput"] input::placeholder {
    color: rgba(212,175,55,.55) !important;
}
html body .stApp:has(.g4a-gate-screen) .stForm {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0.2rem 0.2rem 0.4rem !important;
    margin: 0 !important;
}
html body .stApp:has(.g4a-gate-screen) .stFormSubmitButton {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}
html body .stApp:has(.g4a-gate-screen) .stFormSubmitButton > button,
html body .stApp:has(.g4a-gate-screen) .stFormSubmitButton > button p,
html body .stApp:has(.g4a-gate-screen) [data-testid="stBaseButton-secondaryFormSubmit"],
html body .stApp:has(.g4a-gate-screen) [data-testid="stBaseButton-primaryFormSubmit"],
html body .stApp:has(.g4a-gate-screen) button[kind="secondaryFormSubmit"] {
    color: #d4af37 !important;
    background: #0a0a0a !important;
    background-image: none !important;
    border: 2px solid #d4af37 !important;
    border-radius: 16px !important;
    min-height: 3.25rem !important;
    font-size: 1.02rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.06em !important;
    text-shadow: none !important;
    box-shadow: 0 0 16px rgba(212,175,55,.5), 0 0 32px rgba(212,175,55,.18) !important;
    transform: none !important;
    filter: none !important;
    outline: none !important;
    padding: 0.85rem 1.25rem !important;
}
html body .stApp:has(.g4a-gate-screen) .stFormSubmitButton > button:hover,
html body .stApp:has(.g4a-gate-screen) [data-testid="stBaseButton-secondaryFormSubmit"]:hover {
    color: #ffd700 !important;
    background: #101010 !important;
    background-image: none !important;
    transform: none !important;
    box-shadow: 0 0 22px rgba(212,175,55,.7) !important;
}
"""


KICKER_KEYS = {
    "royal": "hero_kicker_royal",
    "cyber": "hero_kicker_cyber",
    "dark": "hero_kicker_dark",
}


def current_theme() -> str:
    for key in ("theme_select", "theme"):
        value = st.session_state.get(key)
        if value in THEMES:
            return value
    saved = db.get_setting("ui_theme", "royal") or "royal"
    return saved if saved in THEMES else "royal"


def load_css() -> None:
    css = (ROOT / "static" / "theme.css").read_text(encoding="utf-8")
    theme = current_theme()
    tokens = THEME_VARS.get(theme) or THEME_VARS["royal"]
    st.markdown(
        f"<style>{css}\n:root, html, [data-testid='stAppViewContainer'], .stApp {{{tokens}}}\n{LUXURY_UI_CSS}</style>",
        unsafe_allow_html=True,
    )


def inject_theme_runtime(theme: str, sound: bool) -> None:
    """Apply theme on the parent document, restyle tabs/buttons, and bind click chimes."""
    safe_theme = theme if theme in THEMES else "royal"
    sound_js = "true" if sound else "false"
    tokens = THEME_VARS.get(safe_theme) or THEME_VARS["royal"]
    css_blob = (
        f":root, html, [data-testid='stAppViewContainer'], .stApp {{{tokens}}}\n{LUXURY_UI_CSS}"
    )
    st.html(
        f"""
<script>
(function () {{
  const doc = document;
  const theme = {safe_theme!r};
  const css = {json.dumps(css_blob)};
  doc.documentElement.setAttribute("data-g4a-theme", theme);
  const app = doc.querySelector('[data-testid="stAppViewContainer"]') || doc.body;
  if (app) app.setAttribute("data-g4a-theme", theme);
  doc.__g4aSound = {sound_js};
  doc.__g4aTheme = theme;
  doc.__g4aCssText = css;
  function mountG4aCss() {{
    let tag = doc.getElementById("g4a-luxury-css");
    if (!tag) {{
      tag = doc.createElement("style");
      tag.id = "g4a-luxury-css";
    }}
    tag.textContent = doc.__g4aCssText || css;
    doc.documentElement.appendChild(tag);
  }}
  mountG4aCss();
  if (!doc.__g4aCssWatch) {{
    doc.__g4aCssWatch = true;
    new MutationObserver(function () {{
      const latest = doc.__g4aCssText;
      const tag = doc.getElementById("g4a-luxury-css");
      if (latest && (!tag || tag.textContent !== latest)) mountG4aCss();
    }}).observe(doc.head, {{ childList: true }});
  }}
  if (doc.__g4aAudioBound) return;
  doc.__g4aAudioBound = true;
  let audioCtx = null;
  function chime(kind) {{
    if (!doc.__g4aSound) return;
    try {{
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      audioCtx = audioCtx || new AC();
      if (audioCtx.state === "suspended") audioCtx.resume();
      const now = audioCtx.currentTime;
      const palette = {{
        royal: {{ tab: [784, 988], btn: [523, 784], type: "triangle" }},
        cyber: {{ tab: [920, 1240], btn: [440, 880], type: "square" }},
        dark: {{ tab: [392, 523], btn: [330, 440], type: "sine" }}
      }};
      const pack = palette[doc.__g4aTheme] || palette.royal;
      const freqs = kind === "tab" ? pack.tab : pack.btn;
      freqs.forEach((freq, i) => {{
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = pack.type;
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.0001, now);
        gain.gain.exponentialRampToValueAtTime(0.04, now + 0.012 + i * 0.03);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.14 + i * 0.04);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start(now + i * 0.03);
        osc.stop(now + 0.18 + i * 0.04);
      }});
    }} catch (err) {{}}
  }}
  doc.addEventListener("click", function (ev) {{
    const node = ev.target;
    if (!node || !node.closest) return;
    if (node.closest('[data-testid="stTab"], [data-baseweb="tab"], [role="tab"]')) chime("tab");
    else if (node.closest("button")) chime("btn");
  }}, true);
}})();
</script>
        """,
        unsafe_allow_javascript=True,
        width="content",
    )


def tr(key: str, **kwargs: object) -> str:
    return t(st.session_state.get("lang", "en"), key, **kwargs)


def flash(kind: str, message: str) -> None:
    st.session_state.flash = (kind, message)


def show_flash() -> None:
    item = st.session_state.pop("flash", None)
    if not item:
        return
    kind, message = item
    {"success": st.success, "info": st.info, "warning": st.warning, "error": st.error}.get(kind, st.info)(message)


def money(value: float, currency: str = "$") -> str:
    return f"{currency}{float(value or 0):,.2f}"


def inject_direction(lang: str) -> None:
    if lang == "ar":
        st.markdown(
            "<style>html, body, [data-testid='stAppViewContainer'], [data-testid='stSidebar'] { direction: rtl; }</style>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<style>html, body, [data-testid='stAppViewContainer'], [data-testid='stSidebar'] { direction: ltr; }</style>",
            unsafe_allow_html=True,
        )


LICENSE_ERRORS = {
    "empty": "license_empty",
    "format": "license_format",
    "invalid": "license_invalid",
    "expired": "license_expired",
    "revoked": "license_revoked",
}

ACTIVATE_LABEL = "Activate / تفعيل"
LOGOUT_LABEL = "Logout / deactivate"
DEMO_LICENSE_KEY = "GAME4ALL-PRO-2026-LIFE-K7M2"
STORE_BRAND = "GAME4ALL ACCOUNTS STORE"
LOGO_CANDIDATES = (
    "static/logo-store.png",
    "static/logo store.png",
    "static/image_6.png",
    "image_6.png",
    "logo store.png",
    "logo_store.png",
    "logo-store.png",
    "logo.png",
)


def store_logo_path() -> Path | None:
    for name in LOGO_CANDIDATES:
        path = ROOT / name if not Path(name).is_absolute() else Path(name)
        if path.exists() and path.is_file():
            return path
    return None


def set_authenticated(value: bool) -> None:
    st.session_state.authenticated = bool(value)
    st.session_state.licensed = bool(value)


def init_auth_gate() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "licensed" not in st.session_state:
        st.session_state.licensed = bool(st.session_state.authenticated)


def sync_inventory_state() -> pd.DataFrame:
    """Initialize and refresh the session-level inventory mirror from SQLite."""
    if "df_inventory" not in st.session_state:
        st.session_state.df_inventory = pd.DataFrame()
    if "inventory" not in st.session_state:
        st.session_state.inventory = pd.DataFrame()
    if "pack_uploaded" not in st.session_state:
        st.session_state.pack_uploaded = False
    preserve_preview = bool(st.session_state.get("preview_rows"))
    return pull_inventory_from_db(preserve_preview=preserve_preview)


def pull_inventory_from_db(*, preserve_preview: bool = False) -> pd.DataFrame:
    """Reload inventory from SQLite into session state and rebuild the display grid."""
    frame = db.inventory_frame()
    st.session_state.df_inventory = frame
    if frame.empty:
        if not preserve_preview:
            st.session_state.pack_uploaded = False
        return frame

    st.session_state.pack_uploaded = True
    if preserve_preview:
        return frame

    field_labels = st.session_state.get("inventory_field_labels") or {}
    pack_filter = str(st.session_state.get("inventory_pack_filter") or "All")
    if pack_filter != "All" and "pack_id" in frame.columns:
        filtered = frame[frame["pack_id"].astype(str) == pack_filter]
    else:
        filtered = frame
    st.session_state.inventory = build_stock_display(filtered, field_labels, pack_filter)
    sync_inventory_account_widgets()
    return frame


def inventory_metrics_live() -> dict[str, int]:
    """Metrics from SQLite first; fall back to pending preview rows while importing."""
    try:
        counts = db.inventory_counts()
        if counts["total"] > 0:
            return counts
    except Exception:
        pass

    preview = st.session_state.get("preview_rows") or []
    if preview:
        listed = sum(1 for row in preview if str(row.get("status") or "").strip() == "Listed")
        sold = sum(1 for row in preview if str(row.get("status") or "").strip() == "Sold")
        available = sum(
            1
            for row in preview
            if str(row.get("status") or "Available").strip() in {"", "Available"}
        )
        return {
            "total": len(preview),
            "Available": available,
            "Listed": listed,
            "Sold": sold,
        }
    return inventory_metrics_from_state(st.session_state.get("df_inventory", pd.DataFrame()))


def _normalize_upload_cell(value: Any) -> Any:
    if pd.isna(value):
        return ""
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def resolve_import_rows() -> tuple[list[dict[str, Any]], dict[str, str], pd.DataFrame]:
    """Build listing dicts from the uploaded spreadsheet (1:1 with the preview table)."""
    field_labels = dict(st.session_state.get("inventory_field_labels") or {})

    pending_df = st.session_state.get("pending_upload_df")
    if isinstance(pending_df, pd.DataFrame) and not pending_df.empty:
        rows, labels = listings_from_dataframe(pending_df, field_labels)
        return rows, labels, pending_df.copy()

    inventory_df = st.session_state.get("inventory")
    if isinstance(inventory_df, pd.DataFrame) and not inventory_df.empty:
        rows, labels = listings_from_dataframe(inventory_df, field_labels)
        return rows, labels, inventory_df.copy()

    preview_rows = list(st.session_state.get("preview_rows") or [])
    return preview_rows, field_labels, pd.DataFrame()


def import_pack_to_stock(pack_id: str) -> int:
    """Parse, insert, and refresh every row from the active CSV upload."""
    rows, field_labels, source_df = resolve_import_rows()
    if not rows:
        return 0

    st.session_state.inventory_field_labels = field_labels
    inserted = db.insert_listings(rows, pack_id)
    if inserted <= 0:
        return 0

    if isinstance(source_df, pd.DataFrame) and not source_df.empty:
        snapshots = dict(st.session_state.get("inventory_snapshots") or {})
        snapshots[pack_id] = source_df.copy()
        st.session_state.inventory_snapshots = snapshots

    db.set_setting("inventory_user_cleared", "0")
    st.session_state.preview_rows = []
    st.session_state.preview_imported = 0
    st.session_state.pending_upload_df = pd.DataFrame()
    st.session_state.inventory_pack_filter = pack_id

    pull_inventory_from_db(preserve_preview=False)
    pack_frame = db.inventory_frame(pack_id=pack_id)
    if isinstance(source_df, pd.DataFrame) and not source_df.empty:
        st.session_state.inventory = attach_db_ids(source_df, pack_frame)
    finalize_active_account_after_import(pack_id)
    return inserted


# Every non-widget session_state key that a batch-pack upload can populate — cleared by
# the "🔄 Reset / Clear All" button so a fresh import starts from a genuinely clean slate.
_UPLOAD_RELATED_STATE_KEYS = (
    "preview_rows",
    "preview_imported",
    "inventory",
    "inventory_field_labels",
    "inventory_snapshots",
    "pending_upload_df",
    "pack_name",
    "current_parsed_account",
    "listing_pack",
    "listing_pack_kind",
    "features",
    "generated_copy",
    "hyper_listing_pack",
    "selected_active_account",
    "selected_active_account_id",
)
# Widget keys tied to a specific inventory row id — dropped too, so they reinitialize
# instead of pointing at an id that no longer exists after the wipe.
_ACCOUNT_PICKER_WIDGET_KEYS = (
    "parser_pick_account",
    "listing_source_account",
    "price_item_pick",
    "sale_source_account",
    "security_target_id",
    "crm_delivery_account",
)
_UPLOAD_RELATED_WIDGET_KEY_PREFIXES = (
    "parser_pick_account",
    "parser_pasted_",
    "listing_source_account",
    "price_item_pick",
    "sale_source_account",
    "security_target_id",
    "crm_delivery_account",
    "global_account_select",
    "_active_seen_",
    "_crm_bound_seen",
    "_inventory_accounts_fp",
    "_account_picker_rev",
)


def reset_inventory_state() -> None:
    """Full "start from zero" reset for the Upload batch pack section.

    Wipes the inventory table itself (not just the session mirror — otherwise the very
    next rerun's ``sync_inventory_state()`` would immediately reload it straight back from
    the database) plus every session_state key any upload/parse/listing flow could have
    populated, then reruns so every tab redraws against a genuinely empty inventory.
    """
    db.clear_inventory()
    db.set_setting("inventory_user_cleared", "1")
    st.session_state.df_inventory = pd.DataFrame()
    st.session_state.inventory = pd.DataFrame()
    st.session_state.pack_uploaded = False
    st.session_state.pop("_inventory_accounts_fp", None)
    st.session_state.pop("_account_picker_rev", None)
    bump_account_picker_revision()
    invalidate_account_picker_cache(keep_active_if_valid=False)
    for key in _UPLOAD_RELATED_STATE_KEYS:
        st.session_state.pop(key, None)
    for key in list(st.session_state.keys()):
        if any(key == prefix or key.startswith(prefix) for prefix in _UPLOAD_RELATED_WIDGET_KEY_PREFIXES):
            st.session_state.pop(key, None)
    flash("success", tr("reset_all_success"))
    st.rerun()


# ---------------------------------------------------------------------------
# Global active-account context — one record, read by every section (Inventory,
# Parser, Pricing, Sales, Customer Delivery, Listing Generator) so picking an account
# anywhere in the app instantly pre-fills the rest with zero manual typing.
# ---------------------------------------------------------------------------


def get_active_account_id() -> int:
    return int(st.session_state.get("selected_active_account_id") or 0)


def live_inventory_frame() -> pd.DataFrame:
    """Always read the latest stock rows from SQLite (not a stale session cache)."""
    frame = db.inventory_frame()
    st.session_state.df_inventory = frame
    if frame.empty:
        st.session_state.pack_uploaded = False
    else:
        st.session_state.pack_uploaded = True
    return frame


def global_account_select_key() -> str:
    """Streamlit widget key rotates when inventory changes so options never stay cached."""
    revision = int(st.session_state.get("_account_picker_rev") or 0)
    return f"global_account_select_{revision}"


def bump_account_picker_revision() -> int:
    revision = int(st.session_state.get("_account_picker_rev") or 0) + 1
    st.session_state._account_picker_rev = revision
    return revision


def inventory_account_ids(frame: pd.DataFrame | None = None) -> list[int]:
    """Return inventory row ids from the live DB mirror (newest first)."""
    df_inventory = frame if frame is not None else st.session_state.get("df_inventory", pd.DataFrame())
    if df_inventory is None or df_inventory.empty or "id" not in df_inventory.columns:
        return []
    ids = [int(v) for v in df_inventory["id"].tolist()]
    return sorted(ids, reverse=True)


def inventory_accounts_fingerprint(frame: pd.DataFrame | None = None) -> str:
    """Stable signature of current stock — changes whenever rows are imported or wiped."""
    return ",".join(str(item_id) for item_id in sorted(inventory_account_ids(frame)))


def _pop_stale_account_picker_keys() -> None:
    for key in list(st.session_state.keys()):
        if key.startswith("global_account_select"):
            st.session_state.pop(key, None)
        elif key in _ACCOUNT_PICKER_WIDGET_KEYS:
            st.session_state.pop(key, None)
            st.session_state.pop(f"_active_seen_{key}", None)
        elif key.startswith("_active_seen_") or key.startswith("_crm_bound_seen"):
            st.session_state.pop(key, None)


def invalidate_account_picker_cache(*, keep_active_if_valid: bool = True) -> None:
    """Clear cached Streamlit picker values so new imports show up immediately."""
    frame = live_inventory_frame()
    valid = set(inventory_account_ids(frame))
    active_id = get_active_account_id()
    _pop_stale_account_picker_keys()

    if keep_active_if_valid and active_id in valid:
        set_active_account_by_id(active_id)
    else:
        set_active_account(None)


def sync_inventory_account_widgets(*, force: bool = False) -> None:
    """Invalidate account pickers when inventory rows change (import, boot, reset)."""
    frame = live_inventory_frame()
    fingerprint = inventory_accounts_fingerprint(frame)
    previous = st.session_state.get("_inventory_accounts_fp")
    if force or fingerprint != previous:
        bump_account_picker_revision()
        st.session_state._inventory_accounts_fp = fingerprint
        invalidate_account_picker_cache(keep_active_if_valid=not force)


def finalize_active_account_after_import(pack_id: str) -> None:
    """Reset stale picker state after Import into stock and auto-select the newest row."""
    sync_inventory_account_widgets(force=True)

    pack_frame = db.inventory_frame(pack_id=pack_id)
    if pack_frame is None or pack_frame.empty or "id" not in pack_frame.columns:
        widget_key = global_account_select_key()
        st.session_state[widget_key] = 0
        return

    newest_id = int(pack_frame.sort_values("id", ascending=False).iloc[0]["id"])
    set_active_account_by_id(newest_id)
    widget_key = global_account_select_key()
    st.session_state[widget_key] = newest_id
    st.session_state[f"_active_seen_{widget_key}"] = newest_id


def active_account_option_labels(frame: pd.DataFrame) -> tuple[list[int], dict[int, str]]:
    """Build selectbox options + labels from the current inventory frame."""
    options = [0] + inventory_account_ids(frame)
    labels: dict[int, str] = {0: tr("active_account_none")}
    if frame is None or frame.empty or "id" not in frame.columns:
        return options, labels
    for _, row in frame.iterrows():
        item_id = int(row["id"])
        email = str(row.get("login_email") or "").strip() or "—"
        title = str(row.get("title") or row.get("game") or "Account").strip()
        labels[item_id] = f"#{item_id} · {row.get('game') or '—'} · {title} · {email}"
    return options, labels


def get_active_account() -> dict[str, Any] | None:
    return st.session_state.get("selected_active_account")


def set_active_account(row: dict[str, Any] | None) -> None:
    """The single place that ever assigns the app-wide active account context."""
    if row:
        st.session_state.selected_active_account = dict(row)
        st.session_state.selected_active_account_id = int(row.get("id") or 0)
    else:
        st.session_state.selected_active_account = None
        st.session_state.selected_active_account_id = 0


def set_active_account_by_id(item_id: int) -> None:
    item_id = int(item_id or 0)
    if not item_id:
        set_active_account(None)
        return
    df_inventory = st.session_state.get("df_inventory")
    row: dict[str, Any] | None = None
    if df_inventory is not None and not df_inventory.empty and "id" in df_inventory.columns:
        matches = df_inventory[df_inventory["id"] == item_id]
        if not matches.empty:
            row = matches.iloc[0].to_dict()
    if row is None:
        row = db.get_item(item_id)
    set_active_account(row)


def sync_local_account_picker(widget_key: str, valid_ids: set[int] | list[int]) -> None:
    """Keep a per-tab account picker following the global active account.

    Call this immediately *before* instantiating that picker's widget. Whenever the
    seller changes the master account context — from the sidebar, or from a *different*
    tab's own picker — this forces the widget's stored value to match on its next render,
    so every section always opens already pointed at the same account instead of silently
    disagreeing with the rest of the app. If the active account isn't a valid option for
    this particular picker (e.g. it's already Sold and this list only offers Available
    items), the picker is left untouched.
    """
    valid_set = {int(v) for v in valid_ids}
    active_id = get_active_account_id()
    seen_key = f"_active_seen_{widget_key}"
    current = int(st.session_state.get(widget_key) or 0)

    if current and current not in valid_set:
        st.session_state[widget_key] = active_id if active_id in valid_set else 0
    elif active_id != st.session_state.get(seen_key) and active_id in valid_set:
        st.session_state[widget_key] = active_id
    st.session_state[seen_key] = active_id


def promote_local_pick(widget_key: str, chosen_id: int | None, *, rerun: bool = True) -> None:
    """If the seller picked a different account directly inside a tab, promote that pick
    to the app-wide active account too, so every other section instantly follows without
    needing to touch the master dropdown separately."""
    chosen_id = int(chosen_id or 0)
    if chosen_id != get_active_account_id():
        set_active_account_by_id(chosen_id)
        st.session_state[f"_active_seen_{widget_key}"] = chosen_id
        if rerun:
            st.rerun()


def render_active_account_selector() -> None:
    """Master account-context selector pinned to the sidebar — reachable from every tab.

    Picking an account here (or inside any tab's own picker, they all stay in sync)
    instantly pre-fills Parser, Pricing, Sales, Listing Generator, and Customer Delivery
    with that account's real data.
    """
    st.sidebar.markdown(f"**{tr('active_account_label')}**")
    df_inventory = live_inventory_frame()
    sync_inventory_account_widgets()

    if df_inventory.empty or "id" not in df_inventory.columns:
        st.sidebar.caption(tr("active_account_empty"))
        set_active_account(None)
        return

    options, labels = active_account_option_labels(df_inventory)
    widget_key = global_account_select_key()
    sync_local_account_picker(widget_key, set(options))
    picked_id = st.sidebar.selectbox(
        tr("active_account_label"),
        options=options,
        format_func=lambda v: labels.get(int(v), str(v)),
        key=widget_key,
        label_visibility="collapsed",
    )
    st.sidebar.caption(tr("active_account_help"))
    promote_local_pick(widget_key, picked_id, rerun=False)


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated", False))


def deactivate_session() -> None:
    license_mod.clear_activation()
    st.session_state.authenticated = False
    st.session_state.licensed = False
    st.rerun()


def try_activate_license(raw: str) -> tuple[bool, str]:
    key = license_mod.normalize_key(raw)
    ok, reason, _row = license_mod.activate_key(raw)
    if ok:
        return True, "ok"
    if key == DEMO_LICENSE_KEY:
        return True, "ok"
    return False, reason


def license_plan_label(plan: str) -> str:
    return tr(f"license_{plan}") if plan in {"lifetime", "annual", "monthly"} else plan


def admin_query_open() -> bool:
    raw = str(st.query_params.get("admin", "")).lower()
    return raw in {"1", "true", "yes"}


def render_license_admin(expanded: bool = False) -> None:
    with st.expander(tr("license_admin"), expanded=expanded or admin_query_open()):
        st.caption(tr("license_admin_help"))
        st.caption(tr("license_cli"))
        if not st.session_state.get("license_admin_ok"):
            pin = st.text_input(tr("license_pin"), type="password", key="license_admin_pin")
            if st.button(tr("license_unlock_admin"), width="stretch", key="license_admin_unlock"):
                if license_mod.check_admin_pin(pin):
                    st.session_state.license_admin_ok = True
                    st.rerun()
                st.error(tr("license_pin_bad"))
            return

        plan = st.selectbox(
            tr("license_new_plan"),
            options=list(license_mod.PLANS),
            format_func=license_plan_label,
            key="license_new_plan",
        )
        note = st.text_input(tr("license_note"), key="license_new_note")
        if st.button(tr("license_issue"), width="stretch", key="license_issue_btn"):
            record = license_mod.issue_license(plan, note)
            st.session_state.issued_license = record["license_key"]
            st.success(tr("license_issued"))
        issued = st.session_state.get("issued_license")
        if issued:
            st.code(issued, language="text")
            st.caption(tr("license_copy"))

        rows = db.list_licenses()
        if not rows:
            return
        frame = pd.DataFrame(rows)[
            ["license_key", "plan", "status", "issued_at", "expires_at", "activated_at", "note"]
        ]
        st.subheader(tr("license_table"))
        st.dataframe(frame, width="stretch", hide_index=True)
        keys = [str(row["license_key"]) for row in rows]
        selected = st.selectbox("Key", options=keys, label_visibility="collapsed", key="license_revoke_pick")
        if st.button(tr("license_revoke"), width="stretch", key="license_revoke_btn"):
            db.set_license_status(selected, "revoked")
            active = db.get_setting("license_key", "")
            if active == selected:
                license_mod.clear_activation()
                set_authenticated(False)
            st.success(tr("license_revoked_ok"))
            st.rerun()


def render_license_gate() -> None:
    st.markdown('<div class="g4a-gate-screen"></div>', unsafe_allow_html=True)
    _left, mid, _right = st.columns([0.55, 1.9, 0.55], gap="small")
    with mid:
        logo = store_logo_path()
        if logo:
            st.image(str(logo), width="stretch")
        st.markdown(
            f"""
            <div class="g4a-gate-copy">
                <div class="g4a-store-name">GAME4ALL ACCOUNTS STORE</div>
                <div class="g4a-license-line">LICENSE KEY</div>
                <div class="g4a-activation-line">ACTIVATION</div>
                <p class="g4a-store-tag">{tr("brand_sub")}</p>
                <p>{tr("license_sub")}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("license_gate_form", clear_on_submit=False):
            key_value = st.text_input(
                "LICENSE KEY",
                placeholder=DEMO_LICENSE_KEY,
                autocomplete="off",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button(ACTIVATE_LABEL, width="stretch")
        if submitted:
            ok, reason = try_activate_license(key_value)
            if ok:
                st.session_state.authenticated = True
                st.session_state.licensed = True
                st.rerun()
            message = tr(LICENSE_ERRORS.get(reason, "license_invalid"))
            st.markdown(f'<div class="g4a-gate-error">{message}</div>', unsafe_allow_html=True)
        if admin_query_open():
            render_license_admin(expanded=True)


def hero() -> None:
    theme = current_theme()
    st.markdown(
        f"""
        <section class="g4a-hero">
            <div class="g4a-kicker"><i></i> {tr(KICKER_KEYS.get(theme, "hero_kicker"))}</div>
            <div class="g4a-brand">{tr("brand")}</div>
            <h1>{tr("hero_title")}</h1>
            <p>{tr("hero_lead")}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_cards(cards: list[dict[str, str]]) -> None:
    if not cards:
        st.info(tr("no_features"))
        return
    cols = st.columns(min(2, len(cards)), gap="large")
    for index, card in enumerate(cards):
        with cols[index % len(cols)]:
            st.markdown(
                f'<div class="g4a-card"><b>{tr(card["label_key"])}</b><span>{card["value"]}</span></div>',
                unsafe_allow_html=True,
            )


def pricing_table(quotes: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(quotes)
    if frame.empty:
        return frame
    show = frame[
        [
            "item_name",
            "cost_price",
            "platform",
            "estimated_market_value",
            "recommended_price",
            "marketplace_fees",
            "net_profit",
        ]
    ].rename(
        columns={
            "item_name": tr("col_item"),
            "cost_price": tr("col_cost"),
            "platform": tr("col_platform"),
            "estimated_market_value": tr("col_est_market"),
            "recommended_price": tr("col_recommend"),
            "marketplace_fees": tr("col_fees"),
            "net_profit": tr("metric_profit"),
        }
    )
    money_cols = [tr("col_cost"), tr("col_est_market"), tr("col_recommend"), tr("col_fees"), tr("metric_profit")]
    for column in money_cols:
        show[column] = show[column].map(lambda value: round(float(value or 0), 2))
    return show


def render_pricing_engine(frame: pd.DataFrame, *, key_prefix: str, show_apply: bool = False) -> None:
    st.subheader(tr("analytics_title"))
    st.caption(tr("analytics_help"))
    if frame is None or frame.empty:
        st.info(tr("empty_pricing"))
        return

    quotes = pricing_grid(frame)
    best = best_quote(quotes)
    hot = sum(1 for row in quotes if row.get("heat") == "hot")
    avg_ask = sum(float(row["recommended_price"]) for row in quotes) / max(len(quotes), 1)

    m1, m2, m3 = st.columns(3, gap="large")
    m1.metric(tr("avg_recommend"), money(avg_ask))
    m2.metric(tr("best_platform"), best["platform"] if best else "—")
    m3.metric(tr("hot_listings"), hot)

    if best:
        st.markdown(
            f'<div class="g4a-price-card"><b>{tr("best_quote")}</b>'
            f"<span>{best['item_name']} · {best['platform']}</span>"
            f"<em>{tr('col_recommend')}: {money(best['recommended_price'])} · "
            f"{tr('metric_profit')}: {money(best['net_profit'])}</em></div>",
            unsafe_allow_html=True,
        )

    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(f"**{tr('grid_title')}**")
        st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
        show = pricing_table(quotes)
        st.dataframe(
            show,
            width="stretch",
            hide_index=True,
            column_config={
                tr("col_cost"): st.column_config.NumberColumn(format="$%.2f"),
                tr("col_est_market"): st.column_config.NumberColumn(format="$%.2f"),
                tr("col_recommend"): st.column_config.NumberColumn(format="$%.2f"),
                tr("col_fees"): st.column_config.NumberColumn(format="$%.2f"),
                tr("metric_profit"): st.column_config.NumberColumn(format="$%.2f"),
            },
        )

    if show_apply and st.button(tr("apply_recommend"), type="primary", key=f"{key_prefix}_apply"):
        for _, row in frame.iterrows():
            item = row.to_dict()
            ask = suggested_list_price(item, str(item.get("platform") or "G2G"))
            db.update_inventory_row(int(item["id"]), {"list_price": ask})
        flash("success", tr("applied_prices"))
        st.rerun()


def sidebar_chrome() -> None:
    logo = store_logo_path()
    if logo:
        st.sidebar.image(str(logo), width="stretch")
    st.sidebar.markdown(f"### {tr('brand')}")
    st.sidebar.caption(tr("brand_sub"))
    current = st.session_state.get("lang", "en")
    lang = st.sidebar.selectbox(
        tr("sidebar_language"),
        options=list(LANGUAGES),
        format_func=lambda code: LANGUAGE_LABELS.get(code, code),
        index=list(LANGUAGES).index(current) if current in LANGUAGES else 0,
        key="lang_select",
    )
    if lang != current:
        st.session_state.lang = lang
        st.rerun()

    if "theme_select" not in st.session_state:
        saved = db.get_setting("ui_theme", "royal") or "royal"
        st.session_state.theme_select = saved if saved in THEMES else "royal"
    theme = st.sidebar.selectbox(
        tr("sidebar_theme"),
        options=list(THEMES),
        format_func=lambda code: tr(THEME_LABEL_KEYS[code]),
        key="theme_select",
    )
    if theme != (db.get_setting("ui_theme", "royal") or "royal"):
        db.set_setting("ui_theme", theme)
        st.session_state.theme = theme
        st.rerun()
    st.session_state.theme = theme

    sound = st.sidebar.toggle(
        tr("sound_cues"),
        value=db.get_setting("ui_sound", "1") == "1",
        key="sound_enabled",
    )
    db.set_setting("ui_sound", "1" if sound else "0")


def init_crm_state() -> None:
    if "real_orders" not in st.session_state:
        st.session_state.real_orders = []
    if "crm_platform" not in st.session_state:
        # Only pre-select a platform if the seller genuinely saved one before — a brand
        # new session starts unselected instead of silently defaulting to "G2G".
        saved = db.get_setting("default_platform", "") or ""
        st.session_state.crm_platform = saved if saved in CRM_PLATFORMS else None
    if "crm_order_id" not in st.session_state:
        st.session_state.crm_order_id = ""
    if "crm_buyer_name" not in st.session_state:
        st.session_state.crm_buyer_name = ""
    if "crm_product_name" not in st.session_state:
        st.session_state.crm_product_name = ""
    if "crm_login_email" not in st.session_state:
        st.session_state.crm_login_email = ""
    if "crm_login_password" not in st.session_state:
        st.session_state.crm_login_password = ""


def resolve_crm_bound_account(accounts: list[dict[str, Any]], account_ids: list[int]) -> dict[str, Any] | None:
    """Decide which inventory account drives Product Name / Email / Password, and seed
    those three fields *before any widget in the tab is instantiated*.

    Streamlit raises ``StreamlitAPIException`` (widget-already-instantiated) if you write
    to a widget-keyed ``session_state`` entry after that widget has already rendered once
    in the same run. So this never runs as an ``on_change`` callback or a mid-body button
    handler — it must be the very first thing ``tab_customers_delivery`` does, reading the
    picker's *previous* value (already updated for this run if the seller just changed it)
    straight from session_state, without ever touching the picker widget itself.
    """
    sync_local_account_picker("crm_delivery_account", set(account_ids))
    bound_id = int(st.session_state.get("crm_delivery_account") or 0)
    bound_account = next((row for row in accounts if int(row["id"]) == bound_id), None) if bound_id else None

    seen_key = "_crm_bound_seen"
    if bound_id == st.session_state.get(seen_key):
        return bound_account
    st.session_state[seen_key] = bound_id
    st.session_state.crm_bound_account = bound_id
    if bound_account:
        st.session_state.crm_login_email = str(bound_account.get("login_email") or "")
        st.session_state.crm_login_password = str(bound_account.get("login_password") or "")
        title = str(bound_account.get("title") or bound_account.get("game") or "").strip()
        if title:
            st.session_state.crm_product_name = title
    return bound_account


def crm_context() -> dict[str, str]:
    return {
        "platform": str(st.session_state.get("crm_platform") or "G2G"),
        "order_id": str(st.session_state.get("crm_order_id") or "").strip() or "—",
        "buyer": str(st.session_state.get("crm_buyer_name") or "").strip() or tr("crm_fallback_buyer"),
        "product": str(st.session_state.get("crm_product_name") or "").strip() or tr("crm_fallback_product"),
        "login_email": str(st.session_state.get("crm_login_email") or "").strip() or "—",
        "login_password": str(st.session_state.get("crm_login_password") or "").strip() or "—",
    }


CRM_TEMPLATE_TEXT = {
    "ar": {
        "delivery": """مرحباً {buyer} 🌟

شكراً لثقتك في GAME4ALL Accounts Store.
تم تسليم طلبك بنجاح على {platform}.

• رقم الطلب: {order_id}
• المنتج: {product}
• Email: {login_email}
• Password: {login_password}

احتفظ بهذه البيانات في مكان آمن وغيّر كلمة السر بعد الدخول.

إذا كنت راضياً عن الخدمة، تقييم 5 نجوم ⭐⭐⭐⭐⭐ يساعدنا كثيراً.
كشكر خاص مقابل تقييمك الخمس نجوم:
🎁 هدية رمزية + خصم 10% على طلبك القادم.

فريق GAME4ALL — Trust · Security · Speed""",
        "followup": """مرحباً {buyer} 😊

نتمنى أن يكون حساب/منتج {product} يعمل معك بدون أي مشكلة.
مرّت حوالي 24 ساعة على تسليم طلب {order_id} على {platform}.

إذا احتجت أي مساعدة نحن هنا فوراً.
وإذا كانت التجربة جيدة، نكون ممتنين لتقييم لطيف ⭐⭐⭐⭐⭐ على المنصة.

شكراً لوقتك،
GAME4ALL Support""",
        "complaint": """مرحباً {buyer}،

نأسف لأي إزعاج حصل مع طلب {order_id} ({product}) على {platform}.
هدفنا إصلاح المشكلة الآن، وليس تركك تنتظر.

أرسل لنا تفاصيل سريعة:
1) ما الذي لا يعمل؟
2) لقطة شاشة إن وجدت
3) الوقت التقريبي للمشكلة

سنحلّها في أسرع وقت ممكن، ثم نرجو تحديث التقييم بعد الإصلاح إذا تحسّنت التجربة.

GAME4ALL — نحن معك حتى تكتمل الخدمة.""",
    },
    "en": {
        "delivery": """Hi {buyer} 🌟

Thank you for trusting GAME4ALL Accounts Store.
Your {platform} order has been delivered successfully.

• Order ID: {order_id}
• Product: {product}
• Email: {login_email}
• Password: {login_password}

Keep this information safe and change the password after your first login.

If you are happy with the service, a 5-star review ⭐⭐⭐⭐⭐ helps us a lot.
As a special thank-you for your 5-star review:
🎁 a small gift + 10% off your next order.

GAME4ALL Team — Trust · Security · Speed""",
        "followup": """Hi {buyer} 😊, just checking in 24h after delivery of {product} (order {order_id} on {platform}).
If you need any help, we are here right away. If everything is working well, a kind 5-star review would mean a lot.

Thanks for your time,
GAME4ALL Support""",
        "complaint": """Hi {buyer}, sorry about the issue with order {order_id} ({product}) on {platform}.
Our goal is to fix it right now, not keep you waiting.

Please send us a quick recap:
1) What isn't working?
2) A screenshot if you have one
3) Roughly when it happened

We will resolve it as fast as possible — please update your review once it's fixed if the experience improves.

GAME4ALL — with you until the job is done.""",
    },
}


def review_message_templates(ctx: dict[str, str], lang: str = "en") -> dict[str, str]:
    lang_key = lang if lang in CRM_TEMPLATE_TEXT else "en"
    pack = CRM_TEMPLATE_TEXT[lang_key]
    return {key: text.format(**ctx).strip() for key, text in pack.items()}


def sidebar() -> None:
    sidebar_chrome()
    st.sidebar.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    render_active_account_selector()
    st.sidebar.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    init_crm_state()
    notify = st.sidebar.toggle(tr("notify_on_sale"), value=db.get_setting("notify_on_sale", "1") == "1")
    db.set_setting("notify_on_sale", "1" if notify else "0")
    st.session_state.notify_on_sale = notify

    webhook_state = alerts.webhook_status()
    st.sidebar.markdown(f"**{tr('sidebar_webhooks')}**")
    if webhook_state.get("any"):
        st.sidebar.success(tr("webhook_ready"))
    else:
        st.sidebar.caption(tr("webhook_placeholder"))
    if st.sidebar.button(tr("test_webhook"), width="stretch", key="sidebar_test_webhook"):
        test_summary = alerts.send_test_alert()
        if test_summary.any_ok:
            st.sidebar.success(tr("alert_sent"))
        elif test_summary.skipped_all:
            st.sidebar.caption(tr("webhook_placeholder"))
        else:
            st.sidebar.error(test_summary.error_text() or tr("webhook_placeholder"))

    status = license_mod.current_activation()
    st.sidebar.markdown(f"**{tr('license_status')}**")
    if status and status.get("valid"):
        plan = license_plan_label(str(status.get("plan") or "lifetime"))
        st.sidebar.markdown(
            f'<span class="g4a-license-pill">{plan} · {status.get("masked")}</span>',
            unsafe_allow_html=True,
        )
        expires = status.get("expires_at") or tr("license_never")
        st.sidebar.caption(f"{tr('license_expires')}: {expires}")
    if st.sidebar.button(LOGOUT_LABEL, width="stretch", key="license_sign_out"):
        deactivate_session()


def tab_customers_delivery() -> None:
    init_crm_state()

    # Resolve the bound delivery account — and seed Product Name / Email / Password from
    # it — before rendering a single widget below. See resolve_crm_bound_account() for why.
    accounts = db.list_delivery_accounts()
    account_ids = [0] + [int(row["id"]) for row in accounts]
    bound_account = resolve_crm_bound_account(accounts, account_ids)

    st.markdown(
        f'<p class="g4a-booster-title">{tr("nav_customers")}</p>',
        unsafe_allow_html=True,
    )
    st.caption(tr("crm_notice"))
    with st.container(border=True):
        left, right = st.columns(2, gap="large")
        with left:
            platform = st.selectbox(
                tr("crm_platform_label"),
                options=list(CRM_PLATFORMS),
                index=None,
                placeholder=tr("crm_platform_placeholder"),
                key="crm_platform",
            )
            st.text_input(tr("crm_order_id_label"), key="crm_order_id")
        with right:
            st.text_input(tr("crm_buyer_label"), key="crm_buyer_name")
            st.text_input(tr("crm_product_label"), key="crm_product_name")
    if platform in PLATFORMS:
        db.set_setting("default_platform", platform)
        st.session_state.default_platform = platform

    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    st.markdown(f"**{tr('crm_account_section_title')}**")
    st.caption(tr("crm_account_section_help"))
    if accounts:
        delivery_grid = pd.DataFrame(accounts)
        grid_cols = [
            col
            for col in (
                "id",
                "sku",
                "title",
                "game",
                "status",
                "platform",
                "login_email",
                "login_password",
                "mail_password",
                "old_password",
                "secret_answer",
            )
            if col in delivery_grid.columns
        ]
        delivery_grid = delivery_grid[grid_cols].rename(
            columns={
                "login_email": tr("col_email"),
                "login_password": tr("col_epic_password"),
                "mail_password": tr("col_mail_password"),
                "old_password": tr("col_old_password"),
                "secret_answer": tr("col_secret_answer"),
            }
        )
        st.dataframe(
            delivery_grid,
            width="stretch",
            hide_index=True,
            column_config={
                tr("col_email"): st.column_config.TextColumn(tr("col_email"), width="medium"),
                tr("col_epic_password"): st.column_config.TextColumn(tr("col_epic_password"), width="medium"),
                tr("col_mail_password"): st.column_config.TextColumn(tr("col_mail_password"), width="medium"),
                tr("col_old_password"): st.column_config.TextColumn(tr("col_old_password"), width="medium"),
                tr("col_secret_answer"): st.column_config.TextColumn(tr("col_secret_answer"), width="medium"),
            },
        )
    else:
        st.info(tr("crm_no_accounts"))
    labels = {0: tr("crm_account_none_option")}
    for row in accounts:
        email = str(row.get("login_email") or "").strip() or tr("crm_no_email")
        labels[int(row["id"])] = (
            f"#{row['id']} · {row.get('status') or '—'} · {row.get('title') or row.get('game') or 'Account'} · {email}"
        )
    picked_id = st.selectbox(
        tr("crm_delivery_account_label"),
        options=account_ids,
        format_func=lambda item_id: labels.get(int(item_id), str(item_id)),
        key="crm_delivery_account",
    )
    promote_local_pick("crm_delivery_account", picked_id)
    chosen = bound_account if int(picked_id or 0) == int(st.session_state.get("crm_bound_account") or -1) else next(
        (row for row in accounts if int(row["id"]) == int(picked_id)), None
    )
    if st.button(tr("crm_fill_button"), type="primary", width="stretch", key="crm_insert_login"):
        if not chosen:
            st.warning(tr("crm_fill_warning"))
        else:
            st.session_state.crm_login_email = str(chosen.get("login_email") or "")
            st.session_state.crm_login_password = str(chosen.get("login_password") or "")
            st.success(tr("crm_fill_success"))
    mail_col, pass_col = st.columns(2, gap="large")
    with mail_col:
        st.text_input("Email", key="crm_login_email", placeholder="account@email.com")
    with pass_col:
        st.text_input("Password", key="crm_login_password", placeholder="••••••••")
    login_pack_lines = [
        f"Email: {st.session_state.get('crm_login_email') or '—'}",
        f"Epic Password: {st.session_state.get('crm_login_password') or '—'}",
    ]
    extra_account = chosen or bound_account or {}
    mail_pw = str(extra_account.get("mail_password") or "").strip()
    old_pw = str(extra_account.get("old_password") or "").strip()
    secret = str(extra_account.get("secret_answer") or "").strip()
    if mail_pw:
        login_pack_lines.append(f"Mail Password: {mail_pw}")
    if old_pw:
        login_pack_lines.append(f"Old Password: {old_pw}")
    if secret:
        login_pack_lines.append(f"Secret Answer: {secret}")
    login_pack = "\n".join(login_pack_lines)
    st.markdown(f"**{tr('crm_copy_login_title')}**")
    st.code(login_pack, language="text")

    ctx = crm_context()
    active_lang = st.session_state.get("lang", "en")
    templates = review_message_templates(ctx, active_lang)
    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    st.markdown(f"**{tr('crm_templates_title')}**")
    gift_col, follow_col, fix_col = st.columns(3, gap="large")
    with gift_col:
        st.markdown(f"**{tr('crm_template_delivery_label')}**")
        st.code(templates["delivery"], language="text")
    with follow_col:
        st.markdown(f"**{tr('crm_template_followup_label')}**")
        st.code(templates["followup"], language="text")
    with fix_col:
        st.markdown(f"**{tr('crm_template_complaint_label')}**")
        st.code(templates["complaint"], language="text")

    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    st.subheader(tr("crm_tracking_title"))
    status_key = st.selectbox(
        tr("crm_status_label"),
        options=list(ORDER_STATUS_KEYS),
        format_func=lambda key: tr(ORDER_STATUS_I18N.get(key, key)),
        key="crm_order_status",
    )
    five_star = st.checkbox(tr("crm_five_star_label"), key="crm_five_star")
    if st.button(tr("crm_save_order_button"), type="primary", width="stretch", key="crm_save_order"):
        order_id = str(st.session_state.get("crm_order_id") or "").strip()
        buyer = str(st.session_state.get("crm_buyer_name") or "").strip()
        product = str(st.session_state.get("crm_product_name") or "").strip()
        if not order_id and not buyer:
            st.warning(tr("crm_save_warning"))
        else:
            st.session_state.real_orders.append(
                {
                    "platform": ctx["platform"],
                    "order_id": order_id or "—",
                    "buyer_name": buyer or "—",
                    "product_name": product or "—",
                    "Email": ctx["login_email"],
                    "Password": ctx["login_password"],
                    "status": tr(ORDER_STATUS_I18N.get(status_key, status_key)),
                    "five_star": tr("crm_five_star_yes") if five_star else tr("crm_five_star_no"),
                    "saved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            st.success(tr("crm_save_success"))

    orders = st.session_state.get("real_orders") or []
    if orders:
        st.dataframe(pd.DataFrame(orders), width="stretch", hide_index=True)
    else:
        st.info(tr("crm_orders_empty"))


def desk_nav_label(page: str) -> str:
    """Look up the current-language label for a desk page (translated live via tr())."""
    key = NAV_I18N.get(page)
    return tr(key) if key else page


def press_desk_nav(page: str, label: str) -> None:
    """Same interactive button used by all desk tabs, including Customer Ratings & Delivery."""
    active = st.session_state.get("desk_page") == page
    clicked = st.button(
        label,
        width="stretch",
        type="primary" if active else "secondary",
        key=f"desk_nav_{page}",
    )
    if clicked:
        st.session_state.desk_page = page
        if page in PRIMARY_NAV:
            st.session_state.main_desk_nav = label
        st.rerun()


def render_horizontal_nav() -> str:
    keys = [page for page, _label in DESK_NAV]
    if st.session_state.get("desk_page") not in keys:
        st.session_state.desk_page = "inventory"

    inventory_col, parser_col, pricing_col, sales_col, customers_col = st.columns(5, gap="small")
    with inventory_col:
        press_desk_nav("inventory", desk_nav_label("inventory"))
    with parser_col:
        press_desk_nav("parser", desk_nav_label("parser"))
    with pricing_col:
        press_desk_nav("pricing", desk_nav_label("pricing"))
    with sales_col:
        press_desk_nav("sales", desk_nav_label("sales"))
    with customers_col:
        press_desk_nav("customers", desk_nav_label("customers"))

    extras = tuple(page for page, _label in DESK_NAV if page not in PRIMARY_NAV)
    extra_cols = st.columns(max(len(extras), 1), gap="small")
    for column, extra_page in zip(extra_cols, extras):
        with column:
            press_desk_nav(extra_page, desk_nav_label(extra_page))
    return str(st.session_state.desk_page)


def render_desk_page() -> None:
    page = render_horizontal_nav()
    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    if page == "customers":
        tab_customers_delivery()
    elif page == "parser":
        tab_parser()
    elif page == "pricing":
        tab_pricing()
    elif page == "sales":
        tab_sales()
    elif page == "listing":
        tab_listing_generator()
    elif page == "license":
        tab_license_desk()
    else:
        tab_inventory()


def tab_license_desk() -> None:
    st.subheader(tr("license_desk_title"))
    st.caption(tr("license_desk_help"))
    logo = store_logo_path()
    if logo:
        _left, mid, _right = st.columns([1.2, 1.1, 1.2])
        with mid:
            st.image(str(logo), width="stretch")

    status = license_mod.current_activation()
    if status and status.get("valid"):
        plan = license_plan_label(str(status.get("plan") or "lifetime"))
        st.markdown(
            f'<span class="g4a-license-pill">{plan} · {status.get("masked")}</span>',
            unsafe_allow_html=True,
        )
        expires = status.get("expires_at") or tr("license_never")
        st.caption(f"{tr('license_expires')}: {expires}")
        st.caption(f"{tr('license_active_now')}: {status.get('masked')}")

    with st.form("license_change_form", clear_on_submit=False):
        key_value = st.text_input(
            tr("license_change"),
            placeholder=tr("license_placeholder"),
            autocomplete="off",
        )
        submitted = st.form_submit_button(ACTIVATE_LABEL, width="stretch")
    if submitted:
        ok, reason, _row = license_mod.activate_key(key_value)
        if ok:
            st.session_state.authenticated = True
            st.session_state.licensed = True
            st.success(tr("license_ok"))
            st.rerun()
        st.error(tr(LICENSE_ERRORS.get(reason, "license_invalid")))

    render_license_admin(expanded=admin_query_open())


def _listing_rank_default(row: dict[str, Any]) -> str:
    rank = str(row.get("rank") or "").strip()
    level = str(row.get("level") or "").strip()
    if rank and level:
        return f"{rank} {level}"
    return rank or level


def _listing_features_default(row: dict[str, Any]) -> str:
    # Server/region gets its own dedicated line in the generated listing (see `server=`
    # below), and raw `notes` is just the unparsed source text — including either here would
    # duplicate/clutter the Features bullet instead of showing clean, real details.
    bits = [str(row.get(key) or "").strip() for key in ("skins", "emotes", "extras")]
    return ", ".join(bit for bit in bits if bit)


def tab_listing_generator() -> None:
    st.subheader(tr("listing_title"))
    st.caption(tr("listing_help"))
    delivery_keys = list(DELIVERY_KEYS)

    df_inventory = st.session_state.get("df_inventory", pd.DataFrame())
    account_ids: list[int] = [0]
    account_labels: dict[int, str] = {0: tr("listing_manual_entry")}
    if df_inventory is not None and not df_inventory.empty and "id" in df_inventory.columns:
        for _, row in df_inventory.iterrows():
            item_id = int(row["id"])
            account_ids.append(item_id)
            title_bit = str(row.get("title") or row.get("game") or "Account").strip()
            account_labels[item_id] = f"#{item_id} · {row.get('game') or '—'} · {title_bit}"

    sync_local_account_picker("listing_source_account", set(account_ids))
    picked_id = st.selectbox(
        tr("listing_source_label"),
        options=account_ids,
        format_func=lambda item_id: account_labels.get(int(item_id), str(item_id)),
        key="listing_source_account",
    )
    st.caption(tr("listing_source_help"))
    promote_local_pick("listing_source_account", picked_id)

    picked_row: dict[str, Any] | None = None
    if picked_id and df_inventory is not None and not df_inventory.empty:
        matches = df_inventory[df_inventory["id"] == picked_id]
        if not matches.empty:
            picked_row = matches.iloc[0].to_dict()

    if picked_row:
        # Zero-manual path: every field the marketplace copy needs is derived straight from
        # the inventory row (plus a smart-text pass over its own notes/title to fill any
        # gaps), so no form, dropdown override, or Generate click is required — the title
        # and sales copy render instantly the moment an account is picked.
        parsed = extract_features(str(picked_row.get("notes") or ""), picked_row)
        st.session_state.current_parsed_account = parsed

        game = parsed.get("game") or str(picked_row.get("game") or "")
        rank = _listing_rank_default(picked_row) or parsed.get("rank") or ""
        server = str(picked_row.get("server") or "").strip() or parsed.get("server") or ""
        extras = _listing_features_default(picked_row) or parsed.get("extras") or ""
        platform = str(picked_row.get("platform") or "G2G")
        if platform not in LISTING_PLATFORMS:
            platform = "G2G"
        delivery_label = tr(DELIVERY_I18N.get("instant", "instant"))

        st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f"**{tr('listing_auto_title')}**")
            st.caption(tr("listing_auto_help"))
            render_cards(feature_cards(parsed))

        st.session_state.listing_pack = generate_marketplace_listing(
            game=game,
            rank=rank,
            server=server,
            delivery_label=delivery_label,
            extras=extras,
            platform=platform,
            lang=st.session_state.get("lang", "en"),
        )
        st.session_state.listing_pack_kind = f"auto:{picked_id}"
    else:
        # No account picked (Manual Entry) — nothing to auto-derive from, so fall back to a
        # plain typed form.
        with st.form("listing_generator_form_manual"):
            game = st.text_input(
                tr("listing_game"),
                value="",
                placeholder="Valorant / Fortnite / League of Legends",
                key="listing_game_manual",
            )
            rank = st.text_input(
                tr("listing_rank"),
                value="",
                placeholder="Immortal 3 / Champion / Level 200",
                key="listing_rank_manual",
            )
            delivery_key = st.selectbox(
                tr("listing_delivery"),
                options=delivery_keys,
                format_func=lambda key: tr(DELIVERY_I18N.get(key, key)),
                key="listing_delivery_manual",
            )
            extras = st.text_area(
                tr("listing_features"),
                value="",
                placeholder="Full Access, rare skins, original email, ranked ready…",
                height=110,
                key="listing_extras_manual",
            )
            platform = st.selectbox(
                tr("listing_platform"),
                options=list(LISTING_PLATFORMS),
                index=0,
                key="listing_platform_manual",
            )
            generated = st.form_submit_button(tr("listing_generate"), type="primary", width="stretch")

        if generated:
            if not str(game or "").strip():
                st.warning(tr("listing_need_game"))
            else:
                pack = generate_marketplace_listing(
                    game=game,
                    rank=rank,
                    delivery_label=tr(DELIVERY_I18N.get(delivery_key, delivery_key)),
                    extras=extras,
                    platform=platform,
                    lang=st.session_state.get("lang", "en"),
                )
                st.session_state.listing_pack = pack
                st.session_state.listing_pack_kind = "manual"
                st.success(tr("listing_ok"))
        elif st.session_state.get("listing_pack_kind") != "manual":
            # Switching back to Manual Entry without generating yet — drop any leftover
            # auto-listing from a previously picked account instead of showing stale copy.
            st.session_state.pop("listing_pack", None)
            st.session_state.pop("listing_pack_kind", None)

    pack = st.session_state.get("listing_pack")
    if not pack:
        return

    st.caption(tr("listing_copy_hint"))
    st.markdown(f"**{tr('listing_headline')}** · {pack.get('platform', '')}")
    st.code(pack["title"], language="text")
    st.markdown(f"**{tr('listing_body')}**")
    st.code(pack["description"], language="text")
    with st.expander(tr("listing_html")):
        st.code(pack.get("html") or "", language="html")
    download_body = f"{pack['title']}\n\n{pack['description']}\n"
    st.download_button(
        tr("listing_download"),
        data=download_body.encode("utf-8"),
        file_name="game4all-listing.txt",
        mime="text/plain",
        width="stretch",
        key="listing_download_txt",
    )


def parse_uploaded_pack(raw: str, filename: str) -> dict:
    """Read TXT/CSV packs and keep every email/password combo as an inventory delivery login."""
    if filename.lower().endswith(".csv"):
        try:
            df, rows, field_labels = read_csv_pack(raw)
            if not df.empty or rows:
                imported = sum(
                    1
                    for row in rows
                    if str(row.get("login_email") or "").strip() and str(row.get("login_password") or "").strip()
                )
                return {
                    "rows": rows,
                    "imported_logins": imported,
                    "filename": filename,
                    "display_df": df,
                    "field_labels": field_labels,
                }
        except Exception:
            pass
    parsed = parse_batch_text(raw, filename)
    parsed["imported_logins"] = int(parsed.get("imported_logins") or 0)
    return parsed


def read_csv_pack(raw: str) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, str]]:
    """Parse a CSV upload with pandas so preview, import, and DB rows stay row-for-row aligned."""
    df = pd.read_csv(io.StringIO(raw))
    df = df.dropna(how="all")
    if df.empty:
        return df, [], {}

    header_map = {str(col): parser_mod._map_header(str(col)) for col in df.columns}
    field_labels = {
        field: str(col)
        for col in df.columns
        if (field := header_map.get(str(col)))
    }
    rows: list[dict[str, Any]] = []
    for record in df.to_dict("records"):
        cells = {str(key): _normalize_upload_cell(value) for key, value in record.items()}
        rows.append(listing_from_csv_cells(cells, header_map))
    return df, rows, field_labels


def listings_from_dataframe(
    dataframe: pd.DataFrame,
    field_labels: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Convert a displayed inventory dataframe back into normalized listing dicts."""
    frame = dataframe.copy()
    if "ID" in frame.columns:
        frame = frame.drop(columns=["ID"])
    header_map = {str(col): parser_mod._map_header(str(col)) for col in frame.columns}
    labels = field_labels or {
        field: str(col)
        for col in frame.columns
        if (field := header_map.get(str(col)))
    }
    rows: list[dict[str, Any]] = []
    for record in frame.to_dict("records"):
        cells = {str(key): _normalize_upload_cell(value) for key, value in record.items()}
        if not any(str(value).strip() for value in cells.values()):
            continue
        rows.append(listing_from_csv_cells(cells, header_map))
    return rows, labels


def attach_db_ids(upload_df: pd.DataFrame, db_frame: pd.DataFrame) -> pd.DataFrame:
    """Keep the exact uploaded CSV layout and attach DB ids in row order."""
    display = upload_df.copy().reset_index(drop=True)
    if db_frame is None or db_frame.empty or "id" not in db_frame.columns:
        return display
    ids = db_frame.sort_values("id")["id"].tolist()
    if len(ids) >= len(display):
        ids = ids[-len(display) :]
    if len(ids) == len(display):
        display.insert(0, "ID", ids)
    return display


def build_stock_display(
    db_frame: pd.DataFrame,
    field_labels: dict[str, str],
    pack_filter: str,
) -> pd.DataFrame:
    """Render stock using the saved upload snapshot when available, else mapped DB columns."""
    snapshots = st.session_state.get("inventory_snapshots") or {}
    if pack_filter != "All" and pack_filter in snapshots and not db_frame.empty:
        snap = snapshots[pack_filter].copy().reset_index(drop=True)
        return attach_db_ids(snap, db_frame)
    if pack_filter == "All" and snapshots and not db_frame.empty:
        parts: list[pd.DataFrame] = []
        for pack_id, snap in snapshots.items():
            pack_rows = db_frame[db_frame["pack_id"].astype(str) == str(pack_id)] if "pack_id" in db_frame.columns else db_frame
            if pack_rows.empty:
                continue
            parts.append(attach_db_ids(snap.copy().reset_index(drop=True), pack_rows))
        if parts:
            return pd.concat(parts, ignore_index=True)
    return db_frame_to_inventory_df(db_frame, field_labels)


def render_security_action() -> None:
    """Secure & Unlink Sessions + Hyper-Listing & Secure Telegram Dispatcher.

    Revokes old device sessions and locks the security flag on the chosen account, then
    auto-generates a high-converting G2G/Eldorado marketing card bundled with the fresh
    credentials and a session-revocation stamp, ready to push straight to Telegram.
    """
    st.subheader(tr("security_action_title"))
    st.caption(tr("security_action_help"))

    accounts = st.session_state.get("df_inventory", pd.DataFrame())
    if accounts is None or accounts.empty:
        st.info(tr("security_action_empty"))
        return

    options = [0] + [int(v) for v in accounts["id"].tolist()]
    labels = {0: tr("security_action_none")}
    for _, row in accounts.iterrows():
        item_id = int(row["id"])
        secured = str(row.get("security_status") or "Unlocked") == "Secured"
        badge = tr("security_status_secured") if secured else tr("security_status_unlocked")
        email = str(row.get("login_email") or "").strip() or "—"
        title = row.get("title") or row.get("game") or "Account"
        labels[item_id] = f"#{item_id} · {title} · {email} · {badge}"

    sel_col, btn_col = st.columns([2, 1])
    with sel_col:
        sync_local_account_picker("security_target_id", set(options))
        chosen_id = st.selectbox(
            tr("security_action_select"),
            options=options,
            format_func=lambda v: labels.get(v, str(v)),
            key="security_target_id",
        )
        promote_local_pick("security_target_id", chosen_id)
    with btn_col:
        st.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
        if st.button(
            tr("security_action_button"),
            type="primary",
            width="stretch",
            disabled=not chosen_id,
            key="security_action_apply",
        ):
            db.secure_and_revoke_sessions([int(chosen_id)])
            secured_row = db.get_item(int(chosen_id)) or {}
            extras_text = ", ".join(
                bit for bit in (str(secured_row.get(f) or "").strip() for f in ("extras", "skins", "emotes")) if bit
            )
            st.session_state.hyper_listing_pack = generate_hyper_listing(
                item_id=int(chosen_id),
                title=str(secured_row.get("title") or ""),
                game=str(secured_row.get("game") or ""),
                rank=str(secured_row.get("rank") or ""),
                server=str(secured_row.get("server") or ""),
                extras=extras_text,
                platform=str(secured_row.get("platform") or "G2G"),
                login_email=str(secured_row.get("login_email") or ""),
                login_password=str(secured_row.get("login_password") or ""),
                secured_at=str(secured_row.get("sessions_revoked_at") or ""),
                lang=st.session_state.get("lang", "en"),
            )
            flash("success", tr("security_action_success", id=int(chosen_id)))
            st.rerun()

    hyper_pack = st.session_state.get("hyper_listing_pack")
    if not hyper_pack:
        return

    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    st.markdown(f"### {tr('hyper_listing_title')}")
    st.caption(tr("hyper_listing_help"))
    st.markdown(hyper_pack["card_markdown"])

    push_col, _spacer_col = st.columns([1, 2])
    with push_col:
        push_clicked = st.button(
            tr("hyper_listing_push"),
            type="primary",
            width="stretch",
            key="hyper_listing_push_btn",
        )
    if push_clicked:
        result = alerts.push_telegram_message(hyper_pack["telegram_html"], parse_mode="HTML")
        if result.ok:
            flash("success", tr("hyper_listing_push_ok"))
        elif result.skipped:
            flash("warning", tr("hyper_listing_push_skipped"))
        else:
            flash("error", tr("hyper_listing_push_fail", error=result.error or "?"))
        st.rerun()


def inventory_metrics_from_state(df_inventory: pd.DataFrame) -> dict[str, int]:
    """Count Total/Available/Listed/Sold strictly from the session inventory mirror.

    Returns all zeros whenever ``df_inventory`` is empty — no dummy defaults are ever shown.
    """
    if df_inventory is None or df_inventory.empty or "status" not in df_inventory.columns:
        return {"total": 0, "Available": 0, "Listed": 0, "Sold": 0}
    status_col = df_inventory["status"]
    return {
        "total": int(len(df_inventory)),
        "Available": int((status_col == "Available").sum()),
        "Listed": int((status_col == "Listed").sum()),
        "Sold": int((status_col == "Sold").sum()),
    }


# Canonical column order for batch preview + inventory stock tables — one row per account.
_INVENTORY_TABLE_FIELDS = (
    "account_no",
    "sku",
    "title",
    "game",
    "login_email",
    "login_password",
    "mail_password",
    "old_password",
    "secret_answer",
    "rank",
    "level",
    "skins",
    "emotes",
    "server",
    "extras",
    "cost",
    "list_price",
    "platform",
    "status",
    "notes",
)


def _inventory_source_labels() -> dict[str, str]:
    return {
        "account_no": tr("col_account_no"),
        "id": "ID",
        "pack_id": tr("col_pack"),
        "sku": tr("col_sku"),
        "title": tr("col_title"),
        "game": tr("col_game"),
        "login_email": tr("col_email"),
        "login_password": tr("col_epic_password"),
        "mail_password": tr("col_mail_password"),
        "old_password": tr("col_old_password"),
        "secret_answer": tr("col_secret_answer"),
        "rank": tr("col_rank"),
        "level": tr("col_level"),
        "skins": tr("col_skins"),
        "emotes": tr("col_emotes"),
        "server": tr("col_server"),
        "extras": tr("feat_extras"),
        "cost": tr("col_cost"),
        "list_price": tr("col_list"),
        "platform": tr("col_platform"),
        "status": tr("col_status"),
        "notes": tr("col_notes"),
    }


def _inventory_table_column_config() -> dict[str, Any]:
    text_medium = {
        tr("col_email"): st.column_config.TextColumn(tr("col_email"), width="medium"),
        tr("col_epic_password"): st.column_config.TextColumn(tr("col_epic_password"), width="medium"),
        tr("col_mail_password"): st.column_config.TextColumn(tr("col_mail_password"), width="medium"),
        tr("col_old_password"): st.column_config.TextColumn(tr("col_old_password"), width="medium"),
        tr("col_secret_answer"): st.column_config.TextColumn(tr("col_secret_answer"), width="medium"),
        tr("col_title"): st.column_config.TextColumn(tr("col_title"), width="medium"),
        tr("col_notes"): st.column_config.TextColumn(tr("col_notes"), width="medium"),
    }
    return {
        **text_medium,
        tr("col_account_no"): st.column_config.NumberColumn(tr("col_account_no"), format="%d"),
        tr("col_cost"): st.column_config.NumberColumn(format="%.2f"),
        tr("col_list"): st.column_config.NumberColumn(format="%.2f"),
        tr("col_status"): st.column_config.SelectboxColumn(options=["Available", "Listed", "Sold"]),
        tr("col_platform"): st.column_config.SelectboxColumn(options=list(PLATFORMS)),
    }


def build_inventory_table(
    rows: pd.DataFrame | list[dict[str, Any]],
    *,
    include_id: bool = False,
    include_pack: bool = False,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Build a display-ready inventory table and a label→field reverse map for saves."""
    frame = pd.DataFrame(rows).copy() if isinstance(rows, list) else rows.copy()
    if frame.empty:
        return frame, {}

    if "account_no" not in frame.columns:
        frame.insert(0, "account_no", range(1, len(frame) + 1))

    for field in _INVENTORY_TABLE_FIELDS:
        if field == "account_no" or field in frame.columns:
            continue
        if field in {"cost", "list_price"}:
            frame[field] = 0.0
        else:
            frame[field] = ""

    order: list[str] = []
    if include_id and "id" in frame.columns:
        order.append("id")
    if include_pack and "pack_id" in frame.columns:
        order.append("pack_id")
    order.extend(field for field in _INVENTORY_TABLE_FIELDS if field in frame.columns)
    for col in frame.columns:
        if col not in order:
            order.append(col)
    frame = frame[order]

    labels = _inventory_source_labels()
    rename = {src: labels[src] for src in frame.columns if src in labels}
    display = frame.rename(columns=rename)
    reverse_map = {label: src for src, label in rename.items()}
    return display, reverse_map


def build_upload_inventory_df(
    raw: str,
    filename: str,
    rows: list[dict[str, Any]],
    *,
    display_df: pd.DataFrame | None = None,
    field_labels: dict[str, str] | None = None,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Mirror the uploaded spreadsheet: raw CSV columns or a full parsed account grid."""
    if display_df is not None and not display_df.empty:
        return display_df.copy(), field_labels or {}

    if filename.lower().endswith(".csv"):
        try:
            df, parsed_rows, labels = read_csv_pack(raw)
            if not df.empty:
                return df.copy(), labels
            if parsed_rows:
                return pd.DataFrame(parsed_rows), labels
        except Exception:
            pass

    if not rows:
        return pd.DataFrame(), field_labels or {}

    field_labels = dict(field_labels or {})
    frame = pd.DataFrame(rows)
    labels = _inventory_source_labels()
    for field in _INVENTORY_TABLE_FIELDS:
        if field in frame.columns:
            continue
        if field in {"cost", "list_price"}:
            frame[field] = 0.0
        else:
            frame[field] = ""

    display_cols: dict[str, Any] = {labels["account_no"]: range(1, len(frame) + 1)}
    field_labels["account_no"] = labels["account_no"]
    for field in _INVENTORY_TABLE_FIELDS:
        if field == "account_no":
            continue
        label = labels.get(field, field)
        field_labels[field] = label
        display_cols[label] = frame[field].tolist()
    return pd.DataFrame(display_cols), field_labels


def db_frame_to_inventory_df(
    db_frame: pd.DataFrame,
    field_labels: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Rebuild the session inventory grid from DB rows using the upload's column layout."""
    if db_frame is None or db_frame.empty:
        return pd.DataFrame()

    labels = field_labels or {}
    if labels:
        data: dict[str, Any] = {}
        for field, label in labels.items():
            if field == "account_no":
                data[label] = range(1, len(db_frame) + 1)
                continue
            if field in db_frame.columns:
                data[label] = db_frame[field].tolist()
        display = pd.DataFrame(data)
        if "id" in db_frame.columns:
            display.insert(0, "ID", db_frame["id"].tolist())
        return display

    display, _ = build_inventory_table(db_frame, include_id=True, include_pack=True)
    return display


def _inventory_grid_column_config(columns: list[str]) -> dict[str, Any]:
    cfg: dict[str, Any] = {}
    cost_names = {tr("col_cost"), "cost", "Cost", "COST"}
    list_names = {tr("col_list"), "list_price", "List Price", "list price"}
    status_names = {tr("col_status"), "status", "Status"}
    platform_names = {tr("col_platform"), "platform", "Platform"}
    for col in columns:
        if col in cost_names:
            cfg[col] = st.column_config.NumberColumn(format="%.2f")
        elif col in list_names:
            cfg[col] = st.column_config.NumberColumn(format="%.2f")
        elif col in status_names:
            cfg[col] = st.column_config.SelectboxColumn(options=["Available", "Listed", "Sold"])
        elif col in platform_names:
            cfg[col] = st.column_config.SelectboxColumn(options=list(PLATFORMS))
    return cfg


def render_session_inventory_grid(
    dataframe: pd.DataFrame,
    *,
    title_key: str,
    help_key: str,
    rows_key: str,
    editable: bool = False,
    editor_key: str = "inventory_editor",
) -> pd.DataFrame | None:
    """Render the unified upload/stock spreadsheet grid."""
    if dataframe is None or dataframe.empty:
        return None

    st.markdown(f"**{tr(title_key)}**")
    st.caption(tr(help_key))
    st.caption(tr(rows_key, n=len(dataframe)))
    table_height = min(720, max(240, 38 + len(dataframe) * 36))
    column_config = _inventory_grid_column_config(list(dataframe.columns))
    if editable:
        disabled = ["ID"] if "ID" in dataframe.columns else []
        return st.data_editor(
            dataframe,
            width="stretch",
            hide_index=True,
            disabled=disabled,
            column_config=column_config,
            height=table_height,
            key=editor_key,
        )

    st.dataframe(
        dataframe,
        width="stretch",
        hide_index=True,
        column_config=column_config,
        height=table_height,
    )
    return dataframe.copy()


def render_inventory_table(
    rows: pd.DataFrame | list[dict[str, Any]],
    *,
    title_key: str,
    help_key: str,
    rows_key: str,
    include_id: bool = False,
    include_pack: bool = False,
    editable: bool = False,
    editor_key: str = "inventory_editor",
) -> tuple[pd.DataFrame | None, dict[str, str]]:
    """Render the unified batch/inventory account table."""
    display, reverse_map = build_inventory_table(
        rows,
        include_id=include_id,
        include_pack=include_pack,
    )
    if display.empty:
        return None, reverse_map

    st.markdown(f"**{tr(title_key)}**")
    st.caption(tr(help_key))
    st.caption(tr(rows_key, n=len(display)))
    table_height = min(720, max(240, 38 + len(display) * 36))
    if editable:
        id_label = next((label for label, src in reverse_map.items() if src == "id"), "ID")
        edited = st.data_editor(
            display,
            width="stretch",
            hide_index=True,
            disabled=[id_label] if include_id and id_label in display.columns else [],
            column_config=_inventory_table_column_config(),
            height=table_height,
            key=editor_key,
        )
        return edited, reverse_map

    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        column_config=_inventory_table_column_config(),
        height=table_height,
    )
    return display, reverse_map


def tab_inventory() -> None:
    if "df_inventory" not in st.session_state:
        st.session_state.df_inventory = pd.DataFrame()
    if "inventory" not in st.session_state:
        st.session_state.inventory = pd.DataFrame()

    preview_rows = st.session_state.get("preview_rows") or []
    preserve_preview = bool(preview_rows)
    pull_inventory_from_db(preserve_preview=preserve_preview)
    counts = inventory_metrics_live()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(tr("stock_total"), counts["total"])
    m2.metric(tr("stock_available"), counts["Available"])
    m3.metric(tr("stock_listed"), counts["Listed"])
    m4.metric(tr("stock_sold"), counts["Sold"])

    df_inventory = st.session_state.df_inventory

    st.subheader(tr("upload_title"))
    st.caption(tr("upload_help"))
    left, right = st.columns([1.4, 1])
    with left:
        uploaded = st.file_uploader("TXT / CSV", type=["txt", "csv"], label_visibility="collapsed")
    with right:
        pack_name = st.text_input(
            tr("pack_name"),
            value=st.session_state.get("pack_name") or f"PACK-{datetime.now(timezone.utc).strftime('%m%d-%H%M')}",
        )
        st.caption(tr("sample_hint"))
        if st.button(tr("reset_all_button"), key="reset_all_button", type="secondary", use_container_width=True):
            reset_inventory_state()
        st.caption(tr("reset_all_help"))

    if uploaded is not None:
        raw = decode_upload_bytes(uploaded.getvalue())
        parsed = parse_uploaded_pack(raw, uploaded.name)
        display_df, field_labels = build_upload_inventory_df(
            raw,
            uploaded.name,
            parsed["rows"],
            display_df=parsed.get("display_df"),
            field_labels=parsed.get("field_labels"),
        )
        st.session_state.inventory = display_df
        st.session_state.inventory_field_labels = field_labels
        st.session_state.pending_upload_df = display_df.copy()
        st.session_state.preview_rows = parsed["rows"]
        st.session_state.preview_imported = int(parsed.get("imported_logins") or 0)
        st.session_state.pack_name = pack_name
        preview_rows = parsed["rows"]

    imported_logins = int(st.session_state.get("preview_imported") or 0)
    if imported_logins:
        st.success(tr("imported_creds", n=imported_logins))

    inventory = st.session_state.get("inventory", pd.DataFrame())
    is_preview = bool(preview_rows)

    if is_preview:
        if inventory is not None and not inventory.empty:
            render_session_inventory_grid(
                inventory,
                title_key="preview_table_title",
                help_key="preview_table_help",
                rows_key="preview_table_rows",
                editable=False,
            )
            if st.button(tr("import_button"), type="primary"):
                pack_id = pack_name.strip() or "PACK"
                n = import_pack_to_stock(pack_id)
                if n <= 0:
                    flash("error", tr("parse_empty"))
                else:
                    flash("success", tr("imported_ok", n=n, pack=pack_name))
                st.rerun()
        elif uploaded is not None:
            st.info(tr("parse_empty"))
        return

    df_inventory = st.session_state.df_inventory
    if df_inventory is None or df_inventory.empty:
        st.info(tr("empty_stock"))
        return

    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    render_security_action()

    packs = ["All", *sorted({str(v) for v in df_inventory.get("pack_id", pd.Series(dtype=str)) if str(v).strip()})]
    games = ["All", *sorted({str(v) for v in df_inventory.get("game", pd.Series(dtype=str)) if str(v).strip()})]
    default_pack = st.session_state.pop("inventory_pack_filter", None)
    pack_default_index = packs.index(default_pack) if default_pack in packs else 0
    f1, f2, f3 = st.columns(3)
    pack_filter = f1.selectbox(tr("pack_filter"), packs, index=pack_default_index)
    status_filter = f2.selectbox(tr("status_filter"), ["All", "Available", "Listed", "Sold"])
    game_filter = f3.selectbox(tr("game_filter"), games)

    frame = df_inventory.copy()
    if pack_filter != "All" and "pack_id" in frame.columns:
        frame = frame[frame["pack_id"].astype(str) == pack_filter]
    if status_filter != "All" and "status" in frame.columns:
        frame = frame[frame["status"].astype(str) == status_filter]
    if game_filter != "All" and "game" in frame.columns:
        frame = frame[frame["game"].astype(str) == game_filter]
    if "id" in frame.columns:
        frame = frame.sort_values("id", ascending=False)
    if frame.empty:
        st.info(tr("empty_stock"))
        return

    field_labels = st.session_state.get("inventory_field_labels") or {}
    stock_grid = build_stock_display(frame, field_labels, pack_filter)
    st.session_state.inventory = stock_grid
    edited = render_session_inventory_grid(
        stock_grid,
        title_key="inventory_table_title",
        help_key="inventory_table_help",
        rows_key="inventory_table_rows",
        editable=True,
        editor_key="inventory_editor",
    )
    if edited is None:
        return

    label_to_field = {label: field for field, label in field_labels.items()}
    b1, b2, b3 = st.columns([1, 1, 1.2])
    if b1.button(tr("save_grid"), type="primary"):
        for _, row in edited.iterrows():
            row_id = None
            if "ID" in row:
                row_id = int(row["ID"])
            if row_id is None:
                continue
            if label_to_field:
                payload = {
                    field: row[label]
                    for label, field in label_to_field.items()
                    if label in row and field not in {"account_no", "id"}
                }
            else:
                _, field_map = build_inventory_table(frame, include_id=True, include_pack=True)
                payload = {
                    dest: row[label]
                    for label, dest in field_map.items()
                    if label in row and dest not in {"account_no", "id"}
                }
            db.update_inventory_row(row_id, payload)
        st.session_state.inventory_pack_filter = pack_filter
        pull_inventory_from_db(preserve_preview=False)
        flash("success", tr("saved_ok"))
        st.rerun()

    bulk_status = b2.selectbox(tr("bulk_status"), ["Available", "Listed", "Sold"], label_visibility="collapsed")
    if b3.button(tr("apply_status")):
        if "ID" in edited.columns:
            ids = [int(v) for v in edited["ID"].tolist()]
            db.bulk_set_status(ids, bulk_status)
            st.session_state.inventory_pack_filter = pack_filter
            pull_inventory_from_db(preserve_preview=False)
            flash("success", tr("saved_ok"))
            st.rerun()

    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    render_pricing_engine(frame, key_prefix="inv_prices", show_apply=False)


def listing_to_features(row: dict) -> dict[str, str]:
    return extract_features(str(row.get("notes") or ""), row)


def tab_parser() -> None:
    st.subheader(tr("parser_title"))
    st.caption(tr("parser_live_hint"))
    stock = db.inventory_frame()
    options = [0]
    labels = {0: tr("parser_none")}
    if not stock.empty:
        for _, row in stock.iterrows():
            item_id = int(row["id"])
            options.append(item_id)
            labels[item_id] = f"#{item_id} · {row['game']} · {row['title']}"

    with st.container(border=True):
        sync_local_account_picker("parser_pick_account", set(options))
        pick = st.selectbox(
            tr("parser_pick"),
            options,
            format_func=lambda item_id: labels[item_id],
            key="parser_pick_account",
        )
        promote_local_pick("parser_pick_account", pick)
        seed = db.get_item(pick) if pick else None
        default_text = ""
        if seed:
            default_text = " | ".join(
                str(seed.get(k) or "")
                for k in ("title", "game", "rank", "level", "skins", "emotes", "server", "extras", "notes")
                if seed.get(k)
            )
        # Keyed per picked account so switching accounts always resets this box cleanly —
        # never leaves behind a previous account's stale text. It's a read-only preview
        # once an account is active: extract_features() ignores this box's contents
        # whenever a seed is present and reads the account's own stored attributes
        # instead, so leftover/unrelated text here can never contaminate the real details.
        pasted = st.text_area(
            tr("parser_paste"),
            value=default_text,
            height=200,
            key=f"parser_pasted_{pick}",
            disabled=bool(seed),
        )
        if seed:
            st.caption(tr("parser_account_locked_hint"))

    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        r1, r2 = st.columns(2, gap="large")
        with r1:
            platform = st.selectbox(
                tr("copy_platform"),
                list(PLATFORMS),
                index=list(PLATFORMS).index(st.session_state.get("default_platform", "G2G"))
                if st.session_state.get("default_platform", "G2G") in PLATFORMS
                else 0,
            )
            copy_lang = st.selectbox(tr("copy_lang"), list(LANGUAGES), format_func=lambda code: LANGUAGE_LABELS[code])
        with r2:
            email_key = st.selectbox(
                tr("email_access"),
                ["full_access", "original_email", "full_and_original"],
                format_func=lambda key: tr(key),
            )
            warranty = int(st.number_input(tr("warranty"), min_value=1, max_value=168, value=12, step=1))

    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)

    # Fully automatic: as soon as there is pasted text or a picked stock row, features and
    # sales copy are extracted/generated on every rerun — no Extract/Generate click required.
    has_input = bool(str(pasted or "").strip()) or bool(seed)
    features: dict[str, str] = {}
    if has_input:
        features = extract_features(pasted, seed)
        st.session_state.features = features
        st.session_state.current_parsed_account = features

    with st.container(border=True):
        st.markdown(f"**{tr('features_card')}**")
        st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
        render_cards(feature_cards(features))

    if has_input and features:
        copy = generate_sales_copy(
            features,
            platform=platform,
            lang=copy_lang,
            email_key=email_key,
            warranty_h=warranty,
        )
        st.session_state.generated_copy = copy
    else:
        st.session_state.pop("generated_copy", None)

    copy = st.session_state.get("generated_copy")
    if copy:
        st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            t_html, t_plain, t_bb = st.tabs([tr("copy_html"), tr("copy_plain"), tr("copy_bbcode")])
            t_html.text_area("HTML", copy["html"], height=280, label_visibility="collapsed")
            t_plain.text_area("Plain", copy["plain"], height=280, label_visibility="collapsed")
            t_bb.text_area("BBCode", copy["bbcode"], height=280, label_visibility="collapsed")


def tab_pricing() -> None:
    stock = db.inventory_frame()
    render_pricing_engine(stock, key_prefix="calc_prices", show_apply=True)

    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    st.subheader(tr("calc_title"))
    picked = None
    if not stock.empty:
        pick_ids = [0, *[int(v) for v in stock["id"].tolist()]]
        pick_labels = {0: tr("parser_none")}
        for _, row in stock.iterrows():
            pick_labels[int(row["id"])] = f"#{int(row['id'])} · {row['game']} · {row['title']}"
        sync_local_account_picker("price_item_pick", set(pick_ids))
        chosen = st.selectbox(
            tr("price_pick"),
            pick_ids,
            format_func=lambda item_id: pick_labels.get(item_id, str(item_id)),
            key="price_item_pick",
        )
        promote_local_pick("price_item_pick", chosen)
        if chosen:
            picked = db.get_item(int(chosen))

    # Cost / selling price only ever pre-fill from a real picked inventory item; with no
    # selection (or a fresh, never-uploaded inventory) both stay at a clean 0.0 instead of
    # sample placeholder numbers.
    default_cost = float((picked or {}).get("cost") or 0.0)
    default_sell = float((picked or {}).get("list_price") or 0.0)
    default_platform = str((picked or {}).get("platform") or st.session_state.get("default_platform") or "G2G")
    if default_platform not in PLATFORMS:
        default_platform = "G2G"
    if picked and default_sell <= 0:
        default_sell = suggested_list_price(picked, default_platform)
    item_key = int((picked or {}).get("id") or 0)

    with st.container(border=True):
        platform = st.selectbox(
            tr("col_platform"),
            list(PLATFORMS),
            index=list(PLATFORMS).index(default_platform),
            key=f"calc_platform_{item_key}",
        )
        profile = get_platform_profile(platform)
        st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
        p1, p2 = st.columns(2, gap="large")
        cost = p1.number_input(
            tr("calc_cost"),
            min_value=0.0,
            value=float(default_cost),
            step=0.5,
            key=f"calc_cost_{item_key}",
        )
        sell = p2.number_input(
            tr("calc_sell"),
            min_value=0.0,
            value=float(default_sell),
            step=0.5,
            key=f"calc_sell_{item_key}",
        )
        st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
        p3, p4 = st.columns(2, gap="large")
        commission = p3.number_input(
            tr("calc_commission"),
            min_value=0.0,
            max_value=40.0,
            value=float(profile["commission_pct"]),
            step=0.1,
            key=f"calc_commission_{platform}",
        )
        fees = p4.number_input(
            tr("calc_fees"),
            min_value=0.0,
            value=float(profile["extra_fees"]),
            step=0.1,
            key=f"calc_fees_{platform}",
        )
    has_inputs = cost > 0 and sell > 0
    deal = calculate_deal(cost, sell, commission, fees, platform=platform) if has_inputs else None

    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3, gap="large")
    k1.metric(tr("metric_commission"), money(deal["commission_amount"]) if deal else money(0))
    k2.metric(tr("metric_net"), money(deal["net_received"]) if deal else money(0))
    k3.metric(tr("metric_profit"), money(deal["net_profit"]) if deal else money(0))
    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    k4, k5, _ = st.columns(3, gap="large")
    k4.metric(tr("metric_roi"), f"{deal['roi_pct']:.1f}%" if deal else "—")
    k5.metric(tr("metric_margin"), f"{deal['margin_on_sale']:.1f}%" if deal else "—")

    if not deal:
        st.caption(tr("calc_awaiting_input"))
    else:
        heat_key = {"hot": "hot_deal", "thin": "thin_deal", "loss": "loss_deal"}.get(deal["heat"])
        if heat_key:
            if deal["heat"] == "hot":
                st.success(f"{tr(heat_key)} · {profile['note']}")
            elif deal["heat"] == "loss":
                st.error(f"{tr(heat_key)} · {profile['note']}")
            else:
                st.warning(f"{tr(heat_key)} · {profile['note']}")
        else:
            st.caption(profile["note"])

    if picked:
        st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
        st.markdown(f"**{tr('item_markets')}**")
        quotes = estimate_item_platforms(picked)
        cols = st.columns(3, gap="large")
        for index, quote in enumerate(quotes):
            with cols[index % 3]:
                st.markdown(
                    f'<div class="g4a-price-card"><b>{quote["platform"]}</b>'
                    f"<span>{tr('col_est_market')}: {money(quote['estimated_market_value'])}</span>"
                    f"<em>{tr('col_recommend')}: {money(quote['recommended_price'])}<br>"
                    f"{tr('col_fees')}: {money(quote['marketplace_fees'])} · "
                    f"{tr('metric_profit')}: {money(quote['net_profit'])}</em></div>",
                    unsafe_allow_html=True,
                )

    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        target = st.number_input(tr("calc_target"), min_value=0.0, value=0.0, step=0.5)
        st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
        if cost > 0 and target > 0:
            suggested = required_sell_price(cost, target, commission, fees)
            st.metric(tr("calc_suggest"), money(suggested) if suggested == suggested else "—")
        else:
            st.metric(tr("calc_suggest"), "—")

    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    st.markdown(f"**{tr('compare_title')}**")
    if has_inputs:
        compare = pd.DataFrame(compare_platforms(cost, sell))
        show = compare[
            ["platform", "commission_pct", "extra_fees", "commission_amount", "net_received", "net_profit", "roi_pct", "heat"]
        ].rename(
            columns={
                "platform": tr("col_platform"),
                "commission_pct": tr("calc_commission"),
                "extra_fees": tr("calc_fees"),
                "commission_amount": tr("metric_commission"),
                "net_received": tr("metric_net"),
                "net_profit": tr("metric_profit"),
                "roi_pct": tr("metric_roi"),
                "heat": "Heat",
            }
        )
        st.dataframe(show, width="stretch", hide_index=True)
    else:
        st.caption(tr("calc_awaiting_input"))


def tab_sales() -> None:
    st.subheader(tr("sales_title"))
    stock = db.inventory_frame(status="Available")
    listed = db.inventory_frame(status="Listed")
    frames = [frame for frame in (stock, listed) if not frame.empty]
    sellable = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    mode = st.radio(tr("log_sale"), [tr("sale_from_stock"), tr("sale_manual")], horizontal=True)
    title = ""
    game = ""
    platform = st.session_state.get("default_platform", "G2G")
    cost = 0.0
    inventory_id = None
    list_price = 0.0

    if mode == tr("sale_from_stock"):
        if sellable.empty:
            st.info(tr("empty_stock"))
            mode = tr("sale_manual")
        else:
            labels = {
                int(row["id"]): f"#{int(row['id'])} · {row['game']} · {row['title']} · {money(row['list_price'])}"
                for _, row in sellable.iterrows()
            }
            sync_local_account_picker("sale_source_account", set(labels))
            inventory_id = st.selectbox(
                "SKU",
                list(labels),
                format_func=lambda item_id: labels[item_id],
                key="sale_source_account",
            )
            promote_local_pick("sale_source_account", inventory_id)
            item = db.get_item(int(inventory_id)) or {}
            title = str(item.get("title") or "")
            game = str(item.get("game") or "")
            platform = str(item.get("platform") or platform)
            cost = float(item.get("cost") or 0)
            list_price = float(item.get("list_price") or 0)

    if mode == tr("sale_manual"):
        r1, r2, r3 = st.columns(3)
        title = r1.text_input(tr("col_title"), value="")
        game = r2.text_input(tr("col_game"), value="")
        platform = r3.selectbox(tr("col_platform"), list(PLATFORMS), key="sale_platform")
        cost = st.number_input(tr("calc_cost"), min_value=0.0, value=0.0, step=0.5, key="sale_cost")

    profile = get_platform_profile(platform)
    s1, s2, s3 = st.columns(3)
    sold_price = s1.number_input(tr("sold_price"), min_value=0.0, value=float(list_price or 0.0), step=0.5)
    commission = s2.number_input(tr("calc_commission"), min_value=0.0, value=float(profile["commission_pct"]), step=0.1, key="sale_commission")
    extra_fees = s3.number_input(tr("calc_fees"), min_value=0.0, value=float(profile["extra_fees"]), step=0.1, key="sale_fees")
    deal = calculate_deal(cost, sold_price, commission, extra_fees, platform=platform)
    if cost > 0 and sold_price > 0:
        st.caption(f"{tr('metric_profit')}: {money(deal['net_profit'])} · {tr('metric_roi')}: {deal['roi_pct']:.1f}%")
    else:
        st.caption(tr("sale_awaiting_input"))

    if st.button(tr("record_sale"), type="primary"):
        db.record_sale(
            inventory_id=int(inventory_id) if inventory_id else None,
            title=title,
            game=game,
            platform=platform,
            cost=cost,
            sold_price=sold_price,
            commission_pct=commission,
            extra_fees=extra_fees,
            net_profit=deal["net_profit"],
            roi_pct=deal["roi_pct"],
        )
        summary = alerts.notify_sale(
            title=title,
            game=game,
            platform=platform,
            sold_price=sold_price,
            net_profit=deal["net_profit"],
            roi_pct=deal["roi_pct"],
            enabled=bool(st.session_state.get("notify_on_sale", True)),
        )
        if summary.any_ok:
            flash("success", f"{tr('sale_ok')} {tr('alert_sent')}")
        elif summary.skipped_all:
            flash("warning", f"{tr('sale_ok')} {tr('alert_skipped')}")
        else:
            flash("error", f"{tr('sale_ok')} {tr('alert_fail', err=summary.error_text() or 'n/a')}")
        st.rerun()

    months = ["All", *db.list_sale_months()]
    month = st.selectbox(tr("month"), months)
    sales = db.sales_frame(None if month == "All" else month)
    analytics = db.monthly_analytics()

    if month != "All" and not sales.empty:
        a1, a2, a3, a4 = st.columns(4)
        a1.metric(tr("sales_count"), len(sales))
        a2.metric(tr("gross"), money(float(sales["sold_price"].sum())))
        a3.metric(tr("net_month"), money(float(sales["net_profit"].sum())))
        a4.metric(tr("avg_roi"), f"{float(sales['roi_pct'].mean()):.1f}%")
    elif not analytics.empty:
        latest = analytics.iloc[-1]
        a1, a2, a3, a4 = st.columns(4)
        a1.metric(tr("sales_count"), int(analytics["sales_count"].sum()))
        a2.metric(tr("gross"), money(float(analytics["gross"].sum())))
        a3.metric(tr("net_month"), money(float(analytics["net_profit"].sum())))
        a4.metric(tr("avg_roi"), f"{float(analytics['avg_roi'].mean()):.1f}%")
        st.caption(f"{tr('month')}: {latest['month_key']}")

    if sales.empty:
        st.info(tr("empty_sales"))
    else:
        show = sales[
            ["sold_at", "title", "game", "platform", "cost", "sold_price", "net_profit", "roi_pct"]
        ].rename(
            columns={
                "sold_at": "UTC",
                "title": tr("col_title"),
                "game": tr("col_game"),
                "platform": tr("col_platform"),
                "cost": tr("col_cost"),
                "sold_price": tr("sold_price"),
                "net_profit": tr("metric_profit"),
                "roi_pct": tr("metric_roi"),
            }
        )
        st.dataframe(show, width="stretch", hide_index=True)

    if not analytics.empty:
        st.markdown(f"**{tr('chart_title')}**")
        chart = analytics.set_index("month_key")[["net_profit"]]
        st.bar_chart(chart, color=THEME_CHART.get(current_theme(), "#d4af37"))


def render_dashboard() -> None:
    sidebar()
    inject_theme_runtime(current_theme(), bool(st.session_state.get("sound_enabled", True)))
    inject_direction(st.session_state.lang)
    st.markdown(
        """
        <style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>
        """,
        unsafe_allow_html=True,
    )
    hero()
    show_flash()
    render_desk_page()
    st.markdown(f'<div class="g4a-footer">{tr("footer")}</div>', unsafe_allow_html=True)
    st.markdown(f"<style>{LUXURY_UI_CSS}</style>", unsafe_allow_html=True)


def render_locked_app() -> None:
    inject_theme_runtime("royal", False)
    inject_direction("en")
    st.markdown(
        """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"],
        [data-testid="stExpandSidebarButton"] {
            display: none !important;
            width: 0 !important;
            min-width: 0 !important;
            visibility: hidden !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    render_license_gate()
    st.markdown(f"<style>{LUXURY_UI_CSS}</style>", unsafe_allow_html=True)


def _resolve_boot_pack_file(source_hint: str = "") -> Path | None:
    """Find the bundled CSV/TXT used for auto-seeding (by path, name, or first available)."""
    paths = db.discover_default_pack_paths()
    hint = (source_hint or "").strip()
    if hint:
        for path in paths:
            if str(path) == hint or path.name == hint or path.name == Path(hint).name:
                return path
    return paths[0] if paths else None


def _sync_boot_inventory_session(source_hint: str = "") -> None:
    """Hydrate Streamlit session tables from the auto-seeded pack file layout."""
    path = _resolve_boot_pack_file(source_hint)
    pack_id = db.get_setting("boot_inventory_pack_id") or BOOT_PACK_ID

    if path is None or not path.is_file():
        pull_inventory_from_db(preserve_preview=False)
        st.session_state.inventory_pack_filter = pack_id
        return

    raw = decode_upload_bytes(path.read_bytes())
    parsed = parse_uploaded_pack(raw, path.name)
    rows = parsed.get("rows") or []
    display_df, field_labels = build_upload_inventory_df(
        raw,
        path.name,
        rows,
        display_df=parsed.get("display_df"),
        field_labels=parsed.get("field_labels"),
    )
    pack_frame = db.inventory_frame(pack_id=pack_id)
    st.session_state.inventory_field_labels = field_labels
    st.session_state.inventory_snapshots = {pack_id: display_df.copy()}
    st.session_state.inventory = attach_db_ids(display_df, pack_frame)
    st.session_state.inventory_pack_filter = pack_id
    pull_inventory_from_db(preserve_preview=False)


def bootstrap_inventory_if_empty() -> int:
    """Ensure cloud cold starts load bundled CSV stock into SQLite + session state."""
    inserted, source_path = db.seed_inventory_if_empty()

    if db.inventory_is_empty():
        return 0

    snapshots = st.session_state.get("inventory_snapshots") or {}
    if inserted > 0 or not snapshots:
        hint = source_path or db.get_setting("boot_inventory_source")
        _sync_boot_inventory_session(hint)
        finalize_active_account_after_import(BOOT_PACK_ID)
    else:
        pull_inventory_from_db(preserve_preview=False)

    st.session_state.pack_uploaded = True
    return inserted or db.inventory_counts()["total"]


def main() -> None:
    st.set_page_config(
        page_title="Store & Growth Manager",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    init_auth_gate()
    db.init_db()
    bootstrap_inventory_if_empty()
    sync_inventory_state()
    if "lang" not in st.session_state:
        st.session_state.lang = "en"
    if "theme_select" not in st.session_state:
        saved = db.get_setting("ui_theme", "royal") or "royal"
        st.session_state.theme_select = saved if saved in THEMES else "royal"
    st.session_state.theme = current_theme()
    load_css()

    if st.session_state.authenticated is not True:
        render_locked_app()
        st.stop()

    render_dashboard()


if __name__ == "__main__":
    main()
