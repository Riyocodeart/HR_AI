"""
filter.py
─────────
Handles everything after the JD is parsed:
  1. load_candidates()     — reads a CSV and normalises column names
  2. score_candidates()    — filters & scores each candidate against the JD
  3. export_excel()        — produces a formatted, colour-coded .xlsx report
  4. export_csv()          — returns scored results as CSV bytes

Scoring formula
───────────────
  total_score (0–100) = skill_score (0–40)
                      + role_score  (0–30)
                      + exp_score   (0–30)

Skill score  : (# required skills found in candidate profile) / (# required) × 40
Role score   : keyword overlap between JD title and candidate title / JD words × 30
Exp score    : 30 if within [exp_min, exp_max]; reduced linearly for over/under-qualified
"""

import io
import re
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from services.key_rotation import load_gemini_api_keys

SKILL_ALIASES = {

    # Programming
    "python": ["python"],

    "r": [
        "r programming",
        "r language"
    ],

    # SQL & Databases
    "sql": [
        "sql",
        "mysql",
        "postgresql",
        "sqlite",
        "sql server"
    ],

    "mongodb": [
        "mongodb",
        "mongo"
    ],

    # Data Science
    "data science": [
        "data science"
    ],

    "statistics": [
        "statistics",
        "statistical analysis"
    ],

    "eda": [
        "eda",
        "exploratory data analysis"
    ],

    "feature engineering": [
        "feature engineering",
        "feature selection"
    ],

    # Machine Learning
    "machine learning": [
        "ml",
        "machine learning",
        "machine learning basics"
    ],

    "deep learning": [
        "deep learning",
        "neural networks"
    ],

    "nlp": [
        "nlp",
        "natural language processing"
    ],

    "computer vision": [
        "computer vision",
        "cv"
    ],

    "recommendation systems": [
        "recommendation systems",
        "recommender systems"
    ],

    # ML Libraries
    "pandas": [
        "pandas"
    ],

    "numpy": [
        "numpy"
    ],

    "matplotlib": [
        "matplotlib"
    ],

    "scikit-learn": [
        "scikit-learn",
        "sklearn"
    ],

    "tensorflow": [
        "tensorflow"
    ],

    "keras": [
        "keras"
    ],

    "pytorch": [
        "pytorch",
        "torch"
    ],

    "xgboost": [
        "xgboost"
    ],

    "lightgbm": [
        "lightgbm",
        "lgbm"
    ],

    # Data Engineering
    "spark": [
        "spark",
        "apache spark",
        "pyspark"
    ],

    "hadoop": [
        "hadoop",
        "apache hadoop"
    ],

    "kafka": [
        "kafka",
        "apache kafka"
    ],

    "airflow": [
        "airflow",
        "apache airflow"
    ],

    "etl": [
        "etl",
        "data pipeline",
        "data pipelines"
    ],

    "data engineering": [
        "data engineering",
        "data engineer"
    ],

    "data warehousing": [
        "data warehousing",
        "data warehouse"
    ],

    "databricks": [
        "databricks"
    ],

    "snowflake": [
        "snowflake"
    ],

    "big data": [
        "big data"
    ],

    # Cloud
    "aws": [
        "aws",
        "amazon web services"
    ],

    "cloud": [
        "cloud",
        "cloud computing",
        "cloud architecture"
    ],

    # BI Tools
    "power bi": [
        "power bi",
        "powerbi"
    ],

    "tableau": [
        "tableau"
    ],

    "excel": [
        "excel",
        "microsoft excel"
    ],

    # AI / GenAI
    "transformers": [
        "transformers",
        "huggingface",
        "hugging face"
    ],

    "llm": [
        "llm",
        "large language models"
    ],

    "genai": [
        "genai",
        "generative ai"
    ],

    "chatgpt": [
        "chatgpt"
    ],

    "prompt engineering": [
        "prompt engineering"
    ],

    "mlops": [
        "mlops",
        "machine learning operations"
    ],

    # Misc
    "research": [
        "research",
        "research publications",
        "publications"
    ],

    "git": [
        "git",
        "github",
        "version control"
    ],

    "linux": [
        "linux",
        "unix"
    ],

    # Programming Languages (merged from skill_synonyms)
    "javascript": ["js", "ecmascript", "javascript"],
    "typescript": ["ts", "typescript"],
    "java": ["core java", "java se", "java"],
    "c++": ["cpp", "c++"],
    "c#": ["csharp", ".net", "c#"],
    "go": ["golang", "go"],
    "kotlin": ["kotlin"],
    "swift": ["swift"],
    "php": ["php"],
    "scala": ["scala"],

    # Cloud (expanded)
    "gcp": ["gcp", "google cloud platform", "google cloud"],
    "azure": ["azure", "microsoft azure"],

    # DevOps
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "terraform": ["terraform"],
    "jenkins": ["jenkins"],
    "github actions": ["github actions"],

    # Databases
    "postgresql": ["postgresql", "postgres", "postgres db"],
    "redis": ["redis"],
    "elasticsearch": ["elasticsearch"],
    "sqlite": ["sqlite"],
    "oracle": ["oracle"],

    # Backend
    "django": ["django"],
    "flask": ["flask"],
    "fastapi": ["fastapi"],
    "node.js": ["node.js", "nodejs", "node"],
    "spring boot": ["spring boot"],

    # Frontend
    "react": ["react", "reactjs"],
    "angular": ["angular"],
    "vue.js": ["vue.js", "vue"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],

    # MLOps / Modern AI
    "langchain": ["langchain"],
    "llamaindex": ["llamaindex"],
    "mlflow": ["mlflow"],
    "wandb": ["wandb", "weights & biases"],
    "onnx": ["onnx"],
    "lora": ["lora"],
    "faiss": ["faiss"],
    "catboost": ["catboost"],
    "dbt": ["dbt"],
    "bert": ["bert"],
    "opencv": ["opencv"],
    "object detection": ["object detection"],
    "image classification": ["image classification"],
    "artificial intelligence": ["ai", "artificial intelligence"],
    "data analysis": ["data analysis", "analytics", "analytical"],
    "predictive modeling": ["predictive modeling", "predictive analytics"]
}

