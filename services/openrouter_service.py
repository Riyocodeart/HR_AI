from services.llm_service import LLMProvider


class OpenRouterProvider(LLMProvider):

    def __init__(self, api_key):
        self.api_key = api_key

    def extract_jd(self, text: str):
        raise NotImplementedError()

    def summarize_candidate(self, candidate_data):
        raise NotImplementedError()
