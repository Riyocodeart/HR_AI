from dotenv import load_dotenv

from services.provider_factory import get_provider
from services.key_rotation import load_gemini_api_keys

load_dotenv()

provider = get_provider("gemini", load_gemini_api_keys())

print("Provider:", type(provider).__name__)
print("Response:", provider.test_connection())
