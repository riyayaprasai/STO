"""
GET /api/news/headlines    – recent headlines (public, no auth required)
GET /api/news/search       – search articles by query / ticker
GET /api/news/trending     – trending topics from recent articles

These are public wrappers around the existing news-aggregator service so the
frontend can access article data without needing an X-Api-Key header.
"""
import html
import re
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from services.news_aggregator import get_headlines, get_trending_topics, search_articles

router = APIRouter()

# Strip residual HTML entities from titles/descriptions that came from RSS
_HTML_ENT = re.compile(r"&#\d+;|&[a-z]+;", re.I)


def _clean(text: Optional[str]) -> Optional[str]:
    if not text:
        return text
    return html.unescape(text)


def _fmt(article) -> dict:
    return {
        "id": article.id,
        "title": _clean(article.title),
        "description": _clean(article.description),
        "url": article.url,
        "source": article.source_name,
        "category": article.category,
        "sentiment": article.sentiment,
        "published_at": (
            article.published_at.isoformat() if article.published_at else None
        ),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/news/headlines")
def news_headlines(
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Return the most recent headlines (last 24 h) across all sources."""
    result = get_headlines(db, category=category, page=page, page_size=page_size)
    return {
        "total": result["total"],
        "page": page,
        "articles": [_fmt(a) for a in result["articles"]],
    }


@router.get("/news/search")
def news_search(
    q: str = Query(..., description="Keyword or ticker symbol, e.g. AAPL"),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Full-text search across article titles and descriptions."""
    result = search_articles(db, q=q, category=category, page=page, page_size=page_size)
    return {
        "total": result["total"],
        "query": q,
        "page": page,
        "articles": [_fmt(a) for a in result["articles"]],
    }


@router.get("/news/trending")
def news_trending(
    window: str = Query("24h", description="Time window: 1h, 6h, 24h, 7d"),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Return trending phrases / topics extracted from recent article titles."""
    topics = get_trending_topics(db, window=window, category=category)
    return {"window": window, "topics": topics}
