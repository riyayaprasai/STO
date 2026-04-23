"""
GET /v1/headlines – top headlines from the last 24 hours.

Results are ranked by recency and cached with a 60-second TTL.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from config import CACHE_TTL
from database import get_db
from models import Article, User
from schemas import HeadlinesResponse
from services.news_aggregator import get_headlines, refresh_articles
from utils.cache import cache

from ._helpers import article_to_schema

router = APIRouter()


@router.get("/headlines", response_model=HeadlinesResponse, tags=["headlines"])
async def get_top_headlines(
    q: Optional[str] = Query(None, description="Keywords to filter headlines"),
    sources: Optional[str] = Query(None, description="Comma-separated source IDs"),
    category: Optional[str] = Query(None, description="e.g. technology, business, sports"),
    language: Optional[str] = Query(None, description="ISO 639-1 code, e.g. en"),
    country: Optional[str] = Query(None, description="ISO 3166-1 alpha-2 code, e.g. us"),
    headlines_limit: int = Query(10, ge=1, le=100, alias="headlinesLimit",
                                 description="Max top stories to return"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HeadlinesResponse:
    cache_key = cache.make_key(
        "headlines",
        q=q, sources=sources, category=category, language=language,
        country=country, headlines_limit=headlines_limit, page=page,
        page_size=page_size,
    )
    if (cached := cache.get(cache_key)) is not None:
        return cached

    if db.query(Article).count() < 10:
        await refresh_articles(db)

    result = get_headlines(
        db,
        q=q, sources=sources, category=category, language=language,
        country=country, headlines_limit=headlines_limit,
        page=page, page_size=page_size, user_tier=user.tier,
    )

    effective_page_size = min(page_size, headlines_limit)
    response = HeadlinesResponse(
        total_results=result["total"],
        page=page,
        page_size=effective_page_size,
        articles=[article_to_schema(a) for a in result["articles"]],
    )

    cache.set(cache_key, response, CACHE_TTL["headlines"])
    return response
