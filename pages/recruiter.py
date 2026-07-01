"""
pages.recruiter
===============
The recruiter pipeline — Steps 01 (Upload JD) → 02 (Upload Candidates)
→ 03 (Score) → 04 (Export). Main workflow page.

Logic preserved verbatim from the legacy ``app.py``; only the entry
point and imports were reorganised so this page can be loaded by the
router in ``app.py``.

Dependencies
------------
* ``services.jd_service``        — three-tier parsing chain
* ``services.scoring_service``   — candidate scoring
* ``services.linkedin_service``  — URL builders (used after parse)
* ``services.export_service``    — Excel / CSV export
* ``core.helpers``               — gemini_keys, score_band
* ``core.cleaner``               — DataCleaner (existing module)
* ``ui.jd_parser_animation``     — file-text extraction helper
"""

from __future__ import annotations

import hashlib

import streamlit as st

from core.cleaner import DataCleaner
from core.helpers import gemini_keys as _gemini_keys, score_band
from services import jd_service
from services.export_service import export_csv, export_excel
from services.linkedin_service import (
    generate_linkedin_url,
    generate_xray_search_url,
)
from services.scoring_service import (
    detect_columns,
    load_candidates,
    score_candidates,
)
from ui.jd_parser_animation import extract_text_from_upload


# ─── Local helpers ─────────────────────────────────────────────────────────────
def _score_badge(score) -> str:
    """``"score-high" | "score-mid" | "score-low"`` — used by the candidate
    card HTML which already styles those class names."""
    return f"score-{score_band(score)}"


def _parse_jd_chain(jd_text: str, container):
    """Thin local alias — keeps the recruiter call sites unchanged."""
    return jd_service.parse_jd_chain(jd_text, container)


