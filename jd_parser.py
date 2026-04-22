"""
jd_parser.py  —  NexRecruit AI  (Refactored)
═════════════════════════════════════════════
Robust JD extraction pipeline:
  Step 1 → Text pre-processing   (normalize PDF noise, whitespace, encoding garbage)
  Step 2 → Section detection     (split JD into semantic zones)
  Step 3 → Rule-based extraction (regex with ranked patterns)
  Step 4 → Intelligent fallbacks (company NER-lite, role heuristics)
  Step 5 → Validation layer      (reject garbage values, retry with alternates)
  Step 6 → Standardised output   (clean JSON-serialisable dict)

Zero external APIs required. Optional LLM fallback for role + company only.
"""

import re
import json
import zipfile
import xml.etree.ElementTree as ET
import io
from typing import Optional

# ══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE BASE
# ══════════════════════════════════════════════════════════════════════════════

SKILLS_DB = [
    # Programming languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "kotlin", "swift", "php", "ruby", "scala", "r", "matlab", "bash", "shell",
    # Web
    "react", "angular", "vue", "node.js", "nodejs", "django", "flask", "fastapi",
    "spring", "asp.net", "html", "css", "rest", "graphql", "next.js",
    # Data / ML
    "machine learning", "deep learning", "nlp", "computer vision", "tensorflow",
    "pytorch", "keras", "scikit-learn", "pandas", "numpy", "opencv", "spark",
    "hadoop", "tableau", "power bi", "excel", "data analysis", "data science",
    "statistics", "sql", "nosql", "etl",
    # Cloud / DevOps
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "terraform",
    "ansible", "jenkins", "ci/cd", "devops", "git", "github", "gitlab", "linux",
    # Databases
    "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "oracle",
    "sql server", "dynamodb", "cassandra", "firebase",
    # Mobile
    "android", "ios", "flutter", "react native", "xamarin",
    # HR / Business
    "recruitment", "talent acquisition", "onboarding", "payroll", "hris",
    "performance management", "employee relations", "sourcing", "screening",
    "communication", "leadership", "project management", "agile", "scrum",
    "jira", "confluence", "ms office", "microsoft office", "salesforce",
    # Design
    "figma", "adobe xd", "photoshop", "illustrator", "ui/ux",
]

INDIAN_CITIES = [
    "mumbai", "delhi", "bangalore", "bengaluru", "hyderabad", "chennai",
    "kolkata", "pune", "ahmedabad", "jaipur", "surat", "lucknow", "noida",
    "gurgaon", "gurugram", "chandigarh", "indore", "bhopal", "nagpur",
    "kochi", "visakhapatnam", "vadodara", "coimbatore", "patna",
]

GLOBAL_CITIES = [
    "new york", "san francisco", "london", "singapore", "dubai", "toronto",
    "sydney", "berlin", "amsterdam", "paris", "tokyo", "chicago", "seattle",
    "boston", "austin", "remote", "hybrid", "anywhere",
]

ALL_LOCATIONS = INDIAN_CITIES + GLOBAL_CITIES

EMPLOYMENT_TYPES = {
    "full-time": "Full-time",
    "full time": "Full-time",
    "part-time": "Part-time",
    "part time": "Part-time",
    "contract": "Contract",
    "freelance": "Freelance",
    "internship": "Internship",
    "intern": "Internship",
    "temporary": "Temporary",
    "permanent": "Full-time",
}

EDUCATION_KEYWORDS = [
    r"b\.?tech", r"m\.?tech", r"b\.?e\.?", r"m\.?e\.?",
    r"b\.?sc", r"m\.?sc", r"bca", r"mca",
    r"b\.?com", r"m\.?com", r"mba",
    r"bachelor", r"master", r"phd", r"ph\.d",
    r"graduate", r"post.?graduate", r"diploma",
    r"degree in", r"engineering",
]

INDUSTRY_MAP = {
    "software": "Information Technology",
    " it ": "Information Technology",          # FIX: was "it " — matched "it" inside any word.
    "information technology": "Information Technology",
    "technology": "Information Technology",
    "data": "Data & Analytics",
    "machine learning": "AI / Machine Learning",
    "artificial intelligence": "AI / Machine Learning",
    "finance": "Finance / Banking",
    "banking": "Finance / Banking",
    "fintech": "FinTech",
    "healthcare": "Healthcare",
    "pharma": "Pharmaceuticals",
    "ecommerce": "E-Commerce",
    "e-commerce": "E-Commerce",
    "retail": "Retail",
    "logistics": "Logistics / Supply Chain",
    "supply chain": "Logistics / Supply Chain",
    "marketing": "Marketing",
    "sales": "Sales",
    " hr ": "Human Resources",                  # FIX: was "hr" — matched "their", "charter", etc.
    "human resource": "Human Resources",
    "recruitment": "Human Resources",
    "education": "Education / EdTech",
    "edtech": "Education / EdTech",
    "telecom": "Telecommunications",
    "manufacturing": "Manufacturing",
    "consulting": "Consulting",
    "media": "Media / Entertainment",
    "gaming": "Gaming",
    "cybersecurity": "Cybersecurity",
    "security": "Cybersecurity",
    "insurance": "Insurance",
    "real estate": "Real Estate",
    "hospitality": "Hospitality",
    "automotive": "Automotive",
}

