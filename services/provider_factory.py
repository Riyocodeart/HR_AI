from services.gemini_service import GeminiProvider
from services.openrouter_service import OpenRouterProvider


def get_provider(name, api_key):
    """Return the requested provider. Gemini accepts one key or many."""

    if name.lower() == "gemini":
        return GeminiProvider(api_key)

    if name.lower() == "openrouter":
        return OpenRouterProvider(api_key)

    raise ValueError(f"Unsupported provider: {name}")