ALIAS_TO_CANONICAL = {}

for canonical, aliases in SKILL_ALIASES.items():
    for alias in aliases:
        ALIAS_TO_CANONICAL[alias.lower()] = canonical



ROLE_SIMILARITY = {

    "data scientist": [
        "machine learning engineer",
        "ai engineer",
        "research scientist"
    ],

    "machine learning engineer": [
        "data scientist",
        "ai engineer",
        "research scientist",
        "ml architect"
    ],

    "ai engineer": [
        "machine learning engineer",
        "data scientist",
        "ml architect"
    ],

    "research scientist": [
        "data scientist",
        "machine learning engineer"
    ],

    "ml architect": [
        "machine learning engineer",
        "ai engineer"
    ],

    "data analyst": [
        "business analyst"
    ],

    "business analyst": [
        "data analyst"
    ],

    "data engineer": [
        "big data engineer",
        "etl developer"
    ],

    "big data engineer": [
        "data engineer"
    ],

    "etl developer": [
        "data engineer"
    ]
}

# ── Known company founding years (real + fictional from dataset) ──────────────
# Real Indian tech companies
COMPANY_FOUNDED = {
    # Real Indian tech
    "flipkart":      2007,
    "zomato":        2008,
    "ola":           2010,
    "razorpay":      2014,
    "swiggy":        2014,
    "cred":          2018,
    "mad street den":2013,
    "mindtree":      1999,
    "infosys":       1981,
    "wipro":         1945,
    "tcs":           1968,
    "hcl":           1976,
    "cognizant":     1994,
    "tech mahindra": 1986,
    # Real global
    "google":        1998,
    "amazon":        1994,
    "microsoft":     1975,
    "meta":          2004,
    "facebook":      2004,
    "apple":         1976,
    "netflix":       1997,
    "uber":          2009,
    "openai":        2015,
    "anthropic":     2021,
    "deepmind":      2010,
    # Fictional (from dataset — can never be older than ~2011 based on data)
    "dunder mifflin":  2011,
    "globex inc":      2011,
    "initech":         2011,
    "hooli":           2011,
    "pied piper":      2011,
    "acme corp":       2011,
    "stark industries":2011,
    "wayne enterprises":2011,
}