# Common corporate suffixes used for company NER heuristic
CORP_SUFFIXES = re.compile(
    r'\b(?:pvt\.?\s*ltd\.?|private\s+limited|limited|llc|inc\.?|corp\.?|'
    r'technologies|solutions|systems|services|consulting|group|ventures|'
    r'software|labs|studio|studios|digital|global|india|worldwide)\b',
    re.IGNORECASE
)

# Phrases that indicate a SENTENCE, not a job title — used in validation
SENTENCE_INDICATORS = re.compile(
    r'\b(?:we are|we\'re|our|looking for|seeking|responsible|must have|'
    r'will be|should have|candidate|applicant|you will|you\'ll|'
    r'the role|the position|this role|this position|manage|lead|develop|'
    r'design|build|work with|collaborate|ensure|support|provide|maintain)\b',
    re.IGNORECASE
)

# Job title word patterns — helps disambiguate titles vs noise
JOB_TITLE_WORDS = re.compile(
    r'\b(?:engineer|developer|analyst|manager|lead|director|architect|'
    r'designer|scientist|consultant|specialist|officer|associate|executive|'
    r'head|vp|president|intern|trainee|coordinator|recruiter|hr|'
    r'backend|frontend|fullstack|full.?stack|devops|data|senior|junior|'
    r'principal|staff|product|program|project|qa|sre|mlops|cloud)\b',
    re.IGNORECASE
)

# Section heading patterns — split the JD into semantic zones
SECTION_PATTERNS = {
    "title":            re.compile(r'^\s*(?:job\s+title|position\s+title|role\s+title|designation)\s*[:\-]?\s*$', re.IGNORECASE | re.MULTILINE),
    "about_company":    re.compile(r'^\s*(?:about\s+(?:us|the\s+company|our\s+company|[A-Z][A-Za-z0-9\s&]{1,40})|company\s+overview|who\s+we\s+are)\s*[:\-]?\s*$', re.IGNORECASE | re.MULTILINE),
    "responsibilities": re.compile(r'^\s*(?:responsibilities|key\s+responsibilities|what\s+you(?:\'ll|\s+will)\s+do|roles?\s+&?\s+responsibilities|duties|job\s+description)\s*[:\-]?\s*$', re.IGNORECASE | re.MULTILINE),
    "requirements":     re.compile(r'^\s*(?:requirements?|qualifications?|what\s+we(?:\'re|\s+are)\s+looking\s+for|must\s+have|skills?\s+required|experience)\s*[:\-]?\s*$', re.IGNORECASE | re.MULTILINE),
    "skills":           re.compile(r'^\s*(?:skills?|technical\s+skills?|key\s+skills?|required\s+skills?)\s*[:\-]?\s*$', re.IGNORECASE | re.MULTILINE),
    "benefits":         re.compile(r'^\s*(?:benefits?|perks?|what\s+we\s+offer|compensation|why\s+(?:join\s+us|work\s+with\s+us))\s*[:\-]?\s*$', re.IGNORECASE | re.MULTILINE),
}


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — TEXT PRE-PROCESSING
# ══════════════════════════════════════════════════════════════════════════════

def preprocess_text(raw: str) -> str:
    """
    Clean raw extracted text before any parsing.

    WHY each fix:
    • PDF extraction often produces hyphenated line-breaks ("develop-\nment") —
      we rejoin them.
    • Bullet Unicode variants (•, ◦, ▪, ‣, →, ►) become plain hyphens so regex
      patterns don't need to enumerate them.
    • Multiple spaces/tabs collapse to single space (PDF column artefacts).
    • 3+ consecutive newlines collapse to 2 (preserves paragraph breaks for
      section detection without drowning in blank lines).
    • Strip zero-width / non-printable chars that sneak in from copy-paste.
    """
    # Rejoin PDF soft-hyphen line breaks
    text = re.sub(r'-\n\s*', '', raw)

    # Normalise Unicode bullets / arrows to ASCII hyphen
    text = re.sub(r'[•◦▪▸►‣→–]', '-', text)

    # Collapse whitespace within lines (preserve newlines)
    text = re.sub(r'[ \t]+', ' ', text)

    # Collapse 3+ newlines → 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip zero-width / control chars except newline/tab
    text = re.sub(r'[^\S\n\t]+', ' ', text)       # duplicate of above, safe
    text = re.sub(r'[\x00-\x08\x0b-\x1f\x7f-\x9f]', '', text)

    # Strip trailing spaces per line
    text = '\n'.join(line.rstrip() for line in text.splitlines())

    return text.strip()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — SECTION DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def detect_sections(text: str) -> dict:
    """
    Split the JD text into named zones.

    WHY: When we run extract_role() on the entire document, the regex can match
    a bullet like "We are looking for a Senior Engineer who will design…" —
    which is a sentence, not a title. Splitting into sections lets us restrict
    role extraction to only the first ~5 lines (before any section heading).

    Returns a dict: { zone_name: text_fragment, ... }
    """
    lines = text.splitlines()
    sections: dict[str, list[str]] = {"header": []}
    current = "header"

    for line in lines:
        matched_section = None
        for section_name, pattern in SECTION_PATTERNS.items():
            if pattern.match(line):
                matched_section = section_name
                break

        if matched_section:
            current = matched_section
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)

    return {k: '\n'.join(v).strip() for k, v in sections.items()}


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — FIELD EXTRACTORS (rule-based)
# ══════════════════════════════════════════════════════════════════════════════

