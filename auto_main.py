import streamlit as st
import pandas as pd
import base64
import os
import json
import pickle
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Gmail API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NexRecruit · Email Outreach",
    page_icon="✉",
    layout="wide",
    initial_sidebar_state="expanded",
)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_FILE  = "token.pickle"
CREDS_FILE  = "credentials.json"

# ─── CSS (same black/purple/white theme) ───────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Outfit:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --black:        #08080f;
        --black-mid:    #0f0f1a;
        --black-card:   #12121f;
        --black-hover:  #1a1a2e;
        --purple:       #7c3aed;
        --purple-mid:   #9d5cf6;
        --purple-light: #c4b5fd;
        --purple-pale:  #1e1040;
        --border:       rgba(255,255,255,0.12);
        --border-p:     rgba(124,58,237,0.45);
        --green:        #10b981;
        --red:          #f43f5e;
    }

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif !important;
        background: var(--black) !important;
        color: #ffffff !important;
        font-size: 17px !important;
    }

    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: var(--black-mid); }
    ::-webkit-scrollbar-thumb { background: var(--purple); border-radius: 3px; }

    section[data-testid="stSidebar"] {
        background: var(--black-mid) !important;
        border-right: 1px solid var(--border) !important;
    }
    section[data-testid="stSidebar"] * { color: #ffffff !important; }

    .main .block-container { background: var(--black) !important; padding-top: 1.5rem; max-width: 1280px; }

    /* ── Page Header ── */
    .page-header { padding: 1.5rem 0 0.75rem; }
    .page-pill {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: var(--purple-pale); border: 1px solid var(--border-p);
        border-radius: 999px; padding: 0.3rem 0.9rem;
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
        letter-spacing: 0.12em; text-transform: uppercase; color: var(--purple-light); margin-bottom: 0.75rem;
    }
    .page-header h1 {
        font-family: 'Syne', sans-serif; font-size: 2.8rem; font-weight: 800;
        letter-spacing: -0.03em; color: #ffffff; line-height: 1.1; margin: 0 0 0.4rem;
    }
    .page-header h1 .glow {
        background: linear-gradient(135deg, var(--purple-mid), var(--purple-light));
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .page-header p {
        font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;
        color: rgba(255,255,255,0.3); letter-spacing: 0.1em; text-transform: uppercase;
    }

    /* ── White Cards ── */
    .wcard {
        background: #ffffff; border: 1px solid #e5e7eb; border-radius: 16px;
        padding: 2rem 2.25rem; margin-bottom: 1.5rem; position: relative; overflow: hidden;
    }
    .wcard::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, var(--purple), var(--purple-light));
    }
    .wcard-glow {
        position: absolute; top: -50px; right: -50px; width: 180px; height: 180px;
        background: radial-gradient(circle, rgba(124,58,237,0.06) 0%, transparent 70%); pointer-events: none;
    }
    .card-badge {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: var(--purple-pale); border: 1px solid var(--border-p);
        border-radius: 8px; padding: 0.25rem 0.8rem;
        font-family: 'JetBrains Mono', monospace; font-size: 0.65rem;
        letter-spacing: 0.15em; text-transform: uppercase; color: var(--purple-light); margin-bottom: 0.5rem;
    }
    .card-title {
        font-family: 'Syne', sans-serif; font-size: 1.4rem; font-weight: 700;
        color: #111111; margin-bottom: 1.1rem;
    }

    /* ── Candidate pills ── */
    .cand-pill-wrap { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }
    .cand-pill {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: #f5f3ff; border: 1.5px solid #e0d7ff;
        border-radius: 999px; padding: 0.4rem 1rem;
        font-family: 'Outfit', sans-serif; font-size: 0.88rem; font-weight: 500;
        color: #3b0764; cursor: pointer; transition: all 0.15s;
    }
    .cand-pill.selected {
        background: var(--purple); border-color: var(--purple);
        color: #ffffff; box-shadow: 0 0 14px rgba(124,58,237,0.4);
    }
    .cand-pill .pill-score {
        font-family: 'JetBrains Mono', monospace; font-size: 0.65rem;
        background: rgba(124,58,237,0.12); border-radius: 999px; padding: 0.1rem 0.45rem;
        color: var(--purple);
    }
    .cand-pill.selected .pill-score { background: rgba(255,255,255,0.2); color: #fff; }

    /* ── Email preview card ── */
    .email-preview {
        background: #fafafa; border: 1px solid #e5e7eb; border-radius: 12px;
        padding: 1.5rem 1.75rem; font-family: 'Outfit', sans-serif; color: #111;
    }
    .email-preview .ep-to {
        font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #6b7280;
        margin-bottom: 0.3rem; letter-spacing: 0.06em;
    }
    .email-preview .ep-subject {
        font-family: 'Syne', sans-serif; font-size: 1.15rem; font-weight: 700;
        color: #111; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.75rem; margin-bottom: 0.9rem;
    }
    .email-preview .ep-body {
        font-size: 0.95rem; color: #374151; line-height: 1.75; white-space: pre-wrap;
    }

    /* ── Status badges ── */
    .status-sent {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.3);
        color: #10b981; border-radius: 8px; padding: 0.3rem 0.85rem;
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; letter-spacing: 0.08em;
    }
    .status-fail {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: rgba(244,63,94,0.12); border: 1px solid rgba(244,63,94,0.3);
        color: #f43f5e; border-radius: 8px; padding: 0.3rem 0.85rem;
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; letter-spacing: 0.08em;
    }

    /* ── Gmail connect card ── */
    .gmail-card {
        background: #fff8f0; border: 1px solid #fed7aa; border-radius: 12px;
        padding: 1.25rem 1.5rem; margin-bottom: 1rem;
    }
    .gmail-card .gc-title {
        font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 700; color: #92400e; margin-bottom: 0.35rem;
    }
    .gmail-card .gc-body { font-size: 0.88rem; color: #78350f; line-height: 1.7; }
    .gmail-card code {
        background: #fef3c7; padding: 0.1rem 0.4rem; border-radius: 4px;
        font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #92400e;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, var(--purple) 0%, #9333ea 100%) !important;
        color: #fff !important; border: none !important; border-radius: 10px !important;
        font-family: 'Outfit', sans-serif !important; font-size: 0.95rem !important;
        font-weight: 600 !important; padding: 0.7rem 1.75rem !important;
        box-shadow: 0 0 20px rgba(124,58,237,0.3) !important;
    }
    .stButton > button:hover { box-shadow: 0 0 32px rgba(124,58,237,0.55) !important; }

    .stTextArea textarea, .stTextInput input, .stSelectbox select {
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
    label {
        font-family: 'JetBrains Mono', monospace !important; font-size: 0.72rem !important;
        letter-spacing: 0.1em !important; text-transform: uppercase !important;
        color: rgba(255,255,255,0.5) !important;
    }
    .wcard label { color: #6b7280 !important; }
    .stCaption { font-family: 'JetBrains Mono', monospace !important; font-size: 0.68rem !important; color: rgba(255,255,255,0.3) !important; }
    .wcard .stCaption { color: #9ca3af !important; }
    [data-testid="stAlert"] {
        background: #f5f3ff !important; border: 1px solid #e0d7ff !important;
        border-radius: 10px !important; font-size: 1rem !important; color: #111 !important;
    }
    hr { border-color: rgba(255,255,255,0.07) !important; }
    .stMultiSelect [data-baseweb="tag"] { background: var(--purple) !important; }
    .stCheckbox label { font-size: 0.9rem !important; text-transform: none !important; color: #374151 !important; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# GMAIL AUTH HELPERS
# ═══════════════════════════════════════════════════════
def get_gmail_service():
    """Authenticate and return Gmail API service."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_FILE):
                return None, "credentials_missing"
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    try:
        service = build("gmail", "v1", credentials=creds)
        return service, "ok"
    except Exception as e:
        return None, str(e)


def send_email(service, to_email, subject, body):
    """Send a plain-text email via Gmail API."""
    msg = MIMEMultipart("alternative")
    msg["To"]      = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


# ═══════════════════════════════════════════════════════
# EMAIL TEMPLATE GENERATOR
# ═══════════════════════════════════════════════════════
def generate_email(candidate_name, candidate_role, score, email_type, jd_role, company_name, sender_name):
    subject_map = {
        "Interview Invitation":    f"Interview Invitation — {jd_role} at {company_name}",
        "Shortlisting Notice":     f"You've Been Shortlisted — {jd_role} at {company_name}",
        "Further Info Request":    f"Next Steps — {jd_role} Application at {company_name}",
        "Congratulations — Offer": f"🎉 Offer Letter — {jd_role} at {company_name}",
        "Rejection (Polite)":      f"Regarding Your Application — {jd_role} at {company_name}",
    }

    bodies = {
        "Interview Invitation": f"""Dear {candidate_name},

Thank you for your interest in the {jd_role} position at {company_name}.

After carefully reviewing your profile, we are pleased to inform you that you have been selected for an interview. Your background and experience make you a strong candidate, and we are excited to learn more about you.

Interview Details:
• Position  : {jd_role}
• Format    : To be confirmed (Video / In-person)
• Duration  : Approximately 45–60 minutes

Please reply to this email with your availability over the next 5 business days, and we will coordinate a suitable time.

We look forward to speaking with you.

Warm regards,
{sender_name}
{company_name} — Talent Acquisition""",

        "Shortlisting Notice": f"""Dear {candidate_name},

We are writing to inform you that you have been shortlisted for the {jd_role} role at {company_name}.

Your profile stood out to our team, and we would like to move forward with the next stage of our selection process. Our team will reach out shortly with further details regarding timelines and next steps.

In the meantime, feel free to reply to this email if you have any questions.

Best regards,
{sender_name}
{company_name} — Talent Acquisition""",

        "Further Info Request": f"""Dear {candidate_name},

Thank you for applying for the {jd_role} position at {company_name}.

We have reviewed your application and would like to learn more about your experience before proceeding. Could you please share the following:

  1. A brief overview of your most relevant projects or achievements
  2. Your current notice period / availability to join
  3. Your expected compensation range (optional)

Please reply at your earliest convenience. We aim to get back to all candidates within 3–5 business days.

Regards,
{sender_name}
{company_name} — Talent Acquisition""",

        "Congratulations — Offer": f"""Dear {candidate_name},

Congratulations! 🎉

We are thrilled to extend an offer for the {jd_role} position at {company_name}. After a thorough evaluation process, it is our pleasure to welcome you to the team.

Please find the formal offer letter attached. Kindly review the terms and confirm your acceptance by replying to this email or signing the attached document by the date indicated.

If you have any questions or would like to discuss the offer further, do not hesitate to reach out. We are very excited about the possibility of having you on board.

Warmly,
{sender_name}
{company_name} — Talent Acquisition""",

        "Rejection (Polite)": f"""Dear {candidate_name},

Thank you sincerely for taking the time to apply for the {jd_role} role at {company_name} and for the effort you put into your application.

After careful consideration, we have decided to move forward with other candidates whose experience more closely aligns with the current requirements of this role. This was not an easy decision given the quality of applications we received.

We genuinely appreciate your interest in {company_name} and encourage you to apply for future openings that match your profile. We will keep your details on file for upcoming opportunities.

We wish you the very best in your job search and future career.

Kind regards,
{sender_name}
{company_name} — Talent Acquisition""",
    }

    return subject_map.get(email_type, ""), bodies.get(email_type, "")


# ═══════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════
for key in ["scored_df", "selected_candidates", "email_drafts", "send_log"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "selected_candidates" else []
if "email_drafts" not in st.session_state or st.session_state.email_drafts is None:
    st.session_state.email_drafts = {}
if "send_log" not in st.session_state or st.session_state.send_log is None:
    st.session_state.send_log = []

# ═══════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:800;
        background:linear-gradient(135deg,#fff,#c4b5fd);-webkit-background-clip:text;-webkit-text-fill-color:transparent">
        ✉ NexRecruit AI
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:rgba(255,255,255,0.35);
        letter-spacing:0.18em;text-transform:uppercase;margin-top:0.2rem">Email Outreach Module</div>
    """, unsafe_allow_html=True)
    st.divider()

    st.markdown('<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.65rem;letter-spacing:0.14em;text-transform:uppercase;color:rgba(255,255,255,0.45)">Sender Details</span>', unsafe_allow_html=True)
    sender_name    = st.text_input("Your Name", value="Hiring Manager", label_visibility="collapsed",
                                    placeholder="Hiring Manager Name")
    company_name   = st.text_input("Company Name", value="Our Company", label_visibility="collapsed",
                                    placeholder="Company Name")
    jd_role        = st.text_input("Role / Position", value="Software Engineer", label_visibility="collapsed",
                                    placeholder="Role being hired for")

    st.divider()
    st.markdown('<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.65rem;letter-spacing:0.14em;text-transform:uppercase;color:rgba(255,255,255,0.45)">Email Type</span>', unsafe_allow_html=True)
    email_type = st.selectbox("Email Template", [
        "Interview Invitation",
        "Shortlisting Notice",
        "Further Info Request",
        "Congratulations — Offer",
        "Rejection (Polite)",
    ], label_visibility="collapsed")

    st.divider()
    # Gmail auth status
    st.markdown('<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.65rem;letter-spacing:0.14em;text-transform:uppercase;color:rgba(255,255,255,0.45)">Gmail Connection</span>', unsafe_allow_html=True)
    if not GMAIL_AVAILABLE:
        st.markdown('<span style="color:#f43f5e;font-size:0.8rem">⚠ google-api packages not installed</span>', unsafe_allow_html=True)
        st.caption("Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    elif not os.path.exists(CREDS_FILE):
        st.markdown('<span style="color:#f59e0b;font-size:0.8rem">⚠ credentials.json not found</span>', unsafe_allow_html=True)
        st.caption("Place credentials.json in the app folder.")
    elif os.path.exists(TOKEN_FILE):
        st.markdown('<span style="color:#10b981;font-size:0.8rem">✓ Gmail connected</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#f59e0b;font-size:0.8rem">○ Not authenticated yet</span>', unsafe_allow_html=True)
        if st.button("Connect Gmail", use_container_width=True):
            svc, status = get_gmail_service()
            if status == "ok":
                st.success("Gmail connected!")
                st.rerun()
            else:
                st.error(f"Auth failed: {status}")

# ═══════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════
st.markdown("""
<div class="page-header">
    <div class="page-pill">✉ &nbsp; Automated Email Outreach</div>
    <h1>Send <span class="glow">Personalised Emails</span><br>to Your Candidates.</h1>
    <p>Select candidates → Review & Edit → Send via Gmail</p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# GMAIL SETUP GUIDE (if not ready)
# ═══════════════════════════════════════════════════════
if not GMAIL_AVAILABLE or not os.path.exists(CREDS_FILE):
    st.markdown("""
    <div class="wcard">
        <div class="wcard-glow"></div>
        <div class="card-badge">✉ &nbsp; Setup Guide</div>
        <div class="card-title">Gmail API Setup (Free)</div>
        <div class="gmail-card">
            <div class="gc-title">Step 1 — Install required packages</div>
            <div class="gc-body">Run in your terminal:<br>
            <code>pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib</code></div>
        </div>
        <div class="gmail-card">
            <div class="gc-title">Step 2 — Create Google Cloud credentials</div>
            <div class="gc-body">
            1. Go to <strong>console.cloud.google.com</strong><br>
            2. Create a new project → Enable <strong>Gmail API</strong><br>
            3. Go to <strong>APIs & Services → Credentials → Create OAuth 2.0 Client ID</strong><br>
            4. Application type: <strong>Desktop App</strong><br>
            5. Download the JSON → rename it <code>credentials.json</code><br>
            6. Place <code>credentials.json</code> in the same folder as this app
            </div>
        </div>
        <div class="gmail-card">
            <div class="gc-title">Step 3 — Authenticate</div>
            <div class="gc-body">Click <strong>Connect Gmail</strong> in the sidebar. A browser window will open for Google login. After approval, a <code>token.pickle</code> file is saved — you only do this once.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# STEP 1 — LOAD SCORED CSV
# ═══════════════════════════════════════════════════════
st.markdown('<div class="wcard"><div class="wcard-glow"></div><div class="card-badge">✉ &nbsp; Step 01</div><div class="card-title">Load Scored Candidate Data</div>', unsafe_allow_html=True)

up_col1, up_col2 = st.columns([1, 1], gap="large")
with up_col1:
    st.caption("Upload the scored CSV exported from the main recruiter app")
    uploaded = st.file_uploader("Upload scored candidates CSV", type=["csv"], label_visibility="collapsed")
    if uploaded:
        df = pd.read_csv(uploaded)
        st.session_state.scored_df = df
        st.success(f"✓ Loaded {len(df)} candidates · {len(df.columns)} columns")

with up_col2:
    if st.session_state.scored_df is not None:
        df = st.session_state.scored_df
        # Detect email column (last column or column named 'email')
        email_col = df.columns[-1]
        for c in df.columns:
            if "email" in c.lower():
                email_col = c
                break
        st.markdown(f"""
        <div style="background:#f5f3ff;border:1px solid #e0d7ff;border-radius:10px;padding:1rem 1.25rem">
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;letter-spacing:0.15em;
                text-transform:uppercase;color:var(--purple);margin-bottom:0.5rem">Detected Columns</div>
            <div style="font-size:0.9rem;color:#374151;line-height:2">
                <b>Total rows:</b> {len(df)}<br>
                <b>Email column:</b> <code style="background:#ede9fe;padding:0.1rem 0.4rem;border-radius:4px;font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:#5b21b6">{email_col}</code><br>
                <b>All columns:</b> {', '.join(df.columns.tolist())}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# STEP 2 — SELECT CANDIDATES
# ═══════════════════════════════════════════════════════
if st.session_state.scored_df is not None:
    df = st.session_state.scored_df

    # Detect columns
    email_col = df.columns[-1]
    name_col  = df.columns[0]
    score_col = None
    for c in df.columns:
        if "email" in c.lower():
            email_col = c
        if c.lower() in ("name", "candidate_name", "full_name", "candidate"):
            name_col = c
        if "total_score" in c.lower() or c.lower() == "score":
            score_col = c

    st.markdown('<div class="wcard"><div class="wcard-glow"></div><div class="card-badge">✉ &nbsp; Step 02</div><div class="card-title">Select Candidates to Email</div>', unsafe_allow_html=True)

    # Quick filter
    f1, f2 = st.columns([2, 1], gap="large")
    with f1:
        search_q = st.text_input("Search candidates", placeholder="Type a name to filter…", label_visibility="collapsed")
    with f2:
        if score_col:
            min_score = st.slider("Min score filter", 0, 100, 0)
        else:
            min_score = 0

    # Filter df
    filtered = df.copy()
    if search_q:
        filtered = filtered[filtered[name_col].astype(str).str.contains(search_q, case=False, na=False)]
    if score_col and min_score > 0:
        filtered = filtered[filtered[score_col] >= min_score]

    # Select All / Deselect All
    sa_col1, sa_col2, sa_col3 = st.columns([1, 1, 4])
    if sa_col1.button("Select All", use_container_width=True):
        st.session_state.selected_candidates = filtered[name_col].tolist()
        st.rerun()
    if sa_col2.button("Clear All", use_container_width=True):
        st.session_state.selected_candidates = []
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Render candidate pills
    pills_html = '<div class="cand-pill-wrap">'
    for _, row in filtered.iterrows():
        name  = str(row[name_col])
        email = str(row[email_col]) if email_col in row.index else "—"
        score = str(int(row[score_col])) if score_col and pd.notna(row[score_col]) else "—"
        sel   = "selected" if name in st.session_state.selected_candidates else ""
        pills_html += f'<span class="cand-pill {sel}" title="{email}"><span>👤 {name}</span><span class="pill-score">{score}</span></span>'
    pills_html += '</div>'
    st.markdown(pills_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Multiselect (functional selection)
    all_names = filtered[name_col].tolist()
    selected  = st.multiselect(
        "Select candidates (tick boxes)",
        options=all_names,
        default=[n for n in st.session_state.selected_candidates if n in all_names],
        label_visibility="collapsed",
    )
    st.session_state.selected_candidates = selected

    if selected:
        st.markdown(f"""
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;color:#6b7280;
            letter-spacing:0.1em;margin-top:0.5rem">{len(selected)} candidate(s) selected</div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# STEP 3 — GENERATE & EDIT EMAIL DRAFTS
# ═══════════════════════════════════════════════════════
if st.session_state.scored_df is not None and st.session_state.selected_candidates:
    df        = st.session_state.scored_df
    email_col = df.columns[-1]
    name_col  = df.columns[0]
    score_col = None
    for c in df.columns:
        if "email" in c.lower():   email_col = c
        if c.lower() in ("name","candidate_name","full_name","candidate"): name_col = c
        if "total_score" in c.lower() or c.lower() == "score": score_col = c

    st.markdown('<div class="wcard"><div class="wcard-glow"></div><div class="card-badge">✉ &nbsp; Step 03</div><div class="card-title">Review & Edit Email Drafts</div>', unsafe_allow_html=True)

    if st.button("⚡  Generate All Drafts", use_container_width=True):
        drafts = {}
        for name in st.session_state.selected_candidates:
            row = df[df[name_col].astype(str) == name].iloc[0]
            candidate_role = str(row.get("role", row.get("job_title", row.get("title", "Candidate"))))
            score          = int(row[score_col]) if score_col and pd.notna(row[score_col]) else 0
            subj, body     = generate_email(name, candidate_role, score, email_type, jd_role, company_name, sender_name)
            drafts[name]   = {"subject": subj, "body": body}
        st.session_state.email_drafts = drafts
        st.success(f"✓ Generated {len(drafts)} email draft(s). Review and edit below.")
        st.rerun()

    if st.session_state.email_drafts:
        st.markdown("<br>", unsafe_allow_html=True)
        for name in st.session_state.selected_candidates:
            if name not in st.session_state.email_drafts:
                continue
            row        = df[df[name_col].astype(str) == name].iloc[0]
            to_email   = str(row[email_col]) if email_col in row.index else "unknown@email.com"
            draft      = st.session_state.email_drafts[name]

            with st.expander(f"✉  {name}  ·  {to_email}", expanded=True):
                ec1, ec2 = st.columns([1, 1], gap="large")

                with ec1:
                    st.markdown(f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.65rem;color:#6b7280;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.25rem">Edit Subject</div>', unsafe_allow_html=True)
                    new_subject = st.text_input(
                        f"subject_{name}", value=draft["subject"],
                        key=f"subj_{name}", label_visibility="collapsed"
                    )

                    st.markdown(f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.65rem;color:#6b7280;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.25rem;margin-top:0.75rem">Edit Message</div>', unsafe_allow_html=True)
                    new_body = st.text_area(
                        f"body_{name}", value=draft["body"],
                        height=320, key=f"body_{name}", label_visibility="collapsed"
                    )

                    if st.button("💾  Save Changes", key=f"save_{name}"):
                        st.session_state.email_drafts[name]["subject"] = new_subject
                        st.session_state.email_drafts[name]["body"]    = new_body
                        st.success("✓ Changes saved.")

                with ec2:
                    st.markdown(f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.65rem;color:#6b7280;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.5rem">Live Preview</div>', unsafe_allow_html=True)
                    preview_subj = st.session_state.get(f"subj_{name}", draft["subject"]) or draft["subject"]
                    preview_body = st.session_state.get(f"body_{name}", draft["body"])    or draft["body"]
                    st.markdown(f"""
                    <div class="email-preview">
                        <div class="ep-to">To: {to_email}</div>
                        <div class="ep-subject">{preview_subj}</div>
                        <div class="ep-body">{preview_body}</div>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# STEP 4 — SEND EMAILS
# ═══════════════════════════════════════════════════════
if (st.session_state.scored_df is not None
        and st.session_state.selected_candidates
        and st.session_state.email_drafts):

    df        = st.session_state.scored_df
    email_col = df.columns[-1]
    name_col  = df.columns[0]
    for c in df.columns:
        if "email" in c.lower():   email_col = c
        if c.lower() in ("name","candidate_name","full_name","candidate"): name_col = c

    st.markdown('<div class="wcard"><div class="wcard-glow"></div><div class="card-badge">✉ &nbsp; Step 04</div><div class="card-title">Send Emails</div>', unsafe_allow_html=True)

    # Summary before sending
    ready = [n for n in st.session_state.selected_candidates if n in st.session_state.email_drafts]
    st.markdown(f"""
    <div style="background:#f5f3ff;border:1px solid #e0d7ff;border-radius:10px;padding:1rem 1.25rem;margin-bottom:1rem">
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;letter-spacing:0.15em;
            text-transform:uppercase;color:var(--purple);margin-bottom:0.4rem">Ready to send</div>
        <div style="font-size:1rem;color:#374151">
            <b>{len(ready)}</b> email(s) will be sent via your connected Gmail account.
        </div>
    </div>
    """, unsafe_allow_html=True)

    confirm = st.checkbox("✓  I have reviewed all drafts and confirm sending", value=False)

    send_col1, send_col2 = st.columns([1, 2])
    with send_col1:
        send_clicked = st.button("✉  Send All Emails", use_container_width=True, disabled=not confirm)

    if send_clicked and confirm:
        if not GMAIL_AVAILABLE:
            st.error("Gmail packages not installed. See setup guide above.")
        elif not os.path.exists(CREDS_FILE) and not os.path.exists(TOKEN_FILE):
            st.error("Gmail not authenticated. Use 'Connect Gmail' in the sidebar.")
        else:
            service, status = get_gmail_service()
            if status != "ok":
                st.error(f"Gmail auth error: {status}")
            else:
                log = []
                progress = st.progress(0)
                for i, name in enumerate(ready):
                    row      = df[df[name_col].astype(str) == name].iloc[0]
                    to_email = str(row[email_col])
                    draft    = st.session_state.email_drafts[name]
                    # Use latest edited values from widget state if available
                    subject  = st.session_state.get(f"subj_{name}", draft["subject"]) or draft["subject"]
                    body     = st.session_state.get(f"body_{name}", draft["body"])    or draft["body"]
                    try:
                        send_email(service, to_email, subject, body)
                        log.append({"name": name, "email": to_email, "status": "sent"})
                        st.markdown(f'<div class="status-sent">✓ &nbsp; Sent to {name} ({to_email})</div><br>', unsafe_allow_html=True)
                    except Exception as e:
                        log.append({"name": name, "email": to_email, "status": f"failed: {e}"})
                        st.markdown(f'<div class="status-fail">✗ &nbsp; Failed: {name} — {e}</div><br>', unsafe_allow_html=True)
                    progress.progress((i + 1) / len(ready))

                st.session_state.send_log = log
                sent_count = sum(1 for l in log if l["status"] == "sent")
                st.success(f"✓ {sent_count}/{len(ready)} emails sent successfully.")

    # Send Log
    if st.session_state.send_log:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("View Send Log"):
            log_df = pd.DataFrame(st.session_state.send_log)
            st.dataframe(log_df, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ─── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:2rem 0 1rem;border-top:1px solid rgba(255,255,255,0.07);margin-top:1.5rem">
    <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:800;
        background:linear-gradient(135deg,#fff,#c4b5fd);-webkit-background-clip:text;-webkit-text-fill-color:transparent">
        ✉ NexRecruit AI · Email Outreach
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.6rem;letter-spacing:0.2em;
        text-transform:uppercase;color:rgba(255,255,255,0.18);margin-top:0.3rem">
        Powered by Gmail API · Free Tier
    </div>
</div>
""", unsafe_allow_html=True)
