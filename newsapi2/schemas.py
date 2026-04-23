from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional, List


# ── User ─────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    pass


class AdminUserCreate(UserBase):
    tier: str = "free"  # free | developer | business | enterprise


class UserTierUpdate(BaseModel):
    tier: str  # free | developer | business | enterprise


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    api_key: str
    tier: str
    created_at: datetime


# ── Source ───────────────────────────────────────────────────────────────────

class SourceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    url: str
    category: str
    language: str
    country: str


class SourcesResponse(BaseModel):
    status: str = "ok"
    sources: List[SourceSchema]


# ── Article ──────────────────────────────────────────────────────────────────

class ArticleSourceRef(BaseModel):
    id: str
    name: str


class RelatedArticleStub(BaseModel):
    id: str
    title: str
    url: str
    published_at: datetime


class ArticleSchema(BaseModel):
    id: str
    source: ArticleSourceRef
    author: Optional[str] = None
    title: str
    description: Optional[str] = None
    url: str
    url_to_image: Optional[str] = None
    published_at: datetime
    category: Optional[str] = None
    language: str
    country: Optional[str] = None
    sentiment: str


class ArticleDetailSchema(ArticleSchema):
    related_articles: List[RelatedArticleStub] = []


class ArticlesResponse(BaseModel):
    status: str = "ok"
    total_results: int
    page: int
    page_size: int
    articles: List[ArticleSchema]


class ArticleDetailResponse(BaseModel):
    status: str = "ok"
    article: ArticleDetailSchema


# ── Headlines ────────────────────────────────────────────────────────────────

class HeadlinesResponse(BaseModel):
    status: str = "ok"
    total_results: int
    page: int
    page_size: int
    articles: List[ArticleSchema]


# ── Trending ─────────────────────────────────────────────────────────────────

class TopicSchema(BaseModel):
    term: str
    count: int
    trend: str  # rising | stable | declining


class TrendingResponse(BaseModel):
    status: str = "ok"
    window: str
    topics: List[TopicSchema]


# ── Error ────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    status: str = "error"
    code: str
    message: str