def _clean_field(value: Optional[str], max_len: int = 80) -> Optional[str]:
    """Strip common trailing punctuation and whitespace. Return None if empty."""
    if not value:
        return None
    value = value.strip().strip('.,;:-–—"\'')
    return value if value and len(value) <= max_len else None


def extract_role(text: str, sections: dict) -> Optional[str]:
    """
    Extract job title.

    BEFORE (bugs):
    1. Pattern r"^([A-Z][A-Za-z\\s\\-\\/]{3,60})\\n" could match the very first
       sentence of an "About" paragraph if it started with a capital letter and
       was < 80 chars — producing garbage like "We are a fast-growing startup".
    2. The fallback "first non-empty line < 80 chars" is extremely naive; on PDFs
       the first line is often the company letterhead or a section label.
    3. No validation that the result looks like a job title.

    AFTER (fixes):
    1. First try explicit label patterns on the full text (highest confidence).
    2. Then look only at the 'header' section (first few lines before any heading).
    3. Apply a validation heuristic: the string must NOT look like a sentence AND
       must contain at least one recognisable job-title word (OR be very short ≤ 6
       words, which is almost always a title).
    4. Walk each candidate through validation before accepting it.
    """
    candidates: list[tuple[int, str]] = []   # (priority, value)

    # Priority 1 — explicit label in the text
    explicit_patterns = [
        r'(?:job\s+title|position\s+title|role\s+title|designation)\s*[:\-]\s*([^\n]{3,70})',
        r'(?:position|role)\s*[:\-]\s*([^\n]{3,70})',
        r'(?:hiring\s+for|we\s+are\s+hiring\s+(?:a|an)?)\s+([^\n,\.]{3,60})',
        r'(?:opening|vacancy|opportunity)\s*(?:for|:)\s*([^\n]{3,60})',
    ]
    for pat in explicit_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            candidates.append((1, m.group(1).strip()))

    # Priority 2 — look in the header section only (before first section heading)
    header_text = sections.get("header", "")
    header_lines = [
        l.strip() for l in header_text.splitlines()
        if l.strip() and len(l.strip()) >= 3
        and not re.match(r'^(date|ref|ref\s*no|job\s*id|posted|apply)\s*[:\-]', l.strip(), re.IGNORECASE)
        and not re.match(r'^about\b', l.strip(), re.IGNORECASE)
    ][:6]

    # Heuristic: if first two short lines exist and second has a job-title word
    # but first does not → the first is likely the company name, second is the title.
    # This handles "Acme Corp\nSenior Engineer" patterns.
    if len(header_lines) >= 2:
        first, second = header_lines[0], header_lines[1]
        first_has_title  = bool(JOB_TITLE_WORDS.search(first))
        second_has_title = bool(JOB_TITLE_WORDS.search(second))
        first_has_corp   = bool(CORP_SUFFIXES.search(first))

        if (second_has_title and not first_has_title) or first_has_corp:
            # First line is company name, second is role
            candidates.append((2, second))
            # Also add company candidate from first line if not already found
            if _clean_field(first) and not first_has_title:
                from_first = _clean_field(first, max_len=60)
                if from_first:
                    candidates.insert(0, (2, f"__COMPANY__:{from_first}"))
        else:
            for line in header_lines:
                if CORP_SUFFIXES.search(line) and not JOB_TITLE_WORDS.search(line):
                    continue
                candidates.append((2, line))

    # Priority 3 — fallback: first non-empty, non-heading, non-meta line in full text
    skip_prefixes = re.compile(
        r'^(date|ref|ref\s*no|job\s*id|posted|apply|location|city|office|'
        r'employment|full.?time|part.?time|contract|salary|compensation|'
        r'about\b)',
        re.IGNORECASE
    )
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        is_heading = any(p.match(line) for p in SECTION_PATTERNS.values())
        if is_heading:
            continue
        if skip_prefixes.match(line):
            continue
        candidates.append((3, line))
        break

    # Now validate each candidate in priority order
    for priority, candidate in sorted(candidates, key=lambda x: x[0]):
        if candidate.startswith("__COMPANY__:"):
            continue   # skip company hints here
        validated = _validate_role(candidate)
        if validated:
            return validated

    return None


def _extract_header_company_hint(sections: dict) -> Optional[str]:
    """
    When a JD starts with 'CompanyName\\nJobTitle' (no explicit labels), the
    first header line is often the company. Return it so extract_company() can
    use it as an additional candidate.
    """
    header_text = sections.get("header", "")
    header_lines = [
        l.strip() for l in header_text.splitlines()
        if l.strip() and len(l.strip()) >= 2
    ][:4]

    if len(header_lines) >= 2:
        first, second = header_lines[0], header_lines[1]
        first_has_title  = bool(JOB_TITLE_WORDS.search(first))
        second_has_title = bool(JOB_TITLE_WORDS.search(second))
        first_has_corp   = bool(CORP_SUFFIXES.search(first))

        if (second_has_title and not first_has_title) or first_has_corp:
            return _clean_field(first, max_len=60)

    return None


