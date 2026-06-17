from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path(".env")

print("Exists:", env_path.exists())

load_dotenv(env_path)

print("KEY:", os.getenv("GEMINI_API_KEY"))
