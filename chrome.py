"""
chrome.py
─────────
Generates LinkedIn People Search URLs from a parsed JD dict.
Importable as a module (used by app.py) or run standalone for CLI use.
"""

import json
import urllib.parse


def generate_linkedin_url(jd: dict) -> str:
    """
    Build a LinkedIn People Search URL from a parsed JD dictionary.

    Args:
        jd: dict produced by jd_parser.parse_jd() — must contain at least
            'role' and/or 'skills'.

    Returns:
        A fully-formed LinkedIn search URL string.
    """
    role   = jd.get("role", "")
    skills = jd.get("skills", [])

    # Build a concise query: role + up to 4 top skills
    parts = [p for p in [role] + skills[:4] if p]
    query = " ".join(parts)

    encoded_query = urllib.parse.quote(query)

    url = (
        "https://www.linkedin.com/search/results/people/"
        f"?keywords={encoded_query}"
        "&origin=GLOBAL_SEARCH_HEADER"
    )
    return url


# ── CLI usage ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    with open("parsed_jd.json", "r") as f:
        jd = json.load(f)

    url = generate_linkedin_url(jd)
    print("\n✅ Your LinkedIn Search Link:\n")
    print(url)