"""Shared helpers for v1 routers."""
from models import Article
from schemas import ArticleSchema, ArticleSourceRef


def article_to_schema(art: Article) -> ArticleSchema:
    return ArticleSchema(
        id=art.id,
        source=ArticleSourceRef(id=art.source_id or "", name=art.source_name or ""),
        author=art.author,
        title=art.title,
        description=art.description,
        url=art.url,
        url_to_image=art.url_to_image,
        published_at=art.published_at,
        category=art.category,
        language=art.language or "en",
        country=art.country,
        sentiment=art.sentiment or "neutral",
    )
