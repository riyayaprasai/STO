"""
GET /v1/sources – list available news sources with optional filtering.

Results are cached with a 1-hour TTL.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from config import CACHE_TTL
from database import get_db
from models import Source, User
from schemas import SourceSchema, SourcesResponse
from utils.cache import cache

router = APIRouter()


@router.get("/sources", response_model=SourcesResponse, tags=["sources"])
def get_sources(
    category: Optional[str] = Query(None, description="Filter by category"),
    language: Optional[str] = Query(None, description="Filter by ISO 639-1 language code"),
    country: Optional[str] = Query(None, description="Filter by ISO 3166-1 alpha-2 country code"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SourcesResponse:
    cache_key = cache.make_key("sources", category=category, language=language, country=country)
    if (cached := cache.get(cache_key)) is not None:
        return cached

    query = db.query(Source).filter(Source.is_active.is_(True))
    if category:
        query = query.filter(Source.category == category)
    if language:
        query = query.filter(Source.language == language)
    if country:
        query = query.filter(Source.country == country)

    sources = query.order_by(Source.name).all()
    response = SourcesResponse(
        sources=[SourceSchema.model_validate(s) for s in sources]
    )

    cache.set(cache_key, response, CACHE_TTL["sources"])
    return response
