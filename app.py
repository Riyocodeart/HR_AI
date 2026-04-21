import streamlit as st
import pandas as pd
import json

from jd_parser import parse_jd, parse_jd_from_upload
from filter import load_candidates, score_candidates, export_excel, export_csv
from chrome import generate_linkedin_url

st.set_page_config(
    page_title="NexRecruit AI",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Outfit:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --black:        #08080f;
        --black-mid:    #0f0f1a;
        --black-card:   #12121f;
        --black-hover:  #1a1a2e;
        --purple:       #7c3aed;
        --purple-mid:   #9d5cf6;
        --purple-light: #c4b5fd;
        --purple-pale:  #1e1040;
        --purple-glow:  rgba(124,58,237,0.18);
        --border:       rgba(255,255,255,0.12);
        --border-p:     rgba(124,58,237,0.45);
        --green:        #10b981;
        --green-bg:     rgba(16,185,129,0.15);
        --red:          #f43f5e;
        --red-bg:       rgba(244,63,94,0.15);
    }

    /* ── Global ── */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif !important;
        background: var(--black) !important;
        color: #ffffff !important;
        font-size: 17px !important;
    }

    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: var(--black-mid); }
    ::-webkit-scrollbar-thumb { background: var(--purple); border-radius: 3px; }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: var(--black-mid) !important;
        border-right: 1px solid var(--border) !important;
    }
    section[data-testid="stSidebar"] * { color: #ffffff !important; }

    .sidebar-brand {
        font-family: 'Syne', sans-serif;
        font-size: 1.6rem;
        font-weight: 800;
        background: linear-gradient(135deg, #fff 0%, var(--purple-light) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sidebar-tagline {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: rgba(255,255,255,0.4) !important;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        margin-top: 0.25rem;
    }
    .sidebar-step {
        display: flex; align-items: flex-start; gap: 0.75rem;
        padding: 0.6rem 0; border-bottom: 1px solid var(--border);
    }
    .sidebar-step-num {
        font-family: 'JetBrains Mono', monospace; font-size: 0.65rem;
        color: var(--purple-light) !important; background: var(--purple-pale);
        border: 1px solid var(--border-p); border-radius: 4px;
        padding: 0.2rem 0.45rem; min-width: 24px; text-align: center; margin-top: 0.12rem;
    }
    .sidebar-step-label { font-size: 0.92rem; font-weight: 600; color: #ffffff !important; }
    .sidebar-step-sub {
        font-family: 'JetBrains Mono', monospace; font-size: 0.67rem;
        color: rgba(255,255,255,0.35) !important; letter-spacing: 0.04em; margin-top: 0.1rem;
    }

    /* ── Main ── */
    .main .block-container { background: var(--black) !important; padding-top: 1.5rem; max-width: 1300px; }

    /* ── Page Header ── */
    .page-header { padding: 2rem 0 1rem; }
    .page-header-pill {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: var(--purple-pale); border: 1px solid var(--border-p);
        border-radius: 999px; padding: 0.35rem 1rem;
        font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
        letter-spacing: 0.12em; text-transform: uppercase; color: var(--purple-light); margin-bottom: 0.9rem;
    }
    .page-header h1 {
        font-family: 'Syne', sans-serif; font-size: 3.4rem; font-weight: 800;
        letter-spacing: -0.03em; color: #ffffff; line-height: 1.05; margin: 0 0 0.5rem;
    }
    .page-header h1 .glow {
        background: linear-gradient(135deg, var(--purple-mid) 0%, var(--purple-light) 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .page-header p {
        font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;
        color: rgba(255,255,255,0.35); letter-spacing: 0.1em; text-transform: uppercase;
    }

    /* ── Step Cards — WHITE boxes ── */
    .step-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 2.25rem 2.5rem;
        margin-bottom: 1.75rem;
        position: relative;
        overflow: hidden;
        color: #111 !important;
    }
    .step-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, var(--purple), var(--purple-light));
    }
    .step-card-glow {
        position: absolute; top: -60px; right: -60px; width: 220px; height: 220px;
        background: radial-gradient(circle, rgba(124,58,237,0.07) 0%, transparent 70%); pointer-events: none;
    }
    .step-num-badge {
        display: inline-flex; align-items: center; gap: 0.5rem;
        background: var(--purple-pale); border: 1px solid var(--border-p);
        border-radius: 8px; padding: 0.28rem 0.85rem;
        font-family: 'JetBrains Mono', monospace; font-size: 0.68rem;
        letter-spacing: 0.15em; text-transform: uppercase; color: var(--purple-light); margin-bottom: 0.5rem;
    }
    .step-title {
        font-family: 'Syne', sans-serif; font-size: 1.5rem; font-weight: 700;
        color: #111111; letter-spacing: -0.01em; margin-bottom: 1.35rem;
    }

    /* ── JD Fields — white bg, dark text ── */
    .jd-field {
        background: #f5f3ff;
        border: 1px solid #e0d7ff;
        border-radius: 10px; padding: 0.75rem 1rem; margin-bottom: 0.55rem;
        position: relative; overflow: hidden;
    }
    .jd-field::before {
        content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
        background: linear-gradient(180deg, var(--purple), var(--purple-mid)); border-radius: 4px 0 0 4px;
    }
    .jd-field .lbl {
        font-family: 'JetBrains Mono', monospace; font-size: 0.65rem;
        letter-spacing: 0.18em; text-transform: uppercase; color: var(--purple); opacity: 0.8;
    }
    .jd-field .val {
        font-family: 'Syne', sans-serif; font-size: 1.1rem; font-weight: 600;
        color: #111111; margin-top: 0.15rem;
    }

    /* ── Tags ── */
    .tag {
        display: inline-block; padding: 0.28rem 0.8rem; border-radius: 6px;
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; letter-spacing: 0.06em; margin: 0.2rem;
    }
    .tag-skill { background: var(--purple-pale); color: var(--purple-light); border: 1px solid var(--border-p); }
    .tag-match { background: var(--green-bg); color: var(--green); border: 1px solid rgba(16,185,129,0.3); }
    .tag-miss  { background: var(--red-bg); color: var(--red); border: 1px solid rgba(244,63,94,0.3); }

    /* ── LinkedIn Card ── */
    .linkedin-card {
        background: linear-gradient(135deg, #0a1628 0%, #0d1f38 100%);
        border: 1px solid rgba(0,119,181,0.35); border-radius: 12px;
        padding: 1.35rem 1.6rem; position: relative; overflow: hidden;
    }
    .linkedin-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, #0077b5, transparent);
    }
    .linkedin-card .li-label {
        font-family: 'JetBrains Mono', monospace; font-size: 0.68rem;
        letter-spacing: 0.18em; text-transform: uppercase; color: #4fa3d4; margin-bottom: 0.7rem;
    }
    .linkedin-card .li-url {
        font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: rgba(255,255,255,0.6);
        background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
        border-radius: 6px; padding: 0.7rem 1rem; word-break: break-all; line-height: 1.7;
    }

    /* ── Metric Cards — white boxes ── */
    .metric-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 14px; padding: 1.5rem 1rem; text-align: center; position: relative; overflow: hidden;
    }
    .metric-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, var(--purple), var(--purple-light));
    }
    .metric-card .m-value {
        font-family: 'Syne', sans-serif; font-size: 2.6rem; font-weight: 800;
        background: linear-gradient(135deg, var(--purple) 0%, var(--purple-light) 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; line-height: 1;
    }
    .metric-card .m-label {
        font-family: 'JetBrains Mono', monospace; font-size: 0.68rem;
        letter-spacing: 0.14em; text-transform: uppercase; color: #6b7280; margin-top: 0.45rem;
    }

    /* ── Pts Cards — white ── */
    .pts-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px; padding: 1.2rem 1.35rem; text-align: center;
        border-top: 3px solid var(--purple);
    }
    .pts-card .pts-num {
        font-family: 'Syne', sans-serif; font-size: 2rem; font-weight: 800;
        background: linear-gradient(135deg, var(--purple-mid), var(--purple-light));
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .pts-card .pts-lbl {
        font-family: 'JetBrains Mono', monospace; font-size: 0.68rem;
        letter-spacing: 0.14em; text-transform: uppercase; color: #6b7280; margin-top: 0.3rem;
    }

    /* ── Candidate Rows — white ── */
    .cand-row {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px; padding: 1.1rem 1.5rem; margin-bottom: 0.65rem;
        display: flex; align-items: center; gap: 1rem; position: relative; overflow: hidden;
    }
    .cand-row::before {
        content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
        background: linear-gradient(180deg, var(--purple), var(--purple-mid)); border-radius: 4px 0 0 4px;
    }
    .rank-badge {
        font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; font-weight: 600;
        color: var(--purple-light); background: var(--purple-pale); border: 1px solid var(--border-p);
        border-radius: 8px; padding: 0.28rem 0.55rem; min-width: 38px; text-align: center; flex-shrink: 0;
    }
    .cand-name { font-family: 'Syne', sans-serif; font-size: 1.1rem; font-weight: 700; color: #111111; }
    .cand-meta {
        font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
        letter-spacing: 0.05em; color: #6b7280; margin-top: 0.18rem;
    }
    .score-bar-bg { height: 4px; background: #f3f0ff; border-radius: 2px; margin-bottom: 0.7rem; }
    .score-bar-fill { height: 4px; border-radius: 2px; background: linear-gradient(90deg, var(--purple), var(--purple-light)); }

    /* ── Export Info — white ── */
    .export-info {
        background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 1.5rem 1.75rem;
        border-top: 3px solid var(--purple);
    }
    .export-info .ei-title {
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
        letter-spacing: 0.16em; text-transform: uppercase; color: var(--purple); margin-bottom: 0.85rem;
    }
    .export-info .ei-item {
        display: flex; align-items: flex-start; gap: 0.65rem; padding: 0.5rem 0;
        border-bottom: 1px solid #f3f4f6; font-size: 0.95rem; color: #374151;
    }
    .export-info .ei-item:last-child { border-bottom: none; }
    .export-info .ei-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--purple); flex-shrink: 0; margin-top: 0.42rem; }

    /* ── Empty placeholder ── */
    .empty-placeholder {
        text-align: center; padding: 3rem 1rem;
        border: 1px dashed rgba(124,58,237,0.3); border-radius: 12px; background: #f5f3ff;
    }
    .empty-placeholder .ep-icon { font-size: 2.2rem; opacity: 0.3; margin-bottom: 0.5rem; }
    .empty-placeholder .ep-text {
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
        letter-spacing: 0.14em; text-transform: uppercase; color: #9ca3af;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, var(--purple) 0%, #9333ea 100%) !important;
        color: #fff !important; border: none !important; border-radius: 10px !important;
        font-family: 'Outfit', sans-serif !important; font-size: 0.95rem !important;
        font-weight: 600 !important; padding: 0.7rem 1.75rem !important;
        box-shadow: 0 0 22px rgba(124,58,237,0.35) !important;
    }
    .stButton > button:hover { box-shadow: 0 0 36px rgba(124,58,237,0.6) !important; }

    .stLinkButton > a {
        background: var(--black-hover) !important; color: var(--purple-light) !important;
        border: 1px solid var(--border-p) !important; border-radius: 10px !important;
        font-family: 'Outfit', sans-serif !important; font-size: 0.9rem !important; font-weight: 600 !important;
    }
    .stDownloadButton > button {
        background: #ffffff !important; color: #111111 !important;
        border: 1px solid #e5e7eb !important; border-radius: 10px !important;
        font-family: 'Outfit', sans-serif !important; font-size: 0.92rem !important; font-weight: 500 !important;
    }
    .stDownloadButton > button:hover { border-color: var(--purple) !important; color: var(--purple) !important; }

    /* ── Inputs — white ── */
    .stTextArea textarea, .stTextInput input {
        background: #ffffff !important; border: 1px solid #e5e7eb !important;
        border-radius: 10px !important; color: #111111 !important;
        font-family: 'Outfit', sans-serif !important; font-size: 1rem !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: var(--purple) !important; box-shadow: 0 0 0 3px rgba(124,58,237,0.15) !important;
    }
    [data-testid="stFileUploader"] {
        background: #ffffff !important; border: 1px dashed rgba(124,58,237,0.4) !important; border-radius: 12px !important;
    }

    /* ── Labels & captions ── */
    label {
        font-family: 'JetBrains Mono', monospace !important; font-size: 0.75rem !important;
        letter-spacing: 0.1em !important; text-transform: uppercase !important; color: rgba(255,255,255,0.55) !important;
    }
    .step-card label { color: #6b7280 !important; }
    .stCaption { font-family: 'JetBrains Mono', monospace !important; font-size: 0.7rem !important; color: rgba(255,255,255,0.3) !important; letter-spacing: 0.07em !important; }
    .step-card .stCaption { color: #9ca3af !important; }

    /* ── Alerts ── */
    [data-testid="stAlert"] {
        background: #f5f3ff !important; border: 1px solid #e0d7ff !important;
        border-radius: 10px !important; font-family: 'Outfit', sans-serif !important;
        font-size: 1rem !important; color: #111 !important;
    }

    /* ── Progress ── */
    div[data-testid="stProgress"] > div > div { background: linear-gradient(90deg, var(--purple), var(--purple-light)) !important; }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        background: #f9fafb !important; border: 1px solid #e5e7eb !important;
        border-radius: 10px !important; font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.72rem !important; color: #6b7280 !important; letter-spacing: 0.1em !important;
    }
    .stDataFrame { border: 1px solid #e5e7eb !important; border-radius: 10px !important; overflow: hidden !important; }

    /* ── Radio ── */
    .stRadio label { font-size: 0.85rem !important; text-transform: none !important; }
    .step-card .stRadio label { color: #374151 !important; }

    /* ── Slider ── */
    .step-card .stSlider label { color: #6b7280 !important; }

    hr { border-color: rgba(255,255,255,0.08) !important; }
    .stCodeBlock { background: #1e1040 !important; border: 1px solid var(--border-p) !important; border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-brand">⬡ NexRecruit AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-tagline">Intelligent Candidate Screening</div>', unsafe_allow_html=True)
    st.divider()
    for num, title, sub in [
        ("01", "Upload Job Description",  "PDF · DOCX · TXT"),
        ("02", "Extract Requirements",    "Offline AI parsing"),
        ("03", "LinkedIn Search Link",    "Boolean query builder"),
        ("04", "Upload Candidates",       "CSV dataset upload"),
        ("05", "Filter & Score",          "Skill · Role · Experience"),
        ("06", "Export Results",          "Excel or CSV report"),
    ]:
        st.markdown(f"""
        <div class="sidebar-step">
            <div class="sidebar-step-num">{num}</div>
            <div><div class="sidebar-step-label">{title}</div>
            <div class="sidebar-step-sub">{sub}</div></div>
        </div>""", unsafe_allow_html=True)
    st.divider()
    st.markdown('<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.65rem;letter-spacing:0.15em;color:rgba(255,255,255,0.2)">⬡ FULLY OFFLINE · NO API KEY</span>', unsafe_allow_html=True)

# ─── Session State ─────────────────────────────────────────────────────────────
for key in ["jd_data", "jd_text", "candidates_df", "scored_df", "linkedin_url"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ─── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <div class="page-header-pill">⬡ &nbsp; AI-Powered Recruiting</div>
    <h1>Find the <span class="glow">Right Talent</span><br>Faster Than Ever.</h1>
    <p>Upload JD → Extract → Score → Export</p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# STEP 1
# ══════════════════════════════════════════════════════════════════════
st.markdown('<div class="step-card"><div class="step-card-glow"></div><div class="step-num-badge">⬡ &nbsp; Step 01</div><div class="step-title">Upload Job Description</div>', unsafe_allow_html=True)

jd_col1, jd_col2 = st.columns([1, 1], gap="large")

with jd_col1:
    upload_mode = st.radio("Input method", ["Upload File (PDF / DOCX / TXT)", "Paste text"], horizontal=True)
    if upload_mode == "Upload File (PDF / DOCX / TXT)":
        jd_file = st.file_uploader("Drop your JD here", type=["pdf", "docx", "txt"], label_visibility="collapsed")
        if jd_file:
            try:
                jd_data_parsed, jd_text_input = parse_jd_from_upload(jd_file)
                st.session_state.jd_data      = jd_data_parsed
                st.session_state.jd_text      = jd_text_input
                st.session_state.linkedin_url = generate_linkedin_url(jd_data_parsed)
                st.success(f"✓ Parsed **{jd_file.name}** — {len(jd_text_input):,} characters extracted")
            except ImportError as e:
                st.error(f"Missing dependency: {e}")
            except Exception as e:
                st.error(f"Could not parse file: {e}")
    else:
        jd_text_pasted = st.text_area("Paste JD text here", height=230,
            placeholder="Role: Data Scientist\nSkills: Python, ML, SQL\nLocation: Mumbai\nExperience: 3-5 years\n...",
            label_visibility="collapsed")
        if st.button("⬡  Extract JD Details", use_container_width=True):
            if jd_text_pasted:
                jd_data_parsed = parse_jd(jd_text_pasted)
                st.session_state.jd_data      = jd_data_parsed
                st.session_state.jd_text      = jd_text_pasted
                st.session_state.linkedin_url = generate_linkedin_url(jd_data_parsed)
                st.success("✓ JD extracted successfully.")
                st.rerun()

with jd_col2:
    jd = st.session_state.jd_data
    if jd:
        for label, value in [
            ("Role", jd.get("role", "—")), ("Location", jd.get("location", "—")),
            ("Experience", f"{jd.get('experience_min','?')}–{jd.get('experience_max','?')} yrs"),
            ("Industry", jd.get("industry", "—")), ("Type", jd.get("employment_type", "—")),
            ("Company", jd.get("company", "—")),
        ]:
            st.markdown(f'<div class="jd-field"><div class="lbl">{label}</div><div class="val">{value}</div></div>', unsafe_allow_html=True)
        skills = jd.get("skills", [])
        if skills:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("".join(f'<span class="tag tag-skill">{s}</span>' for s in skills), unsafe_allow_html=True)
        if jd.get("summary"):
            st.markdown("<br>", unsafe_allow_html=True)
            st.info(f"📝 {jd['summary']}")
    else:
        st.markdown('<div class="empty-placeholder"><div class="ep-icon">⬡</div><div class="ep-text">Parsed JD details will appear here</div></div>', unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# STEP 2
# ══════════════════════════════════════════════════════════════════════
if st.session_state.jd_data and st.session_state.linkedin_url:
    st.markdown('<div class="step-card"><div class="step-card-glow"></div><div class="step-num-badge">⬡ &nbsp; Step 02</div><div class="step-title">LinkedIn People Search</div>', unsafe_allow_html=True)
    li_col1, li_col2 = st.columns([3, 1], gap="large")
    url = st.session_state.linkedin_url
    jd  = st.session_state.jd_data
    with li_col1:
        st.markdown(f'<div class="linkedin-card"><div class="li-label">⬡ Generated search URL from your JD</div><div class="li-url">{url}</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.code(url, language=None)
    with li_col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.link_button("→ Open on LinkedIn", url, use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)
        skills_str = ', '.join(jd.get('skills', [])[:4])
        st.markdown(f"""
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:#374151;letter-spacing:0.05em;line-height:2.2">
            <div style="color:var(--purple);text-transform:uppercase;letter-spacing:0.15em;font-size:0.65rem;margin-bottom:0.35rem;font-weight:600">Built from</div>
            <div>Role · <strong>{jd.get('role','—')}</strong></div>
            {'<div>Skills · <strong>' + skills_str + '</strong></div>' if skills_str else ''}
        </div>""", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("Tip — After opening LinkedIn, apply filters for location, current company, or degree of connection.")
    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# STEP 3
# ══════════════════════════════════════════════════════════════════════
if st.session_state.jd_data:
    st.markdown('<div class="step-card"><div class="step-card-glow"></div><div class="step-num-badge">⬡ &nbsp; Step 03</div><div class="step-title">Upload Candidate Dataset</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        st.caption("Upload CSV · 30–50 candidates recommended")
        csv_file = st.file_uploader("Candidate CSV", type=["csv"], label_visibility="collapsed")
        if csv_file:
            df = load_candidates(csv_file)
            st.session_state.candidates_df = df
            st.success(f"✓ Loaded {len(df)} candidates across {len(df.columns)} columns")
        if st.session_state.candidates_df is not None:
            st.markdown('<div style="margin-top:0.75rem;font-family:\'JetBrains Mono\',monospace;font-size:0.7rem;color:#6b7280;letter-spacing:0.06em;line-height:2">Expected: name · role · location · experience · skills<br>Column names are auto-detected (case-insensitive).</div>', unsafe_allow_html=True)
    with c2:
        if st.session_state.candidates_df is not None:
            st.caption("Preview — first 5 rows")
            st.dataframe(st.session_state.candidates_df.head(), use_container_width=True, height=220)
    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# STEP 4
# ══════════════════════════════════════════════════════════════════════
if st.session_state.jd_data and st.session_state.candidates_df is not None:
    st.markdown('<div class="step-card"><div class="step-card-glow"></div><div class="step-num-badge">⬡ &nbsp; Step 04</div><div class="step-title">Filter, Score & Rank Candidates</div>', unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns(3)
    for col, lbl, pts in [(sc1,"Skill Match","40"), (sc2,"Role Match","30"), (sc3,"Experience","30")]:
        col.markdown(f'<div class="pts-card"><div class="pts-num">{pts}</div><div class="pts-lbl">{lbl} · max pts</div></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("⬡  Score All Candidates", use_container_width=True):
        with st.spinner("Scoring candidates…"):
            scored, name_col = score_candidates(st.session_state.candidates_df, st.session_state.jd_data)
            st.session_state.scored_df = scored
            st.session_state.name_col_detected = name_col

    if st.session_state.scored_df is not None:
        scored   = st.session_state.scored_df
        name_col = st.session_state.get("name_col_detected", None)
        st.markdown("<br>", unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        for col, val, lbl in [
            (m1, len(scored), "Total Candidates"),
            (m2, len(scored[scored["total_score"] >= 70]), "Strong Matches 70+"),
            (m3, round(scored["total_score"].mean(), 1), "Avg Score / 100"),
            (m4, scored["location_match"].str.contains("✅").sum(), "Location Match"),
        ]:
            col.markdown(f'<div class="metric-card"><div class="m-value">{val}</div><div class="m-label">{lbl}</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        top_n = st.slider("Show top N", 5, min(50, len(scored)), min(10, len(scored)))

        for _, row in scored.head(top_n).iterrows():
            rank     = int(row["rank"])
            score    = int(row["total_score"])
            name_val = str(row[name_col]) if name_col and name_col in row.index else f"Candidate {rank}"
            role_val = str(row.get("role", row.get("job_title", row.get("title", "—"))))
            loc_val  = str(row.get("location", row.get("city", "—")))
            loc_flag = str(row.get("location_match", ""))
            matched  = str(row.get("matched_skills", ""))
            missing  = str(row.get("missing_skills", ""))
            score_color = "#7c3aed" if score >= 70 else ("#374151" if score >= 50 else "#f43f5e")
            st.markdown(f"""
            <div class="cand-row">
                <div class="rank-badge">#{rank}</div>
                <div style="flex:1;min-width:0">
                    <div class="cand-name">{name_val}</div>
                    <div class="cand-meta">{role_val} &nbsp;·&nbsp; {loc_val} &nbsp;{loc_flag}</div>
                    <div style="margin-top:0.45rem">
                        {''.join(f'<span class="tag tag-match">{s}</span>' for s in matched.split(", ") if s and s!="None")}
                        {''.join(f'<span class="tag tag-miss">✗ {s}</span>' for s in missing.split(", ") if s and s!="None")}
                    </div>
                </div>
                <div style="text-align:right;min-width:68px">
                    <div style="font-family:'Syne',sans-serif;font-size:1.9rem;font-weight:800;color:{score_color};line-height:1">{score}</div>
                    <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:#9ca3af">/ 100</div>
                </div>
            </div>
            <div class="score-bar-bg"><div class="score-bar-fill" style="width:{score}%"></div></div>
            """, unsafe_allow_html=True)

        with st.expander("View full scored table"):
            st.dataframe(scored, use_container_width=True, height=400)

    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# STEP 5
# ══════════════════════════════════════════════════════════════════════
if st.session_state.scored_df is not None:
    st.markdown('<div class="step-card"><div class="step-card-glow"></div><div class="step-num-badge">⬡ &nbsp; Step 05</div><div class="step-title">Export Results</div>', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 2], gap="large")
    with col1:
        excel_bytes = export_excel(st.session_state.scored_df, st.session_state.jd_data)
        st.download_button("⬇  Download Excel Report", excel_bytes,
            file_name=f"nexrecruit_{st.session_state.jd_data.get('role','').replace(' ','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button("⬇  Download CSV", export_csv(st.session_state.scored_df),
            file_name="nexrecruit_results.csv", mime="text/csv", use_container_width=True)
    with col2:
        st.markdown("""
        <div class="export-info">
            <div class="ei-title">⬡ &nbsp; Excel Report Includes</div>
            <div class="ei-item"><div class="ei-dot"></div>Ranked candidates sheet with color-coded scores</div>
            <div class="ei-item"><div class="ei-dot"></div>JD Summary sheet with all extracted details</div>
            <div class="ei-item"><div class="ei-dot"></div>Skill match breakdown per candidate</div>
        </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ─── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:2.5rem 0 1rem;border-top:1px solid rgba(255,255,255,0.07);margin-top:1.5rem">
    <div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:800;
        background:linear-gradient(135deg,#fff,#c4b5fd);-webkit-background-clip:text;-webkit-text-fill-color:transparent">
        ⬡ NexRecruit AI
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;letter-spacing:0.2em;
        text-transform:uppercase;color:rgba(255,255,255,0.2);margin-top:0.35rem">
        Intelligent · Offline · Precise
    </div>
</div>
""", unsafe_allow_html=True)