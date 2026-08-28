"""GAME4ALL Manager Pro — Streamlit command desk for listing stock, copy, fees, and sales.

Run:
    streamlit run app.py
"""

from __future__ import annotations

import importlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import alerts
import database as db
import i18n as i18n_mod
import license as license_mod
import pricing as pricing_mod
from parser import (
    extract_features,
    feature_cards,
    generate_sales_copy,
    parse_batch_text,
)

db = importlib.reload(db)
i18n_mod = importlib.reload(i18n_mod)
license_mod = importlib.reload(license_mod)
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

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

THEMES = ("royal", "cyber", "dark")
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
    gap: 14px !important;
    background: transparent !important;
    border-bottom: none !important;
    padding: 6px 0 14px !important;
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {
    display: none !important;
    background: transparent !important;
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
    min-height: 3.2rem !important;
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
html body .stApp [data-testid="stTab"] { margin: 0 6px 10px 0 !important; }
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
.g4a-card span { color: #ffffff !important; }
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


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated", False))


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
                placeholder=tr("license_placeholder"),
                autocomplete="off",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button(ACTIVATE_LABEL, width="stretch")
        if submitted:
            ok, reason, _row = license_mod.activate_key(key_value)
            if ok:
                st.session_state.authenticated = True
                st.session_state.licensed = True
                st.rerun()
            message = tr(LICENSE_ERRORS.get(reason, "license_invalid"))
            st.markdown(f'<div class="g4a-gate-error">{message}</div>', unsafe_allow_html=True)
        render_license_admin(expanded=admin_query_open())


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


def sidebar() -> None:
    sidebar_chrome()

    default_platform = db.get_setting("default_platform", "G2G")
    platform = st.sidebar.selectbox(
        tr("sidebar_platform"),
        options=list(PLATFORMS),
        index=list(PLATFORMS).index(default_platform) if default_platform in PLATFORMS else 0,
    )
    if platform != default_platform:
        db.set_setting("default_platform", platform)
    st.session_state.default_platform = platform

    notify = st.sidebar.toggle(tr("notify_on_sale"), value=db.get_setting("notify_on_sale", "1") == "1")
    db.set_setting("notify_on_sale", "1" if notify else "0")
    st.session_state.notify_on_sale = notify

    status = alerts.webhook_status()
    st.sidebar.markdown(f"**{tr('sidebar_webhooks')}**")
    pill = "on" if status["any"] else "off"
    label = tr("webhook_ready") if status["any"] else tr("webhook_placeholder")
    st.sidebar.markdown(f'<span class="g4a-pill {pill}">{label}</span>', unsafe_allow_html=True)
    if st.sidebar.button(tr("test_webhook"), width="stretch"):
        summary = alerts.send_test_alert()
        if summary.any_ok:
            st.sidebar.success(tr("test_ok"))
        elif summary.skipped_all:
            st.sidebar.warning(tr("webhook_placeholder"))
        else:
            st.sidebar.error(tr("test_fail", err=summary.error_text() or "n/a"))

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
    if st.sidebar.button("Logout / Deactivate", width="stretch", key="license_sign_out"):
        license_mod.clear_activation()
        st.session_state.authenticated = False
        st.session_state.licensed = False
        st.rerun()
    with st.sidebar:
        render_license_admin(expanded=False)


def tab_inventory() -> None:
    counts = db.inventory_counts()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(tr("stock_total"), counts["total"])
    m2.metric(tr("stock_available"), counts["Available"])
    m3.metric(tr("stock_listed"), counts["Listed"])
    m4.metric(tr("stock_sold"), counts["Sold"])

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

    if uploaded is not None:
        raw = uploaded.getvalue().decode("utf-8", errors="replace")
        parsed = parse_batch_text(raw, uploaded.name)
        st.session_state.preview_rows = parsed["rows"]
        st.session_state.preview_skipped = parsed["skipped_credentials"]
        st.session_state.pack_name = pack_name

    preview = st.session_state.get("preview_rows") or []
    skipped = int(st.session_state.get("preview_skipped") or 0)
    if skipped:
        st.warning(tr("skipped_creds", n=skipped))
    if preview:
        st.dataframe(pd.DataFrame(preview), width="stretch", hide_index=True)
        if st.button(tr("import_button"), type="primary"):
            n = db.insert_listings(preview, pack_name.strip() or "PACK")
            st.session_state.preview_rows = []
            st.session_state.preview_skipped = 0
            flash("success", tr("imported_ok", n=n, pack=pack_name))
            st.rerun()
    elif uploaded is not None:
        st.info(tr("parse_empty"))

    packs = ["All", *db.list_packs()]
    games = ["All", *db.list_games()]
    f1, f2, f3 = st.columns(3)
    pack_filter = f1.selectbox(tr("pack_filter"), packs)
    status_filter = f2.selectbox(tr("status_filter"), ["All", "Available", "Listed", "Sold"])
    game_filter = f3.selectbox(tr("game_filter"), games)

    frame = db.inventory_frame(
        status=None if status_filter == "All" else status_filter,
        pack_id=None if pack_filter == "All" else pack_filter,
        game=None if game_filter == "All" else game_filter,
    )
    if frame.empty:
        st.info(tr("empty_stock"))
        return

    display = frame[
        [
            "id",
            "pack_id",
            "sku",
            "title",
            "game",
            "rank",
            "level",
            "skins",
            "emotes",
            "server",
            "cost",
            "list_price",
            "platform",
            "status",
            "notes",
        ]
    ].copy()
    display.columns = [
        "id",
        tr("col_pack"),
        tr("col_sku"),
        tr("col_title"),
        tr("col_game"),
        tr("col_rank"),
        tr("col_level"),
        tr("col_skins"),
        tr("col_emotes"),
        tr("col_server"),
        tr("col_cost"),
        tr("col_list"),
        tr("col_platform"),
        tr("col_status"),
        tr("col_notes"),
    ]
    edited = st.data_editor(
        display,
        width="stretch",
        hide_index=True,
        disabled=["id"],
        column_config={
            tr("col_status"): st.column_config.SelectboxColumn(options=["Available", "Listed", "Sold"]),
            tr("col_platform"): st.column_config.SelectboxColumn(options=list(PLATFORMS)),
            tr("col_cost"): st.column_config.NumberColumn(format="%.2f"),
            tr("col_list"): st.column_config.NumberColumn(format="%.2f"),
        },
        key="inventory_editor",
    )
    b1, b2, b3 = st.columns([1, 1, 1.2])
    if b1.button(tr("save_grid"), type="primary"):
        field_map = {
            tr("col_pack"): "pack_id",
            tr("col_sku"): "sku",
            tr("col_title"): "title",
            tr("col_game"): "game",
            tr("col_rank"): "rank",
            tr("col_level"): "level",
            tr("col_skins"): "skins",
            tr("col_emotes"): "emotes",
            tr("col_server"): "server",
            tr("col_cost"): "cost",
            tr("col_list"): "list_price",
            tr("col_platform"): "platform",
            tr("col_status"): "status",
            tr("col_notes"): "notes",
        }
        for _, row in edited.iterrows():
            payload = {dest: row[src] for src, dest in field_map.items() if src in row}
            db.update_inventory_row(int(row["id"]), payload)
        flash("success", tr("saved_ok"))
        st.rerun()

    bulk_status = b2.selectbox(tr("bulk_status"), ["Available", "Listed", "Sold"], label_visibility="collapsed")
    if b3.button(tr("apply_status")):
        ids = [int(v) for v in edited["id"].tolist()]
        db.bulk_set_status(ids, bulk_status)
        flash("success", tr("saved_ok"))
        st.rerun()

    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    render_pricing_engine(frame, key_prefix="inv_prices", show_apply=False)


def listing_to_features(row: dict) -> dict[str, str]:
    return extract_features(str(row.get("notes") or ""), row)


def tab_parser() -> None:
    st.subheader(tr("parser_title"))
    stock = db.inventory_frame()
    options = [0]
    labels = {0: tr("parser_none")}
    if not stock.empty:
        for _, row in stock.iterrows():
            item_id = int(row["id"])
            options.append(item_id)
            labels[item_id] = f"#{item_id} · {row['game']} · {row['title']}"

    with st.container(border=True):
        pick = st.selectbox(tr("parser_pick"), options, format_func=lambda item_id: labels[item_id])
        seed = db.get_item(pick) if pick else None
        default_text = ""
        if seed:
            default_text = " | ".join(
                str(seed.get(k) or "")
                for k in ("title", "game", "rank", "level", "skins", "emotes", "server", "extras", "notes")
                if seed.get(k)
            )
        pasted = st.text_area(tr("parser_paste"), value=default_text, height=200)

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
    a1, a2 = st.columns(2, gap="large")
    extract_clicked = a1.button(tr("extract_btn"), width="stretch")
    generate_clicked = a2.button(tr("generate_btn"), type="primary", width="stretch")
    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)

    if extract_clicked or generate_clicked or seed:
        features = extract_features(pasted, seed)
        st.session_state.features = features
    features = st.session_state.get("features") or {}
    with st.container(border=True):
        st.markdown(f"**{tr('features_card')}**")
        st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
        render_cards(feature_cards(features))

    if generate_clicked:
        if not features:
            st.info(tr("no_features"))
            return
        copy = generate_sales_copy(
            features,
            platform=platform,
            lang=copy_lang,
            email_key=email_key,
            warranty_h=warranty,
        )
        st.session_state.generated_copy = copy

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
        chosen = st.selectbox(
            tr("price_pick"),
            pick_ids,
            format_func=lambda item_id: pick_labels.get(item_id, str(item_id)),
            key="price_item_pick",
        )
        if chosen:
            picked = db.get_item(int(chosen))

    default_cost = float((picked or {}).get("cost") or 15.0)
    default_sell = float((picked or {}).get("list_price") or 0)
    default_platform = str((picked or {}).get("platform") or st.session_state.get("default_platform") or "G2G")
    if default_platform not in PLATFORMS:
        default_platform = "G2G"
    if picked and default_sell <= 0:
        default_sell = suggested_list_price(picked, default_platform)
    if default_sell <= 0:
        default_sell = 29.9
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
    deal = calculate_deal(cost, sell, commission, fees, platform=platform)

    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3, gap="large")
    k1.metric(tr("metric_commission"), money(deal["commission_amount"]))
    k2.metric(tr("metric_net"), money(deal["net_received"]))
    k3.metric(tr("metric_profit"), money(deal["net_profit"]))
    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    k4, k5, _ = st.columns(3, gap="large")
    k4.metric(tr("metric_roi"), f"{deal['roi_pct']:.1f}%")
    k5.metric(tr("metric_margin"), f"{deal['margin_on_sale']:.1f}%")

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
        target = st.number_input(tr("calc_target"), min_value=0.0, value=8.0, step=0.5)
        st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
        suggested = required_sell_price(cost, target, commission, fees)
        st.metric(tr("calc_suggest"), money(suggested) if suggested == suggested else "—")

    st.markdown('<div class="g4a-spacer"></div>', unsafe_allow_html=True)
    st.markdown(f"**{tr('compare_title')}**")
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
            inventory_id = st.selectbox("SKU", list(labels), format_func=lambda item_id: labels[item_id])
            item = db.get_item(int(inventory_id)) or {}
            title = str(item.get("title") or "")
            game = str(item.get("game") or "")
            platform = str(item.get("platform") or platform)
            cost = float(item.get("cost") or 0)
            list_price = float(item.get("list_price") or 0)

    if mode == tr("sale_manual"):
        r1, r2, r3 = st.columns(3)
        title = r1.text_input(tr("col_title"), value="GAME4ALL listing")
        game = r2.text_input(tr("col_game"), value="Valorant")
        platform = r3.selectbox(tr("col_platform"), list(PLATFORMS), key="sale_platform")
        cost = st.number_input(tr("calc_cost"), min_value=0.0, value=15.0, step=0.5, key="sale_cost")

    profile = get_platform_profile(platform)
    s1, s2, s3 = st.columns(3)
    sold_price = s1.number_input(tr("sold_price"), min_value=0.0, value=float(list_price or 29.9), step=0.5)
    commission = s2.number_input(tr("calc_commission"), min_value=0.0, value=float(profile["commission_pct"]), step=0.1, key="sale_commission")
    extra_fees = s3.number_input(tr("calc_fees"), min_value=0.0, value=float(profile["extra_fees"]), step=0.1, key="sale_fees")
    deal = calculate_deal(cost, sold_price, commission, extra_fees, platform=platform)
    st.caption(f"{tr('metric_profit')}: {money(deal['net_profit'])} · {tr('metric_roi')}: {deal['roi_pct']:.1f}%")

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


