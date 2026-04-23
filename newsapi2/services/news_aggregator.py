"""
News aggregation service.

Responsibilities:
  - Seed the ``sources`` table with curated RSS sources on first run.
  - Fetch articles from RSS feeds concurrently, run sentiment analysis,
    and persist them with URL-based deduplication.
  - Provide search / filter / pagination helpers used by the v1 routers.
  - Compute trending topics from recent article titles.
"""
import asyncio
import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import aiohttp
from sqlalchemy import or_
from sqlalchemy.orm import Session

from config import TIER_HISTORY_DAYS
from models import Article, Source
from services.sentiment import analyze_sentiment
from utils.id_generator import generate_article_id

logger = logging.getLogger(__name__)

# ── Curated source catalogue ─────────────────────────────────────────────────

DEFAULT_SOURCES: list[dict] = [
    # General
    {
        "id": "bbc-news",
        "name": "BBC News",
        "description": "Up-to-the-minute news, breaking news, video, audio and feature stories.",
        "url": "https://www.bbc.co.uk/news",
        "rss_url": "https://feeds.bbci.co.uk/news/rss.xml",
        "category": "general",
        "language": "en",
        "country": "gb",
    },
    {
        "id": "reuters",
        "name": "Reuters",
        "description": "Reuters.com brings you the latest news from around the world.",
        "url": "https://www.reuters.com",
        "rss_url": "https://feeds.reuters.com/reuters/topNews",
        "category": "general",
        "language": "en",
        "country": "us",
    },
    {
        "id": "google-news-top",
        "name": "Google News – Top Stories",
        "description": "Top stories aggregated by Google News.",
        "url": "https://news.google.com",
        "rss_url": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
        "category": "general",
        "language": "en",
        "country": "us",
    },
    {
        "id": "google-news-business",
        "name": "Google News – Business",
        "description": "Business news aggregated by Google News.",
        "url": "https://news.google.com",
        "rss_url": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
        "category": "business",
        "language": "en",
        "country": "us",
    },
    {
        "id": "google-news-tech",
        "name": "Google News – Technology",
        "description": "Technology news aggregated by Google News.",
        "url": "https://news.google.com",
        "rss_url": "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en",
        "category": "technology",
        "language": "en",
        "country": "us",
    },
    {
        "id": "npr-news",
        "name": "NPR News",
        "description": "National Public Radio delivers breaking national and world news.",
        "url": "https://www.npr.org",
        "rss_url": "https://feeds.npr.org/1001/rss.xml",
        "category": "general",
        "language": "en",
        "country": "us",
    },
    {
        "id": "al-jazeera",
        "name": "Al Jazeera English",
        "description": "News, analysis from the Middle East and worldwide.",
        "url": "https://www.aljazeera.com",
        "rss_url": "https://www.aljazeera.com/xml/rss/all.xml",
        "category": "general",
        "language": "en",
        "country": "qa",
    },
    # Technology
    {
        "id": "techcrunch",
        "name": "TechCrunch",
        "description": "TechCrunch is a leading technology media property.",
        "url": "https://techcrunch.com",
        "rss_url": "https://techcrunch.com/feed/",
        "category": "technology",
        "language": "en",
        "country": "us",
    },
    {
        "id": "the-verge",
        "name": "The Verge",
        "description": "Tech, science, art, and culture.",
        "url": "https://www.theverge.com",
        "rss_url": "https://www.theverge.com/rss/index.xml",
        "category": "technology",
        "language": "en",
        "country": "us",
    },
    {
        "id": "ars-technica",
        "name": "Ars Technica",
        "description": "Technology news, analysis, and product reviews.",
        "url": "https://arstechnica.com",
        "rss_url": "https://feeds.arstechnica.com/arstechnica/index",
        "category": "technology",
        "language": "en",
        "country": "us",
    },
    {
        "id": "wired",
        "name": "Wired",
        "description": "In-depth coverage of tech, science, health, and business.",
        "url": "https://www.wired.com",
        "rss_url": "https://www.wired.com/feed/rss",
        "category": "technology",
        "language": "en",
        "country": "us",
    },
    {
        "id": "engadget",
        "name": "Engadget",
        "description": "Technology news, reviews and features.",
        "url": "https://www.engadget.com",
        "rss_url": "https://www.engadget.com/rss.xml",
        "category": "technology",
        "language": "en",
        "country": "us",
    },
    # Business
    {
        "id": "forbes-business",
        "name": "Forbes Business",
        "description": "Business news and financial information from Forbes.",
        "url": "https://www.forbes.com/business",
        "rss_url": "https://www.forbes.com/business/feed/",
        "category": "business",
        "language": "en",
        "country": "us",
    },
    {
        "id": "marketwatch",
        "name": "MarketWatch",
        "description": "Stock market news, financial news, business news.",
        "url": "https://www.marketwatch.com",
        "rss_url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        "category": "business",
        "language": "en",
        "country": "us",
    },
    # Sports
    {
        "id": "espn",
        "name": "ESPN",
        "description": "Sports news, scores, and highlights.",
        "url": "https://www.espn.com",
        "rss_url": "https://www.espn.com/espn/rss/news",
        "category": "sports",
        "language": "en",
        "country": "us",
    },
    {
        "id": "bbc-sport",
        "name": "BBC Sport",
        "description": "Sports news and results from BBC Sport.",
        "url": "https://www.bbc.co.uk/sport",
        "rss_url": "http://feeds.bbci.co.uk/sport/rss.xml",
        "category": "sports",
        "language": "en",
        "country": "gb",
    },
    # Science
    {
        "id": "science-daily",
        "name": "Science Daily",
        "description": "Latest scientific research and discoveries.",
        "url": "https://www.sciencedaily.com",
        "rss_url": "https://www.sciencedaily.com/rss/all.xml",
        "category": "science",
        "language": "en",
        "country": "us",
    },
    {
        "id": "nasa",
        "name": "NASA",
        "description": "Breaking news from NASA.",
        "url": "https://www.nasa.gov",
        "rss_url": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "category": "science",
        "language": "en",
        "country": "us",
    },
    # Entertainment
    {
        "id": "variety",
        "name": "Variety",
        "description": "Entertainment news, film and TV reviews.",
        "url": "https://variety.com",
        "rss_url": "https://variety.com/feed/",
        "category": "entertainment",
        "language": "en",
        "country": "us",
    },
    # Health
    {
        "id": "who-news",
        "name": "WHO News",
        "description": "World Health Organization news releases.",
        "url": "https://www.who.int",
        "rss_url": "https://www.who.int/rss-feeds/news-english.xml",
        "category": "health",
        "language": "en",
        "country": "ch",
    },
]

