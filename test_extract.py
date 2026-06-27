from dotenv import load_dotenv

from services.provider_factory import get_provider
from services.key_rotation import load_gemini_api_keys

load_dotenv()

provider = get_provider("gemini", load_gemini_api_keys())

sample_jd = """
We are hiring a Data Scientist in Mumbai.

Requirements:
- Python
- SQL
- Machine Learning
Experience: 3-5 years
"""

print(provider.extract_jd(sample_jd))