def _detect_honeypot(candidate_row: dict) -> tuple[bool, str]:
    """
    Detect profile-coherence honeypots that should not appear in the top 100.
    Returns (is_honeypot, reason).

    Checks:
      1. Career tenure predates company founding (impossible timeline)
      2. Expert/advanced skill claimed with 0 months of usage
      3. Multiple is_current=True jobs simultaneously
      4. Total claimed YOE > sum of career history by >5 years
    """
    import re as _re
    from datetime import datetime

    career  = candidate_row.get("career_history", []) or []
    skills  = candidate_row.get("skills", []) or []
    profile = candidate_row.get("profile", {}) or {}
    # career_history may be a string in flattened DataFrame rows — skip check
    if not isinstance(career, list):
        career = []

    # ── Check 1: tenure predates company founding ─────────────────────────────
    for job in career:
        company = (job.get("company") or "").strip().lower()
        start_raw = job.get("start_date")
        if not company or not start_raw:
            continue
        founded = COMPANY_FOUNDED.get(company)
        if founded is None:
            continue
        try:
            start_yr = datetime.strptime(start_raw, "%Y-%m-%d").year
            if start_yr < founded:
                return True, f"Tenure at {job['company']} starts {start_yr} but company founded {founded}"
        except ValueError:
            continue

    # ── Check 2: expert/advanced skill with 0 months usage ───────────────────
    # skills can be a list of dicts (raw JSONL) or a string (DataFrame row)
    skills_list = skills if isinstance(skills, list) else []
    expert_zero = [
        sk["name"] for sk in skills_list
        if isinstance(sk, dict)
        and sk.get("proficiency") in ("expert", "advanced")
        and (sk.get("duration_months") or 0) == 0
    ]
    if len(expert_zero) >= 3:
        return True, f"Claims expert/advanced in {len(expert_zero)} skills with 0 months usage: {', '.join(expert_zero[:3])}"

    # ── Check 3: multiple simultaneous current jobs ───────────────────────────
    current_jobs = [j for j in career if j.get("is_current") is True]
    if len(current_jobs) > 1:
        return True, f"{len(current_jobs)} simultaneous current jobs: {', '.join(j.get('company','?') for j in current_jobs)}"

    # ── Check 4: claimed YOE vs career history mismatch >5 years ─────────────
    claimed_yoe = profile.get("years_of_experience") or 0
    if career and claimed_yoe > 0:
        total_months = sum(j.get("duration_months") or 0 for j in career)
        career_yoe = total_months / 12
        if career_yoe > 0 and abs(claimed_yoe - career_yoe) > 5:
            return True, f"Claimed {claimed_yoe}y experience but career history shows {career_yoe:.1f}y"

    return False, ""


def _role_match_score(jd_role: str, cand_role: str) -> int:

    jd_role = jd_role.lower().strip()
    cand_role = cand_role.lower().strip()

    # Exact match
    if jd_role == cand_role:
        return 30

    # Similar role family
    if cand_role in ROLE_SIMILARITY.get(jd_role, []):
        return 25

    # Fallback to existing overlap logic
    jd_words = set(jd_role.split())
    cand_words = set(cand_role.split())

    overlap = jd_words & cand_words

    return round(
        len(overlap) / max(len(jd_words), 1) * 25
    )

# ──────────────────────────────────────────────────────────────────────────────
# COLUMN NAME VARIANTS  (add aliases here if your CSV uses different headings)
# ──────────────────────────────────────────────────────────────────────────────
_COL_ALIASES: dict[str, list[str]] = {
    "name":       ["name", "candidate_name", "full_name", "applicant"],
    "role":       ["role", "job_title", "title", "position", "designation"],
    "location":   ["location", "city", "place", "loc", "region"],
    "experience": ["experience", "exp", "years_of_experience", "years", "yoe"],
    "skills":     ["skills", "skill", "tech_skills", "technical_skills", "technologies"],
    "company":    ["company", "current_company", "employer", "organisation", "organization"],
    "education":  ["education", "edu", "degree", "qualification"],
}


