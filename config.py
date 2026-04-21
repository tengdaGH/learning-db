"""
Centralized configuration for the Personal Learning Database.
Reads from environment variables with sensible defaults.
"""
import os
from pathlib import Path

# Load .env file if present
from dotenv import load_dotenv
load_dotenv(override=True)

# ─── Database ─────────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "learning.db"

# ─── MiniMax / Anthropic API ──────────────────────────────────────────────────
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic")
MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7-highspeed")

# ─── Tavily API ───────────────────────────────────────────────────────────────
TAVILY_KEYS = []
_key1 = os.getenv("TAVILY_API_KEY_1")
_key2 = os.getenv("TAVILY_API_KEY_2")
if _key1:
    TAVILY_KEYS.append(_key1)
if _key2:
    TAVILY_KEYS.append(_key2)

# ─── Flask ────────────────────────────────────────────────────────────────────
FLASK_PORT = int(os.getenv("FLASK_PORT", "5001"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"
