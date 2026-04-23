import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./newsapi.db")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

# Tier rate limits: requests per day and per minute (None = unlimited)
TIER_LIMITS: dict[str, dict] = {
    "free":       {"daily": 1_000,   "per_minute": 10},
    "developer":  {"daily": 10_000,  "per_minute": 60},
    "business":   {"daily": 100_000, "per_minute": 300},
    "enterprise": {"daily": None,    "per_minute": None},
}

# Cache TTLs in seconds per endpoint type
CACHE_TTL: dict[str, int] = {
    "headlines": 60,
    "articles":  300,
    "sources":   3600,
    "trending":  300,
}

# How many days back each tier can query (None = unlimited)
TIER_HISTORY_DAYS: dict[str, int | None] = {
    "free":       30,
    "developer":  365,
    "business":   None,
    "enterprise": None,
}
