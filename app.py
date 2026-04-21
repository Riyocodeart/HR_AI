import streamlit as st
import pandas as pd
import json

from jd_parser import parse_jd, parse_jd_from_upload
from filter import load_candidates, score_candidates, export_excel, export_csv
from chrome import generate_linkedin_url

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Recruiter",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { background: #f8fafc; }
    .step-card {
        background: white; border-radius: 12px; padding: 1.5rem;
        margin-bottom: 1rem; border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-card {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white; border-radius: 10px; padding: 1rem 1.25rem; text-align: center;
    }
    .metric-card .value { font-size: 2rem; font-weight: 700; }
    .metric-card .label { font-size: 0.8rem; opacity: 0.85; margin-top: 0.25rem; }
    .jd-field {
        background: #f8fafc; border: 1px solid #e2e8f0;
        border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem;
    }
    .jd-field .label { font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }
    .jd-field .value { font-size: 1rem; color: #1e293b; font-weight: 500; margin-top: 0.25rem; }
    .linkedin-card {
        background: linear-gradient(135deg, #0077b5 0%, #005885 100%);
        border-radius: 12px; padding: 1.25rem 1.5rem; margin-top: 0.75rem; color: white;
    }
    .linkedin-card .li-title {
        font-size: 0.8rem; font-weight: 600; opacity: 0.85;
        text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.5rem;
    }
    .linkedin-card .li-url {
        font-size: 0.78rem; word-break: break-all;
        background: rgba(255,255,255,0.12); border-radius: 6px;
        padding: 0.5rem 0.75rem; font-family: monospace;
        margin-bottom: 0.75rem; line-height: 1.5;
    }
    .candidate-row {
        display: flex; align-items: center; padding: 0.75rem 1rem;
        border-radius: 8px; margin-bottom: 0.5rem;
        border: 1px solid #e2e8f0; background: white;
    }
    .rank-badge {
        width: 28px; height: 28px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 0.8rem; flex-shrink: 0; margin-right: 0.75rem;
    }
    .rank-1 { background: #fef3c7; color: #92400e; }
    .rank-2 { background: #f1f5f9; color: #475569; }
    .rank-3 { background: #fde68a; color: #78350f; }
    .rank-other { background: #f1f5f9; color: #64748b; }
    .tag {
        display: inline-block; padding: 0.2rem 0.6rem;
        border-radius: 9999px; font-size: 0.7rem; font-weight: 500; margin: 0.15rem;
    }
    .tag-skill { background: #ede9fe; color: #5b21b6; }
    .tag-match { background: #dcfce7; color: #166534; }
    .tag-miss  { background: #fee2e2; color: #991b1b; }
    .sidebar-logo {
        font-size: 1.4rem; font-weight: 700;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    div[data-testid="stProgress"] > div > div { background: linear-gradient(90deg, #6366f1, #8b5cf6) !important; }
    .stButton > button {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: white; border: none; border-radius: 8px;
        font-weight: 600; padding: 0.5rem 1.5rem;
    }
    .stButton > button:hover { opacity: 0.9; }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">🎯 AI Recruiter</div>', unsafe_allow_html=True)
    st.caption("Intelligent Candidate Screening")
    st.divider()
    st.markdown("**Pipeline Steps**")
    for icon, label in [
        ("📄", "Upload JD  (PDF / DOCX / TXT)"),
        ("🤖", "Offline Extraction"),
        ("🔗", "LinkedIn Search Link"),
        ("📊", "Upload Candidates"),
        ("🔍", "Filter & Score"),
        ("📥", "Export Results"),
    ]:
        st.markdown(f"{icon} {label}")
    st.divider()
    st.caption("No API key required — runs fully offline.")

# ─── Session State ─────────────────────────────────────────────────────────────
for key in ["jd_data", "jd_text", "candidates_df", "scored_df", "linkedin_url"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ─── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🎯 AI Recruiter — Intelligent Candidate Screening")
st.caption("Upload a JD → extract requirements → score candidates → find talent on LinkedIn")
st.divider()

# ══════════════════════════════════════════════════════════════════════
# STEP 1 — Upload JD & Parse
# ══════════════════════════════════════════════════════════════════════
st.markdown('<div class="step-card">', unsafe_allow_html=True)
st.markdown("### 📄 Step 1 — Upload Job Description")

jd_col1, jd_col2 = st.columns([1, 1], gap="large")

with jd_col1:
    upload_mode = st.radio("Input method", ["Upload File (PDF / DOCX / TXT)", "Paste text"], horizontal=True)

    if upload_mode == "Upload File (PDF / DOCX / TXT)":
        jd_file = st.file_uploader(
            "Drop your JD here", type=["pdf", "docx", "txt"], label_visibility="collapsed"
        )
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
        jd_text_pasted = st.text_area(
            "Paste JD text here", height=200,
            placeholder="Role: Data Scientist\nSkills: Python, ML, SQL\nLocation: Mumbai\nExperience: 3-5 years\n...",
            label_visibility="collapsed",
        )
        parse_btn = st.button("🤖 Extract JD Details", use_container_width=True)
        if parse_btn and jd_text_pasted:
            jd_data_parsed = parse_jd(jd_text_pasted)
            st.session_state.jd_data      = jd_data_parsed
            st.session_state.jd_text      = jd_text_pasted
            st.session_state.linkedin_url = generate_linkedin_url(jd_data_parsed)
            st.success("✅ JD extracted successfully!")
            st.rerun()

with jd_col2:
    jd = st.session_state.jd_data
    if jd:
        for label, value in [
            ("Role",       jd.get("role", "—")),
            ("Location",   jd.get("location", "—")),
            ("Experience", f"{jd.get('experience_min','?')}–{jd.get('experience_max','?')} yrs"),
            ("Industry",   jd.get("industry", "—")),
            ("Type",       jd.get("employment_type", "—")),
            ("Company",    jd.get("company", "—")),
        ]:
            st.markdown(f'<div class="jd-field"><div class="label">{label}</div><div class="value">{value}</div></div>', unsafe_allow_html=True)

        skills = jd.get("skills", [])
        if skills:
            st.markdown("**Skills Required**")
            st.markdown("".join(f'<span class="tag tag-skill">{s}</span>' for s in skills), unsafe_allow_html=True)

        if jd.get("summary"):
            st.info(f"📝 {jd['summary']}")
    else:
        st.info("📋 Extracted JD details will appear here after parsing.")

st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# STEP 2 — LinkedIn Search Link
# ══════════════════════════════════════════════════════════════════════
if st.session_state.jd_data and st.session_state.linkedin_url:
    st.markdown('<div class="step-card">', unsafe_allow_html=True)
    st.markdown("### 🔗 Step 2 — LinkedIn People Search")

    li_col1, li_col2 = st.columns([3, 1], gap="large")
    url = st.session_state.linkedin_url
    jd  = st.session_state.jd_data

    with li_col1:
        st.markdown(f"""
        <div class="linkedin-card">
            <div class="li-title">🔍 LinkedIn Search URL — generated from your JD</div>
            <div class="li-url">{url}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("**Copy the link** (click the icon on the right of the code block):")
        st.code(url, language=None)

    with li_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.link_button("🚀 Open on LinkedIn", url, use_container_width=True)
        st.markdown("**Query built from:**")
        st.markdown(f"- Role: `{jd.get('role','—')}`")
        skills = jd.get("skills", [])
        if skills:
            st.markdown(f"- Skills: `{', '.join(skills[:4])}`")

    st.caption("💡 Tip — After opening LinkedIn, add filters like **location**, **current company**, or **connections** to narrow your search.")
    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# STEP 3 — Upload Candidates CSV
# ══════════════════════════════════════════════════════════════════════
if st.session_state.jd_data:
    st.markdown('<div class="step-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Step 3 — Upload Candidate Dataset")

    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        st.markdown("**Upload CSV** (30–50 candidates recommended)")
        csv_file = st.file_uploader("Candidate CSV", type=["csv"], label_visibility="collapsed")
        if csv_file:
            df = load_candidates(csv_file)
            st.session_state.candidates_df = df
            st.success(f"✓ Loaded {len(df)} candidates, {len(df.columns)} columns")
        if st.session_state.candidates_df is not None:
            st.markdown("**Expected columns:** name · role · location · experience · skills")
            st.caption("Column names are auto-detected (case-insensitive).")

    with c2:
        if st.session_state.candidates_df is not None:
            st.markdown("**Preview (first 5 rows)**")
            st.dataframe(st.session_state.candidates_df.head(), use_container_width=True, height=220)

    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# STEP 4 — Filter & Score
# ══════════════════════════════════════════════════════════════════════
if st.session_state.jd_data and st.session_state.candidates_df is not None:
    st.markdown('<div class="step-card">', unsafe_allow_html=True)
    st.markdown("### 🔍 Step 4 — Filter, Score & Rank Candidates")

    jd = st.session_state.jd_data
    sc1, sc2, sc3 = st.columns(3)
    sc1.markdown("🧠 **Skill Match** — up to 40 pts")
    sc2.markdown("🎯 **Role Match** — up to 30 pts")
    sc3.markdown("📅 **Experience Match** — up to 30 pts")

    if st.button("🚀 Score All Candidates", use_container_width=True):
        with st.spinner("Scoring candidates…"):
            scored, name_col = score_candidates(st.session_state.candidates_df, jd)
            st.session_state.scored_df = scored
            st.session_state.name_col_detected = name_col

    if st.session_state.scored_df is not None:
        scored   = st.session_state.scored_df
        name_col = st.session_state.get("name_col_detected", None)

        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f'<div class="metric-card"><div class="value">{len(scored)}</div><div class="label">Total Candidates</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-card"><div class="value">{len(scored[scored["total_score"] >= 70])}</div><div class="label">Strong Matches (70+)</div></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="metric-card"><div class="value">{round(scored["total_score"].mean(), 1)}</div><div class="label">Avg Score / 100</div></div>', unsafe_allow_html=True)
        m4.markdown(f'<div class="metric-card"><div class="value">{scored["location_match"].str.contains("✅").sum()}</div><div class="label">Location Match</div></div>', unsafe_allow_html=True)

        st.divider()
        st.markdown("#### 🏆 Top Candidates")
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
            rank_cls = {1: "rank-1", 2: "rank-2", 3: "rank-3"}.get(rank, "rank-other")

            st.markdown(f"""
            <div class="candidate-row">
                <div class="rank-badge {rank_cls}">#{rank}</div>
                <div style="flex:1">
                    <div style="font-weight:600;color:#1e293b">{name_val}</div>
                    <div style="font-size:0.8rem;color:#64748b">{role_val} &nbsp;·&nbsp; {loc_val} &nbsp;{loc_flag}</div>
                    <div style="margin-top:0.3rem">
                        {''.join(f'<span class="tag tag-match">{s}</span>' for s in matched.split(", ") if s and s!="None")}
                        {''.join(f'<span class="tag tag-miss">✗ {s}</span>' for s in missing.split(", ") if s and s!="None")}
                    </div>
                </div>
                <div style="text-align:right;min-width:70px">
                    <div style="font-size:1.4rem;font-weight:700;color:#6366f1">{score}</div>
                    <div style="font-size:0.7rem;color:#94a3b8">/ 100</div>
                </div>
            </div>
            <div style="height:4px;background:#f1f5f9;border-radius:2px;margin-bottom:0.5rem">
                <div style="height:4px;width:{score}%;background:linear-gradient(90deg,#6366f1,#8b5cf6);border-radius:2px"></div>
            </div>
            """, unsafe_allow_html=True)

        with st.expander("📋 View full scored table"):
            st.dataframe(scored, use_container_width=True, height=400)

    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# STEP 5 — Export
# ══════════════════════════════════════════════════════════════════════
if st.session_state.scored_df is not None:
    st.markdown('<div class="step-card">', unsafe_allow_html=True)
    st.markdown("### 📥 Step 5 — Export Results")

    col1, col2 = st.columns([1, 2])
    with col1:
        excel_bytes = export_excel(st.session_state.scored_df, st.session_state.jd_data)
        st.download_button(
            "⬇️ Download Excel Report", excel_bytes,
            file_name=f"ai_recruiter_results_{st.session_state.jd_data.get('role','').replace(' ','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.download_button(
            "⬇️ Download CSV", export_csv(st.session_state.scored_df),
            file_name="ai_recruiter_results.csv", mime="text/csv",
            use_container_width=True,
        )
    with col2:
        st.info(
            "📊 **Excel report includes:**\n"
            "- Ranked candidates sheet with color-coded scores (green/yellow/red)\n"
            "- JD Summary sheet with all extracted details\n"
            "- Skill match breakdown per candidate"
        )
    st.markdown("</div>", unsafe_allow_html=True)