def _find_col(df: pd.DataFrame, field: str) -> str | None:
    """Return the first DataFrame column that matches any alias for `field`."""
    for alias in _COL_ALIASES.get(field, []):
        if alias in df.columns:
            return alias
    return None


def _parse_experience(raw) -> float:
    """Extract the first numeric value from an experience cell."""
    nums = re.findall(r"\d+\.?\d*", str(raw))
    return float(nums[0]) if nums else 0.0

def _extract_skill_tokens(phrase: str) -> list[str]:
    """
    When the JD parser outputs a full sentence as a "skill" (e.g.
    "production experience with embeddings-based retrieval systems
    (sentence-transformers, faiss)" or "proficiency in pytorch or
    tensorflow"), extract the actual technology tokens so _skill_match
    has something concrete to look for.

    Strategy:
      1. Pull terms inside parentheses (even unclosed) — likely real names.
      2. Strip common filler prefixes ("experience with", "knowledge of", etc.)
      3. Split what remains on "and", "or", "," to get individual tokens.
      4. Always include the original phrase as a fallback.
    """
    import re as _re
    tokens = [phrase]

    # 1. Extract terms inside parentheses (handles unclosed parens too)
    parens = _re.findall(r"\(([^)]*)", phrase)
    for p in parens:
        for t in _re.split(r"[,/]", p):
            t = t.strip()
            if t:
                tokens.append(t)

    # 2. Strip filler prefixes
    fillers = _re.compile(
        r"^(?:(?:production|hands[- ]on|practical|strong|solid|deep|proven)\s+)?"
        r"(?:experience\s+(?:with|in|using)|knowledge\s+of|"
        r"familiarity\s+with|proficiency\s+in|expertise\s+in|"
        r"exposure\s+to|working\s+knowledge\s+of|"
        r"hands[- ]on(?:\s+experience)?\s+(?:with|in)|"
        r"strong\s+background\s+in|understanding\s+of|"
        r"background\s+in)\s+",
        _re.IGNORECASE
    )
    cleaned = fillers.sub("", phrase).strip()

    # 3. Split on "and", "or", ",", "/" — get individual tokens
    if cleaned:
        for part in _re.split(r"\s+(?:and|or)\s+|[,/]", cleaned):
            part = part.strip(" ()[]")
            # Drop generic filler leftovers
            if part and not _re.match(
                r"^(?:similar\s+(?:tools?|frameworks?|libraries?|databases?|systems?)|"
                r"etc\.?|others?)$", part, _re.I
            ):
                tokens.append(part)

    # 4. Deduplicate, lowercase, non-empty, min 2 chars
    seen = set()
    result = []
    for t in tokens:
        t = t.strip().lower()
        if len(t) >= 2 and t not in seen:
            seen.add(t)
            result.append(t)
    return result