# ─── Public entry point ────────────────────────────────────────────────────────
def render() -> None:
    """Render the full recruiter pipeline."""

    # Global UI Design Adjustments to fix flat layout issues across the board
    st.markdown("""
    <style>
        .premium-cand-card {
            background: #0d1117 !important;
            border: 1px solid #21262d !important;
            border-radius: 12px !important;
            padding: 1.5rem !important;
            margin-bottom: 1.25rem !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .section-label {
            font-size: 0.68rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.08em !important;
            color: #8b949e !important;
            margin-bottom: 0.35rem !important;
            margin-top: 0.75rem !important;
        }
        .tag-container {
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 6px !important;
            margin-bottom: 0.5rem !important;
        }
        .clean-tag-match {
            background: rgba(46, 160, 67, 0.15) !important;
            color: #3fb950 !important;
            border: 1px solid rgba(46, 160, 67, 0.3) !important;
            padding: 3px 10px !important;
            border-radius: 6px !important;
            font-size: 0.78rem !important;
            font-weight: 500 !important;
        }
        .clean-tag-miss {
            background: rgba(248, 81, 73, 0.1) !important;
            color: #f85149 !important;
            border: 1px solid rgba(248, 81, 73, 0.2) !important;
            padding: 3px 10px !important;
            border-radius: 6px !important;
            font-size: 0.78rem !important;
            font-weight: 500 !important;
            opacity: 0.85;
        }
        .score-display-box {
            background: rgba(88, 166, 255, 0.08) !important;
            border: 1px solid rgba(88, 166, 255, 0.2) !important;
            padding: 0.5rem 1rem !important;
            border-radius: 8px !important;
            text-align: center !important;
            min-width: 80px !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="page-header">
      <div class="page-header-pill">⬡ &nbsp; AI-Powered Recruiting</div>
      <h1>Find the <span class="glow">Right Talent</span><br>Faster Than Ever.</h1>
      <p>Upload JD → AI Extract → Score → Export → Email</p>
    </div>
    """, unsafe_allow_html=True)

    # ── STEP 1: Upload JD ──────────────────────────────────────────────────────
    st.markdown('<div class="step-card"><div class="step-card-glow"></div><div class="step-num-badge">⬡ &nbsp; Step 01</div><div class="step-title">Upload Job Description</div>', unsafe_allow_html=True)
    jd_col1, jd_col2 = st.columns([1, 1], gap="large")

    # Capture what (if anything) needs parsing this rerun.
    jd_text_to_parse: str | None = None
    file_hash_to_set: str | None = None

    with jd_col1:
        upload_mode = st.radio("Input method", ["Upload File (PDF / DOCX / TXT)", "Paste text"], horizontal=True)
        if upload_mode == "Upload File (PDF / DOCX / TXT)":
            jd_file = st.file_uploader("Drop your JD here", type=["pdf","docx","txt"], label_visibility="collapsed")
            if jd_file:
                file_hash = hashlib.md5(jd_file.getvalue()).hexdigest()
                if st.session_state._jd_file_hash != file_hash:
                    extracted = extract_text_from_upload(jd_file)
                    if not extracted.strip():
                        st.error("Could not extract any text from this file.")
                    else:
                        jd_text_to_parse = extracted
                        file_hash_to_set = file_hash
        else:
            jd_text_pasted = st.text_area(
                "Paste JD text here", height=200,
                placeholder="Role: Data Scientist\nCompany: Acme Corp\nSkills: Python, ML, SQL\nLocation: Mumbai\nExperience: 3-5 years...",
                label_visibility="collapsed",
            )
            if st.button("⬡  Extract JD Details", width='stretch'):
                if jd_text_pasted.strip():
                    jd_text_to_parse = jd_text_pasted

        if st.session_state.jd_data:
            with st.expander("✏ Manually correct extracted fields", expanded=False):
                jd = st.session_state.jd_data
                ca, cb = st.columns(2)
                new_role    = ca.text_input("Role",    value=jd.get("role","") or "")
                new_company = cb.text_input("Company", value=jd.get("company","") or "")
                cc, cd = st.columns(2)
                new_loc     = cc.text_input("Location", value=jd.get("location","") or "")
                new_ind     = cd.text_input("Industry", value=jd.get("industry","") or "")
                if st.button("💾 Save Corrections"):
                    updated = dict(st.session_state.jd_data)
                    updated.update(role=new_role or updated.get("role"), company=new_company or updated.get("company"),
                                   location=new_loc or updated.get("location"), industry=new_ind or updated.get("industry"))
                    st.session_state.jd_data      = updated
                    st.session_state.linkedin_url = generate_linkedin_url(updated)
                    st.session_state.xray_url     = generate_xray_search_url(updated)
                    st.success("✓ Saved.")
                    st.rerun()

    # ── Right column: animate on fresh parse, static otherwise, empty if neither
    if jd_text_to_parse:
        # Three-tier chain: Gemini → Qwen → regex. Animation wraps the winner.
        legacy = _parse_jd_chain(jd_text_to_parse, jd_col2)

        if legacy:
            st.session_state.jd_data       = legacy
            st.session_state.jd_text       = jd_text_to_parse
            st.session_state.jd_source     = legacy.get("_source", "qwen-offline")
            st.session_state.linkedin_url  = generate_linkedin_url(legacy)
            st.session_state.xray_url      = generate_xray_search_url(legacy)
            if file_hash_to_set:
                st.session_state._jd_file_hash = file_hash_to_set

    elif st.session_state.jd_data:
        with jd_col2:
            jd = st.session_state.jd_data
            src = st.session_state.jd_source or "qwen-offline"
            badge_cls = "source-badge" if src in ("gemini", "qwen-offline") else "source-badge offline"
            src_label = {
                "gemini":           "✓ Gemini AI Extracted",
                "qwen-offline":     "✓ Qwen 2.5 · Offline",
                "offline-regex":    "⚠ Offline Regex Extracted",
            }.get(src, src)
            st.markdown(f'<div style="margin-bottom:0.75rem"><span class="{badge_cls}">{src_label}</span></div>', unsafe_allow_html=True)
            for label, value in [
                ("Role", jd.get("role","—")), ("Company", jd.get("company","—")),
                ("Location", jd.get("location","—")),
                ("Experience", f"{jd.get('experience_min','?')}–{jd.get('experience_max','?')} yrs"),
                ("Industry", jd.get("industry","—")), ("Type", jd.get("employment_type","—")),
                ("Education", jd.get("education","—")),
            ]:
                st.markdown(f'<div class="jd-field"><div class="lbl">{label}</div><div class="val">{value}</div></div>', unsafe_allow_html=True)
            skills = jd.get("skills", [])
            if skills:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("".join(f'<span class="tag tag-jd">{s}</span>' for s in skills), unsafe_allow_html=True)
            if jd.get("summary"):
                st.markdown(f'<div style="margin-top:0.75rem;background:#f5f3ff;border:1px solid #ede9fe;border-radius:10px;padding:0.75rem 1rem;font-size:0.88rem;color:#374151">📝 {jd["summary"]}</div>', unsafe_allow_html=True)
    else:
        with jd_col2:
            st.markdown("""
            <div style="border:1.5px dashed rgba(124,58,237,0.25);border-radius:14px;
                        padding:3rem 2rem;text-align:center;color:rgba(255,255,255,0.15)">
              <div style="font-size:2rem;margin-bottom:0.5rem">⬡</div>
              <div style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase">
                Parsed JD details will appear here
              </div>
            </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── STEP 2: Upload Candidates ───────────────────────────────────────────────
    if st.session_state.jd_data:
        st.markdown('<div class="step-card"><div class="step-card-glow"></div><div class="step-num-badge">⬡ &nbsp; Step 02</div><div class="step-title">Upload Candidate Dataset</div>', unsafe_allow_html=True)

        tab_jsonl, tab_csv = st.tabs(["📄  JSONL (Hackathon Dataset)", "📊  CSV / Excel"])

        # ── Tab A: JSONL ──────────────────────────────────────────────────
        with tab_jsonl:
            ja, jb = st.columns([1, 1], gap="large")
            with ja:
                import glob
                import os as _os
                from pathlib import Path as _Path

                def _find_jsonl() -> str:
                    search_roots = [
                        _os.getcwd(),
                        _os.path.dirname(_os.path.abspath(__file__)),
                        _os.path.join(_os.path.expanduser("~"), "Downloads"),
                        _os.path.join(_os.path.expanduser("~"), "Desktop"),
                        _os.path.join(_os.path.expanduser("~"), "OneDrive"),
                        _os.path.join(_os.path.expanduser("~"), "Documents"),
                    ]
                    for root in search_roots:
                        try:
                            for match in glob.glob(
                                _os.path.join(root, "**", "candidates.jsonl"),
                                recursive=True,
                            ):
                                return match
                        except Exception:
                            continue
                    return ""

                if not st.session_state.get("jsonl_auto_path"):
                    st.session_state.jsonl_auto_path = _find_jsonl()

                st.markdown("**⚡ Load from local path**")
                st.caption("Reads directly from disk — no browser upload limit.")

                detected = st.session_state.jsonl_auto_path or ""
                if detected:
                    st.success(f"✓ Found: `{detected}`")
                else:
                    st.warning("Could not auto-detect — paste the full path below.")

                local_path = st.text_input(
                    "Path to candidates.jsonl",
                    value=detected,
                    placeholder=r"C:\Users\...\candidates.jsonl",
                    label_visibility="collapsed",
                    key="jsonl_local_path",
                )
                load_local = st.button("⚡ Load from Path", use_container_width=True, key="btn_load_local")

                st.markdown("<br>", unsafe_allow_html=True)

                st.markdown("**📁 Or upload file** *(only if under 200 MB)*")
                jsonl_file = st.file_uploader(
                    "candidates.jsonl",
                    type=["jsonl", "json"],
                    label_visibility="collapsed",
                    key="jsonl_uploader",
                )

                def _load_jsonl_from_path(path: str) -> None:
                    import pandas as pd
                    from parser.jsonl_reader import JSONLReader

                    if not _Path(path).exists():
                        st.error(f"File not found: {path}")
                        return

                    with st.spinner(f"Reading {_Path(path).name}… (100k candidates takes ~25s)"):
                        reader = JSONLReader(path, skip_invalid=True)
                        candidates_raw, parse_errors = reader.read_all()

                    cleaner = DataCleaner()
                    rows = []
                    for c in candidates_raw:
                        raw_dict = c.to_dict() if hasattr(c, "to_dict") else {}
                        try:
                            raw_dict = cleaner.clean_candidate(raw_dict)
                        except Exception:
                            pass

                        p   = c.profile
                        sig = c.redrob_signals
                        edu_str = ""
                        if c.education:
                            edu_str = f"{c.education[0].degree} {c.education[0].institution}".strip()
                        rows.append({
                            "candidate_id":       c.candidate_id,
                            "name":               p.anonymized_name or c.candidate_id,
                            "role":               p.current_title,
                            "company":            p.current_company,
                            "location":           ", ".join(filter(None, [p.location, p.country])),
                            "experience":         p.years_of_experience,
                            "skills":             ", ".join(s.name for s in c.skills),
                            "education":          edu_str,
                            "email":              "",
                            "open_to_work":       sig.open_to_work_flag,
                            "notice_period_days": sig.notice_period_days,
                            "github_score":       sig.github_activity_score,
                            "response_rate":      sig.recruiter_response_rate,
                            "last_active":        sig.last_active_date or "",
                            "completeness":       sig.profile_completeness_score,
                            "quality_score":      raw_dict.get("quality_score", 100),
                            "data_status":        raw_dict.get("status", ""),
                            "warnings":           raw_dict.get("warnings", ""),
                        })

                    df = pd.DataFrame(rows)
                    rejected_mask = df["data_status"] == "Rejected"
                    st.session_state.rejected_df = df[rejected_mask].reset_index(drop=True)
                    df = df[~rejected_mask].reset_index(drop=True)

                    st.session_state.candidates_df = df
                    st.session_state.col_map = {
                        "name": "name", "role": "role", "location": "location",
                        "experience": "experience", "skills": "skills",
                        "company": "company", "education": "education",
                    }

                    n_rej = int(rejected_mask.sum())
                    st.success(
                        f"✓ {len(df):,} candidates loaded · "
                        f"{len(parse_errors)} skipped · "
                        f"{n_rej:,} rejected by data-quality rules (excluded from scoring)"
                    )

                    if n_rej:
                        with st.expander(f"⛔ {n_rej:,} rejected candidates (excluded from scoring)"):
                            st.dataframe(
                                st.session_state.rejected_df[
                                    ["candidate_id", "name", "quality_score", "warnings"]
                                ].head(20),
                                use_container_width=True,
                            )
                    if parse_errors:
                        with st.expander(f"⚠ {len(parse_errors)} skipped"):
                            for e in parse_errors[:10]:
                                st.caption(f"Line {e.line_number}: {e.reason}")

                if load_local and local_path.strip():
                    try:
                        _load_jsonl_from_path(local_path.strip())
                    except Exception as e:
                        st.error(f"Could not load: {e}")

                if jsonl_file:
                    try:
                        import tempfile
                        with tempfile.NamedTemporaryFile(
                            delete=False, suffix=".jsonl", mode="wb",
                        ) as tmp:
                            tmp.write(jsonl_file.read())
                            tmp_path = tmp.name
                        _load_jsonl_from_path(tmp_path)
                        _os.unlink(tmp_path)
                    except Exception as e:
                        st.error(f"Could not load JSONL: {e}")

            with jb:
                if st.session_state.candidates_df is not None:
                    st.caption("Preview — first 5 rows")
                    st.dataframe(
                        st.session_state.candidates_df.head(),
                        use_container_width=True, height=240,
                    )

        # ── Tab B: CSV / Excel ────────────────────────────────────────────
        with tab_csv:
            ca, cb = st.columns([1, 1], gap="large")
            with ca:
                st.caption("CSV or Excel (.xlsx) — any column names. AI maps them automatically.")
                cand_file = st.file_uploader(
                    "Candidate file",
                    type=["csv", "xlsx", "xls"],
                    label_visibility="collapsed",
                    key="csv_uploader",
                )
                if cand_file:
                    try:
                        df = load_candidates(cand_file)
                        st.session_state.candidates_df = df
                        st.success(f"✓ {len(df)} candidates loaded · {len(df.columns)} columns")
                        col_map = detect_columns(df, st.session_state.jd_data, api_key=_gemini_keys())
                        st.session_state.col_map = col_map
                        if col_map:
                            st.caption("Detected: " + " · ".join(f"{v}→{k}" for k, v in col_map.items()))
                    except Exception as e:
                        st.error(f"Could not load file: {e}")
            with cb:
                if st.session_state.candidates_df is not None:
                    st.caption("Preview — first 5 rows")
                    st.dataframe(
                        st.session_state.candidates_df.head(),
                        use_container_width=True, height=240,
                    )

        st.markdown("</div>", unsafe_allow_html=True)

    # ── STEP 3: Score ───────────────────────────────────────────────────────────
    if st.session_state.jd_data and st.session_state.candidates_df is not None:
        st.markdown('<div class="step-card"><div class="step-card-glow"></div><div class="step-num-badge">⬡ &nbsp; Step 03</div><div class="step-title">AI Score & Rank Candidates</div>', unsafe_allow_html=True)
        sc1, sc2, sc3 = st.columns(3)
        keys = _gemini_keys()
        for col, lbl, pts, desc in [
            (sc1, "Skill Match", "40", "Required skills vs. candidate's full profile"),
            (sc2, "Role Match",  "30", "Title / seniority alignment"),
            (sc3, "Signal",      "30", "Location, career signals, activity, education"),
        ]:
            col.markdown(f"""
            <div class="metric-card" style="text-align:center">
              <div class="m-value">{pts}</div>
              <div class="m-label">{lbl} · max pts</div>
              <div style="font-size:0.72rem;color:rgba(255,255,255,0.3);margin-top:0.3rem">{desc}</div>
            </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if keys:
            st.markdown('<span class="source-badge">⬡ Gemini AI Scoring</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="source-badge offline">⬡ Intelligent Offline Scoring — Weighted Skill + Role + Signal</span>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("⬡  Score All Candidates", width='stretch'):
            with st.spinner("Scoring candidates… this may take a moment for large datasets"):
                try:
                    scored, name_col, source = score_candidates(
                        st.session_state.candidates_df,
                        st.session_state.jd_data,
                        api_key=_gemini_keys()
                    )
                    st.session_state.scored_df         = scored
                    st.session_state.name_col_detected = name_col
                    st.session_state.score_source      = source
                    st.success(f"✓ Scored {len(scored)} candidates via {'Gemini AI' if source=='gemini' else 'offline rules'}")
                except Exception as e:
                    st.error(f"Scoring failed: {e}")

        if st.session_state.scored_df is not None:
            scored   = st.session_state.scored_df
            name_col = st.session_state.name_col_detected
            source   = st.session_state.score_source or "offline-rule"

            st.markdown("<br>", unsafe_allow_html=True)
            m1, m2, m3, m4 = st.columns(4)
            for col, val, lbl in [
                (m1, len(scored), "Total Candidates"),
                (m2, len(scored[scored["total_score"] >= 70]), "Strong Matches 70+"),
                (m3, round(float(scored["total_score"].mean()), 1), "Avg Score / 100"),
                (m4, int(scored["total_score"].max()), "Top Score"),
            ]:
                col.markdown(f'<div class="metric-card"><div class="m-value">{val}</div><div class="m-label">{lbl}</div></div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            top_n = st.slider("Show top N candidates", 5, min(100, len(scored)), min(10, len(scored)))
            for _, row in scored.head(top_n).iterrows():
                rank     = int(row.get("rank", 0))
                score    = int(row.get("total_score", 0))
                name_val = str(row[name_col]) if name_col and name_col in row.index else f"Candidate #{rank}"
                role_val = str(row.get(st.session_state.col_map.get("role","role"), row.get("role","—")))
                loc_val  = str(row.get(st.session_state.col_map.get("location","location"), row.get("location","—")))
                
                # ── STAGE 1: COMPREHENSIVE SKILL CONSOLIDATION ──────────────────
                raw_matched = [s.strip().lower() for s in str(row.get("matched_skills","")).split(",") if s.strip()]
                raw_missing = [s.strip().lower() for s in str(row.get("missing_skills","")).split(",") if s.strip()]
                
                VECTOR_DBS = {"pinecone", "weaviate", "qdrant", "milvus", "opensearch", "elasticsearch", "faiss"}
                METRICS = {"ndcg", "mrr", "map"}
                
                matched = []
                has_vector_db_match = False
                has_metrics_match = False
                
                for s in raw_matched:
                    if s in VECTOR_DBS:
                        if not has_vector_db_match:
                            matched.append("Vector Databases")
                            has_vector_db_match = True
                    elif s in METRICS:
                        if not has_metrics_match:
                            matched.append("Ranking Metrics (NDCG/MRR/MAP)")
                            has_metrics_match = True
                    elif "or something similar" in s or s == "none":
                        continue
                    else:
                        matched.append(s.title() if len(s) > 4 else s.upper())
                        
                missing = []
                for s in raw_missing:
                    if s in VECTOR_DBS:
                        if not has_vector_db_match and "Vector Databases" not in missing:
                            missing.append("Vector Databases")
                    elif s in METRICS:
                        if not has_metrics_match and "Ranking Metrics (NDCG/MRR/MAP)" not in missing:
                            missing.append("Ranking Metrics (NDCG/MRR/MAP)")
                    elif "or something similar" in s or s == "none":
                        continue
                    else:
                        missing.append(s.title() if len(s) > 4 else s.upper())
                # ────────────────────────────────────────────────────────────────

                rationale = str(row.get("rationale",""))
                skill_sc  = int(row.get("skill_score", 0))
                role_sc   = int(row.get("role_score", 0))
                signal_sc = int(row.get("signal_score", 0))

                matched_badges = "".join(f'<span class="clean-tag-match">✓ {m}</span>' for m in matched)
                missing_badges = "".join(f'<span class="clean-tag-miss">✗ {x}</span>' for x in missing)

                st.markdown(f"""
                <div class="premium-cand-card">
                  <div style="display: flex; align-items: flex-start; justify-content: space-between;">
                    <div>
                      <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-family: monospace; font-size: 1.1rem; color: #58a6ff; font-weight: bold;">#{rank}</span>
                        <span style="font-size: 1.2rem; font-weight: 600; color: #c9d1d9;">{name_val}</span>
                      </div>
                      <div style="font-size: 0.88rem; color: #8b949e; margin-top: 0.25rem;">
                        {role_val} &nbsp;·&nbsp; <span style="color: #6e7681;">{loc_val}</span>
                      </div>
                      <div style="font-family: monospace; font-size: 0.78rem; color: #8b949e; margin-top: 0.4rem; background: #161b22; padding: 4px 8px; border-radius: 4px; display: inline-block;">
                        Skills: <span style="color: #58a6ff;">{skill_sc}/40</span> &nbsp;|&nbsp; Role: <span style="color: #58a6ff;">{role_sc}/30</span> &nbsp;|&nbsp; Signals: <span style="color: #58a6ff;">{signal_sc}/30</span>
                      </div>
                    </div>
                    <div class="score-display-box">
                      <div style="font-size: 1.6rem; font-weight: 700; color: #58a6ff; line-height: 1.1;">{score}</div>
                      <div style="font-size: 0.68rem; color: #8b949e; text-transform: uppercase; letter-spacing: 0.05em;">Score</div>
                    </div>
                  </div>
                  
                  {f'<div class="section-label">Matched Requirements</div><div class="tag-container">{matched_badges}</div>' if matched_badges else ''}
                  {f'<div class="section-label">Missing Requirements</div><div class="tag-container">{missing_badges}</div>' if missing_badges else ''}
                  
                  {"" if not rationale or rationale == "nan" else f'<div style="margin-top: 1rem; padding-top: 0.75rem; border-top: 1px solid #21262d; font-size: 0.85rem; color: #8b949e; line-height: 1.4;">💡 <strong>AI Insights:</strong> {rationale}</div>'}
                </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✉  Go to Email Outreach →", width='stretch'):
                st.session_state.active_tab = "email"
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # ── STEP 4: Export ─────────────────────────────────────────────────────────
    if st.session_state.scored_df is not None:
        st.markdown('<div class="step-card"><div class="step-card-glow"></div><div class="step-num-badge">⬡ &nbsp; Step 04</div><div class="step-title">Export Results</div>', unsafe_allow_html=True)
        # Guard all session state keys that may not exist
        _jd      = st.session_state.get("jd_data") or {}
        _col_map = st.session_state.get("col_map") or {}
        _src     = st.session_state.get("score_source") or "offline-rule"
        _sdf     = st.session_state.scored_df
        col1, col2 = st.columns([1, 2], gap="large")
        with col1:
            import pandas as _pd
            _role_slug = (_jd.get("role") or "candidates").replace(" ","_")

            # ── Hackathon submission CSV (candidate_id, rank, score, reasoning) ──
            try:
                _top100 = _sdf.head(100).copy()
                _max_score = float(_top100["total_score"].max()) or 1.0
                def _build_reasoning(row):
                    _role  = str(row.get("role", row.get(_col_map.get("role","role"), "—")))
                    _exp   = row.get("experience", row.get(_col_map.get("experience","experience"), "?"))
                    _matched = str(row.get("matched_skills", "")).replace("None","").strip(", ")
                    _rr    = row.get("response_rate", "")
                    _parts = []
                    if _role and _role != "—": _parts.append(_role)
                    try: _parts.append(f"{float(_exp):.1f} yrs exp")
                    except: pass
                    if _matched: _parts.append(f"skills: {_matched[:60]}")
                    try:
                        _rr_f = float(_rr)
                        if _rr_f > 0: _parts.append(f"response rate {_rr_f:.2f}")
                    except: pass
                    return "; ".join(_parts)
                _cid_col = "candidate_id" if "candidate_id" in _top100.columns else None
                _sub = _pd.DataFrame({
                    "candidate_id": _top100[_cid_col] if _cid_col else _top100.index.astype(str),
                    "rank":         range(1, len(_top100) + 1),
                    "score":        (_top100["total_score"] / _max_score).round(4),
                    "reasoning":    _top100.apply(_build_reasoning, axis=1),
                })
                _sub_csv = _sub.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇  Download Submission CSV (Top 100)",
                    _sub_csv,
                    file_name=f"submission_{_role_slug}.csv",
                    mime="text/csv",
                    width='stretch',
                )
            except Exception as _e:
                st.warning(f"Submission CSV error: {_e}")
        with col2:
            st.markdown('''
            <div style="background:rgba(88,166,255,0.05);border:1px solid rgba(88,166,255,0.15);border-radius:12px;padding:1.25rem 1.5rem">
              <div style="font-family:JetBrains Mono,monospace;font-size:0.62rem;letter-spacing:0.15em;
                          text-transform:uppercase;color:#7c3aed;margin-bottom:0.75rem">&#x2B21; Submission Format</div>
              <div style="font-size:0.88rem;color:#c9d1d9;line-height:2.2">
                &#9989; <strong>candidate_id</strong> &mdash; unique candidate identifier<br>
                &#9989; <strong>rank</strong> &mdash; 1 to 100, ordered by score<br>
                &#9989; <strong>score</strong> &mdash; normalised 0.0 &ndash; 1.0 (top = 1.0)<br>
                &#9989; <strong>reasoning</strong> &mdash; role &middot; experience &middot; matched skills &middot; response rate<br>
                &#9989; Exactly 100 rows &mdash; hackathon submission ready
              </div>
            </div>''', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)