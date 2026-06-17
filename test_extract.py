from dotenv import load_dotenv
import os

from services.provider_factory import get_provider

load_dotenv()

provider = get_provider(
    "gemini",
    os.getenv("GEMINI_API_KEY")
)

sample_jd = """
We are hiring a Data Scientist in Mumbai.

Requirements:
- Python
- SQL
- Machine Learning
Experience: 3-5 years
"""

print(provider.extract_jd(sample_jd))