def _best_label(phrase: str) -> str:
    """
    Return the shortest, cleanest display name for a skill phrase.
    Used so matched/missing skill pills show "sentence-transformers"
    not "production experience with embeddings-based retrieval systems
    (sentence-transformers".

    Priority:
      1. Tokens extracted from parentheses (most specific)
      2. Shortest clean token after stripping filler prefix + splitting on and/or
      3. Original phrase as last resort, lightly cleaned
    """
    import re as _re

    phrase = phrase.strip()

    # Fragments like "or similar) deployed to real users." — pure noise, skip
    if _re.match(r"^(?:or|and)\s+similar", phrase, _re.I):
        return phrase.lower()

    tokens = _extract_skill_tokens(phrase)
    # Exclude the raw phrase itself
    candidates = [t for t in tokens if t != phrase.lower().strip()]

    # Filter out generic/noise tokens
    noise = _re.compile(
        r"^(?:or\s+similar|and\s+similar|etc\.?|others?|"
        r"similar\s+(?:tools?|frameworks?|systems?|libraries?|databases?)|"
        r"or\s+neural|or\s+similar\).*|"
        r"(?:ml|ai)\s+space|"  # "ai/ml space" is too vague
        r"strong\s+\w+\.|"   # "strong python." — strip the "strong"
        r"contributions?\s+in)$",
        _re.I
    )
    candidates = [t for t in candidates if not noise.match(t)]

    # For "strong python." → clean to "python"
    phrase_clean = _re.sub(r"^strong\s+", "", phrase, flags=_re.I).rstrip(".").strip().lower()
    if phrase_clean and phrase_clean != phrase.lower().strip():
        candidates.append(phrase_clean)

    # For paren-extracted tokens prefer them (they're usually the real tech name)
    paren_tokens = []
    parens = _re.findall(r"\(([^)]*)", phrase)
    for p in parens:
        for t in _re.split(r"[,/\s]+(?:or|and)\s+|,", p):
            t = t.strip().lower()
            if len(t) >= 2 and not noise.match(t):
                paren_tokens.append(t)

    if paren_tokens:
        # Among paren tokens, prefer the first (usually the primary tech)
        return paren_tokens[0]

    # Split on em-dash / en-dash — last segment is usually the specific tech
    # e.g. 'hybrid search infrastructure — pinecone' -> 'pinecone'
    emdash_parts = _re.split(r'\s*[\u2014\u2013]\s*', phrase)
    if len(emdash_parts) > 1:
        last = emdash_parts[-1].strip().lower()
        if last and not noise.match(last) and len(last) >= 2:
            return last

    if candidates:
        # Pick FIRST candidate (preserves order — first = primary tech)
        stop = {"or", "and", "with", "in", "of", "the", "a", "an"}
        valid = [t for t in candidates if len(t) >= 2 and t not in stop]
        if valid:
            return valid[0]

    # Last resort: lightly clean the original
    cleaned = _re.sub(r"^(?:strong|deep|solid|proven)\s+", "", phrase, flags=_re.I)
    cleaned = _re.sub(r"[.]+$", "", cleaned).strip().lower()
    return cleaned



def _skill_match(skill: str, candidate_text: str) -> bool:
    # Extract concrete tokens from long JD phrases before matching
    tokens = _extract_skill_tokens(skill)
    for token in tokens:
        canonical = ALIAS_TO_CANONICAL.get(token, token)
        aliases = SKILL_ALIASES.get(canonical, [token])
        for alias in aliases:
            pattern = r"\b" + re.escape(alias.lower()) + r"\b"
            if re.search(pattern, candidate_text):
                return True
    return False


# ──────────────────────────────────────────────────────────────────────────────
# LOAD
# ──────────────────────────────────────────────────────────────────────────────

def load_candidates(uploaded_file) -> pd.DataFrame:
    """
    Read a candidate file (CSV or Excel) and normalise all column names to
    lowercase_underscore. Accepts whatever raw columns the file has — no
    pre-formatting required; AI column mapping (see detect_columns) figures
    out what's what later.

    Returns:
        pd.DataFrame with normalised column names, original data untouched.

    Raises:
        ValueError: if the file extension isn't recognised.
    """
    name = getattr(uploaded_file, "name", "").lower()
    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
    elif name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        # Best-effort: try CSV first, then Excel, rather than hard-failing
        # on an unrecognised/missing extension.
        try:
            df = pd.read_csv(uploaded_file)
        except Exception:
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file)

    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


# ──────────────────────────────────────────────────────────────────────────────
# AI-ASSISTED COLUMN DETECTION
# ──────────────────────────────────────────────────────────────────────────────

def detect_columns(df: pd.DataFrame, jd: dict = None, api_key: str = None) -> dict:
    """
    Map canonical fields (name, role, location, experience, skills, email,
    company, education) to whatever columns actually exist in the uploaded
    file. Tries Gemini first (handles messy/unexpected headers — exactly the
    "I had to hand-build the Excel to match the app" problem); falls back to
    the static alias table below if no API key or the call fails.
    """
    keys = load_gemini_api_keys(api_key)
    mapping = {}

    if keys:
        try:
            from services.provider_factory import get_provider
            provider = get_provider("gemini", keys)
            sample_rows = df.head(3).to_dict(orient="records")
            mapping = provider.map_candidate_columns(list(df.columns), sample_rows) or {}
            # Keep only fields that actually exist as columns.
            mapping = {k: v for k, v in mapping.items() if v in df.columns}
        except Exception:
            mapping = {}

    # Fill in anything AI missed using the static alias table.
    for field in _COL_ALIASES:
        if field not in mapping:
            col = _find_col(df, field)
            if col:
                mapping[field] = col

    return mapping


