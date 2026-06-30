"""
ui.styles
=========
The single CSS theme for the entire application. Call :func:`apply` once
near the top of ``app.py`` (after ``st.set_page_config``).

The theme is built around the reference Command-Center screenshots:

* Deep navy page (#0a0e1a) with slightly-elevated cards (#141828).
* Purple primary accent (#7c3aed) with cyan secondary for charts.
* Mono labels for technical chrome; ``Outfit`` for body; ``Syne`` for hero.
* Generous internal padding; subtle 1px borders, not heavy strokes.
* All interactive elements share the same hover signature
  (slight border-glow + subtle lift), so the app feels cohesive.

Token names mirror :class:`core.constants.Colors` so Python code that
draws charts can match the CSS without re-typing hex codes.
"""

from __future__ import annotations

import streamlit as st


_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@500;600;700;800&family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

  :root {
    /* Backgrounds */
    --bg-primary:   #0a0e1a;
    --bg-card:      #141828;
    --bg-elevated:  #1a1f2e;
    --bg-nested:    #0f1320;
    --bg-input:     #11162a;

    /* Borders */
    --border-faint:   rgba(255,255,255,0.05);
    --border:         rgba(255,255,255,0.08);
    --border-strong:  rgba(255,255,255,0.16);
    --border-purple:  rgba(124,58,237,0.35);
    --border-glow:    rgba(124,58,237,0.55);

    /* Text */
    --text:        #ffffff;
    --text-dim:    #9ca3af;
    --text-faint:  #6b7280;
    --text-ghost:  rgba(255,255,255,0.25);

    /* Accents */
    --purple:        #7c3aed;
    --purple-light:  #a78bfa;
    --purple-glow:   rgba(124,58,237,0.45);
    --purple-bg:     rgba(124,58,237,0.10);
    --purple-bg-hi:  rgba(124,58,237,0.22);
    --cyan:          #22d3ee;
    --cyan-glow:     rgba(34,211,238,0.30);

    --green:    #10b981;
    --green-bg: rgba(16,185,129,0.12);
    --amber:    #f59e0b;
    --amber-bg: rgba(245,158,11,0.12);
    --red:      #f43f5e;
    --red-bg:   rgba(244,63,94,0.12);

    --linkedin: #0a66c2;
    --linkedin-bg: rgba(10,102,194,0.10);
  }

  /* ═══ Base ═══ */
  html, body, [class*="css"], .stApp {
    font-family: 'Outfit', -apple-system, system-ui, sans-serif !important;
    background: var(--bg-primary) !important;
    color: var(--text) !important;
  }
  .stApp { background: var(--bg-primary) !important; }
  .main .block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 4rem !important;
    max-width: none !important;
  }

  /* Hide Streamlit chrome */
  #MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }

  /* ═══ Typography ═══ */
  h1, h2, h3, h4, h5, h6 { font-family: 'Syne', sans-serif !important; color: var(--text) !important; letter-spacing: -0.01em; }
  h1 { font-weight: 700 !important; font-size: 2.1rem !important; }
  h2 { font-weight: 600 !important; font-size: 1.5rem !important; }
  h3 { font-weight: 600 !important; font-size: 1.15rem !important; }
  p, li, span, div, label { color: var(--text); }
  .stMarkdown p { color: var(--text); }
  small, .caption, [data-testid="stCaptionContainer"] { color: var(--text-dim) !important; }

  /* Mono labels */
  .mono, .section-label, .step-num {
    font-family: 'JetBrains Mono', monospace !important;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  /* ═══ Sidebar ═══ */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0c1020 0%, #0a0e1a 100%) !important;
    border-right: 1px solid var(--border) !important;
    min-width: 280px !important;
  }
  [data-testid="stSidebar"] > div:first-child { padding-top: 1.25rem; }
  [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--text); }

  /* Brand block */
  .brand-row {
    display: flex; align-items: center; gap: 0.65rem;
    padding: 0 1rem 0.25rem;
  }
  .brand-hex {
    width: 32px; height: 32px; border-radius: 9px;
    background: linear-gradient(135deg, var(--purple), var(--cyan));
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem; color: white; font-weight: 700;
    box-shadow: 0 0 22px var(--purple-glow);
  }
  .brand-name {
    font-family: 'Syne', sans-serif; font-weight: 700;
    font-size: 1.15rem; line-height: 1; color: var(--text);
  }
  .brand-name em { color: var(--purple-light); font-style: normal; }
  .brand-sub {
    font-family: 'JetBrains Mono', monospace; font-size: 0.55rem;
    letter-spacing: 0.16em; color: var(--text-faint);
    text-transform: uppercase; margin-top: 0.25rem; padding-left: 1rem;
  }
  .sidebar-divider {
    height: 1px; background: var(--border-faint);
    margin: 1rem 1rem 0.8rem; border: none;
  }

  /* Sidebar section labels */
  .sidebar-section {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem; letter-spacing: 0.18em;
    text-transform: uppercase; color: var(--text-faint);
    padding: 0.4rem 1rem 0.5rem;
  }

  /* Sidebar nav buttons */
  [data-testid="stSidebar"] .stButton > button {
    width: 100%;
    background: transparent !important;
    color: var(--text-dim) !important;
    border: 1px solid transparent !important;
    border-radius: 10px !important;
    padding: 0.6rem 0.85rem !important;
    text-align: left !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 0.93rem !important;
    font-weight: 500 !important;
    letter-spacing: 0 !important;
    margin: 0 !important;
    justify-content: flex-start !important;
    transition: all 0.18s ease !important;
    box-shadow: none !important;
  }
  [data-testid="stSidebar"] .stButton > button:hover {
    background: var(--purple-bg) !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
    transform: translateX(2px);
  }
  /* Active nav state (use key="nav_<id>_active") */
  [data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--purple-bg-hi), var(--purple-bg)) !important;
    color: var(--text) !important;
    border: 1px solid var(--border-purple) !important;
    box-shadow: 0 0 18px var(--purple-glow), inset 2px 0 0 var(--purple) !important;
  }

  /* Integrations card */
  .integrations-card {
    background: var(--bg-nested);
    border: 1px solid var(--border-faint);
    border-radius: 10px;
    padding: 0.7rem 0.85rem;
    margin: 0 1rem 1rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
  }
  .integrations-card .row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.18rem 0; color: var(--text-dim);
  }
  .integrations-card .status-on  { color: var(--green); }
  .integrations-card .status-off { color: var(--text-faint); }
  .integrations-card .status-on::before,
  .integrations-card .status-off::before {
    content: ""; display: inline-block; width: 6px; height: 6px;
    border-radius: 50%; margin-right: 0.4rem; vertical-align: middle;
  }
  .integrations-card .status-on::before  { background: var(--green); box-shadow: 0 0 6px var(--green); }
  .integrations-card .status-off::before { background: var(--text-ghost); }

  /* ═══ Hero header (top of main area) ═══ */
  .page-hero {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 1.8rem; padding: 0.25rem 0.25rem;
  }
  .page-hero-title {
    font-family: 'Syne', sans-serif; font-weight: 700; font-size: 2rem;
    line-height: 1.15; color: var(--text); margin: 0;
  }
  .page-hero-title em { color: var(--purple-light); font-style: normal; }
  .page-hero-sub {
    font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
    letter-spacing: 0.18em; text-transform: uppercase;
    color: var(--text-faint); margin-top: 0.4rem;
  }
  .page-hero-actions { display: flex; gap: 0.5rem; align-items: center; }
  .deploy-btn {
    background: linear-gradient(135deg, var(--purple), #6d28d9);
    color: white !important; border: none; border-radius: 10px;
    padding: 0.55rem 1.4rem; font-weight: 600; font-family: 'Outfit', sans-serif;
    cursor: pointer; box-shadow: 0 0 18px var(--purple-glow);
    letter-spacing: 0.04em; font-size: 0.9rem;
  }
  .deploy-btn:hover { filter: brightness(1.1); transform: translateY(-1px); }

  /* ═══ Section header rows ═══ */
  .section-label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.68rem !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    color: var(--text-faint) !important;
    margin: 0.5rem 0 0.85rem !important;
  }

  /* ═══ Metric cards (top dashboard row) ═══ */
  .metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.1rem 1.3rem;
    height: 110px;
    display: flex; flex-direction: column; justify-content: space-between;
    transition: all 0.2s ease;
    position: relative; overflow: hidden;
  }
  .metric-card:hover {
    border-color: var(--border-purple);
    box-shadow: 0 0 24px var(--purple-glow);
    transform: translateY(-1px);
  }
  .metric-card::before {
    content: ""; position: absolute; inset: 0;
    background: radial-gradient(ellipse at top right, var(--purple-bg) 0%, transparent 60%);
    pointer-events: none; opacity: 0.6;
  }
  .metric-card-head {
    display: flex; justify-content: space-between; align-items: flex-start;
    position: relative; z-index: 1;
  }
  .metric-card-label {
    font-family: 'JetBrains Mono', monospace; font-size: 0.62rem;
    letter-spacing: 0.16em; text-transform: uppercase; color: var(--text-dim);
  }
  .metric-card-icon {
    width: 26px; height: 26px; border-radius: 7px;
    background: var(--purple-bg);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.85rem; color: var(--purple-light);
  }
  .metric-card-body {
    display: flex; justify-content: space-between; align-items: flex-end;
    position: relative; z-index: 1;
  }
  .metric-card-value {
    font-family: 'Syne', sans-serif; font-weight: 700; font-size: 2.4rem;
    line-height: 1; color: var(--text);
  }
  .metric-card-spark { opacity: 0.85; }
  .metric-card-delta {
    font-size: 0.72rem; color: var(--green); font-weight: 600;
    margin-top: 0.4rem; font-family: 'JetBrains Mono', monospace;
  }
  .metric-card-delta.down { color: var(--red); }

  /* ═══ Dashboard / content cards ═══ */
  .dash-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 1.1rem;
    transition: border-color 0.2s ease;
  }
  .dash-card:hover { border-color: var(--border-strong); }
  .dash-card-head {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 1rem;
  }
  .dash-card-title {
    font-family: 'Syne', sans-serif; font-weight: 600; font-size: 1.05rem;
    color: var(--text); margin: 0;
  }
  .dash-card-title-sub {
    font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
    color: var(--text-faint); margin-left: 0.6rem; font-weight: 400;
  }

  /* ═══ Step cards (Recruiter pipeline) ═══ */
  .step-card {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    padding: 1.4rem 1.6rem !important;
    margin-bottom: 1.25rem !important;
    position: relative; overflow: hidden;
  }
  .step-card-glow {
    position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, var(--purple-glow), transparent);
  }
  .step-num-badge {
    display: inline-block;
    background: var(--purple-bg);
    color: var(--purple-light) !important;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem; letter-spacing: 0.14em;
    padding: 0.32rem 0.75rem; border-radius: 999px;
    border: 1px solid var(--border-purple);
    margin-bottom: 0.6rem;
  }
  .step-title {
    font-family: 'Syne', sans-serif; font-weight: 600; font-size: 1.25rem;
    color: var(--text) !important; margin-bottom: 1.1rem;
  }

  /* Parsed-JD field rows (right column of Step 01) */
  .jd-field {
    display: grid; grid-template-columns: 110px 1fr;
    gap: 0.8rem; padding: 0.4rem 0;
    border-bottom: 1px dashed var(--border-faint);
    font-size: 0.88rem;
  }
  .jd-field:last-child { border-bottom: none; }
  .jd-field .lbl {
    font-family: 'JetBrains Mono', monospace; font-size: 0.62rem;
    letter-spacing: 0.14em; text-transform: uppercase; color: var(--text-dim);
    padding-top: 2px;
  }
  .jd-field .val { color: var(--text); font-weight: 500; }

  .source-badge {
    display: inline-flex; align-items: center; gap: 0.4rem;
    padding: 0.3rem 0.7rem;
    background: var(--green-bg); color: var(--green);
    border: 1px solid var(--green);
    border-radius: 999px; font-size: 0.7rem; font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
  }
  .source-badge.offline {
    background: var(--amber-bg); color: var(--amber); border-color: var(--amber);
  }
  .source-badge.qwen {
    background: var(--purple-bg); color: var(--purple-light); border-color: var(--border-purple);
  }

  /* ═══ Tags / chips ═══ */
  .tag {
    display: inline-block; margin: 2px 5px 2px 0;
    padding: 0.22rem 0.7rem; border-radius: 999px;
    font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
    font-weight: 500; border: 1px solid transparent;
  }
  .tag-jd { background: var(--purple-bg); color: var(--purple-light); border-color: var(--border-purple); }
  .tag-skill { background: var(--bg-elevated); color: var(--text-dim); border-color: var(--border); }
  .tag-match { background: var(--green-bg); color: var(--green); border-color: var(--green); }

  /* ═══ Status pills ═══ */
  .status-pill {
    display: inline-flex; align-items: center; gap: 0.35rem;
    padding: 0.2rem 0.6rem; border-radius: 999px;
    font-family: 'JetBrains Mono', monospace; font-size: 0.65rem;
    font-weight: 600; letter-spacing: 0.04em;
  }
  .status-pill.connected { background: var(--green-bg); color: var(--green); }
  .status-pill.missing { background: var(--red-bg); color: var(--red); }
  .status-pill.ready { background: var(--purple-bg); color: var(--purple-light); }
  .status-pill::before {
    content: ""; width: 6px; height: 6px; border-radius: 50%;
    background: currentColor; box-shadow: 0 0 6px currentColor;
    animation: pulse 1.8s ease-in-out infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%      { opacity: 0.45; transform: scale(0.85); }
  }

  /* ═══ Candidate rows (Top Matches list) ═══ */
  .cand-row {
    display: grid; grid-template-columns: 32px 1fr auto auto;
    gap: 0.85rem; align-items: center;
    padding: 0.65rem 0.1rem;
    border-bottom: 1px solid var(--border-faint);
    transition: background 0.15s ease;
  }
  .cand-row:hover { background: var(--purple-bg); border-radius: 8px; padding-left: 0.6rem; padding-right: 0.6rem; }
  .cand-row:last-child { border-bottom: none; }
  .cand-avatar {
    width: 30px; height: 30px; border-radius: 50%;
    background: linear-gradient(135deg, var(--purple), var(--cyan));
    color: white; display: flex; align-items: center; justify-content: center;
    font-size: 0.78rem; font-weight: 600;
  }
  .cand-name { font-weight: 500; color: var(--text); font-size: 0.9rem; }
  .cand-meta { font-size: 0.74rem; color: var(--text-dim); }
  .cand-score {
    font-family: 'JetBrains Mono', monospace; font-weight: 600;
    font-size: 0.95rem; min-width: 36px; text-align: right;
  }
  .cand-score.high { color: var(--green); }
  .cand-score.mid  { color: var(--amber); }
  .cand-score.low  { color: var(--red); }

  /* ═══ Activity feed ═══ */
  .activity-item {
    display: grid; grid-template-columns: 22px 1fr;
    gap: 0.7rem; align-items: flex-start;
    padding: 0.55rem 0;
    border-bottom: 1px solid var(--border-faint);
  }
  .activity-item:last-child { border-bottom: none; }
  .activity-dot {
    width: 22px; height: 22px; border-radius: 50%;
    background: var(--purple-bg);
    display: flex; align-items: center; justify-content: center;
    color: var(--purple-light); font-size: 0.7rem;
    border: 1px solid var(--border-purple);
  }
  .activity-msg { color: var(--text); font-size: 0.84rem; line-height: 1.4; }
  .activity-ts {
    font-family: 'JetBrains Mono', monospace; font-size: 0.65rem;
    color: var(--text-faint); margin-top: 0.15rem;
  }

  /* ═══ Empty-state placeholders ═══ */
  .empty-state {
    border: 1.5px dashed var(--border-strong);
    border-radius: 14px;
    padding: 2.5rem 1.5rem;
    text-align: center;
    color: var(--text-ghost);
  }
  .empty-state .hex { font-size: 2rem; opacity: 0.5; margin-bottom: 0.5rem; }
  .empty-state .msg {
    font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
    letter-spacing: 0.14em; text-transform: uppercase;
  }

  /* ═══ Inputs ═══ */
  .stTextInput input, .stTextArea textarea, .stNumberInput input {
    background: var(--bg-input) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    font-family: 'Outfit', sans-serif !important;
  }
  .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
    border-color: var(--border-purple) !important;
    box-shadow: 0 0 0 1px var(--border-glow) !important;
  }
  .stSelectbox > div > div {
    background: var(--bg-input) !important; color: var(--text) !important;
    border: 1px solid var(--border) !important; border-radius: 10px !important;
  }
  .stRadio > div { gap: 0.5rem; }
  .stRadio label {
    background: var(--bg-elevated); padding: 0.4rem 0.85rem;
    border-radius: 8px; border: 1px solid var(--border);
    color: var(--text-dim) !important; cursor: pointer;
    transition: all 0.15s ease;
  }
  .stRadio label:has(input:checked) {
    background: var(--purple-bg-hi); color: var(--text) !important;
    border-color: var(--border-purple);
  }

  /* File uploader */
  [data-testid="stFileUploaderDropzone"] {
    background: var(--bg-nested) !important;
    border: 1.5px dashed var(--border-strong) !important;
    border-radius: 14px !important;
    color: var(--text-dim) !important;
    transition: all 0.2s ease;
  }
  [data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--border-purple) !important;
    background: var(--purple-bg) !important;
  }
  [data-testid="stFileUploaderDropzone"] section { color: var(--text-dim) !important; }

  /* Main-area buttons (NOT sidebar) */
  .main .stButton > button {
    background: linear-gradient(135deg, var(--purple), #6d28d9) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.55rem 1.2rem !important;
    font-weight: 600 !important;
    font-family: 'Outfit', sans-serif !important;
    box-shadow: 0 0 14px var(--purple-glow) !important;
    transition: all 0.15s ease;
  }
  .main .stButton > button:hover {
    filter: brightness(1.12);
    transform: translateY(-1px);
    box-shadow: 0 0 22px var(--purple-glow) !important;
  }

  /* Link buttons (secondary) */
  .stLinkButton a {
    background: var(--bg-elevated) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
  }
  .stLinkButton a:hover { border-color: var(--border-purple) !important; }

  /* Expanders */
  [data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
  }
  [data-testid="stExpander"] summary { color: var(--text) !important; }

  /* Dataframes */
  [data-testid="stDataFrame"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
  }

  /* Alerts */
  .stAlert {
    border-radius: 10px !important; border: 1px solid var(--border) !important;
  }
  .stAlert[data-baseweb="notification"] { background: var(--bg-elevated) !important; }

  /* Tabs (Streamlit native) — if anywhere uses st.tabs */
  .stTabs [data-baseweb="tab-list"] {
    background: transparent; border-bottom: 1px solid var(--border);
    gap: 0.4rem;
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent; color: var(--text-dim);
    border-radius: 8px 8px 0 0; padding: 0.5rem 1rem;
  }
  .stTabs [aria-selected="true"] {
    color: var(--text) !important;
    border-bottom: 2px solid var(--purple) !important;
  }

  /* Animations (subtle entrance for cards on first paint) */
  @keyframes fadeUp { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
  .dash-card, .metric-card, .step-card { animation: fadeUp 0.35s ease-out both; }
  .metric-card:nth-child(1) { animation-delay: 0.05s; }
  .metric-card:nth-child(2) { animation-delay: 0.10s; }
  .metric-card:nth-child(3) { animation-delay: 0.15s; }
  .metric-card:nth-child(4) { animation-delay: 0.20s; }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 8px; height: 8px; }
  ::-webkit-scrollbar-track { background: var(--bg-primary); }
  ::-webkit-scrollbar-thumb { background: var(--bg-elevated); border-radius: 4px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--border-purple); }
</style>
"""


def apply() -> None:
    """Inject the theme CSS into the current Streamlit page. Idempotent."""
    st.markdown(_CSS, unsafe_allow_html=True)