def _validate_role(title: str) -> Optional[str]:
    """
    Return the title if it looks like a job title, None otherwise.

    Rules:
    - Must be ≤ 80 characters (already filtered upstream, but double-check)
    - Must NOT look like a sentence (contains "we are", "you will", "must have", etc.)
    - Either: contains a known job-title keyword  OR  is ≤ 6 words
    - Must not be all-lowercase prose (probably a description line)
    """
    title = title.strip().strip('.,;:-–—"\'')

    if not title or len(title) > 80:
        return None

    # Reject obvious meta/label lines ("Location: ...", "Salary: ...", etc.)
    if re.match(r'^(location|city|salary|compensation|date|ref|apply|contact|email|phone)\s*[:\-]', title, re.IGNORECASE):
        return None

    # Reject lines starting with a digit (experience/bullet lines like "4-6 years...")
    if re.match(r'^\d', title):
        return None

    # Reject if it looks like a sentence
    if SENTENCE_INDICATORS.search(title):
        return None

    # Reject if it has too many words and no job-title keyword
    word_count = len(title.split())
    has_title_word = bool(JOB_TITLE_WORDS.search(title))

    if word_count > 8 and not has_title_word:
        return None

    # Reject if it's a pure uppercase acronym blob or a single generic word
    if title.upper() == title and len(title) > 4:
        # Could be section header like "REQUIREMENTS" — reject
        if not re.search(r'\s', title):   # single all-caps word
            return None

    return title if title else None


def extract_company(text: str, sections: dict) -> Optional[str]:
    """
    Detect company name.

    BEFORE (bugs):
    1. Pattern r'(?:at|join)\\s+([A-Z][A-Za-z0-9\\s&]{2,40})(?:\\s+is|\\s+we|\\s+you|,)'
       fails on >80% of real JDs because most don't say "join Acme Corp, we".
    2. Pattern r'company\\s*[:\\-]\\s*(.+)' grabs the entire first sentence of the
       "About the Company" section — producing a sentence, not a name.
    3. No corp-suffix heuristic, no "About" section parsing.

    AFTER (fixes):
    1. Explicit label pattern (highest confidence): "Company: Acme"
    2. "About" section: grab only the FIRST non-empty short line (company
       descriptions start with the company name, e.g. "TechCorp is a…")
    3. Corporate-suffix NER: scan the header/about section for short spans that
       contain a known corp suffix (Pvt Ltd, Inc, Technologies, etc.).
    4. "Join/at" pattern (kept but tightened): require capital start + corp suffix.
    5. Header positional heuristic: "CompanyName\\nJobTitle" two-liner.
    6. Footer heuristic: many JDs end with "Contact: hr@acme.com" — extract the
       domain name as a last resort.
    """
    candidates: list[tuple[int, str]] = []

    # Priority 0 — header positional heuristic ("CompanyName\nJobTitle" pattern)
    hint = _extract_header_company_hint(sections)
    if hint:
        candidates.append((0, hint))

    # Priority 1 — explicit label
    m = re.search(
        r'(?:company|organisation|organization|employer|client)\s*[:\-]\s*([^\n]{2,60})',
        text, re.IGNORECASE
    )
    if m:
        val = _clean_field(m.group(1))
        if val:
            candidates.append((1, val))

    # Priority 2 — corporate suffix scan in header + about sections
    search_zone = (
        sections.get("header", "") + "\n" + sections.get("about_company", "")
    )
    for line in search_zone.splitlines():
        line = line.strip()
        if not line or len(line) > 80:
            continue
        if CORP_SUFFIXES.search(line):
            # Grab just the name portion (up to 60 chars, stop at sentence verb)
            name_match = re.match(r'^([A-Z][A-Za-z0-9\s&,\.]{2,55}?)(?:\s+is\b|\s+was\b|\s+has\b|,|\.|$)', line)
            if name_match:
                val = _clean_field(name_match.group(1))
                if val and len(val.split()) <= 8:
                    candidates.append((2, val))

    # Priority 2b — first line of about_company section even without explicit corp suffix
    about = sections.get("about_company", "")
    for line in about.splitlines():
        line = line.strip()
        if line and 2 <= len(line) <= 70 and re.match(r'^[A-Z]', line):
            # Could be "Infosys Limited is a global leader..." — grab name before verb
            shortened = re.split(r'\s+(?:is\b|was\b|has\b|provides\b|offers\b|delivers\b|are\b)', line)[0].strip()
            val = _clean_field(shortened, max_len=60)
            if val and len(val.split()) <= 6 and not SENTENCE_INDICATORS.search(val):
                candidates.append((2, val))
            break

    # Priority 4 — "join/at" pattern (tightened: must have corp suffix OR all title-cased)
    m2 = re.search(
        r'(?:join|at)\s+([A-Z][A-Za-z0-9\s&\.]{2,40}?)(?=\s+(?:is|was|and|as|today|now|,|\.))',
        text
    )
    if m2:
        val = _clean_field(m2.group(1))
        if val and (CORP_SUFFIXES.search(val) or _is_title_cased(val)):
            candidates.append((4, val))

    # Priority 5 — email domain fallback (last resort)
    em = re.search(r'[\w.\-]+@([\w\-]+)\.(?:com|in|io|co)', text, re.IGNORECASE)
    if em:
        domain = em.group(1)
        if domain.lower() not in ("gmail", "yahoo", "outlook", "hotmail", "mail"):
            candidates.append((5, domain.capitalize()))

    for _, candidate in sorted(candidates, key=lambda x: x[0]):
        if candidate:
            return candidate

    return None


