from abc import ABC, abstractmethod


class LLMProvider(ABC):

    @abstractmethod
    def extract_jd(self, text: str):
        pass

    @abstractmethod
    def summarize_candidate(self, candidate_data):
        pass
