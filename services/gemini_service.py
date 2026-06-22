"""
services/gemini_service.py
───────────────────────────
The real Gemini integration. Previously this file existed but was never
imported by app.py — JD parsing and scoring ran entirely on regex/keyword
rules instead. This version is wired into core/parser.py and core/scorer.py
as the primary path, with the old regex pipeline kept only as an offline
fallback when no API key is present or a call fails.
"""

import json
import re

from google import genai

from services.llm_service import LLMProvider
from services.config import GEMINI_MODEL, SCORING_BATCH_SIZE


class GeminiExtractionError(Exception):
    """Raised when Gemini returns something we can't parse as JSON."""
    pass


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


def _extract_json_block(text: str):
    """
    Pull the first valid JSON object/array out of a model response, even if
    the model added stray prose around it. Tries, in order:
      1. The whole (fence-stripped) text as-is.
      2. The first {...} or [...] balanced block found in the text.
    """
    cleaned = _strip_code_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find the first '{' or '[' and try to match its closing bracket.
    for open_ch, close_ch in (('{', '}'), ('[', ']')):
        start = cleaned.find(open_ch)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(cleaned)):
            if cleaned[i] == open_ch:
                depth += 1
            elif cleaned[i] == close_ch:
                depth -= 1
                if depth == 0:
                    candidate = cleaned[start:i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    raise GeminiExtractionError(f"Could not parse JSON from model response: {text[:300]}")


class GeminiProvider(LLMProvider):

    def __init__(self, api_key, model: str = GEMINI_MODEL):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def _generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return response.text

    # ── Connection check ────────────────────────────────────────────────
    def test_connection(self):
        return self._generate("Say hello in one short sentence.")

    # ── JD extraction ───────────────────────────────────────────────────
    def extract_jd(self, text: str) -> dict:
        prompt = f"""You are an expert technical recruiter. Read the job description
below and extract structured fields. Reason about CONTEXT, not just keyword
matching — e.g. infer seniority from responsibilities even if no years are
stated, and distinguish the HIRING company from any client/customer names
mentioned in the JD body.

Return ONLY valid JSON (no markdown fences, no commentary) with exactly
this shape:
{{
  "role": "<job title, concise>",
  "company": "<the company that is HIRING for this role>",
  "location": "<primary work location, city/region, or 'Remote'>",
  "employment_type": "<Full-time | Part-time | Contract | Internship | Freelance | null>",
  "education": "<minimum education requirement, or null>",
  "industry": "<industry/domain, or null>",
  "experience_min": <integer years, or null>,
  "experience_max": <integer years, or null>,
  "skills": ["<all relevant skills/technologies mentioned, lowercase>"],
  "must_have_skills": ["<skills explicitly described as required/mandatory>"],
  "nice_to_have_skills": ["<skills described as a plus/bonus/preferred>"],
  "summary": "<one or two sentence plain-English summary of the role>"
}}

If a field cannot be determined, use null (or an empty list for list fields).
Do not invent information that isn't supported by the text.

JOB DESCRIPTION:
{text[:12000]}
"""
        raw = self._generate(prompt)
        data = _extract_json_block(raw)
        if not isinstance(data, dict):
            raise GeminiExtractionError("Expected a JSON object for JD extraction.")
        return data

    # ── Candidate file column mapping ───────────────────────────────────
    def map_candidate_columns(self, columns: list, sample_rows: list) -> dict:
        prompt = f"""You're given the column headers and a few sample rows from a
candidate spreadsheet. Map each CANONICAL field below to the actual column
name in this file that best represents it. Only include a canonical key if
you're reasonably confident a matching column exists — omit it otherwise.

CANONICAL FIELDS: name, role, location, experience, skills, email, company,
education

COLUMNS IN FILE: {json.dumps(columns)}

SAMPLE ROWS:
{json.dumps(sample_rows, default=str)[:4000]}

Return ONLY a JSON object mapping canonical_field -> actual_column_name,
e.g. {{"name": "Full Name", "skills": "Tech Stack"}}. No commentary.
"""
        raw = self._generate(prompt)
        data = _extract_json_block(raw)
        if not isinstance(data, dict):
            raise GeminiExtractionError("Expected a JSON object for column mapping.")
        return data

    # ── Batch candidate scoring ─────────────────────────────────────────
    def score_candidates(self, jd: dict, candidates: list) -> list:
        """
        Scores candidates in batches of SCORING_BATCH_SIZE so prompts stay
        small and responses stay reliable, then merges all batches.
        """
        results = []
        for i in range(0, len(candidates), SCORING_BATCH_SIZE):
            batch = candidates[i:i + SCORING_BATCH_SIZE]
            results.extend(self._score_batch(jd, batch))
        return results

    def _score_batch(self, jd: dict, batch: list) -> list:
        prompt = f"""You are an expert technical recruiter ranking candidates against a
job description. Use ALL the information given for each candidate — not
just an explicit "skills" field. Career metadata, activity/engagement
signals, certifications, project history, or anything else present in a
candidate's row should inform your judgement of fit, the same way a human
recruiter would read a full profile rather than just keyword-matching a
resume.

JOB DESCRIPTION:
{json.dumps(jd, default=str)}

CANDIDATES (each is one full row from the uploaded dataset):
{json.dumps(batch, default=str)[:30000]}

For EACH candidate, return an entry with this exact shape:
{{
  "_row_id": <the _row_id from the input, unchanged>,
  "total_score": <integer 0-100>,
  "skill_score": <integer 0-40, how well their skills/experience match required skills>,
  "role_score": <integer 0-30, how well their role/title/seniority matches>,
  "signal_score": <integer 0-30, holistic fit from location, career trajectory,
                    activity/behavioral signals, education, and any other
                    available context — your judgement call>,
  "matched_skills": ["<skills from the JD this candidate clearly has>"],
  "missing_skills": ["<required skills from the JD this candidate appears to lack>"],
  "rationale": "<one concise sentence on why this score, mentioning the
                 single strongest and single weakest factor>"
}}

total_score should equal skill_score + role_score + signal_score.
Rank candidates fairly relative to EACH OTHER within this batch — spread
scores out meaningfully, don't cluster everyone in a narrow band unless
they are genuinely that similar.

Return ONLY a JSON array of these objects, one per candidate, in the same
order as the input. No commentary, no markdown fences.
"""
        raw = self._generate(prompt)
        data = _extract_json_block(raw)
        if not isinstance(data, list):
            raise GeminiExtractionError("Expected a JSON array for candidate scoring.")
        return data

    # ── Chatbot ──────────────────────────────────────────────────────────
    def chat(self, message: str, context: dict, history: list) -> str:
        history_text = "\n".join(
            f"{h.get('role', 'user').upper()}: {h.get('content', '')}"
            for h in (history or [])[-8:]
        )
        prompt = f"""You are an AI recruiting assistant embedded in a hiring dashboard.
Answer the recruiter's question using ONLY the context below. Be concise
and direct — a few sentences or a short list, not an essay. If asked to
compare or recommend candidates, refer to them by name and cite concrete
reasons from the data (scores, skills, location, etc).

JOB DESCRIPTION CONTEXT:
{json.dumps(context.get('jd', {}), default=str)}

SCORED CANDIDATES (top results, ranked):
{json.dumps(context.get('candidates', []), default=str)[:20000]}

CONVERSATION SO FAR:
{history_text}

RECRUITER'S NEW QUESTION:
{message}
"""
        return self._generate(prompt)