def _is_title_cased(s: str) -> bool:
    """Check if every significant word starts with a capital (company name heuristic)."""
    words = s.split()
    if len(words) < 2:
        return bool(re.match(r'^[A-Z]', s))
    stopwords = {"a", "an", "the", "of", "and", "in", "for", "to", "at"}
    significant = [w for w in words if w.lower() not in stopwords]
    return all(w[0].isupper() for w in significant if w)


def extract_experience(text: str) -> tuple[Optional[int], Optional[int]]:
    """
    Extract min/max years of experience.

    BEFORE (bugs):
    1. Pattern r'(\\d+)\\+?\\s*(?:years?|yrs?)\\s*(?:of\\s+)?(?:experience|exp)'
       captured only one group — the function returned (5, 5) when the JD said
       "5+ years", hiding the ambiguity.
    2. No handling for "10+ years" → exp_min=10, exp_max=None (open-ended).
    3. No deduplication when multiple experience mentions exist (e.g. one in
       requirements, one in a bullet) — first match won regardless.

    AFTER (fixes):
    1. Separate pattern for range (3–5 years) vs minimum (5+ years) vs exact.
    2. "+" suffix sets exp_max to None to signal open-ended.
    3. Walk ALL matches, pick the most specific (range > minimum > exact).
    """
    # Pattern A: range — "3 to 5 years", "3-5 years", "3–5 yrs"
    range_pat = re.compile(
        r'(\d+)\s*[-–to]+\s*(\d+)\s*(?:\+)?\s*(?:years?|yrs?)'
        r'(?:\s*of\s*(?:relevant\s+)?(?:experience|exp))?',
        re.IGNORECASE
    )
    # Pattern B: minimum — "5+ years", "minimum 3 years", "at least 4 years"
    min_pat = re.compile(
        r'(?:minimum\s+(?:of\s+)?|at\s+least\s+)?(\d+)\s*\+\s*(?:years?|yrs?)'
        r'(?:\s*of\s*(?:relevant\s+)?(?:experience|exp))?',
        re.IGNORECASE
    )
    # Pattern C: exact with context word — "5 years of experience"
    exact_pat = re.compile(
        r'(\d+)\s*(?:years?|yrs?)\s+of\s+(?:relevant\s+)?(?:experience|exp)',
        re.IGNORECASE
    )
    # Pattern D: labelled — "Experience: 3-5 years"
    labelled_pat = re.compile(
        r'experience\s*[:\-]\s*(\d+)\s*[-–to]*\s*(\d+)?\s*\+?\s*(?:years?|yrs?)',
        re.IGNORECASE
    )

    # Collect all candidates with confidence weight
    best = None  # (exp_min, exp_max, weight)

    for m in labelled_pat.finditer(text):
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        if not best or 4 > (best[2] if best else 99):
            best = (min(lo, hi), max(lo, hi), 4)

    for m in range_pat.finditer(text):
        lo, hi = int(m.group(1)), int(m.group(2))
        if not best or 3 > (best[2] if best else 99):
            best = (min(lo, hi), max(lo, hi), 3)

    for m in min_pat.finditer(text):
        lo = int(m.group(1))
        if not best or 2 > (best[2] if best else 99):
            best = (lo, None, 2)   # open-ended

    for m in exact_pat.finditer(text):
        lo = int(m.group(1))
        if not best or 1 > (best[2] if best else 99):
            best = (lo, lo, 1)

    if best:
        return best[0], best[1]
    return None, None


def extract_location(text: str) -> Optional[str]:
    """
    Find location.

    FIX: Added label-based extraction FIRST (most reliable), then city scan.
    Previously label was checked AFTER city scan so "Location: Anywhere" could
    be missed if a city name appeared earlier in the text.
    Also: truncate after the first comma/period/newline so we don't return
    "New York. Full-time" as a location value.
    """
    # Priority 1 — explicit label
    m = re.search(
        r'(?:location|place|city|office|work\s+location)\s*[:\-]\s*([^\n]{2,60})',
        text, re.IGNORECASE
    )
    if m:
        val = m.group(1).strip()
        # Truncate at sentence-ending punctuation that isn't part of location
        # Keep slashes (Bangalore / Remote) but stop at ". " followed by non-city word
        val = re.split(r'\.\s+(?=[A-Z])', val)[0]   # "New York. Full-time" → "New York"
        val = val.strip().rstrip('.,;')
        if val:
            return val

    # Priority 2 — known city scan (whole text)
    text_lower = text.lower()
    for loc in ALL_LOCATIONS:
        if re.search(r'\b' + re.escape(loc) + r'\b', text_lower):
            return loc.title()

    return None


