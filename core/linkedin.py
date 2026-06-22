"""
core/linkedin.py
─────────────────
Generates LinkedIn People Search URLs (and a Google X-ray fallback) from a
parsed JD dict.

IMPORTANT — what this can and can't do
───────────────────────────────────────
LinkedIn's own People Search supports a `currentCompany` filter, but it only
accepts internal LinkedIn company URNs (numeric IDs), not free-text company
names — those IDs are only resolvable through LinkedIn's own (gated,
partner-only) API. There is no public, ToS-compliant way to pass a company
*name* into that filter from outside LinkedIn.

What we CAN do, and what this module does:
  1. Put the target company name into the `keywords` field as a quoted
     phrase. LinkedIn's relevance ranking weighs quoted keyword phrases
     heavily, so `"Data Scientist" "Acme Corp" Python` reliably surfaces
     people who list Acme Corp, far better than role+skills alone (the old
     behaviour, which had ZERO company signal — that's the bug you saw).
  2. Generate a Google "X-ray search" URL as a second option. Recruiters use
     this constantly because it lets you combine `site:linkedin.com/in`
     with an exact-match company name Google indexes from public profiles —
     it's a legitimate, widely-used sourcing technique and not a ToS issue
     since it's just a Google search.
"""

import urllib.parse


def generate_linkedin_url(jd: dict) -> str:
    """
    Build a LinkedIn People Search URL from a parsed JD dictionary, scoped to
    the target hiring company when one is available.

    Args:
        jd: dict produced by core.parser.parse_jd() — should contain 'role',
            'skills', and ideally 'company' (the company that is HIRING,
            i.e. who you want candidates either currently at, or at minimum
            aware of — NOT your own recruiting org).

    Returns:
        A fully-formed LinkedIn search URL string.
    """
    role    = (jd.get("role") or "").strip()
    company = (jd.get("company") or "").strip()
    skills  = jd.get("skills", []) or []

    parts = []
    if role:
        parts.append(f'"{role}"')
    if company:
        parts.append(f'"{company}"')
    parts.extend(skills[:4])

    query = " ".join(p for p in parts if p)
    encoded_query = urllib.parse.quote(query)

    url = (
        "https://www.linkedin.com/search/results/people/"
        f"?keywords={encoded_query}"
        "&origin=GLOBAL_SEARCH_HEADER"
    )
    return url


def generate_xray_search_url(jd: dict) -> str:
    """
    Build a Google X-ray search URL restricted to linkedin.com/in profiles,
    scoped to the target company. This is the more reliable way to actually
    filter by company, since LinkedIn's own search won't accept a plain
    company name for that purpose from outside their platform.
    """
    role    = (jd.get("role") or "").strip()
    company = (jd.get("company") or "").strip()
    location = (jd.get("location") or "").strip()
    skills  = jd.get("skills", []) or []

    terms = ['site:linkedin.com/in']
    if role:
        terms.append(f'"{role}"')
    if company:
        terms.append(f'"{company}"')
    if location:
        terms.append(f'"{location}"')
    if skills:
        skill_clause = " OR ".join(f'"{s}"' for s in skills[:5])
        terms.append(f'({skill_clause})')

    query = " ".join(terms)
    return "https://www.google.com/search?q=" + urllib.parse.quote(query)


# ── CLI usage ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    with open("parsed_jd.json", "r") as f:
        jd = json.load(f)

    print("\n✅ LinkedIn People Search:\n", generate_linkedin_url(jd))
    print("\n✅ Google X-ray Search:\n", generate_xray_search_url(jd))