# Build a lookup dict for quick rss_url access
_SOURCE_RSS: dict[str, str] = {
    s["id"]: s["rss_url"] for s in DEFAULT_SOURCES if s.get("rss_url")
}


# ── Database seeding ─────────────────────────────────────────────────────────

def seed_sources(db: Session) -> None:
    """Insert default sources into the database; update rss_url if it changed."""
    for src in DEFAULT_SOURCES:
        existing = db.query(Source).filter(Source.id == src["id"]).first()
        if existing:
            # Patch the RSS URL in case it was updated in code
            if existing.rss_url != src.get("rss_url"):
                existing.rss_url = src.get("rss_url")
            continue
        db.add(Source(
            id=src["id"],
            name=src["name"],
            description=src.get("description"),
            url=src["url"],
            rss_url=src.get("rss_url"),
            category=src["category"],
            language=src["language"],
            country=src["country"],
        ))
    db.commit()


# ── RSS fetching ─────────────────────────────────────────────────────────────

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; NewsAggregator/1.0; +https://newsapi.example.com)"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}
_STRIP_HTML = re.compile(r"<[^>]+>")


async def _fetch_text(session: aiohttp.ClientSession, url: str) -> str:
    # Upgrade http:// feeds to https:// to avoid redirect loops
    safe_url = url.replace("http://", "https://", 1) if url.startswith("http://") else url
    try:
        async with session.get(
            safe_url,
            headers=_HEADERS,
            timeout=aiohttp.ClientTimeout(total=15),
            allow_redirects=True,
            ssl=False,          # some feeds have self-signed / expired certs
        ) as resp:
            if resp.status >= 400:
                logger.warning("RSS fetch HTTP %s for %s", resp.status, safe_url)
                return ""
            return await resp.text(errors="replace")
    except Exception as exc:
        logger.warning("RSS fetch failed for %s: %s", safe_url, exc)
        return ""


def _parse_published(pub_str: str | None) -> datetime:
    """Best-effort parse of an RSS pubDate string; falls back to now."""
    if pub_str:
        try:
            dt = parsedate_to_datetime(pub_str.strip())
            return dt.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return datetime.now(timezone.utc)


