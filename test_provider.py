from dotenv import load_dotenv
import os

from services.provider_factory import get_provider

load_dotenv()

provider = get_provider(
    "gemini",
    os.getenv("GEMINI_API_KEY")
)

print("Provider:", type(provider).__name__)
print("Response:", provider.test_connection())
