"""
services.gmail_service
======================
Gmail OAuth + send + templated outreach copy. Everything email-related
that used to live inline in ``app.py``.

Public API
----------
* ``get_service()``                    — authenticates and returns a Gmail API client
* ``send_email(svc, to, subj, body)``  — actually sends a single message
* ``generate_email_content(...)``      — picks subject + body template
* ``available_templates()``            — list of template names for the UI dropdown

Design notes
------------
* OAuth flow uses the standard ``token.pickle`` + ``credentials.json``
  files at the project root (unchanged from the original behaviour).
* Heavy imports (``google.*``) live inside ``get_service()`` so this
  module can be imported even on machines without the Google client
  libraries — they're only needed when the user actually hits "Send".
"""

from __future__ import annotations

import base64
import os
import pickle
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from core.logger import get_logger

log = get_logger(__name__)


# ─── OAuth file locations / scopes ─────────────────────────────────────────────
SCOPES: list[str] = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_FILE = "token.pickle"
CREDS_FILE = "credentials.json"


def has_libraries() -> bool:
    """True iff the Google client libraries are importable on this machine."""
    try:
        import googleapiclient  # noqa: F401
        import google_auth_oauthlib  # noqa: F401
        return True
    except ImportError:
        return False


# ─── Authentication ────────────────────────────────────────────────────────────
def get_service() -> tuple[Any | None, str]:
    """
    Return ``(gmail_service, status)`` where ``status`` is:

    * ``"ok"``                  — authenticated successfully
    * ``"credentials_missing"`` — no ``credentials.json`` on disk
    * any other string          — the underlying error message

    Heavy Google imports are lazy so the module loads on machines that
    haven't installed the Google client libraries yet.
    """
    try:
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        return None, f"google_libs_missing: {exc}"

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
        return build("gmail", "v1", credentials=creds), "ok"
    except Exception as exc:  # noqa: BLE001
        log.exception("Gmail build() failed")
        return None, str(exc)


# ─── Sending ───────────────────────────────────────────────────────────────────
def send_email(service: Any, to_email: str, subject: str, body: str) -> None:
    """Send a plain-text email through an authenticated Gmail service."""
    msg = MIMEMultipart("alternative")
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


# ─── Email templates ───────────────────────────────────────────────────────────
_TEMPLATES: dict[str, tuple[str, str]] = {
    "Interview Invitation": (
        "Interview Invitation — {jd_role} at {company_name}",
        """Dear {candidate_name},

Thank you for your interest in the {jd_role} position at {company_name}.

After reviewing your profile, we are pleased to invite you for an interview. Your background makes you a strong candidate.

Interview Details:
• Position  : {jd_role}
• Format    : To be confirmed (Video / In-person)
• Duration  : Approximately 45–60 minutes

Please reply with your availability over the next 5 business days.

Warm regards,
{sender_name}
{company_name} — Talent Acquisition""",
    ),
    "Shortlisting Notice": (
        "You've Been Shortlisted — {jd_role} at {company_name}",
        """Dear {candidate_name},

We are pleased to inform you that you have been shortlisted for the {jd_role} role at {company_name}.

Your profile stood out and we would like to move forward. Our team will reach out with further details shortly.

Best regards,
{sender_name}
{company_name} — Talent Acquisition""",
    ),
    "Further Info Request": (
        "Next Steps — {jd_role} Application at {company_name}",
        """Dear {candidate_name},

Thank you for applying for {jd_role} at {company_name}.

We'd like to learn more before proceeding. Could you share:
  1. A brief overview of your most relevant projects
  2. Your current notice period / availability
  3. Your expected compensation range (optional)

Regards,
{sender_name}
{company_name} — Talent Acquisition""",
    ),
    "Congratulations — Offer": (
        "🎉 Offer Letter — {jd_role} at {company_name}",
        """Dear {candidate_name},

Congratulations! 🎉

We are thrilled to extend an offer for the {jd_role} position at {company_name}. Please review the attached offer letter and confirm your acceptance by replying to this email.

Warmly,
{sender_name}
{company_name} — Talent Acquisition""",
    ),
    "Rejection (Polite)": (
        "Regarding Your Application — {jd_role} at {company_name}",
        """Dear {candidate_name},

Thank you sincerely for applying for the {jd_role} role at {company_name}.

After careful consideration, we have decided to move forward with other candidates whose experience more closely aligns with current requirements. We encourage you to apply for future openings.

We wish you the very best.

Kind regards,
{sender_name}
{company_name} — Talent Acquisition""",
    ),
}


def available_templates() -> list[str]:
    """Return the template names for use in a Streamlit selectbox."""
    return list(_TEMPLATES.keys())


def generate_email_content(
    candidate_name: str,
    email_type: str,
    jd_role: str,
    company_name: str,
    sender_name: str,
) -> tuple[str, str]:
    """
    Render the ``(subject, body)`` tuple for an outreach email.

    Unknown ``email_type`` returns ``("", "")`` so the caller can validate.
    """
    subj_tpl, body_tpl = _TEMPLATES.get(email_type, ("", ""))
    if not subj_tpl:
        return "", ""
    fmt = dict(
        candidate_name=candidate_name,
        jd_role=jd_role,
        company_name=company_name,
        sender_name=sender_name,
    )
    return subj_tpl.format(**fmt), body_tpl.format(**fmt)


__all__ = [
    "get_service",
    "send_email",
    "generate_email_content",
    "available_templates",
    "SCOPES",
    "TOKEN_FILE",
    "CREDS_FILE",
]
