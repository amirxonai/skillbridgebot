"""
config.py — Central configuration for SkillBridge Bot.

All app-level settings live here, making it easy to swap values
(e.g. move to environment variables or a config file) without
touching business logic.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Look for .env in current directory first, then one level up (project root)
_env_file = Path('.env') if Path('.env').exists() else Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=_env_file)

# ---------------------------------------------------------------------------
# Telegram Bot Token
# ---------------------------------------------------------------------------
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS: list[int] = [int(x) for x in os.getenv("ADMIN_IDS", "5024849824").split(",") if x.strip().isdigit()]

# ---------------------------------------------------------------------------
# Bot Identity
# ---------------------------------------------------------------------------
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "skillbridgeuzbot")

# ---------------------------------------------------------------------------
# Infrastructure Configuration
# ---------------------------------------------------------------------------
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///skillbridge.db")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
REDIS_URL: str = os.getenv("REDIS_URL", "")

# ---------------------------------------------------------------------------
# Rating Constraints
# ---------------------------------------------------------------------------
MIN_RATING: int = 1   # Minimum rating a user can give.
MAX_RATING: int = 5   # Maximum rating a user can give.
