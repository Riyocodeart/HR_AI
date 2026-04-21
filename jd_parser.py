"""
jd_parser.py
────────────
Parses a Job Description from a .docx, .pdf, or plain text with ZERO external APIs.
Uses regex + keyword matching. Works fully offline.
"""

import re
import json
import zipfile
import xml.etree.ElementTree as ET
import io

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────

JD_FILE_PATH = "JD.docx"   # ← change to your file name

# ──────────────────────────────────────────────────────────────────────────────
# KNOWLEDGE BASE  (extend these lists as needed)
# ──────────────────────────────────────────────────────────────────────────────

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
    "it ": "Information Technology",
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
    "marketing": "Marketing",
    "sales": "Sales",
    "hr": "Human Resources",
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
}

# ──────────────────────────────────────────────────────────────────────────────
# DOCX TEXT EXTRACTION
# ──────────────────────────────────────────────────────────────────────────────

_WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a .docx file path."""
    with zipfile.ZipFile(file_path, "r") as z:
        with z.open("word/document.xml") as f:
            tree = ET.parse(f)
    root = tree.getroot()
    paragraphs = []
    for para in root.iter(f"{_WORD_NS}p"):
        texts = [node.text for node in para.iter(f"{_WORD_NS}t") if node.text]
        line = "".join(texts).strip()
        if line:
            paragraphs.append(line)
    return "\n".join(paragraphs)


def extract_text_from_docx_bytes(file_bytes: bytes) -> str:
    """Extract text from a .docx given as raw bytes (e.g. Streamlit UploadedFile)."""
    buf = io.BytesIO(file_bytes)
    with zipfile.ZipFile(buf, "r") as z:
        with z.open("word/document.xml") as f:
            tree = ET.parse(f)
    root = tree.getroot()
    paragraphs = []
    for para in root.iter(f"{_WORD_NS}p"):
        texts = [node.text for node in para.iter(f"{_WORD_NS}t") if node.text]
        line = "".join(texts).strip()
        if line:
            paragraphs.append(line)
    return "\n".join(paragraphs)


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    """
    Extract plain text from a PDF given as raw bytes.
    Uses PyPDF2 (pip install pypdf2) — no external APIs needed.
    Falls back gracefully if the library is missing.
    """
    try:
        import pypdf  # pypdf >= 3.x
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    except ImportError:
        try:
            import PyPDF2 as pypdf2
            reader = pypdf2.PdfReader(io.BytesIO(file_bytes))
        except ImportError:
            raise ImportError(
                "PDF support requires pypdf or PyPDF2. "
                "Install it with:  pip install pypdf"
            )

    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n".join(pages)


def parse_jd_from_upload(uploaded_file) -> dict:
    """
    Unified entry-point for Streamlit uploads.

    Accepts a Streamlit UploadedFile whose .name ends in
    .pdf / .docx / .txt  and returns the parsed JD dict.
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

# ──────────────────────────────────────────────────────────────────────────────
# EXTRACTORS
# ──────────────────────────────────────────────────────────────────────────────

