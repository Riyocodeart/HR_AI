import streamlit as st
import pandas as pd
import json
import base64
import os
import pickle
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from jd_parser import parse_jd, parse_jd_from_upload
from filter import load_candidates, score_candidates, export_excel, export_csv
from chrome import generate_linkedin_url

# Gmail API
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False

SCOPES     = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_FILE = "token.pickle"
CREDS_FILE = "credentials.json"

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NexRecruit AI",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Shared CSS ────────────────────────────────────────────────────────────────
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

    /* ── NAV TABS in sidebar ── */
    .nav-tab {
        display: flex; align-items: center; gap: 0.7rem;
        padding: 0.7rem 0.9rem; border-radius: 10px; margin-bottom: 0.35rem;
        cursor: pointer; border: 1px solid transparent;
        transition: all 0.15s; font-size: 0.92rem; font-weight: 500;
        color: rgba(255,255,255,0.55) !important;
    }
    .nav-tab:hover { background: rgba(124,58,237,0.12); color: #fff !important; border-color: var(--border-p); }
    .nav-tab.active {
        background: linear-gradient(135deg, rgba(124,58,237,0.25), rgba(157,92,246,0.15));
        border: 1px solid var(--border-p);
        color: #ffffff !important;
        box-shadow: 0 0 14px rgba(124,58,237,0.2);
    }
    .nav-tab .nav-icon { font-size: 1.1rem; flex-shrink: 0; }
    .nav-tab .nav-label { font-family: 'Outfit', sans-serif; font-weight: 600; }
    .nav-tab .nav-sub {
        font-family: 'JetBrains Mono', monospace; font-size: 0.6rem;
        letter-spacing: 0.08em; color: rgba(255,255,255,0.3) !important;
        margin-top: 0.05rem;
    }
    .nav-tab.active .nav-sub { color: rgba(255,255,255,0.5) !important; }

    .sidebar-brand {
        font-family: 'Syne', sans-serif; font-size: 1.6rem; font-weight: 800;
        background: linear-gradient(135deg, #fff 0%, var(--purple-light) 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .sidebar-tagline {
        font-family: 'JetBrains Mono', monospace; font-size: 0.68rem;
        color: rgba(255,255,255,0.35) !important; letter-spacing: 0.18em; text-transform: uppercase; margin-top: 0.2rem;
    }
    .sidebar-section-label {
        font-family: 'JetBrains Mono', monospace; font-size: 0.6rem;
        letter-spacing: 0.18em; text-transform: uppercase;
        color: rgba(255,255,255,0.25) !important; padding: 0.5rem 0.9rem 0.3rem;
    }
    .sidebar-step {
        display: flex; align-items: flex-start; gap: 0.75rem;
        padding: 0.55rem 0; border-bottom: 1px solid var(--border);
    }
    .sidebar-step-num {
        font-family: 'JetBrains Mono', monospace; font-size: 0.62rem;
        color: var(--purple-light) !important; background: var(--purple-pale);
        border: 1px solid var(--border-p); border-radius: 4px;
        padding: 0.18rem 0.4rem; min-width: 22px; text-align: center; margin-top: 0.1rem;
    }
    .sidebar-step-label { font-size: 0.88rem; font-weight: 600; color: #ffffff !important; }
    .sidebar-step-sub {
        font-family: 'JetBrains Mono', monospace; font-size: 0.62rem;
        color: rgba(255,255,255,0.3) !important; letter-spacing: 0.04em; margin-top: 0.08rem;
    }

    /* ── Main area ── */
    .main .block-container { background: var(--black) !important; padding-top: 1.5rem; max-width: 1300px; }

    /* ── Page Header ── */
    .page-header { padding: 2rem 0 1rem; }
    .page-header-pill {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: var(--purple-pale); border: 1px solid var(--border-p);
        border-radius: 999px; padding: 0.35rem 1rem;
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
        letter-spacing: 0.12em; text-transform: uppercase; color: var(--purple-light); margin-bottom: 0.9rem;
    }
    .page-header h1 {
        font-family: 'Syne', sans-serif; font-size: 3.2rem; font-weight: 800;
        letter-spacing: -0.03em; color: #ffffff; line-height: 1.05; margin: 0 0 0.5rem;
    }
    .page-header h1 .glow {
        background: linear-gradient(135deg, var(--purple-mid) 0%, var(--purple-light) 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .page-header p {
        font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;
        color: rgba(255,255,255,0.3); letter-spacing: 0.1em; text-transform: uppercase;
    }

    /* ── WHITE Step / Email Cards ── */
    .step-card, .wcard {
        background: #ffffff; border: 1px solid #e5e7eb; border-radius: 16px;
        padding: 2.25rem 2.5rem; margin-bottom: 1.75rem;
        position: relative; overflow: hidden; color: #111 !important;
    }
    .step-card::before, .wcard::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, var(--purple), var(--purple-light));
    }
    .step-card-glow, .wcard-glow {
        position: absolute; top: -60px; right: -60px; width: 220px; height: 220px;
        background: radial-gradient(circle, rgba(124,58,237,0.07) 0%, transparent 70%); pointer-events: none;
    }
    .step-num-badge, .card-badge {
        display: inline-flex; align-items: center; gap: 0.5rem;
        background: var(--purple-pale); border: 1px solid var(--border-p);
        border-radius: 8px; padding: 0.28rem 0.85rem;
        font-family: 'JetBrains Mono', monospace; font-size: 0.66rem;
        letter-spacing: 0.15em; text-transform: uppercase; color: var(--purple-light); margin-bottom: 0.5rem;
    }
    .step-title, .card-title {
        font-family: 'Syne', sans-serif; font-size: 1.5rem; font-weight: 700;
        color: #111111; letter-spacing: -0.01em; margin-bottom: 1.35rem;
    }

    /* ── JD Fields ── */
    .jd-field {
        background: #f5f3ff; border: 1px solid #e0d7ff;
        border-radius: 10px; padding: 0.75rem 1rem; margin-bottom: 0.55rem;
        position: relative; overflow: hidden;
    }
    .jd-field::before {
        content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
        background: linear-gradient(180deg, var(--purple), var(--purple-mid)); border-radius: 4px 0 0 4px;
    }
    .jd-field .lbl {
        font-family: 'JetBrains Mono', monospace; font-size: 0.63rem;
        letter-spacing: 0.18em; text-transform: uppercase; color: var(--purple); opacity: 0.8;
    }
    .jd-field .val { font-family: 'Syne', sans-serif; font-size: 1.1rem; font-weight: 600; color: #111111; margin-top: 0.15rem; }

    /* ── Tags ── */
    .tag { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 6px; font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; letter-spacing: 0.06em; margin: 0.18rem; }
    .tag-skill { background: var(--purple-pale); color: var(--purple-light); border: 1px solid var(--border-p); }
    .tag-match { background: var(--green-bg); color: var(--green); border: 1px solid rgba(16,185,129,0.3); }
    .tag-miss  { background: var(--red-bg); color: var(--red); border: 1px solid rgba(244,63,94,0.3); }

    /* ── LinkedIn Card ── */
    .linkedin-card {
        background: linear-gradient(135deg, #0a1628, #0d1f38);
        border: 1px solid rgba(0,119,181,0.35); border-radius: 12px; padding: 1.35rem 1.6rem; position: relative; overflow: hidden;
    }
    .linkedin-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent, #0077b5, transparent); }
    .linkedin-card .li-label { font-family: 'JetBrains Mono', monospace; font-size: 0.66rem; letter-spacing: 0.18em; text-transform: uppercase; color: #4fa3d4; margin-bottom: 0.7rem; }
    .linkedin-card .li-url { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: rgba(255,255,255,0.6); background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 0.7rem 1rem; word-break: break-all; line-height: 1.7; }

    /* ── Metric Cards ── */
    .metric-card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px; padding: 1.5rem 1rem; text-align: center; position: relative; overflow: hidden; }
    .metric-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, var(--purple), var(--purple-light)); }
    .metric-card .m-value { font-family: 'Syne', sans-serif; font-size: 2.6rem; font-weight: 800; background: linear-gradient(135deg, var(--purple) 0%, var(--purple-light) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; line-height: 1; }
    .metric-card .m-label { font-family: 'JetBrains Mono', monospace; font-size: 0.66rem; letter-spacing: 0.14em; text-transform: uppercase; color: #6b7280; margin-top: 0.45rem; }

    /* ── Pts Cards ── */
    .pts-card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 1.2rem 1.35rem; text-align: center; border-top: 3px solid var(--purple); }
    .pts-card .pts-num { font-family: 'Syne', sans-serif; font-size: 2rem; font-weight: 800; background: linear-gradient(135deg, var(--purple-mid), var(--purple-light)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .pts-card .pts-lbl { font-family: 'JetBrains Mono', monospace; font-size: 0.66rem; letter-spacing: 0.14em; text-transform: uppercase; color: #6b7280; margin-top: 0.3rem; }

    /* ── Candidate Rows ── */
    .cand-row { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 1.1rem 1.5rem; margin-bottom: 0.65rem; display: flex; align-items: center; gap: 1rem; position: relative; overflow: hidden; }
    .cand-row::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: linear-gradient(180deg, var(--purple), var(--purple-mid)); border-radius: 4px 0 0 4px; }
    .rank-badge { font-family: 'JetBrains Mono', monospace; font-size: 0.73rem; font-weight: 600; color: var(--purple-light); background: var(--purple-pale); border: 1px solid var(--border-p); border-radius: 8px; padding: 0.28rem 0.55rem; min-width: 38px; text-align: center; flex-shrink: 0; }
    .cand-name { font-family: 'Syne', sans-serif; font-size: 1.1rem; font-weight: 700; color: #111111; }
    .cand-meta { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; letter-spacing: 0.05em; color: #6b7280; margin-top: 0.18rem; }
    .score-bar-bg { height: 4px; background: #f3f0ff; border-radius: 2px; margin-bottom: 0.7rem; }
    .score-bar-fill { height: 4px; border-radius: 2px; background: linear-gradient(90deg, var(--purple), var(--purple-light)); }

    /* ── Export Info ── */
    .export-info { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 1.5rem 1.75rem; border-top: 3px solid var(--purple); }
    .export-info .ei-title { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; letter-spacing: 0.16em; text-transform: uppercase; color: var(--purple); margin-bottom: 0.85rem; }
    .export-info .ei-item { display: flex; align-items: flex-start; gap: 0.65rem; padding: 0.5rem 0; border-bottom: 1px solid #f3f4f6; font-size: 0.95rem; color: #374151; }
    .export-info .ei-item:last-child { border-bottom: none; }
    .export-info .ei-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--purple); flex-shrink: 0; margin-top: 0.42rem; }

    /* ── Empty placeholder ── */
    .empty-placeholder { text-align: center; padding: 3rem 1rem; border: 1px dashed rgba(124,58,237,0.3); border-radius: 12px; background: #f5f3ff; }
    .empty-placeholder .ep-icon { font-size: 2.2rem; opacity: 0.3; margin-bottom: 0.5rem; }
    .empty-placeholder .ep-text { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; letter-spacing: 0.14em; text-transform: uppercase; color: #9ca3af; }

    /* ── Email Preview ── */
    .email-preview { background: #fafafa; border: 1px solid #e5e7eb; border-radius: 12px; padding: 1.5rem 1.75rem; }
    .email-preview .ep-to { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #6b7280; margin-bottom: 0.3rem; letter-spacing: 0.06em; }
    .email-preview .ep-subject { font-family: 'Syne', sans-serif; font-size: 1.15rem; font-weight: 700; color: #111; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.75rem; margin-bottom: 0.9rem; }
    .email-preview .ep-body { font-size: 0.95rem; color: #374151; line-height: 1.75; white-space: pre-wrap; }

    /* ── Status badges ── */
    .status-sent { display: inline-flex; align-items: center; gap: 0.4rem; background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.3); color: #10b981; border-radius: 8px; padding: 0.3rem 0.85rem; font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; }
    .status-fail { display: inline-flex; align-items: center; gap: 0.4rem; background: rgba(244,63,94,0.12); border: 1px solid rgba(244,63,94,0.3); color: #f43f5e; border-radius: 8px; padding: 0.3rem 0.85rem; font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; }

    /* ── Candidate pills ── */
    .cand-pill-wrap { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }
    .cand-pill { display: inline-flex; align-items: center; gap: 0.4rem; background: #f5f3ff; border: 1.5px solid #e0d7ff; border-radius: 999px; padding: 0.4rem 1rem; font-size: 0.88rem; font-weight: 500; color: #3b0764; }
    .cand-pill.selected { background: var(--purple); border-color: var(--purple); color: #ffffff; }
    .cand-pill .pill-score { font-family: 'JetBrains Mono', monospace; font-size: 0.63rem; background: rgba(124,58,237,0.12); border-radius: 999px; padding: 0.1rem 0.45rem; color: var(--purple); }
    .cand-pill.selected .pill-score { background: rgba(255,255,255,0.2); color: #fff; }

    /* ── Gmail setup card ── */
    .gmail-setup { background: #fff8f0; border: 1px solid #fed7aa; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1rem; }
    .gmail-setup .gs-title { font-family: 'Syne', sans-serif; font-size: 1rem; font-weight: 700; color: #92400e; margin-bottom: 0.35rem; }
    .gmail-setup .gs-body { font-size: 0.88rem; color: #78350f; line-height: 1.75; }
    .gmail-setup code { background: #fef3c7; padding: 0.1rem 0.4rem; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #92400e; }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, var(--purple) 0%, #9333ea 100%) !important;
        color: #fff !important; border: none !important; border-radius: 10px !important;
        font-family: 'Outfit', sans-serif !important; font-size: 0.95rem !important;
        font-weight: 600 !important; padding: 0.7rem 1.75rem !important;
        box-shadow: 0 0 22px rgba(124,58,237,0.35) !important;
    }
    .stButton > button:hover { box-shadow: 0 0 36px rgba(124,58,237,0.6) !important; }
    .stLinkButton > a { background: var(--black-hover) !important; color: var(--purple-light) !important; border: 1px solid var(--border-p) !important; border-radius: 10px !important; font-family: 'Outfit', sans-serif !important; font-size: 0.9rem !important; font-weight: 600 !important; }
    .stDownloadButton > button { background: #ffffff !important; color: #111111 !important; border: 1px solid #e5e7eb !important; border-radius: 10px !important; font-family: 'Outfit', sans-serif !important; font-size: 0.92rem !important; font-weight: 500 !important; }
    .stDownloadButton > button:hover { border-color: var(--purple) !important; color: var(--purple) !important; }

    /* ── Inputs ── */
    .stTextArea textarea, .stTextInput input { background: #ffffff !important; border: 1px solid #e5e7eb !important; border-radius: 10px !important; color: #111111 !important; font-family: 'Outfit', sans-serif !important; font-size: 1rem !important; }
    .stTextArea textarea:focus, .stTextInput input:focus { border-color: var(--purple) !important; box-shadow: 0 0 0 3px rgba(124,58,237,0.15) !important; }
    [data-testid="stFileUploader"] { background: #ffffff !important; border: 1px dashed rgba(124,58,237,0.4) !important; border-radius: 12px !important; }

    /* ── Labels ── */
    label { font-family: 'JetBrains Mono', monospace !important; font-size: 0.72rem !important; letter-spacing: 0.1em !important; text-transform: uppercase !important; color: rgba(255,255,255,0.5) !important; }
    .step-card label, .wcard label { color: #6b7280 !important; }
    .stCaption { font-family: 'JetBrains Mono', monospace !important; font-size: 0.68rem !important; color: rgba(255,255,255,0.3) !important; }
    .step-card .stCaption, .wcard .stCaption { color: #9ca3af !important; }
    [data-testid="stAlert"] { background: #f5f3ff !important; border: 1px solid #e0d7ff !important; border-radius: 10px !important; font-size: 1rem !important; color: #111 !important; }
    div[data-testid="stProgress"] > div > div { background: linear-gradient(90deg, var(--purple), var(--purple-light)) !important; }
    .streamlit-expanderHeader { background: #f9fafb !important; border: 1px solid #e5e7eb !important; border-radius: 10px !important; font-family: 'JetBrains Mono', monospace !important; font-size: 0.7rem !important; color: #6b7280 !important; }
    .stDataFrame { border: 1px solid #e5e7eb !important; border-radius: 10px !important; overflow: hidden !important; }
    .stRadio label { font-size: 0.85rem !important; text-transform: none !important; }
    .step-card .stRadio label, .wcard .stRadio label { color: #374151 !important; }
    .step-card .stSlider label, .wcard .stSlider label { color: #6b7280 !important; }
    hr { border-color: rgba(255,255,255,0.08) !important; }
    .stCodeBlock { background: #1e1040 !important; border: 1px solid var(--border-p) !important; border-radius: 10px !important; }
    .stMultiSelect [data-baseweb="tag"] { background: var(--purple) !important; }
    .stCheckbox label { font-size: 0.9rem !important; text-transform: none !important; color: #374151 !important; }
</style>
""", unsafe_allow_html=True)

# ─── Gmail Helpers ─────────────────────────────────────────────────────────────
def get_gmail_service():
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
            flow  = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    try:
        service = build("gmail", "v1", credentials=creds)
        return service, "ok"
    except Exception as e:
        return None, str(e)

def send_email(service, to_email, subject, body):
    msg = MIMEMultipart("alternative")
    msg["To"]      = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()

def generate_email_content(candidate_name, email_type, jd_role, company_name, sender_name):
    subjects = {
        "Interview Invitation":    f"Interview Invitation — {jd_role} at {company_name}",
        "Shortlisting Notice":     f"You've Been Shortlisted — {jd_role} at {company_name}",
        "Further Info Request":    f"Next Steps — {jd_role} Application at {company_name}",
        "Congratulations — Offer": f"🎉 Offer Letter — {jd_role} at {company_name}",
        "Rejection (Polite)":      f"Regarding Your Application — {jd_role} at {company_name}",
    }
    bodies = {
        "Interview Invitation": f"""Dear {candidate_name},

Thank you for your interest in the {jd_role} position at {company_name}.

After carefully reviewing your profile, we are pleased to invite you for an interview. Your background makes you a strong candidate, and we are excited to learn more about you.

Interview Details:
• Position  : {jd_role}
• Format    : To be confirmed (Video / In-person)
• Duration  : Approximately 45–60 minutes

Please reply with your availability over the next 5 business days and we will coordinate a suitable time.

Warm regards,
{sender_name}
{company_name} — Talent Acquisition""",

        "Shortlisting Notice": f"""Dear {candidate_name},

We are pleased to inform you that you have been shortlisted for the {jd_role} role at {company_name}.

Your profile stood out and we would like to move forward with the next stage of our selection process. Our team will reach out shortly with further details.

Best regards,
{sender_name}
{company_name} — Talent Acquisition""",

        "Further Info Request": f"""Dear {candidate_name},

Thank you for applying for the {jd_role} position at {company_name}.

We would like to learn more about your experience before proceeding. Could you please share:

  1. A brief overview of your most relevant projects or achievements
  2. Your current notice period / availability to join
  3. Your expected compensation range (optional)

Regards,
{sender_name}
{company_name} — Talent Acquisition""",

        "Congratulations — Offer": f"""Dear {candidate_name},

Congratulations! 🎉

We are thrilled to extend an offer for the {jd_role} position at {company_name}. It is our pleasure to welcome you to the team.

Please review the attached offer letter and confirm your acceptance by replying to this email.

Warmly,
{sender_name}
{company_name} — Talent Acquisition""",

        "Rejection (Polite)": f"""Dear {candidate_name},

Thank you sincerely for applying for the {jd_role} role at {company_name}.

After careful consideration, we have decided to move forward with other candidates whose experience more closely aligns with current requirements. We appreciate your interest and encourage you to apply for future openings.

We wish you the very best in your career.

Kind regards,
{sender_name}
{company_name} — Talent Acquisition""",
    }
    return subjects.get(email_type, ""), bodies.get(email_type, "")

# ─── Session State ─────────────────────────────────────────────────────────────
defaults = {
    "jd_data": None, "jd_text": None, "candidates_df": None,
    "scored_df": None, "linkedin_url": None,
    "selected_candidates": [], "email_drafts": {}, "send_log": [],
    "active_tab": "recruiter",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-brand">⬡ NexRecruit AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-tagline">AI-Powered Recruiting Suite</div>', unsafe_allow_html=True)
    st.divider()

    # ── Navigation Tabs ──
    st.markdown('<div class="sidebar-section-label">Navigation</div>', unsafe_allow_html=True)

    recruiter_active = "active" if st.session_state.active_tab == "recruiter" else ""
    email_active     = "active" if st.session_state.active_tab == "email"     else ""

    col_r, col_e = st.columns(2)
    if col_r.button("⬡  Recruiter", use_container_width=True):
        st.session_state.active_tab = "recruiter"
        st.rerun()
    if col_e.button("✉  Email", use_container_width=True):
        st.session_state.active_tab = "email"
        st.rerun()

    # Active indicator
    st.markdown(f"""
    <div style="display:flex;gap:0.4rem;margin:0.3rem 0 0.75rem">
        <div style="flex:1;height:3px;border-radius:2px;background:{'linear-gradient(90deg,var(--purple),var(--purple-light))' if st.session_state.active_tab=='recruiter' else 'rgba(255,255,255,0.1)'}"></div>
        <div style="flex:1;height:3px;border-radius:2px;background:{'linear-gradient(90deg,var(--purple),var(--purple-light))' if st.session_state.active_tab=='email' else 'rgba(255,255,255,0.1)'}"></div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Contextual sidebar content ──
    if st.session_state.active_tab == "recruiter":
        st.markdown('<div class="sidebar-section-label">Pipeline Steps</div>', unsafe_allow_html=True)
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
        # Show scored status
        if st.session_state.scored_df is not None:
            n = len(st.session_state.scored_df)
            st.markdown(f"""
            <div style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.25);border-radius:8px;padding:0.65rem 0.9rem">
                <div style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;letter-spacing:0.12em;text-transform:uppercase;color:#10b981">✓ Candidates Scored</div>
                <div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;color:#fff;margin-top:0.2rem">{n} candidates ready</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;color:rgba(255,255,255,0.4);margin-top:0.2rem">Switch to ✉ Email tab to send outreach</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✉  Go to Email Outreach →", use_container_width=True):
                st.session_state.active_tab = "email"
                st.rerun()
        st.markdown('<span style="font-family:\'JetBrains Mono\',monospace;font-size:0.6rem;letter-spacing:0.15em;color:rgba(255,255,255,0.18)">⬡ FULLY OFFLINE · NO API KEY</span>', unsafe_allow_html=True)

    else:  # email tab sidebar
        st.markdown('<div class="sidebar-section-label">Sender Details</div>', unsafe_allow_html=True)
        sender_name  = st.text_input("Your name", value="Hiring Manager",   placeholder="Hiring Manager Name",  label_visibility="collapsed")
        company_name = st.text_input("Company",   value="Our Company",      placeholder="Company Name",          label_visibility="collapsed")
        jd_role_e    = st.text_input("Role",       value="Software Engineer",placeholder="Role being hired for", label_visibility="collapsed")
        st.divider()
        st.markdown('<div class="sidebar-section-label">Email Template</div>', unsafe_allow_html=True)
        email_type = st.selectbox("Template", [
            "Interview Invitation", "Shortlisting Notice",
            "Further Info Request", "Congratulations — Offer", "Rejection (Polite)",
        ], label_visibility="collapsed")
        st.divider()
        st.markdown('<div class="sidebar-section-label">Gmail Connection</div>', unsafe_allow_html=True)
        if not GMAIL_AVAILABLE:
            st.markdown('<span style="color:#f43f5e;font-size:0.8rem">⚠ packages not installed</span>', unsafe_allow_html=True)
            st.caption("pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        elif not os.path.exists(CREDS_FILE):
            st.markdown('<span style="color:#f59e0b;font-size:0.8rem">⚠ credentials.json missing</span>', unsafe_allow_html=True)
            st.caption("Place credentials.json in the app folder.")
        elif os.path.exists(TOKEN_FILE):
            st.markdown('<span style="color:#10b981;font-size:0.85rem">✓ Gmail connected</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span style="color:#f59e0b;font-size:0.8rem">○ Not authenticated</span>', unsafe_allow_html=True)
            if st.button("Connect Gmail", use_container_width=True):
                svc, status = get_gmail_service()
                if status == "ok":
                    st.success("Gmail connected!")
                    st.rerun()
                else:
                    st.error(f"Auth failed: {status}")
        st.divider()
        if st.button("⬡  Back to Recruiter ←", use_container_width=True):
            st.session_state.active_tab = "recruiter"
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# ██████████████████  TAB: RECRUITER PIPELINE  ██████████████████████████
# ═══════════════════════════════════════════════════════════════════════
if st.session_state.active_tab == "recruiter":

    st.markdown("""
    <div class="page-header">
        <div class="page-header-pill">⬡ &nbsp; AI-Powered Recruiting</div>
        <h1>Find the <span class="glow">Right Talent</span><br>Faster Than Ever.</h1>
        <p>Upload JD → Extract → Score → Export → Email</p>
    </div>
    """, unsafe_allow_html=True)

    # ── STEP 1 ──────────────────────────────────────────────────────────
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
                ("Role", jd.get("role","—")), ("Location", jd.get("location","—")),
                ("Experience", f"{jd.get('experience_min','?')}–{jd.get('experience_max','?')} yrs"),
                ("Industry", jd.get("industry","—")), ("Type", jd.get("employment_type","—")),
                ("Company", jd.get("company","—")),
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

    # ── STEP 2 — LinkedIn ───────────────────────────────────────────────
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
            skills_str = ', '.join(jd.get('skills', [])[:4])
            st.markdown(f"""
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.7rem;color:#374151;letter-spacing:0.05em;line-height:2.2;margin-top:0.75rem">
                <div style="color:var(--purple);text-transform:uppercase;letter-spacing:0.15em;font-size:0.63rem;margin-bottom:0.35rem;font-weight:600">Built from</div>
                <div>Role · <strong>{jd.get('role','—')}</strong></div>
                {'<div>Skills · <strong>' + skills_str + '</strong></div>' if skills_str else ''}
            </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Tip — After opening LinkedIn, apply filters for location, current company, or degree of connection.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── STEP 3 — Upload Candidates ──────────────────────────────────────
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
                st.markdown('<div style="margin-top:0.75rem;font-family:\'JetBrains Mono\',monospace;font-size:0.68rem;color:#6b7280;letter-spacing:0.06em;line-height:2">Expected: name · role · location · experience · skills · email<br>Column names auto-detected (case-insensitive).</div>', unsafe_allow_html=True)
        with c2:
            if st.session_state.candidates_df is not None:
                st.caption("Preview — first 5 rows")
                st.dataframe(st.session_state.candidates_df.head(), use_container_width=True, height=220)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── STEP 4 — Score ──────────────────────────────────────────────────
    if st.session_state.jd_data and st.session_state.candidates_df is not None:
        st.markdown('<div class="step-card"><div class="step-card-glow"></div><div class="step-num-badge">⬡ &nbsp; Step 04</div><div class="step-title">Filter, Score & Rank Candidates</div>', unsafe_allow_html=True)
        sc1, sc2, sc3 = st.columns(3)
        for col, lbl, pts in [(sc1,"Skill Match","40"), (sc2,"Role Match","30"), (sc3,"Experience","30")]:
            col.markdown(f'<div class="pts-card"><div class="pts-num">{pts}</div><div class="pts-lbl">{lbl} · max pts</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("⬡  Score All Candidates", use_container_width=True):
            with st.spinner("Scoring candidates…"):
                scored, name_col = score_candidates(st.session_state.candidates_df, st.session_state.jd_data)
                st.session_state.scored_df           = scored
                st.session_state.name_col_detected   = name_col

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
                role_val = str(row.get("role", row.get("job_title", row.get("title","—"))))
                loc_val  = str(row.get("location", row.get("city","—")))
                loc_flag = str(row.get("location_match",""))
                matched  = str(row.get("matched_skills",""))
                missing  = str(row.get("missing_skills",""))
                sc_color = "#7c3aed" if score >= 70 else ("#374151" if score >= 50 else "#f43f5e")
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
                        <div style="font-family:'Syne',sans-serif;font-size:1.9rem;font-weight:800;color:{sc_color};line-height:1">{score}</div>
                        <div style="font-family:'JetBrains Mono',monospace;font-size:0.63rem;color:#9ca3af">/ 100</div>
                    </div>
                </div>
                <div class="score-bar-bg"><div class="score-bar-fill" style="width:{score}%"></div></div>
                """, unsafe_allow_html=True)
            with st.expander("View full scored table"):
                st.dataframe(scored, use_container_width=True, height=400)

            # ── CTA to email tab ──
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
            <div style="background:linear-gradient(135deg,rgba(124,58,237,0.12),rgba(157,92,246,0.08));
                border:1px solid rgba(124,58,237,0.3);border-radius:12px;padding:1.25rem 1.5rem;text-align:center">
                <div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;color:#fff;margin-bottom:0.3rem">
                    Ready to reach out? ✉
                </div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;color:rgba(255,255,255,0.45);letter-spacing:0.08em;margin-bottom:0.75rem">
                    Switch to the Email tab to send personalised outreach to your top candidates
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✉  Go to Automate Email →", use_container_width=True):
                st.session_state.active_tab = "email"
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # ── STEP 5 — Export ─────────────────────────────────────────────────
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

# ═══════════════════════════════════════════════════════════════════════
# ██████████████████  TAB: EMAIL OUTREACH  █████████████████████████████
# ═══════════════════════════════════════════════════════════════════════
else:
    # Grab sidebar values (set above)
    sender_name  = st.session_state.get("_sender_name",  "Hiring Manager")
    company_name = st.session_state.get("_company_name", "Our Company")
    jd_role_e    = st.session_state.get("_jd_role",      "Software Engineer")
    email_type   = st.session_state.get("_email_type",   "Interview Invitation")
    # Read from sidebar widgets via their keys
    try:
        sender_name  = st.session_state["Your name"]
        company_name = st.session_state["Company"]
        jd_role_e    = st.session_state["Role"]
        email_type   = st.session_state["Template"]
    except Exception:
        pass

    st.markdown("""
    <div class="page-header">
        <div class="page-header-pill">✉ &nbsp; Automated Email Outreach</div>
        <h1>Send <span class="glow">Personalised Emails</span><br>to Your Candidates.</h1>
        <p>Select → Review & Edit → Send via Gmail</p>
    </div>
    """, unsafe_allow_html=True)

    # Gmail setup guide
    if not GMAIL_AVAILABLE or not os.path.exists(CREDS_FILE):
        st.markdown("""
        <div class="wcard"><div class="wcard-glow"></div>
        <div class="card-badge">✉ &nbsp; Setup Required</div>
        <div class="card-title">Gmail API Setup (Free · One-time)</div>
        <div class="gmail-setup">
            <div class="gs-title">Step 1 — Install packages</div>
            <div class="gs-body"><code>pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib</code></div>
        </div>
        <div class="gmail-setup">
            <div class="gs-title">Step 2 — Create credentials</div>
            <div class="gs-body">Go to <strong>console.cloud.google.com</strong> → New project → Enable <strong>Gmail API</strong> → APIs & Services → Credentials → OAuth 2.0 Client ID → Desktop App → Download JSON → rename to <code>credentials.json</code> → place in app folder.</div>
        </div>
        <div class="gmail-setup">
            <div class="gs-title">Step 3 — Connect</div>
            <div class="gs-body">Click <strong>Connect Gmail</strong> in the sidebar. A browser login opens once, then <code>token.pickle</code> saves permanently.</div>
        </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Step E1 — Load Data ─────────────────────────────────────────────
    st.markdown('<div class="wcard"><div class="wcard-glow"></div><div class="card-badge">✉ &nbsp; Step 01</div><div class="card-title">Load Scored Candidate Data</div>', unsafe_allow_html=True)

    # If scored_df already in session (from recruiter tab), auto-use it
    if st.session_state.scored_df is not None:
        st.markdown(f"""
        <div style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.25);border-radius:10px;padding:0.9rem 1.2rem;margin-bottom:0.75rem">
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;letter-spacing:0.12em;text-transform:uppercase;color:#10b981">✓ Loaded from Recruiter Tab</div>
            <div style="font-size:0.95rem;color:#374151;margin-top:0.25rem"><strong>{len(st.session_state.scored_df)}</strong> candidates already scored and ready · {len(st.session_state.scored_df.columns)} columns</div>
        </div>
        """, unsafe_allow_html=True)

    up_col1, up_col2 = st.columns([1, 1], gap="large")
    with up_col1:
        st.caption("Or upload a scored CSV directly")
        uploaded = st.file_uploader("Upload scored candidates CSV", type=["csv"], label_visibility="collapsed", key="email_csv_upload")
        if uploaded:
            df = pd.read_csv(uploaded)
            st.session_state.scored_df = df
            st.success(f"✓ Loaded {len(df)} candidates · {len(df.columns)} columns")
    with up_col2:
        if st.session_state.scored_df is not None:
            df = st.session_state.scored_df
            email_col = df.columns[-1]
            for c in df.columns:
                if "email" in c.lower(): email_col = c; break
            st.markdown(f"""
            <div style="background:#f5f3ff;border:1px solid #e0d7ff;border-radius:10px;padding:1rem 1.25rem">
                <div style="font-family:'JetBrains Mono',monospace;font-size:0.63rem;letter-spacing:0.15em;text-transform:uppercase;color:var(--purple);margin-bottom:0.5rem">Column Detection</div>
                <div style="font-size:0.92rem;color:#374151;line-height:2.1">
                    <b>Rows:</b> {len(df)}<br>
                    <b>Email column:</b> <code style="background:#ede9fe;padding:0.1rem 0.4rem;border-radius:4px;font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:#5b21b6">{email_col}</code><br>
                    <b>Columns:</b> {', '.join(df.columns.tolist())}
                </div>
            </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Step E2 — Select Candidates ────────────────────────────────────
    if st.session_state.scored_df is not None:
        df = st.session_state.scored_df
        email_col = df.columns[-1]; name_col = df.columns[0]; score_col = None
        for c in df.columns:
            if "email" in c.lower(): email_col = c
            if c.lower() in ("name","candidate_name","full_name","candidate"): name_col = c
            if "total_score" in c.lower() or c.lower() == "score": score_col = c

        st.markdown('<div class="wcard"><div class="wcard-glow"></div><div class="card-badge">✉ &nbsp; Step 02</div><div class="card-title">Select Candidates to Email</div>', unsafe_allow_html=True)

        f1, f2 = st.columns([2, 1], gap="large")
        with f1:
            search_q = st.text_input("Search by name", placeholder="Type a name to filter…", label_visibility="collapsed", key="email_search")
        with f2:
            min_score = st.slider("Min score", 0, 100, 0, key="email_min_score") if score_col else 0

        filtered = df.copy()
        if search_q:
            filtered = filtered[filtered[name_col].astype(str).str.contains(search_q, case=False, na=False)]
        if score_col and min_score > 0:
            filtered = filtered[filtered[score_col] >= min_score]

        sa1, sa2, _ = st.columns([1, 1, 4])
        if sa1.button("Select All", use_container_width=True, key="sel_all"):
            st.session_state.selected_candidates = filtered[name_col].tolist(); st.rerun()
        if sa2.button("Clear All",  use_container_width=True, key="clr_all"):
            st.session_state.selected_candidates = []; st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # Visual pills (display only)
        pills_html = '<div class="cand-pill-wrap">'
        for _, row in filtered.iterrows():
            name  = str(row[name_col])
            score = str(int(row[score_col])) if score_col and pd.notna(row.get(score_col)) else "—"
            sel   = "selected" if name in st.session_state.selected_candidates else ""
            pills_html += f'<span class="cand-pill {sel}"><span>👤 {name}</span><span class="pill-score">{score}</span></span>'
        pills_html += '</div>'
        st.markdown(pills_html, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        all_names = filtered[name_col].tolist()
        selected  = st.multiselect("Select candidates", options=all_names,
            default=[n for n in st.session_state.selected_candidates if n in all_names],
            label_visibility="collapsed", key="email_multiselect")
        st.session_state.selected_candidates = selected
        if selected:
            st.markdown(f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.68rem;color:#6b7280;letter-spacing:0.1em;margin-top:0.4rem">{len(selected)} candidate(s) selected</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Step E3 — Generate & Edit Drafts ───────────────────────────────
    if st.session_state.scored_df is not None and st.session_state.selected_candidates:
        df = st.session_state.scored_df
        email_col = df.columns[-1]; name_col = df.columns[0]; score_col = None
        for c in df.columns:
            if "email" in c.lower(): email_col = c
            if c.lower() in ("name","candidate_name","full_name","candidate"): name_col = c
            if "total_score" in c.lower() or c.lower() == "score": score_col = c

        st.markdown('<div class="wcard"><div class="wcard-glow"></div><div class="card-badge">✉ &nbsp; Step 03</div><div class="card-title">Review & Edit Email Drafts</div>', unsafe_allow_html=True)

        if st.button("⚡  Generate All Drafts", use_container_width=True):
            drafts = {}
            for name in st.session_state.selected_candidates:
                subj, body = generate_email_content(name, email_type, jd_role_e, company_name, sender_name)
                drafts[name] = {"subject": subj, "body": body}
            st.session_state.email_drafts = drafts
            st.success(f"✓ {len(drafts)} draft(s) generated. Review and edit below.")
            st.rerun()

        if st.session_state.email_drafts:
            st.markdown("<br>", unsafe_allow_html=True)
            for name in st.session_state.selected_candidates:
                if name not in st.session_state.email_drafts: continue
                row      = df[df[name_col].astype(str) == name].iloc[0]
                to_email = str(row[email_col]) if email_col in row.index else "unknown@email.com"
                draft    = st.session_state.email_drafts[name]

                with st.expander(f"✉  {name}  ·  {to_email}", expanded=True):
                    ec1, ec2 = st.columns([1, 1], gap="large")
                    with ec1:
                        st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.63rem;color:#6b7280;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.2rem">Subject Line</div>', unsafe_allow_html=True)
                        new_subject = st.text_input(f"subj_inp_{name}", value=draft["subject"], key=f"subj_{name}", label_visibility="collapsed")
                        st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.63rem;color:#6b7280;letter-spacing:0.1em;text-transform:uppercase;margin:0.75rem 0 0.2rem">Message Body</div>', unsafe_allow_html=True)
                        new_body = st.text_area(f"body_inp_{name}", value=draft["body"], height=310, key=f"body_{name}", label_visibility="collapsed")
                        if st.button("💾  Save Changes", key=f"save_{name}"):
                            st.session_state.email_drafts[name]["subject"] = new_subject
                            st.session_state.email_drafts[name]["body"]    = new_body
                            st.success("✓ Saved.")
                    with ec2:
                        st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.63rem;color:#6b7280;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.4rem">Live Preview</div>', unsafe_allow_html=True)
                        prev_subj = st.session_state.get(f"subj_{name}", draft["subject"]) or draft["subject"]
                        prev_body = st.session_state.get(f"body_{name}", draft["body"])    or draft["body"]
                        st.markdown(f"""
                        <div class="email-preview">
                            <div class="ep-to">To: {to_email}</div>
                            <div class="ep-subject">{prev_subj}</div>
                            <div class="ep-body">{prev_body}</div>
                        </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Step E4 — Send ─────────────────────────────────────────────────
    if st.session_state.scored_df is not None and st.session_state.selected_candidates and st.session_state.email_drafts:
        df = st.session_state.scored_df
        email_col = df.columns[-1]; name_col = df.columns[0]
        for c in df.columns:
            if "email" in c.lower(): email_col = c
            if c.lower() in ("name","candidate_name","full_name","candidate"): name_col = c

        st.markdown('<div class="wcard"><div class="wcard-glow"></div><div class="card-badge">✉ &nbsp; Step 04</div><div class="card-title">Send Emails</div>', unsafe_allow_html=True)

        ready = [n for n in st.session_state.selected_candidates if n in st.session_state.email_drafts]
        st.markdown(f"""
        <div style="background:#f5f3ff;border:1px solid #e0d7ff;border-radius:10px;padding:1rem 1.25rem;margin-bottom:1rem">
            <div style="font-family:'JetBrains Mono',monospace;font-size:0.63rem;letter-spacing:0.15em;text-transform:uppercase;color:var(--purple);margin-bottom:0.35rem">Ready to send</div>
            <div style="font-size:1rem;color:#374151"><b>{len(ready)}</b> email(s) will be sent via your connected Gmail account.</div>
        </div>""", unsafe_allow_html=True)

        confirm = st.checkbox("✓  I have reviewed all drafts and confirm sending", value=False)
        sc1, sc2 = st.columns([1, 2])
        send_clicked = sc1.button("✉  Send All Emails", use_container_width=True, disabled=not confirm)

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
                    log = []; progress = st.progress(0)
                    for i, name in enumerate(ready):
                        row      = df[df[name_col].astype(str) == name].iloc[0]
                        to_email = str(row[email_col])
                        draft    = st.session_state.email_drafts[name]
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
                    st.success(f"✓ {sum(1 for l in log if l['status']=='sent')}/{len(ready)} emails sent.")

        if st.session_state.send_log:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("View Send Log"):
                st.dataframe(pd.DataFrame(st.session_state.send_log), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ─── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:2.5rem 0 1rem;border-top:1px solid rgba(255,255,255,0.07);margin-top:1.5rem">
    <div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:800;
        background:linear-gradient(135deg,#fff,#c4b5fd);-webkit-background-clip:text;-webkit-text-fill-color:transparent">
        ⬡ NexRecruit AI
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.6rem;letter-spacing:0.2em;
        text-transform:uppercase;color:rgba(255,255,255,0.18);margin-top:0.3rem">
        Intelligent · Offline · Precise
    </div>
</div>
""", unsafe_allow_html=True)