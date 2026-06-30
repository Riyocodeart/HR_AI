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

    # LinkedIn search now lives in its own tab — see the sidebar.

    # ── STEP 2: Upload Candidates ───────────────────────────────────────────────
    if st.session_state.jd_data:
        st.markdown('<div class="step-card"><div class="step-card-glow"></div><div class="step-num-badge">⬡ &nbsp; Step 02</div><div class="step-title">Upload Candidate Dataset</div>', unsafe_allow_html=True)

        tab_jsonl, tab_csv = st.tabs(["📄  JSONL (Hackathon Dataset)", "📊  CSV / Excel"])

        # ── Tab A: JSONL ──────────────────────────────────────────────────
        with tab_jsonl:
            ja, jb = st.columns([1, 1], gap="large")
            with ja:
                # ── Auto-detect candidates.jsonl on the machine ──────────
                import glob
                import os as _os
                from pathlib import Path as _Path

                def _find_jsonl() -> str:
                    """Search common locations for candidates.jsonl."""
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

                # ── Option 1: Load from local path ───────────────────────
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

                # ── Option 2: Browser upload (fallback) ──────────────────
                st.markdown("**📁 Or upload file** *(only if under 200 MB)*")
                jsonl_file = st.file_uploader(
                    "candidates.jsonl",
                    type=["jsonl", "json"],
                    label_visibility="collapsed",
                    key="jsonl_uploader",
                )

                # ── Shared loader function ───────────────────────────────
                def _load_jsonl_from_path(path: str) -> None:
                    """
                    Read a JSONL, run DataCleaner on every candidate, split
                    Rejected from Accepted/Needs Review (Blueprint Step 5/6),
                    and stash the scoring-eligible DataFrame.
                    """
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
                        # core/cleaner.py DataCleaner expects nested dict shape
                        # (profile / skills / education / redrob_signals).
                        # Use .to_dict() so DataCleaner sees plain dicts, not
                        # nested dataclass objects.
                        raw_dict = c.to_dict() if hasattr(c, "to_dict") else {}
                        try:
                            raw_dict = cleaner.clean_candidate(raw_dict)
                        except Exception:
                            pass  # uncleaned row still gets through with defaults

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

                    # ── Blueprint Step 5/6 split ─────────────────────────
                    # Rejected → audit-only (rejected_df). Accepted / Needs
                    # Review → scoring pool (candidates_df). Critical: the
                    # scorer must NEVER see Rejected rows.
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
                            st.caption(
                                "Failed quality checks (quality_score < 50). Kept for audit "
                                "only — see Blueprint datacleaning.md Step 5/6."
                            )
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

                # ── Trigger: local path ──────────────────────────────────
                if load_local and local_path.strip():
                    try:
                        _load_jsonl_from_path(local_path.strip())
                    except Exception as e:
                        st.error(f"Could not load: {e}")

                # ── Trigger: browser upload ──────────────────────────────
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
                        # NOTE: core/cleaner.py DataCleaner.clean_candidate() is
                        # built for the nested JSONL hackathon-dataset shape
                        # (profile / skills / education / redrob_signals — see
                        # Blueprint datacleaning.md). Generic CSV/Excel uploads
                        # have flat, arbitrary column names (mapped later by
                        # detect_columns), so DataCleaner cannot validate them.
                        # CSV/Excel rows are AI-column-mapped only, not
                        # quality-filtered.
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
            st.markdown('<span class="source-badge offline">⚠ Offline Rule-Based Scoring (add Gemini key for AI)</span>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("⬡  Score All Candidates", width='stretch'):
            with st.spinner("Scoring candidates with Gemini AI… this takes ~10-20s for large datasets"):
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

            top_n = st.slider("Show top N candidates", 5, min(50, len(scored)), min(10, len(scored)))
            for _, row in scored.head(top_n).iterrows():
                rank     = int(row.get("rank", 0))
                score    = int(row.get("total_score", 0))
                name_val = str(row[name_col]) if name_col and name_col in row.index else f"Candidate #{rank}"
                role_val = str(row.get(st.session_state.col_map.get("role","role"), row.get("role","—")))
                loc_val  = str(row.get(st.session_state.col_map.get("location","location"), row.get("location","—")))
                matched  = [s.strip() for s in str(row.get("matched_skills","")).split(",") if s.strip() and s.strip() != "None"]
                missing  = [s.strip() for s in str(row.get("missing_skills","")).split(",") if s.strip() and s.strip() != "None"]
                rationale = str(row.get("rationale",""))
                badge    = _score_badge(score)

                skill_sc  = int(row.get("skill_score", 0))
                role_sc   = int(row.get("role_score", 0))
                signal_sc = int(row.get("signal_score", 0))

                st.markdown(f"""
                <div class="cand-card {badge}">
                  <div style="display:flex;align-items:flex-start;justify-content:space-between">
                    <div style="display:flex;align-items:center">
                      <div class="cand-rank">#{rank}</div>
                      <div>
                        <div class="cand-name">{name_val}</div>
                        <div class="cand-meta">{role_val} &nbsp;·&nbsp; {loc_val}</div>
                        <div class="cand-meta" style="margin-top:0.15rem">
                          Skill {skill_sc}/40 &nbsp;·&nbsp; Role {role_sc}/30 &nbsp;·&nbsp; Signal {signal_sc}/30
                        </div>
                      </div>
                    </div>
                    <div style="text-align:right">
                      <div class="cand-score">{score}</div>
                      <div class="cand-score-sub">/ 100</div>
                    </div>
                  </div>
                  <div style="margin-top:0.6rem">
                    {"".join(f'<span class="tag tag-match">✓ {s}</span>' for s in matched)}
                    {"".join(f'<span class="tag tag-miss">✗ {s}</span>' for s in missing)}
                  </div>
                  {"" if not rationale or rationale == "nan" else f'<div class="rationale-box">💡 {rationale}</div>'}
                </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✉  Go to Email Outreach →", width='stretch'):
                st.session_state.active_tab = "email"
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # ── STEP 4: Export ─────────────────────────────────────────────────────────
    if st.session_state.scored_df is not None:
        st.markdown('<div class="step-card"><div class="step-card-glow"></div><div class="step-num-badge">⬡ &nbsp; Step 04</div><div class="step-title">Export Results</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 2], gap="large")
        with col1:
            excel_bytes = export_excel(
                st.session_state.scored_df,
                st.session_state.jd_data,
                col_map=st.session_state.col_map,
                score_source=st.session_state.score_source,
            )
            role_slug = (st.session_state.jd_data.get("role") or "candidates").replace(" ","_")
            st.download_button("⬇  Download Excel Report", excel_bytes,
                file_name=f"nexrecruit_{role_slug}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width='stretch')
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button("⬇  Download CSV", export_csv(st.session_state.scored_df),
                file_name="nexrecruit_results.csv", mime="text/csv", width='stretch')
        with col2:
            st.markdown("""
            <div style="background:#f5f3ff;border:1px solid #ede9fe;border-radius:12px;padding:1.25rem 1.5rem">
              <div style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;letter-spacing:0.15em;
                          text-transform:uppercase;color:var(--purple);margin-bottom:0.75rem">⬡ Report Includes</div>
              <div style="font-size:0.88rem;color:#374151;line-height:2.1">
                ✅ Ranked candidates — colour-coded (green / amber / red)<br>
                ✅ AI rationale per candidate<br>
                ✅ Matched vs. missing skills breakdown<br>
                ✅ JD Summary sheet — all extracted fields<br>
                ✅ Score source label (AI or offline)
              </div>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)