def extract_employment_type(text: str) -> str:
    """
    Detect employment type.

    FIX: Use word-boundary matching to avoid substring hits. E.g. "intern" was
    matching "international" in company names, incorrectly returning "Internship".
    """
    text_lower = text.lower()
    for keyword, label in EMPLOYMENT_TYPES.items():
        # Use word boundary to avoid false positives
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text_lower):
            return label
    return "Full-time"


def extract_education(text: str, sections: dict) -> Optional[str]:
    """
    Detect required education.

    BEFORE (bug): Strategy 2 had a loop `for pat in EDUCATION_KEYWORDS` but the
    body never used `pat` — it always searched the same compiled regex. So if the
    first keyword ("b.tech") didn't match, it would re-search with the same
    (wrong) pattern for every subsequent keyword. The loop was effectively useless.

    AFTER: Single search with a properly compiled union pattern, then section-aware
    extraction.
    """
    # Prefer education section if detected
    edu_section = sections.get("requirements", "") or text

    # Strategy 1 — dedicated education section
    section_match = re.search(
        r'(?:^|\n)\s*education\s*[:\-]?\s*\n((?:.+\n?){1,5})',
        text, re.IGNORECASE
    )
    if section_match:
        for line in section_match.group(1).splitlines():
            line = re.sub(r'^[\*\-\•\>\s]+', '', line).strip()
            if line and len(line) > 8:
                return line.rstrip(",.")

    # Strategy 2 — degree keyword search (fixed: build union pattern once)
    degree_union = (
        r'(?:bachelor\'?s?|master\'?s?|phd|ph\.d|b\.?tech|m\.?tech|mba|bca|mca|'
        r'b\.?sc|m\.?sc|b\.?e|m\.?e|graduate|post.?graduate|degree)'
    )
    # Require word boundary BEFORE the keyword to avoid matching "requirement" → "ment"
    m = re.search(r'(?<!\w)' + degree_union + r'[^\n]{0,80}', edu_section, re.IGNORECASE)
    if m:
        return m.group(0).strip().rstrip(",.")

    return None


def extract_skills(text: str, sections: dict) -> list[str]:
    """
    Extract skills.

    FIX: Prefer the requirements/skills section text for skill scanning. Scanning
    the full document can pick up skills mentioned in company marketing copy as
    background context, inflating the list. Also fixed "r" matching inside words
    by requiring it to be followed by a non-word char.
    """
    # Use requirements + skills sections if available, else full text
    scan_text = (
        sections.get("requirements", "") + "\n" +
        sections.get("skills", "") + "\n" +
        sections.get("responsibilities", "")
    ).strip() or text

    scan_lower = scan_text.lower()
    found = []

    for skill in SKILLS_DB:
        # Special case: single-letter "r" language needs stricter boundary
        if skill == "r":
            pattern = r'(?<!\w)r(?!\w)'
        else:
            pattern = r'\b' + re.escape(skill) + r'\b'

        if re.search(pattern, scan_lower):
            found.append(skill.title() if len(skill) > 3 else skill.upper())

    return list(dict.fromkeys(found))   # deduplicate, preserve order


def extract_industry(text: str, sections: dict) -> Optional[str]:
    """
    Classify industry.

    BEFORE (bugs):
    1. "it " (with trailing space) would match "it" in the middle of sentences
       like "submit it here" → "Information Technology". Changed to " it " (padded
       both sides), and also added "information technology" as an explicit key.
    2. "hr" matched "their", "charter", "threshold" etc.
    3. No priority ordering — first alphabetical match won.
    4. Industry was inferred from the full document, including candidate-facing
       sections that describe tech stacks rather than the actual industry.

    AFTER: Use only the about_company + header section for industry inference.
    Also use word-boundary matching for short ambiguous keywords.
    """
    # Prefer company description section for industry signals
    scan_text = (
        sections.get("about_company", "") + "\n" +
        sections.get("header", "")
    ).strip() or text

    scan_lower = " " + scan_text.lower() + " "   # pad for " it " matching

    scores: dict[str, int] = {}
    for keyword, industry in INDUSTRY_MAP.items():
        # Short keywords (≤ 3 chars) need padding; long ones use substring match
        if len(keyword.strip()) <= 3:
            pattern = re.escape(keyword)   # keyword already has spaces
        else:
            pattern = r'\b' + re.escape(keyword.strip()) + r'\b'

        if re.search(pattern, scan_lower, re.IGNORECASE):
            # Accumulate score; longer keyword = more specific = higher priority
            scores[industry] = scores.get(industry, 0) + len(keyword.strip())

    if scores:
        # Return the industry with the highest accumulated specificity score
        return max(scores, key=lambda k: scores[k])

    return None


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — VALIDATION LAYER
# ══════════════════════════════════════════════════════════════════════════════

