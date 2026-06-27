from dotenv import load_dotenv
from pathlib import Path

from services.key_rotation import load_gemini_api_keys

env_path = Path(".env")

print("Exists:", env_path.exists())

load_dotenv(env_path)

keys = load_gemini_api_keys()
print("Gemini keys loaded:", len(keys))
