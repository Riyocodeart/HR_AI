from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """
    Common interface every LLM backend (Gemini, OpenRouter, ...) must
    implement so the rest of the app never has to know which provider
    is actually answering.
    """

    @abstractmethod
    def test_connection(self):
        """Lightweight call to verify the API key / connection works."""
        pass

    @abstractmethod
    def extract_jd(self, text: str) -> dict:
        """
        Parse a raw job description into a structured dict. Must return a
        plain Python dict (already JSON-decoded), not a raw string. Expected
        keys (any may be None if not found):
            role, company, location, employment_type, education, industry,
            experience_min, experience_max, skills (list[str]),
            must_have_skills (list[str]), nice_to_have_skills (list[str]),
            summary
        """
        pass

    @abstractmethod
    def map_candidate_columns(self, columns: list, sample_rows: list) -> dict:
        """
        Given raw column headers + a few sample rows from an uploaded
        candidate file, return a mapping of canonical field name ->
        actual column name in the file, e.g.
            {"name": "Full Name", "skills": "Tech Stack", ...}
        Only include keys it's confident about; omit fields it can't find.
        """
        pass

    @abstractmethod
    def score_candidates(self, jd: dict, candidates: list) -> list:
        """
        Score a batch of candidates against a JD in a single call.

        Args:
            jd: structured JD dict (see extract_jd)
            candidates: list of dicts, each the full raw row for one
                candidate (every column the uploaded file had — not just
                the canonical ones), plus a stable '_row_id' key.

        Returns:
            list of dicts, one per candidate, each containing at least:
                _row_id, total_score (0-100), skill_score (0-40),
                role_score (0-30), signal_score (0-30),
                matched_skills (list[str]), missing_skills (list[str]),
                rationale (short string explaining the ranking)
        """
        pass

    @abstractmethod
    def chat(self, message: str, context: dict, history: list) -> str:
        """
        Conversational assistant grounded on the current JD + scored
        candidates. `context` carries whatever session data is available;
        `history` is a list of {"role": "user"/"assistant", "content": str}.
        Returns the assistant's reply text.
        """
        pass