import os
from pathlib import Path
from dotenv import load_dotenv

# Load root .env
PROJECT_ROOT = Path(__file__).resolve().parent.parent
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# LLM API Settings
OPENAI_CHAT_ENDPOINT = os.getenv("OPENAI_CHAT_ENDPOINT", "https://api.groq.com/openai/v1")
OPENAI_CHAT_KEY = os.getenv("OPENAI_CHAT_KEY", "")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "llama-3.3-70b-versatile")

# Judge Model (Can be same or different provider)
JUDGE_CHAT_ENDPOINT = os.getenv("JUDGE_CHAT_ENDPOINT", OPENAI_CHAT_ENDPOINT)
JUDGE_CHAT_KEY = os.getenv("JUDGE_CHAT_KEY", OPENAI_CHAT_KEY)
JUDGE_CHAT_MODEL = os.getenv("JUDGE_CHAT_MODEL", OPENAI_CHAT_MODEL)

# Server & Database Settings
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
DATABASE_PATH = str(PROJECT_ROOT / os.getenv("DATABASE_PATH", "database/audit_logs.db"))

# Security Guard Defaults
CANARY_TOKEN = os.getenv("CANARY_TOKEN", "SECRET_CANARY_TOKEN_XYZ_999")
PROMPTGUARD_STRICT_MODE = os.getenv("PROMPTGUARD_STRICT_MODE", "true").lower() in ("true", "1", "yes")
SEMANTIC_GUARD_THRESHOLD = float(os.getenv("SEMANTIC_GUARD_THRESHOLD", "0.75"))