# ──────────────────────────────────────────────────────────────────────────────
# SCORE — AI (primary path)
# ──────────────────────────────────────────────────────────────────────────────

def _score_candidates_ai(df: pd.DataFrame, jd: dict, api_key: str) -> pd.DataFrame:
    """Batch-scores every candidate via Gemini using the FULL row, not just
    the canonical fields, so any extra signal columns (activity, certs,
    endorsements, last_active, whatever the dataset happens to include) get
    weighed in. Raises on failure so the caller can fall back."""
    from services.provider_factory import get_provider
    provider = get_provider("gemini", load_gemini_api_keys(api_key))

    records = []
    for idx, row in df.iterrows():
        rec = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
        rec["_row_id"] = int(idx)
        records.append(rec)

    results = provider.score_candidates(jd, records)
    by_id = {int(r["_row_id"]): r for r in results if "_row_id" in r}

    rows_total, rows_skill, rows_role, rows_signal = [], [], [], []
    rows_matched, rows_missing, rows_rationale = [], [], []
    for idx in df.index:
        r = by_id.get(int(idx), {})
        skill_sc  = int(r.get("skill_score", 0) or 0)
        role_sc   = int(r.get("role_score", 0) or 0)
        signal_sc = int(r.get("signal_score", 0) or 0)
        total     = min(100, int(r.get("total_score", skill_sc + role_sc + signal_sc) or 0))
        rows_total.append(total)
        rows_skill.append(skill_sc)
        rows_role.append(role_sc)
        rows_signal.append(signal_sc)
        matched = r.get("matched_skills") or []
        missing = r.get("missing_skills") or []
        rows_matched.append(", ".join(matched) if matched else "None")
        rows_missing.append(", ".join(missing) if missing else "None")
        rows_rationale.append(r.get("rationale", ""))

    out = df.copy()
    out["total_score"]    = rows_total
    out["skill_score"]    = rows_skill
    out["role_score"]     = rows_role
    out["signal_score"]   = rows_signal
    out["matched_skills"] = rows_matched
    out["missing_skills"] = rows_missing
    out["rationale"]      = rows_rationale
    return out


# ──────────────────────────────────────────────────────────────────────────────
# SCORE — Offline rule-based (fallback, no API key needed)
# ──────────────────────────────────────────────────────────────────────────────

_LOCATION_ALIASES = {
    "bangalore": "bengaluru", "bengaluru": "bengaluru",
    "bombay": "mumbai", "mumbai": "mumbai",
    "gurgaon": "gurugram", "gurugram": "gurugram",
    "calcutta": "kolkata", "kolkata": "kolkata",
}


def _normalize_location(loc: str) -> str:
    loc = (loc or "").strip().lower()
    return _LOCATION_ALIASES.get(loc, loc)