def _text(el: ET.Element | None) -> str:
    """Return stripped text content of an XML element, or ''."""
    if el is None:
        return ""
    return (el.text or "").strip()


def _parse_rss_xml(xml_text: str, source: Source) -> list[dict]:
    """
    Parse an RSS 2.0 / Atom feed using stdlib xml.etree and return a list of
    normalised article dicts (no sentiment yet).
    """
    results: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return results

    # RSS 2.0: <rss><channel><item>…
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = root.findall(".//item") or root.findall(".//atom:entry", ns)

    for item in items[:20]:
        # Title
        title = _text(item.find("title") or item.find("atom:title", ns))
        if not title:
            continue

        # Link
        url = _text(item.find("link") or item.find("atom:link", ns))
        # Atom <link href="…"/> case
        if not url:
            link_el = item.find("atom:link", ns)
            if link_el is not None:
                url = link_el.get("href", "")
        if not url:
            continue

        # Published date
        pub_el = (
            item.find("pubDate")
            or item.find("atom:published", ns)
            or item.find("atom:updated", ns)
        )
        published_at = _parse_published(_text(pub_el))

        # Description / summary
        desc_el = item.find("description") or item.find("atom:summary", ns)
        raw_desc = _text(desc_el)
        description = _STRIP_HTML.sub("", raw_desc).strip()
        description = description[:500] if description else None

        # Author
        author_el = item.find("author") or item.find("atom:author/atom:name", ns)
        author = _text(author_el) or None

        url_hash = hashlib.md5(url.encode()).hexdigest()

        results.append({
            "id": generate_article_id(),
            "source_id": source.id,
            "source_name": source.name,
            "author": author,
            "title": title,
            "description": description,
            "url": url,
            "published_at": published_at,
            "category": source.category,
            "language": source.language,
            "country": source.country,
            "content_hash": url_hash,
        })

    return results


async def refresh_articles(db: Session, source_ids: list[str] | None = None) -> int:
    """
    Fetch fresh articles from all active RSS sources and persist new ones.

    Returns the count of newly inserted articles.
    """
    query = db.query(Source).filter(Source.is_active.is_(True), Source.rss_url.isnot(None))
    if source_ids:
        query = query.filter(Source.id.in_(source_ids))
    sources: list[Source] = query.all()

    if not sources:
        logger.warning("refresh_articles: no active sources found")
        return 0

    new_count = 0
    failed_feeds = 0

    try:
        async with aiohttp.ClientSession() as session:
            texts = await asyncio.gather(
                *[_fetch_text(session, s.rss_url) for s in sources],
                return_exceptions=True,
            )
    except Exception as exc:
        logger.error("refresh_articles: aiohttp session failed: %s", exc)
        return 0

    for source, text in zip(sources, texts):
        if isinstance(text, Exception):
            logger.warning("refresh_articles: feed %s raised %s: %s",
                           source.id, type(text).__name__, text)
            failed_feeds += 1
            continue
        if not text:
            logger.warning("refresh_articles: feed %s returned empty response", source.id)
            failed_feeds += 1
            continue

        entries = _parse_rss_xml(text, source)
        if not entries:
            logger.debug("refresh_articles: feed %s parsed to 0 entries", source.id)

        for data in entries:
            if db.query(Article).filter(Article.content_hash == data["content_hash"]).first():
                continue

            # Wrap sentiment in try/except so one bad article never kills the whole batch
            try:
                sentiment_result = await analyze_sentiment(data["title"])
                data["sentiment"] = sentiment_result["sentiment"]["category"]
            except Exception as exc:
                logger.warning("refresh_articles: sentiment failed for '%s': %s",
                               data["title"][:60], exc)
                data["sentiment"] = "neutral"

            db.add(Article(**data))
            new_count += 1

    try:
        db.commit()
    except Exception as exc:
        logger.error("refresh_articles: DB commit failed: %s", exc)
        db.rollback()
        return 0

    logger.info(
        "refresh_articles: added %d new articles (%d/%d feeds ok)",
        new_count, len(sources) - failed_feeds, len(sources),
    )
    return new_count


# ── Article search ───────────────────────────────────────────────────────────

