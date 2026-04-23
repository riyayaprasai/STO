"""
GET /v1/articles        – search articles with filtering and pagination
GET /v1/articles/{id}  – retrieve a single article with related stubs
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from config import CACHE_TTL
from database import get_db
from models import Article, User
from schemas import (
    ArticleDetailResponse,
    ArticleDetailSchema,
    ArticlesResponse,
    RelatedArticleStub,
)
from services.news_aggregator import refresh_articles, search_articles
from utils.cache import cache

from ._helpers import article_to_schema

router = APIRouter()


@router.get("/articles", response_model=ArticlesResponse, tags=["articles"])
async def get_articles(
    q: Optional[str] = Query(None, description="Full-text search against title and description"),
    sources: Optional[str] = Query(None, description="Comma-separated source IDs"),
    category: Optional[str] = Query(None, description="e.g. technology, business, health, sports, science, entertainment, general"),
    language: Optional[str] = Query(None, description="ISO 639-1 code, e.g. en"),
    country: Optional[str] = Query(None, description="ISO 3166-1 alpha-2 code, e.g. us"),
    from_: Optional[datetime] = Query(None, alias="from", description="Oldest article date (ISO 8601)"),
    to: Optional[datetime] = Query(None, description="Newest article date (ISO 8601)"),
    sort_by: str = Query("publishedAt", description="relevancy | publishedAt | popularity"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize", description="Results per page (max 100)"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ArticlesResponse:
    if from_ and from_ > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": "parameterInvalid",
                "message": "The `from` date cannot be in the future.",
            },
        )

    if sort_by not in ("relevancy", "publishedAt", "popularity"):
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "code": "parameterInvalid",
                "message": "sortBy must be one of: relevancy, publishedAt, popularity",
            },
        )

    cache_key = cache.make_key(
        "articles",
        q=q, sources=sources, category=category, language=language,
        country=country, from_=str(from_), to=str(to), sort_by=sort_by,
        page=page, page_size=page_size, tier=user.tier,
    )
    if (cached := cache.get(cache_key)) is not None:
        return cached

    # Bootstrap the article DB on first request if empty
    if db.query(Article).count() < 10:
        await refresh_articles(db)

    result = search_articles(
        db,
        q=q, sources=sources, category=category, language=language,
        country=country, from_dt=from_, to_dt=to, sort_by=sort_by,
        page=page, page_size=page_size, user_tier=user.tier,
    )

    response = ArticlesResponse(
        total_results=result["total"],
        page=page,
        page_size=page_size,
        articles=[article_to_schema(a) for a in result["articles"]],
    )

    cache.set(cache_key, response, CACHE_TTL["articles"])
    return response


@router.get("/articles/{article_id}", response_model=ArticleDetailResponse, tags=["articles"])
async def get_article(
    article_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ArticleDetailResponse:
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "code": "articleNotFound",
                "message": f"No article found with id '{article_id}'.",
            },
        )

    related_rows = (
        db.query(Article)
        .filter(Article.category == article.category, Article.id != article_id)
        .order_by(Article.published_at.desc())
        .limit(5)
        .all()
    )
    related = [
        RelatedArticleStub(id=a.id, title=a.title, url=a.url, published_at=a.published_at)
        for a in related_rows
    ]

    detail = ArticleDetailSchema(
        **article_to_schema(article).model_dump(),
        related_articles=related,
    )

    return ArticleDetailResponse(article=detail)