def _score_candidates_offline(df: pd.DataFrame, jd: dict, col_map: dict) -> pd.DataFrame:
    """
    Deterministic keyword/rule scorer. Used when no Gemini key is available.
    Fixes the location bug from the original version: previously, if the JD
    location couldn't be parsed (jd_location == ""), `bool("" and ...)` is
    always False, so EVERY candidate was marked "No match" regardless of
    their actual city. Now a missing JD location is treated as "N/A / not
    specified" rather than a silent fail for every row.
    """
    df = df.copy()

    required_skills = [s.lower().strip() for s in jd.get("skills", []) if s]
    jd_role     = (jd.get("role") or "").lower()
    jd_location = _normalize_location(jd.get("location") or "")
    exp_min     = int(jd.get("experience_min") or 0)
    exp_max     = int(jd.get("experience_max") or 99)

    skills_col   = col_map.get("skills")
    role_col     = col_map.get("role")
    location_col = col_map.get("location")
    exp_col      = col_map.get("experience")

    # ── Pre-compute skill data once (not per candidate) for speed ──────────
    must_have    = [s.lower().strip() for s in jd.get("must_have_skills", []) if s]
    nice_to_have = [s.lower().strip() for s in jd.get("nice_to_have_skills", []) if s]
    if not must_have and not nice_to_have:
        must_have = required_skills
    weight_total = len(must_have) * 2 + len(nice_to_have) * 1

    # Pre-compile one regex pattern per skill (list of compiled patterns)
    def _compile_skill(phrase):
        tokens = _extract_skill_tokens(phrase)
        canonical = ALIAS_TO_CANONICAL.get(tokens[0] if tokens else phrase, phrase)
        all_tokens = tokens + SKILL_ALIASES.get(canonical, [])
        patterns = [re.compile(r"\b" + re.escape(t.lower()) + r"\b") for t in all_tokens if t]
        label = _best_label(phrase)
        return patterns, label

    must_compiled    = [_compile_skill(s) for s in must_have]
    nice_compiled    = [_compile_skill(s) for s in nice_to_have]

    def _fast_match(compiled_patterns, cand_text):
        return any(p.search(cand_text) for patterns, _ in compiled_patterns for p in patterns)

    def _score_skills(cand_text):
        matched_must_labels, missing_must_labels = [], []
        matched_nice_labels, missing_nice_labels = [], []
        for patterns, label in must_compiled:
            if any(p.search(cand_text) for p in patterns):
                matched_must_labels.append(label)
            else:
                missing_must_labels.append(label)
        for patterns, label in nice_compiled:
            if any(p.search(cand_text) for p in patterns):
                matched_nice_labels.append(label)
            else:
                missing_nice_labels.append(label)
        weight_scored = len(matched_must_labels) * 2 + len(matched_nice_labels) * 1
        skill_sc = round(weight_scored / max(weight_total, 1) * 40)
        matched = matched_must_labels + matched_nice_labels
        missing = missing_must_labels + missing_nice_labels
        nm = len(matched_must_labels); nm_total = len(must_have)
        nn = len(matched_nice_labels); nn_total = len(nice_to_have)
        return skill_sc, matched, missing, nm, nm_total, nn, nn_total
    # ─────────────────────────────────────────────────────────────────────────

    rows_skill_sc, rows_role_sc, rows_signal_sc = [], [], []
    rows_loc, rows_matched, rows_missing, rows_total, rows_rationale = [], [], [], [], []

    for _, row in df.iterrows():
        cand_skills_raw = str(row[skills_col]).lower() if skills_col and pd.notna(row.get(skills_col)) else ""
        skill_sc, matched, missing, nm, nm_total, nn, nn_total = _score_skills(cand_skills_raw)
        matched_must = matched[:nm_total]  # for rationale counts

        cand_role = str(row[role_col]).lower() if role_col and pd.notna(row.get(role_col)) else ""
        role_sc = _role_match_score(jd_role, cand_role) if (jd_role and cand_role) else 0

        cand_exp = _parse_experience(row[exp_col]) if exp_col and pd.notna(row.get(exp_col)) else 0.0
        if exp_min <= cand_exp <= exp_max:
            exp_pts = 20
        elif cand_exp > exp_max:
            exp_pts = max(0, 20 - int((cand_exp - exp_max) * 2))
        else:
            exp_pts = max(0, 20 - int((exp_min - cand_exp) * 3))

        cand_loc = _normalize_location(str(row[location_col])) if location_col and pd.notna(row.get(location_col)) else ""
        if not jd_location:
            loc_label, loc_bonus = "— N/A", 5  # JD had no location: don't penalize anyone
        elif cand_loc and jd_location in cand_loc:
            loc_label, loc_bonus = "✅ Yes", 10
        else:
            loc_label, loc_bonus = "❌ No", 0

        # Honeypot check — penalise impossible profiles heavily
        is_honeypot, honeypot_reason = _detect_honeypot(row.to_dict())
        honeypot_penalty = 60 if is_honeypot else 0

        redrob_bonus = 0
        if row.get("open_to_work") is True:
            redrob_bonus += 2
        github = row.get("github_score") or row.get("github_activity_score")
        if github and github not in (-1, None) and float(github) >= 70:
            redrob_bonus += 2
        completeness = row.get("completeness") or row.get("profile_completeness_score")
        if completeness and float(completeness) >= 80:
            redrob_bonus += 1
        signal_sc = exp_pts + loc_bonus + redrob_bonus
        total = max(0, min(100, skill_sc + role_sc + signal_sc) - honeypot_penalty)

        rows_skill_sc.append(skill_sc)
        rows_role_sc.append(role_sc)
        rows_signal_sc.append(signal_sc)
        rows_loc.append(loc_label)
        rows_matched.append(", ".join(matched) if matched else "None")
        rows_missing.append(", ".join(missing) if missing else "None")
        rows_total.append(total)
        rows_rationale.append(
            f"Skills: {nm}/{max(nm_total,1)} must-have, "
            f"{nn}/{max(nn_total,1)} nice-to-have matched. "
            f"Exp: {cand_exp:g}y (req {exp_min}-{exp_max}y). "
            f"Loc: {loc_label}. Signals: +{redrob_bonus}."
            + (f" ⚠ HONEYPOT: {honeypot_reason}" if is_honeypot else "")
        )

    df["total_score"]    = rows_total
    df["skill_score"]    = rows_skill_sc
    df["role_score"]     = rows_role_sc
    df["signal_score"]   = rows_signal_sc
    df["location_match"] = rows_loc
    df["matched_skills"] = rows_matched
    df["missing_skills"] = rows_missing
    df["rationale"]      = rows_rationale
    return df


