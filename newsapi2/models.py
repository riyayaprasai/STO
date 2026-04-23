from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, Float, ForeignKey
from datetime import datetime
import secrets
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    api_key = Column(String, unique=True, index=True)
    tier = Column(String, default="free")          # free | developer | business | enterprise
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Source(Base):
    __tablename__ = "sources"

    id = Column(String, primary_key=True)          # e.g. "bbc-news"
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String, nullable=False)
    rss_url = Column(String, nullable=True)
    category = Column(String, index=True)
    language = Column(String, default="en", index=True)
    country = Column(String, index=True)
    is_active = Column(Boolean, default=True)


class Article(Base):
    __tablename__ = "articles"

    id = Column(String, primary_key=True)          # art_<12-char random>
    source_id = Column(String, index=True)
    source_name = Column(String)
    author = Column(String, nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String, unique=True, index=True)
    url_to_image = Column(String, nullable=True)
    published_at = Column(DateTime, index=True)
    category = Column(String, index=True, nullable=True)
    language = Column(String, default="en", index=True)
    country = Column(String, nullable=True, index=True)
    sentiment = Column(String, default="neutral")
    popularity = Column(Integer, default=0)
    content_hash = Column(String, unique=True, index=True)  # MD5(url) for dedup
    created_at = Column(DateTime, default=datetime.utcnow)


# ── STO App Users (JWT-based, separate from API-key users) ───────────────────

class AppUser(Base):
    """Frontend app users — authenticated via JWT (email + password)."""
    __tablename__ = "app_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Portfolio(Base):
    """One virtual portfolio per AppUser, seeded with $100,000 play money."""
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), unique=True, nullable=False)
    cash = Column(Float, default=100_000.0, nullable=False)


class Position(Base):
    """A stock holding inside a Portfolio."""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    quantity = Column(Integer, default=0, nullable=False)
    avg_price = Column(Float, default=0.0, nullable=False)


# ── helpers ──────────────────────────────────────────────────────────────────

def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def create_user(db, username: str, email: str, tier: str = "free") -> User:
    user = User(username=username, email=email, api_key=generate_api_key(), tier=tier)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_api_key(db, api_key: str) -> User | None:
    return db.query(User).filter(User.api_key == api_key).first()