def extract_role(text: str):
    """Extract job title from common header patterns."""
    patterns = [
        r"(?:job title|role|position|designation)\s*[:\-]\s*(.+)",
        r"(?:hiring for|looking for|we are hiring)\s+(?:a|an)?\s*(.+?)(?:\n|\.)",
        r"^([A-Z][A-Za-z\s\-\/]{3,60})\n",   # Title-cased first line
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            title = m.group(1).strip().rstrip(".")
            if len(title) < 80:
                return title
    # Fallback: first non-empty line
    for line in text.splitlines():
        line = line.strip()
        if line and len(line) < 80:
            return line
    return None


def extract_skills(text: str):
    """Match skills from the knowledge base."""
    text_lower = text.lower()
    found = []
    for skill in SKILLS_DB:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found.append(skill.title() if len(skill) > 3 else skill.upper())
    return list(dict.fromkeys(found))   # deduplicate, preserve order


def extract_experience(text: str):
    """Extract min/max years of experience."""
    patterns = [
        r'(\d+)\s*[-–to]+\s*(\d+)\s*(?:years?|yrs?)',   # 3-5 years
        r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)',  # 5+ years
        r'minimum\s+(?:of\s+)?(\d+)\s*(?:years?|yrs?)',
        r'at\s+least\s+(\d+)\s*(?:years?|yrs?)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            groups = [int(g) for g in m.groups() if g is not None]
            if len(groups) == 2:
                return min(groups), max(groups)
            elif len(groups) == 1:
                return groups[0], groups[0]
    return None, None


def extract_location(text: str):
    """Find location from known cities list."""
    text_lower = text.lower()
    for loc in ALL_LOCATIONS:
        if re.search(r'\b' + re.escape(loc) + r'\b', text_lower):
            return loc.title()
    # Check for explicit location label
    m = re.search(r'(?:location|place|city|office)\s*[:\-]\s*(.+)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip().split("\n")[0]
    return None


def extract_employment_type(text: str):
    text_lower = text.lower()
    for keyword, label in EMPLOYMENT_TYPES.items():
        if keyword in text_lower:
            return label
    return "Full-time"   # default assumption


def extract_education(text: str):
    # Strategy 1: Look for an "Education" section and grab lines inside it
    section_match = re.search(
        r'(?:^|\n)\s*education\s*[:\-]?\s*\n((?:.+\n?){1,5})',
        text, re.IGNORECASE
    )
    if section_match:
        section_text = section_match.group(1)
        # Pick first non-empty, non-bullet line from the section
        for line in section_text.splitlines():
            line = re.sub(r'^[\*\-\•\>\s]+', '', line).strip()
            if line and len(line) > 8:
                return line.rstrip(",.")

    # Strategy 2: Find degree keywords anywhere in the text (no prefix required)
    for pat in EDUCATION_KEYWORDS:
        m = re.search(
            r"(?:bachelor'?s?|master'?s?|phd|ph\.d|b\.?tech|m\.?tech|mba|bca|mca|"
            r"b\.?sc|m\.?sc|graduate|degree)\s+[^\n]{0,80}",
            text, re.IGNORECASE
        )
        if m:
            return m.group(0).strip().rstrip(",.")

    # Strategy 3: Original prefix-based approach as fallback
    for pat in EDUCATION_KEYWORDS:
        m = re.search(
            r'(?:require[sd]?|prefer[sr]?ed|must have|need|hold)?\s*(?:a\s+)?'
            + pat + r'[^\n,.]{0,60}',
            text, re.IGNORECASE
        )
        if m:
            return m.group(0).strip().rstrip(",.")

    return None


def extract_company(text: str):
    patterns = [
        r'(?:company|organization|employer|about us|about)\s*[:\-]\s*(.+)',
        r'(?:at|join)\s+([A-Z][A-Za-z0-9\s&]{2,40})(?:\s+is|\s+we|\s+you|,)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            name = m.group(1).strip().rstrip(".,")
            if len(name) < 60:
                return name
    return None


def extract_industry(text: str):
    text_lower = text.lower()
    for keyword, industry in INDUSTRY_MAP.items():
        if keyword in text_lower:
            return industry
    return None


def build_summary(text: str, role, company, exp_min, exp_max, location):
    """Build a 2-sentence human-readable summary from extracted fields."""
    parts = []

    # Sentence 1
    s1 = "This role"
    if role:
        s1 = f"This is a {role} position"
    if company:
        s1 += f" at {company}"
    if location:
        s1 += f", based in {location}"
    parts.append(s1 + ".")

    # Sentence 2
    s2_parts = []
    if exp_min is not None:
        if exp_min == exp_max:
            s2_parts.append(f"{exp_min} years of experience required")
        else:
            s2_parts.append(f"{exp_min}–{exp_max} years of experience required")
    if s2_parts:
        parts.append("The candidate needs " + " and ".join(s2_parts) + ".")
    else:
        parts.append("Please review the full description for experience requirements.")

    return " ".join(parts)

# ──────────────────────────────────────────────────────────────────────────────
# MAIN PARSER
# ──────────────────────────────────────────────────────────────────────────────

def parse_jd(jd_text: str) -> dict:
    role        = extract_role(jd_text)
    skills      = extract_skills(jd_text)
    location    = extract_location(jd_text)
    exp_min, exp_max = extract_experience(jd_text)
    emp_type    = extract_employment_type(jd_text)
    education   = extract_education(jd_text)
    company     = extract_company(jd_text)
    industry    = extract_industry(jd_text)
    summary     = build_summary(jd_text, role, company, exp_min, exp_max, location)

    return {
        "role":            role,
        "skills":          skills,
        "location":        location,
        "experience_min":  exp_min,
        "experience_max":  exp_max,
        "industry":        industry,
        "employment_type": emp_type,
        "education":       education,
        "company":         company,
        "summary":         summary,
    }

# ──────────────────────────────────────────────────────────────────────────────
# RUN
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"📄 Reading: {JD_FILE_PATH}")
    jd_text = extract_text_from_docx(JD_FILE_PATH)
    print(f"✅ Extracted {len(jd_text)} characters\n")

    result = parse_jd(jd_text)

    print("=" * 50)
    print("         PARSED JD RESULT")
    print("=" * 50)
    print(json.dumps(result, indent=2))

    # Also save to file
    with open("parsed_jd.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\n💾 Saved to parsed_jd.json")