def validate_and_fix(fields: dict, text: str, sections: dict) -> dict:
    """
    Post-extraction validation with targeted retries.

    Checks each field for quality and attempts fallback strategies when
    the primary extraction failed or produced garbage.
    """
    # ── Role validation ─────────────────────────────────────────────────────
    role = fields.get("role")
    if role:
        # If role looks like a sentence, discard and retry
        if _validate_role(role) is None:
            fields["role"] = None
            role = None

    # Role retry — search specifically for "We are hiring a <Title>" patterns
    if not role:
        patterns = [
            r'(?:hiring|looking)\s+(?:for\s+)?(?:a|an)\s+([A-Z][A-Za-z\s\-\/]{3,50}?)(?:\s+to\b|\s+who\b|\s+with\b|\.|\n)',
            r'(?:vacancy|opening)\s+(?:for\s+)?(?:a|an)?\s*([A-Z][A-Za-z\s\-\/]{3,50}?)(?:\s+to\b|\s+who\b|\.|\n)',
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                candidate = _validate_role(m.group(1).strip())
                if candidate:
                    fields["role"] = candidate
                    break

    # ── Company validation ───────────────────────────────────────────────────
    company = fields.get("company")
    if company:
        # Reject if company looks like a sentence or is suspiciously long
        if len(company.split()) > 8 or SENTENCE_INDICATORS.search(company):
            fields["company"] = None

    # ── Experience validation ────────────────────────────────────────────────
    exp_min = fields.get("experience_min")
    exp_max = fields.get("experience_max")

    # Sanity check: exp values should be reasonable (0–40 years)
    if exp_min is not None and (exp_min < 0 or exp_min > 40):
        fields["experience_min"] = None
    if exp_max is not None and (exp_max < 0 or exp_max > 40):
        fields["experience_max"] = None
    if exp_min is not None and exp_max is not None and exp_min > exp_max:
        fields["experience_min"], fields["experience_max"] = exp_max, exp_min

    # Retry experience if missing — try looser patterns
    if fields.get("experience_min") is None:
        loose = re.search(r'(\d+)\s*(?:years?|yrs?)', text, re.IGNORECASE)
        if loose:
            val = int(loose.group(1))
            if 0 < val <= 40:
                fields["experience_min"] = val
                if fields.get("experience_max") is None:
                    fields["experience_max"] = val

    # ── Industry validation ──────────────────────────────────────────────────
    # If industry came from full-text scan and role gives a clearer signal, trust role
    if not fields.get("industry") and fields.get("role"):
        role_lower = (fields["role"] or "").lower()
        for keyword, industry in INDUSTRY_MAP.items():
            if keyword.strip() in role_lower:
                fields["industry"] = industry
                break

    # ── Skills dedup & cap ───────────────────────────────────────────────────
    if fields.get("skills"):
        fields["skills"] = list(dict.fromkeys(fields["skills"]))[:30]

    return fields


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6 — SUMMARY BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def build_summary(role, company, exp_min, exp_max, location) -> str:
    s1 = "This role"
    if role:
        s1 = f"This is a {role} position"
    if company:
        s1 += f" at {company}"
    if location:
        s1 += f", based in {location}"
    s1 += "."

    if exp_min is not None:
        if exp_max is None or exp_min == exp_max:
            s2 = f"The candidate needs {exp_min}+ years of experience."
        else:
            s2 = f"The candidate needs {exp_min}–{exp_max} years of experience."
    else:
        s2 = "Please review the full description for experience requirements."

    return f"{s1} {s2}"


# ══════════════════════════════════════════════════════════════════════════════
# FILE TEXT EXTRACTORS  (unchanged API, minor robustness improvements)
# ══════════════════════════════════════════════════════════════════════════════

_WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_text_from_docx(file_path: str) -> str:
    with zipfile.ZipFile(file_path, "r") as z:
        with z.open("word/document.xml") as f:
            tree = ET.parse(f)
    return _docx_tree_to_text(tree.getroot())


def extract_text_from_docx_bytes(file_bytes: bytes) -> str:
    buf = io.BytesIO(file_bytes)
    with zipfile.ZipFile(buf, "r") as z:
        with z.open("word/document.xml") as f:
            tree = ET.parse(f)
    return _docx_tree_to_text(tree.getroot())


def _docx_tree_to_text(root) -> str:
    """
    FIX: Preserve paragraph breaks properly. Old code joined paragraphs with
    '\n' but lost the blank-line separation that section detection relies on.
    Now we emit an extra blank line after heading-style paragraphs.
    """
    paragraphs = []
    for para in root.iter(f"{_WORD_NS}p"):
        texts = [node.text for node in para.iter(f"{_WORD_NS}t") if node.text]
        line = "".join(texts).strip()

        # Check if this paragraph has bold/heading style (common in DOCX JDs)
        is_heading = False
        for rpr in para.iter(f"{_WORD_NS}rPr"):
            bold = rpr.find(f"{_WORD_NS}b")
            if bold is not None:
                is_heading = True
                break
        ppr = para.find(f"{_WORD_NS}pPr")
        if ppr is not None:
            pstyle = ppr.find(f"{_WORD_NS}pStyle")
            if pstyle is not None:
                style_val = pstyle.get(f"{_WORD_NS}val", "")
                if "heading" in style_val.lower() or "title" in style_val.lower():
                    is_heading = True

        if line:
            paragraphs.append(line)
            if is_heading:
                paragraphs.append("")   # blank line after headings aids section detection

    return "\n".join(paragraphs)


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    """
    FIX: pdfminer.six gives significantly better text extraction than pypdf for
    complex PDFs (multi-column layouts, scanned-style PDFs). We try pdfminer
    first, fall back to pypdf.
    """
    # Try pdfminer first (best quality)
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract
        return pdfminer_extract(io.BytesIO(file_bytes))
    except ImportError:
        pass

    # Fall back to pypdf / PyPDF2
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    except ImportError:
        try:
            import PyPDF2 as pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        except ImportError:
            raise ImportError(
                "PDF support requires pdfminer.six or pypdf. "
                "Install with:  pip install pdfminer.six"
            )

    pages = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            pages.append(t.strip())
    return "\n".join(pages)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def parse_jd(jd_text: str) -> dict:
    """
    Full 6-step JD extraction pipeline.

    Drop-in replacement for the old parse_jd() — same return schema.
    """
    # Step 1 — Pre-process
    text = preprocess_text(jd_text)

    # Step 2 — Detect sections
    sections = detect_sections(text)

    # Step 3+4 — Extract fields
    role         = extract_role(text, sections)
    company      = extract_company(text, sections)
    skills       = extract_skills(text, sections)
    location     = extract_location(text)
    exp_min, exp_max = extract_experience(text)
    emp_type     = extract_employment_type(text)
    education    = extract_education(text, sections)
    industry     = extract_industry(text, sections)

    fields = {
        "role":            role,
        "company":         company,
        "skills":          skills,
        "location":        location,
        "experience_min":  exp_min,
        "experience_max":  exp_max,
        "employment_type": emp_type,
        "education":       education,
        "industry":        industry,
    }

    # Step 5 — Validate & fix
    fields = validate_and_fix(fields, text, sections)

    # Step 6 — Build summary + return
    fields["summary"] = build_summary(
        fields["role"], fields["company"],
        fields["experience_min"], fields["experience_max"],
        fields["location"]
    )

    return fields


def parse_jd_from_upload(uploaded_file) -> tuple[dict, str]:
    """
    Unified Streamlit entry-point. Identical public API to the old version.
    Returns (parsed_dict, raw_text).
    """
    name = uploaded_file.name.lower()
    raw_bytes = uploaded_file.read()

    if name.endswith(".pdf"):
        text = extract_text_from_pdf_bytes(raw_bytes)
    elif name.endswith(".docx"):
        text = extract_text_from_docx_bytes(raw_bytes)
    elif name.endswith(".txt"):
        text = raw_bytes.decode("utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file type: {uploaded_file.name}")

    return parse_jd(text), text


# ══════════════════════════════════════════════════════════════════════════════
# OPTIONAL: LLM FALLBACK (role + company only)
# Call only when rule-based extraction returned None for both.
# Requires ANTHROPIC_API_KEY in environment.
# ══════════════════════════════════════════════════════════════════════════════

def llm_fallback_role_company(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Use an LLM to extract role and company as a last resort.
    Returns (role, company). Both may still be None on failure.
    """
    try:
        import anthropic
        client = anthropic.Anthropic()

        snippet = text[:3000]   # first 3000 chars is usually enough
        prompt = (
            "Extract ONLY the job title and company name from the following job description. "
            "Reply in JSON with exactly two keys: 'role' and 'company'. "
            "If either cannot be determined, set it to null.\n\n"
            f"JD:\n{snippet}"
        )
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",   # cheapest, fast enough for extraction
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()
        # Strip markdown fences if present
        raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)
        return data.get("role"), data.get("company")
    except Exception:
        return None, None


def parse_jd_with_llm_fallback(jd_text: str) -> dict:
    """
    Same as parse_jd() but calls llm_fallback_role_company() when
    rule-based extraction fails to find role or company.
    """
    result = parse_jd(jd_text)

    if not result.get("role") or not result.get("company"):
        llm_role, llm_company = llm_fallback_role_company(jd_text)
        if not result.get("role") and llm_role:
            result["role"] = llm_role
        if not result.get("company") and llm_company:
            result["company"] = llm_company
        # Rebuild summary with updated fields
        result["summary"] = build_summary(
            result["role"], result["company"],
            result["experience_min"], result["experience_max"],
            result["location"]
        )

    return result


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    file_path = sys.argv[1] if len(sys.argv) > 1 else "JD.docx"
    print(f"📄 Reading: {file_path}")
    if file_path.endswith(".docx"):
        raw = extract_text_from_docx(file_path)
    elif file_path.endswith(".txt"):
        with open(file_path, encoding="utf-8") as fh:
            raw = fh.read()
    else:
        with open(file_path, "rb") as fh:
            raw = extract_text_from_pdf_bytes(fh.read())

    print(f"✅ Extracted {len(raw)} characters\n")
    result = parse_jd(raw)
    print("=" * 50)
    print("         PARSED JD RESULT")
    print("=" * 50)
    print(json.dumps(result, indent=2))
    with open("parsed_jd.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\n💾 Saved to parsed_jd.json")