# HR_AI
# 🎯 AI Recruiter — Intelligent Candidate Screening

A full-stack AI-powered recruiter tool built with Streamlit + OpenAI.

## Pipeline
1. **Upload JD** (PDF or paste text)
2. **AI Extraction** — GPT-4o-mini extracts Role, Skills, Location, Experience
3. **Upload Candidates CSV** (30–50 rows)
4. **Filter & Score** — Skill (40pts) + Role (30pts) + Experience (30pts)
5. **Export** — Color-coded Excel + CSV

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
npm install linkedin-profile-scraper
node scrape_linkedin.js
```

## CSV Format
Your candidates CSV should have these columns (names are auto-detected):
| name | role | location | experience | skills |
|------|------|----------|------------|--------|
| Priya Sharma | Data Scientist | Mumbai | 4 | Python ML SQL |

A sample file `sample_candidates.csv` is included with 30 candidates.

## API Key
Enter your OpenAI API key in the sidebar. The app uses `gpt-4o-mini` for cost efficiency.

## Scoring Logic
```
total_score = skill_score (0-40) + role_score (0-30) + experience_score (0-30)
```
- **Skill Score**: % of required skills found in candidate profile × 40
- **Role Score**: keyword overlap between JD role and candidate role × 30  
- **Experience Score**: 30 if within range, reduced for over/under-qualified

# JD Parser

Offline, deterministic Job-Description parser for the Redrob ranking pipeline.

Powered by **Qwen 2.5 7B Instruct** running locally via **Ollama**. No external APIs, no network calls during parsing.

## Pipeline

```
Raw JD ─► Cleaner ─► PromptBuilder ─► Ollama (Qwen2.5:7B) ─►
JSON Extract ─► Schema Validate ─► Normalize ─► dict
```

## Setup

```bash
# 1. Pull the model (one-time, ~4.7 GB)
ollama pull qwen2.5:7b-instruct

# 2. Install Python deps
pip install -r parser/requirements.txt

# 3. Make sure the Ollama daemon is running
ollama serve   # background, default port 11434
```

## Usage

### One-liner

```python
from parser import parse_job_description

with open("job_description.txt") as f:
    result = parse_job_description(f.read())

print(result["job_title"], result["skills"]["required"])
```

### Long-lived (recommended in Streamlit)

```python
from parser import JDParser

parser = JDParser(model="qwen2.5:7b-instruct", seed=42)  # construct once
result = parser.parse(jd_text)                            # call many times
```

### Streamed reveal for UI

```python
for field, value in parser.parse_stream(jd_text):
    print(field, "→", value)
```

## File layout

| File                       | Responsibility                                              |
| -------------------------- | ----------------------------------------------------------- |
| `models.py`                | Pydantic schema (mirrors `jd_schema.json` + tech buckets)   |
| `utils.py`                 | Logger, retry, file readers, hashing                        |
| `cleaner.py`               | Unicode / whitespace / boilerplate cleanup                  |
| `prompt_builder.py`        | System + user prompts (schema embedded)                     |
| `json_validator.py`        | JSON extract → schema validate → repair                     |
| `normalizer.py`            | Canonicalise enums, dedupe lists, coerce numbers            |
| `jd_parser.py`             | Orchestrator + `parse_job_description()` + `JDParser` class |
| `__init__.py`              | Public API re-exports                                       |
| `requirements.txt`         | Runtime deps                                                |

## Guarantees

- **Deterministic** — `temperature=0`, `seed=42`, fixed prompt.
- **Schema-validated** — every output passes `jsonschema` against `jd_schema.json`.
- **Never hallucinates** — missing scalar → `null`, missing list → `[]`.
- **Resilient** — auto-retry once on validation failure, then heuristic JSON repair.
- **Modular** — each file has one responsibility; easy to extend.

## Extending

- **New field?** Add it to `models.JobDescription` and `_SCHEMA_SKETCH` in `prompt_builder.py`. The normalizer / validator pick it up automatically.
- **Different model?** `JDParser(model="llama3.1:8b-instruct", ...)` — any Ollama-served chat model with JSON mode works.
- **Caching?** Use `parser.utils.stable_hash(cleaned_text)` as the key.