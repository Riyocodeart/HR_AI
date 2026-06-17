from google import genai

from services.llm_service import LLMProvider


class GeminiProvider(LLMProvider):

    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)

    def test_connection(self):
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Say hello."
        )
        return response.text

    def extract_jd(self, text: str):

        prompt = f"""
Extract the following information from this job description.

Return ONLY valid JSON.

{{
  "role": "",
  "skills": [],
  "location": "",
  "experience_min": null,
  "experience_max": null
}}

Job Description:
{text}
"""

        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        return response.text

    def summarize_candidate(self, candidate_data):
        raise NotImplementedError("Will implement later")
