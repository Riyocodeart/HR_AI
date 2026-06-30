"""
pages.email
===========
Email outreach tab. All Gmail OAuth, SMTP send, and template rendering
moved to ``services.gmail_service`` in Wave 2; this page owns layout and
recipient selection.

Dependencies
------------
* ``services.gmail_service`` — auth, send, templates
"""

from __future__ import annotations

import streamlit as st

from services import gmail_service


# Backwards-compat aliases — the body code calls these names directly.
get_gmail_service     = gmail_service.get_service
send_email            = gmail_service.send_email
generate_email_content= gmail_service.generate_email_content
CREDS_FILE            = gmail_service.CREDS_FILE
TOKEN_FILE            = gmail_service.TOKEN_FILE
GMAIL_AVAILABLE       = gmail_service.has_libraries()


def render() -> None:
    """Render the email outreach page."""

    sender_name  = st.session_state.get("sb_sender_name", "Hiring Manager")
    company_name = st.session_state.get("sb_company", st.session_state.jd_data.get("company","Our Company") if st.session_state.jd_data else "Our Company")
    jd_role_e    = st.session_state.get("sb_role", st.session_state.jd_data.get("role","Role") if st.session_state.jd_data else "Role")
    email_type   = st.session_state.get("sb_email_type", "Interview Invitation")

    st.markdown("""
    <div class="page-header">
      <div class="page-header-pill">✉ &nbsp; Automated Email Outreach</div>
      <h1>Send <span class="glow">Personalised Emails</span><br>to Your Candidates.</h1>
      <p>Select → Review & Edit → Send via Gmail</p>
    </div>""", unsafe_allow_html=True)

    if not GMAIL_AVAILABLE or not os.path.exists(CREDS_FILE):
        st.markdown("""
        <div class="step-card"><div class="step-card-glow"></div>
        <div class="step-num-badge">✉ &nbsp; Setup Required</div>
        <div class="step-title">Gmail API Setup (Free · One-time)</div>
        <ol style="color:#374151;font-size:0.9rem;line-height:2.2">
          <li>Run: <code>pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib</code></li>
          <li>Go to <b>console.cloud.google.com</b> → New project → Enable Gmail API → Credentials → OAuth 2.0 Desktop → Download JSON → rename to <code>credentials.json</code> → place in app folder.</li>
          <li>Click <b>Connect Gmail</b> in the sidebar. Authenticates once, saves <code>token.pickle</code> permanently.</li>
        </ol>
        </div>""", unsafe_allow_html=True)

    # Load candidates
    st.markdown('<div class="step-card"><div class="step-card-glow"></div><div class="step-num-badge">✉ &nbsp; Step 01</div><div class="step-title">Candidate Data</div>', unsafe_allow_html=True)
    if st.session_state.scored_df is not None:
        n = len(st.session_state.scored_df)
        st.markdown(f'<div style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.25);border-radius:10px;padding:0.8rem 1.1rem"><span style="color:#10b981;font-family:\'JetBrains Mono\',monospace;font-size:0.7rem">✓ {n} candidates from Recruiter tab</span></div>', unsafe_allow_html=True)
    up = st.file_uploader("Or upload scored CSV", type=["csv"], key="email_csv_up")
    if up:
        df_email = pd.read_csv(up)
        st.session_state.scored_df = df_email
        st.success(f"✓ Loaded {len(df_email)} candidates")
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.scored_df is not None:
        df   = st.session_state.scored_df
        name_col  = st.session_state.name_col_detected or df.columns[0]
        email_col = next((c for c in df.columns if "email" in c.lower()), None)
        score_col = "total_score" if "total_score" in df.columns else None

        # Select candidates
        st.markdown('<div class="step-card"><div class="step-card-glow"></div><div class="step-num-badge">✉ &nbsp; Step 02</div><div class="step-title">Select Candidates</div>', unsafe_allow_html=True)
        top_n_email = st.slider("Show top N", 5, min(50, len(df)), min(15, len(df)), key="email_topn")
        df_top = df.head(top_n_email)

        selections = []
        for _, row in df_top.iterrows():
            label = str(row[name_col]) if name_col in row.index else f"Row {_}"
            score_str = f" [{int(row[score_col])}/100]" if score_col else ""
            email_str = f" · {row[email_col]}" if email_col else ""
            if st.checkbox(f"{label}{score_str}{email_str}", key=f"sel_{_}"):
                selections.append(row)
        st.session_state.selected_candidates = selections
        st.markdown("</div>", unsafe_allow_html=True)

        # Preview & Send
        if st.session_state.selected_candidates:
            st.markdown('<div class="step-card"><div class="step-card-glow"></div><div class="step-num-badge">✉ &nbsp; Step 03</div><div class="step-title">Preview & Send</div>', unsafe_allow_html=True)
            for row in st.session_state.selected_candidates:
                cand_name = str(row[name_col]) if name_col in row.index else "Candidate"
                cand_email = str(row[email_col]) if email_col else ""
                subject, body = generate_email_content(cand_name, email_type, jd_role_e, company_name, sender_name)

                with st.expander(f"✉ {cand_name} — {email_type}", expanded=False):
                    new_body = st.text_area("Email body", value=body, height=240, key=f"body_{cand_name}")
                    st.session_state.email_drafts[cand_name] = (subject, new_body, cand_email)

            if st.button("📤  Send All Selected Emails", width='stretch'):
                svc = None
                if GMAIL_AVAILABLE and os.path.exists(CREDS_FILE):
                    svc, status = get_gmail_service()
                    if status != "ok":
                        st.error(f"Gmail auth failed: {status}")
                        svc = None
                sent_count = 0
                for cand_name, (subj, body, to_email) in st.session_state.email_drafts.items():
                    if svc and to_email and "@" in to_email:
                        try:
                            send_email(svc, to_email, subj, body)
                            st.session_state.send_log.append((cand_name, to_email, "✅ Sent"))
                            sent_count += 1
                        except Exception as e:
                            st.session_state.send_log.append((cand_name, to_email, f"❌ {e}"))
                    else:
                        st.session_state.send_log.append((cand_name, to_email or "—", "⚠ Simulated (no Gmail / no email)"))
                        sent_count += 1
                st.success(f"✓ Processed {sent_count} emails")
                st.rerun()

            if st.session_state.send_log:
                st.markdown("**Send Log:**")
                for name, email_addr, status in st.session_state.send_log:
                    st.markdown(f"`{name}` → `{email_addr}` — {status}")

            st.markdown("</div>", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:2.5rem 0 1rem;font-family:'JetBrains Mono',monospace;
            font-size:0.6rem;letter-spacing:0.15em;text-transform:uppercase;color:rgba(255,255,255,0.12)">
  ⬡ NexRecruit AI · Intelligent · Precise
</div>""", unsafe_allow_html=True)
