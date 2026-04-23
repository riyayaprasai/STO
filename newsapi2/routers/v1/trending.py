"""
GET /v1/trending – trending topics derived from recent article titles.

Results are cached with a 5-minute TTL.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from config import CACHE_TTL
from database import get_db
from models import User
from schemas import TopicSchema, TrendingResponse
from services.news_aggregator import get_trending_topics
from utils.cache import cache

router = APIRouter()

_VALID_WINDOWS = frozenset({"1h", "6h", "24h", "7d"})


@router.get("/trending", response_model=TrendingResponse, tags=["trending"])
def get_trending(
    window: str = Query("24h", description="Rolling time window: 1h | 6h | 24h | 7d"),
    category: Optional[str] = Query(None, description="Limit to a specific category"),
    country: Optional[str] = Query(None, description="Country-specific trends"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TrendingResponse:
    if window not in _VALID_WINDOWS:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": "parameterInvalid",
                "message": f"window must be one of: {', '.join(sorted(_VALID_WINDOWS))}",
            },
        )

    cache_key = cache.make_key("trending", window=window, category=category, country=country)
    if (cached := cache.get(cache_key)) is not None:
        return cached

    topics_data = get_trending_topics(db, window=window, category=category, country=country)
    response = TrendingResponse(
        window=window,
        topics=[TopicSchema(**t) for t in topics_data],
    )

    cache.set(cache_key, response, CACHE_TTL["trending"])
    return response