# ──────────────────────────────────────────────────────────────────────────────
# SCORE — Unified public entry point
# ──────────────────────────────────────────────────────────────────────────────

def score_candidates(df: pd.DataFrame, jd: dict, api_key: str = None, mode: str = "auto"):
    """
    Score and rank every candidate against the parsed JD.

    Args:
        df:      Candidate DataFrame (normalised columns).
        jd:      Dict produced by core.parser.parse_jd_with_ai() / parse_jd().
        api_key: Gemini API key. If omitted, reads GEMINI_API_KEY from env.
        mode:    "auto" (Gemini if a key is available, else offline),
                 "ai" (force Gemini, raises if it fails),
                 "offline" (force the deterministic rule-based scorer).

    Returns:
        (scored_df, name_col, source)
        scored_df — original DataFrame + score columns, sorted by total_score
        name_col  — detected column name for candidate names (or None)
        source    — "gemini" or "offline-rule", whichever actually ran
    """
    keys = load_gemini_api_keys(api_key)
    col_map = detect_columns(df, jd, api_key=keys)
    name_col = col_map.get("name") or _find_col(df, "name")

    source = "offline-rule"
    scored = None

    if mode in ("auto", "ai") and keys:
        try:
            scored = _score_candidates_ai(df, jd, keys)
            source = "gemini"
        except Exception:
            if mode == "ai":
                raise
            scored = None

    if scored is None:
        scored = _score_candidates_offline(df, jd, col_map)
        source = "offline-rule"

    # Tie-break rule (required by the hackathon validator): when two
    # candidates have the same total_score, they must be ordered by
    # candidate_id ascending, lexicographically (string comparison, not
    # numeric). `sort_values` alone is stable but only sorts on
    # total_score, so ties fall back to whatever order the input file
    # happened to have — which is NOT candidate_id order and is what was
    # causing "Equal scores at ranks N and N+1: tie-break requires
    # candidate_id ascending" validator failures.
    if "candidate_id" in scored.columns:
        scored["_cid_sort_key"] = scored["candidate_id"].astype(str)
        scored = scored.sort_values(
            ["total_score", "_cid_sort_key"],
            ascending=[False, True],
            kind="mergesort",  # stable sort; irrelevant now but cheap insurance
        ).drop(columns="_cid_sort_key").reset_index(drop=True)
    else:
        # No candidate_id column at all — nothing to break ties on, but at
        # least keep the sort stable and deterministic.
        scored = scored.sort_values(
            "total_score", ascending=False, kind="mergesort"
        ).reset_index(drop=True)

    scored.insert(0, "rank", range(1, len(scored) + 1))

    return scored, name_col, source