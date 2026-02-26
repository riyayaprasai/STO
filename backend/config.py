import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE_PATH = os.getenv("DATABASE_PATH", "")  # default: backend/instance/stoopid.db (set in db.py)
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "stoopid-dev/1.0")
    TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")
    NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
    HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "")
    USE_MOCK_DATA = not bool(
        os.getenv("REDDIT_CLIENT_ID") or os.getenv("TWITTER_BEARER_TOKEN")
    )
