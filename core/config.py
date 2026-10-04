import os
from pathlib import Path
from dotenv import load_dotenv

# Load local .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

OPENAI_CHAT_ENDPOINT = os.getenv("OPENAI_CHAT_ENDPOINT", "https://api.groq.com/openai/v1")
OPENAI_CHAT_KEY = os.getenv("OPENAI_CHAT_KEY", "")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "openai/gpt-oss-120b")
DATABASE_PATH = os.getenv("DATABASE_PATH", "database/audit_logs.db")