def main() -> None:
    st.set_page_config(
        page_title="GAME4ALL MANAGER PRO",
        page_icon="🎮",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    init_auth_gate()
    db.init_db()
    if "lang" not in st.session_state:
        st.session_state.lang = "en"
    if "theme_select" not in st.session_state:
        saved = db.get_setting("ui_theme", "royal") or "royal"
        st.session_state.theme_select = saved if saved in THEMES else "royal"
    st.session_state.theme = current_theme()
    load_css()

    if st.session_state.authenticated:
        db.seed_sample_if_empty()
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
        tab1, tab2, tab3, tab4 = st.tabs(
            [tr("nav_inventory"), tr("nav_parser"), tr("nav_pricing"), tr("nav_sales")]
        )
        with tab1:
            tab_inventory()
        with tab2:
            tab_parser()
        with tab3:
            tab_pricing()
        with tab4:
            tab_sales()
        st.markdown(f'<div class="g4a-footer">{tr("footer")}</div>', unsafe_allow_html=True)
        st.markdown(f"<style>{LUXURY_UI_CSS}</style>", unsafe_allow_html=True)
        return

    inject_theme_runtime("royal", bool(st.session_state.get("sound_enabled", True)))
    inject_direction(st.session_state.lang)
    st.markdown(
        """
        <style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>
        """,
        unsafe_allow_html=True,
    )
    render_license_gate()
    st.markdown(f"<style>{LUXURY_UI_CSS}</style>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