def search_articles(
    db: Session,
    *,
    q: Optional[str] = None,
    sources: Optional[str] = None,
    category: Optional[str] = None,
    language: Optional[str] = None,
    country: Optional[str] = None,
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
    sort_by: str = "publishedAt",
    page: int = 1,
    page_size: int = 20,
    user_tier: str = "free",
) -> dict:
    query = db.query(Article)

    if q:
        query = query.filter(
            or_(Article.title.ilike(f"%{q}%"), Article.description.ilike(f"%{q}%"))
        )
    if sources:
        ids = [s.strip() for s in sources.split(",") if s.strip()]
        query = query.filter(Article.source_id.in_(ids))
    if category:
        query = query.filter(Article.category == category)
    if language:
        query = query.filter(Article.language == language)
    if country:
        query = query.filter(Article.country == country)

    # Enforce historical access window per tier
    history_days = TIER_HISTORY_DAYS.get(user_tier)
    if history_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=history_days)
        if from_dt is None or from_dt < cutoff:
            from_dt = cutoff

    if from_dt:
        query = query.filter(Article.published_at >= from_dt)
    if to_dt:
        query = query.filter(Article.published_at <= to_dt)

    total: int = query.count()

    if sort_by == "popularity":
        query = query.order_by(Article.popularity.desc(), Article.published_at.desc())
    else:
        query = query.order_by(Article.published_at.desc())

    offset = (page - 1) * page_size
    articles = query.offset(offset).limit(page_size).all()

    return {"total": total, "articles": articles}


# ── Headlines ────────────────────────────────────────────────────────────────

def get_headlines(
    db: Session,
    *,
    q: Optional[str] = None,
    sources: Optional[str] = None,
    category: Optional[str] = None,
    language: Optional[str] = None,
    country: Optional[str] = None,
    headlines_limit: int = 10,
    page: int = 1,
    page_size: int = 20,
    user_tier: str = "free",
) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    return search_articles(
        db,
        q=q,
        sources=sources,
        category=category,
        language=language,
        country=country,
        from_dt=cutoff,
        sort_by="publishedAt",
        page=page,
        page_size=min(page_size, headlines_limit),
        user_tier=user_tier,
    )


# ── Trending topics ──────────────────────────────────────────────────────────

_STOP_WORDS = frozenset({
    "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or",
    "but", "is", "are", "was", "were", "be", "been", "has", "have", "had",
    "it", "its", "by", "with", "from", "as", "this", "that", "not", "can",
    "will", "would", "could", "should", "may", "might", "do", "does", "did",
    "up", "out", "about", "over", "after", "into", "no", "new", "more",
    "than", "their", "they", "we", "he", "she", "i", "you", "said", "says",
    "say", "us", "all", "so", "if", "just", "also", "get", "s", "re",
    "after", "before", "amid", "report", "reports", "says", "say", "amid",
})


def _extract_phrases(articles: list[Article]) -> Counter:
    counts: Counter = Counter()
    for art in articles:
        words = re.findall(r"\b[A-Za-z][A-Za-z]{2,}\b", art.title)
        clean = [w for w in words if w.lower() not in _STOP_WORDS]

        # Bigrams (lower-cased)
        for i in range(len(clean) - 1):
            counts[f"{clean[i].lower()} {clean[i + 1].lower()}"] += 1

        # Proper nouns (capitalised words > 4 chars)
        for w in words:
            if w[0].isupper() and w.lower() not in _STOP_WORDS and len(w) > 4:
                counts[w] += 1

    return counts


def get_trending_topics(
    db: Session,
    *,
    window: str = "24h",
    category: Optional[str] = None,
    country: Optional[str] = None,
) -> list[dict]:
    hours = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}.get(window, 24)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    prev_cutoff = cutoff - timedelta(hours=hours)

    def _query(from_dt: datetime, to_dt: datetime) -> list[Article]:
        q = db.query(Article).filter(
            Article.published_at >= from_dt,
            Article.published_at < to_dt,
        )
        if category:
            q = q.filter(Article.category == category)
        if country:
            q = q.filter(Article.country == country)
        return q.all()

    current = _extract_phrases(_query(cutoff, now))
    previous = _extract_phrases(_query(prev_cutoff, cutoff))

    topics: list[dict] = []
    for term, count in current.most_common(20):
        prev_count = previous.get(term, 0)
        if prev_count == 0 or count > prev_count * 1.2:
            trend = "rising"
        elif count < prev_count * 0.8:
            trend = "declining"
        else:
            trend = "stable"
        topics.append({"term": term, "count": count, "trend": trend})

    return topics[:10]
