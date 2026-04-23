"""
On-demand ticker-specific news fetching.

When a user searches for a stock (AAPL, TSLA, …) we pull fresh articles from
multiple free sources to guarantee 20+ results:

  1. Yahoo Finance RSS      — https://feeds.finance.yahoo.com/rss/2.0/headline?s={TICKER}
  2. Google News search      — Multiple search queries (ticker, company name, etc.)
  3. Google News site: feeds — site-specific searches for Reuters, CNBC, MarketWatch,
                               Seeking Alpha, Bloomberg, WSJ, Investopedia, Barrons
  4. Bing News RSS           — https://www.bing.com/news/search?q={TICKER}+stock&format=rss

Articles are stored in the articles table so they're available for
sentiment analysis, search, and trending — exactly like the general RSS feeds.
We re-fetch only when the last fetch for that ticker was > CACHE_MINUTES ago.
"""
import asyncio
import hashlib
import html
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Optional
from urllib.parse import quote_plus

import aiohttp
from sqlalchemy.orm import Session

from models import Article, Source
from utils.id_generator import generate_article_id

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────

CACHE_MINUTES = 15          # Don't re-fetch a ticker more often than this
MAX_ARTICLES_PER_FETCH = 30  # Per-feed cap (increased from 20)
MIN_DESIRED_ARTICLES = 20   # Target minimum articles per ticker search

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# ── Ticker → Company name mapping ─────────────────────────────────────────────
# Used to build better search queries ("Apple AAPL stock" catches more articles).

TICKER_NAMES: dict[str, str] = {
    "AAPL":  "Apple",
    "GOOGL": "Alphabet Google",
    "GOOG":  "Alphabet Google",
    "MSFT":  "Microsoft",
    "AMZN":  "Amazon",
    "TSLA":  "Tesla",
    "META":  "Meta Facebook",
    "NVDA":  "NVIDIA",
    "GME":   "GameStop",
    "AMC":   "AMC Entertainment",
    "NFLX":  "Netflix",
    "HOOD":  "Robinhood",
    "COIN":  "Coinbase",
    "SNAP":  "Snapchat Snap",
    "UBER":  "Uber",
    "LYFT":  "Lyft",
    "BABA":  "Alibaba",
    "PLTR":  "Palantir",
    "RIVN":  "Rivian",
    "LCID":  "Lucid Motors",
    "NIO":   "NIO Electric",
    "INTC":  "Intel",
    "AMD":   "AMD Advanced Micro Devices",
    "QCOM":  "Qualcomm",
    "ORCL":  "Oracle",
    "CRM":   "Salesforce",
    "SHOP":  "Shopify",
    "SQ":    "Block Square Cash App",
    "PYPL":  "PayPal",
    "V":     "Visa",
    "MA":    "Mastercard",
    "JPM":   "JPMorgan Chase",
    "BAC":   "Bank of America",
    "GS":    "Goldman Sachs",
    "WMT":   "Walmart",
    "DIS":   "Disney",
    "BA":    "Boeing",
    "F":     "Ford Motor",
    "GM":    "General Motors",
    "T":     "AT&T",
    "VZ":    "Verizon",
    "XOM":   "ExxonMobil",
    "CVX":   "Chevron",
    "PFE":   "Pfizer",
    "MRNA":  "Moderna",
    "JNJ":   "Johnson Johnson",
    "KO":    "Coca-Cola",
    "PEP":   "PepsiCo",
    "MCD":   "McDonald's",
    "SBUX":  "Starbucks",
    "NKLA":  "Nikola",
    "SPOT":  "Spotify",
    "ABNB":  "Airbnb",
    "RBLX":  "Roblox",
    "U":     "Unity Software",
    "DKNG":  "DraftKings",
    "SOFI":  "SoFi Technologies",
    "OPEN":  "Opendoor",
    "SPCE":  "Virgin Galactic",
    "ROKU":  "Roku",
    "TWLO":  "Twilio",
    "ZM":    "Zoom Video",
    "DOCU":  "DocuSign",
    "SNOW":  "Snowflake",
    "CRWD":  "CrowdStrike",
    "ZS":    "Zscaler",
    "NET":   "Cloudflare",
    "DDOG":  "Datadog",
    "MDB":   "MongoDB",
    "OKTA":  "Okta",
}

_STRIP_HTML = re.compile(r"<[^>]+>")

# Financial news source domains for Google News site: operator
_FINANCIAL_SOURCES = [
    ("reuters.com", "Reuters"),
    ("cnbc.com", "CNBC"),
    ("marketwatch.com", "MarketWatch"),
    ("seekingalpha.com", "Seeking Alpha"),
    ("bloomberg.com", "Bloomberg"),
    ("wsj.com", "Wall Street Journal"),
    ("investopedia.com", "Investopedia"),
    ("barrons.com", "Barron's"),
]


def _source_id_for(ticker: str) -> str:
    return f"ticker-{ticker.lower()}"


def _clean(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    text = html.unescape(text)
    return _STRIP_HTML.sub("", text).strip()[:500] or None


def _parse_pub_date(pub_str: Optional[str]) -> datetime:
    if pub_str:
        try:
            dt = parsedate_to_datetime(pub_str.strip())
            return dt.astimezone(timezone.utc).replace(tzinfo=None)  # store naive UTC
        except Exception:
            pass
    return datetime.utcnow()


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _ensure_source(ticker: str, db: Session) -> Source:
    """Create a Source row for this ticker if it doesn't exist yet."""
    sid = _source_id_for(ticker)
    src = db.query(Source).filter(Source.id == sid).first()
    if not src:
        company = TICKER_NAMES.get(ticker, ticker)
        src = Source(
            id=sid,
            name=f"{ticker} News",
            description=f"Live news feed for {company} ({ticker})",
            url=f"https://finance.yahoo.com/quote/{ticker}",
            rss_url=None,
            category="business",
            language="en",
            country="us",
            is_active=False,  # not part of the general background refresh
        )
        db.add(src)
        db.commit()
    return src


def _last_fetch_time(ticker: str, db: Session) -> Optional[datetime]:
    """Return when we last inserted an article for this ticker (UTC naive)."""
    sid = _source_id_for(ticker)
    latest = (
        db.query(Article.created_at)
        .filter(Article.source_id == sid)
        .order_by(Article.created_at.desc())
        .first()
    )
    return latest[0] if latest else None


import time

_rss_cooldown: dict[str, float] = {}

def _needs_refresh(ticker: str, db: Session) -> bool:
    # If we tried to fetch recently (even if it failed), wait 5 mins
    last_attempt = _rss_cooldown.get(ticker, 0)
    if time.time() - last_attempt < 300:  # 5 minutes block
        return False
        
    last = _last_fetch_time(ticker, db)
    if last is None:
        return True
    age = datetime.utcnow() - last
    return age.total_seconds() > CACHE_MINUTES * 60


# ── RSS fetching ───────────────────────────────────────────────────────────────

async def _fetch(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with session.get(
            url,
            headers=_HEADERS,
            timeout=aiohttp.ClientTimeout(total=12),
            allow_redirects=True,
            ssl=False,
        ) as resp:
            if resp.status >= 400:
                logger.warning("ticker_news: HTTP %s for %s", resp.status, url)
                return ""
            return await resp.text(errors="replace")
    except Exception as exc:
        logger.warning("ticker_news: fetch failed %s — %s", url, exc)
        return ""


def _rss_to_articles(xml_text: str, source: Source) -> list[dict]:
    """Parse RSS 2.0 / Atom XML into raw article dicts (no sentiment yet)."""
    results: list[dict] = []
    if not xml_text.strip():
        return results
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return results

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = root.findall(".//item") or root.findall(".//atom:entry", ns)

    for item in items[:MAX_ARTICLES_PER_FETCH]:
        title = _clean(
            (item.findtext("title") or item.findtext("atom:title", namespaces=ns) or "")
        )
        if not title:
            continue

        url = (
            item.findtext("link")
            or item.findtext("atom:link", namespaces=ns)
            or ""
        ).strip()
        if not url:
            link_el = item.find("atom:link", ns)
            if link_el is not None:
                url = link_el.get("href", "")
        if not url:
            continue

        pub_el = (
            item.find("pubDate")
            or item.find("atom:published", ns)
            or item.find("atom:updated", ns)
        )
        published_at = _parse_pub_date(pub_el.text if pub_el is not None else None)

        desc_raw = (
            item.findtext("description")
            or item.findtext("atom:summary", namespaces=ns)
            or ""
        )
        description = _clean(desc_raw)

        content_hash = hashlib.md5(url.encode()).hexdigest()

        results.append({
            "id": generate_article_id(),
            "source_id": source.id,
            "source_name": source.name,
            "author": None,
            "title": title,
            "description": description,
            "url": url,
            "published_at": published_at,
            "category": "business",
            "language": "en",
            "country": "us",
            "content_hash": content_hash,
        })

    return results


# ── Feed URL builders ──────────────────────────────────────────────────────────

def _build_feed_urls(ticker: str, company: str) -> list[str]:
    """
    Build a comprehensive list of RSS feed URLs for a given ticker.
    Uses multiple free sources to guarantee 20+ articles:
      1. Yahoo Finance RSS
      2. Google News — ticker search
      3. Google News — company name search
      4. Google News — site: operator for major financial news outlets
      5. Bing News RSS
      6. Google News — earnings/SEC/quarterly results searches
    """
    urls: list[str] = []

    # NOTE: Yahoo Finance RSS removed — it shares Yahoo's global rate limiter
    # and was causing 429 errors that cascaded across the entire app.
    # Google News + Bing News provide sufficient coverage.

    # 2. Google News — ticker search
    urls.append(
        f"https://news.google.com/rss/search"
        f"?q={quote_plus(ticker + ' stock')}&hl=en-US&gl=US&ceid=US:en"
    )

    # 3. Google News — company name search
    urls.append(
        f"https://news.google.com/rss/search"
        f"?q={quote_plus(company + ' stock market')}&hl=en-US&gl=US&ceid=US:en"
    )

    # 4. Google News — earnings / financial results search
    urls.append(
        f"https://news.google.com/rss/search"
        f"?q={quote_plus(ticker + ' earnings OR revenue OR quarterly')}&hl=en-US&gl=US&ceid=US:en"
    )

    # 5. Google News — SEC / filing news
    urls.append(
        f"https://news.google.com/rss/search"
        f"?q={quote_plus(ticker + ' SEC filing OR 10-K OR 10-Q OR annual report')}&hl=en-US&gl=US&ceid=US:en"
    )

    # 6. Google News site: operator — pull from specific financial news sites
    for domain, _display_name in _FINANCIAL_SOURCES:
        urls.append(
            f"https://news.google.com/rss/search"
            f"?q={quote_plus(ticker + ' site:' + domain)}&hl=en-US&gl=US&ceid=US:en"
        )

    # 7. Bing News RSS — good fallback, different index than Google
    urls.append(
        f"https://www.bing.com/news/search"
        f"?q={quote_plus(ticker + ' stock')}&format=rss"
    )

    # 8. Bing News — company name search
    urls.append(
        f"https://www.bing.com/news/search"
        f"?q={quote_plus(company + ' stock')}&format=rss"
    )

    return urls


# ── Public API ─────────────────────────────────────────────────────────────────

async def fetch_and_store(ticker: str, db: Session) -> int:
    """
    Pull fresh articles for `ticker` from multiple free news sources,
    run sentiment analysis, store in DB.  Returns count of NEW articles added.
    """
    ticker = ticker.upper().strip()
    company = TICKER_NAMES.get(ticker, ticker)
    source = _ensure_source(ticker, db)

    feed_urls = _build_feed_urls(ticker, company)

    new_count = 0

    async with aiohttp.ClientSession() as session:
        texts = await asyncio.gather(
            *[_fetch(session, u) for u in feed_urls],
            return_exceptions=True,
        )

    all_entries: list[dict] = []
    for text in texts:
        if isinstance(text, Exception) or not text:
            continue
        all_entries.extend(_rss_to_articles(text, source))

    # Dedup within this batch by content_hash
    seen: set[str] = set()
    unique = []
    for entry in all_entries:
        if entry["content_hash"] not in seen:
            seen.add(entry["content_hash"])
            unique.append(entry)

    for data in unique:
        if db.query(Article).filter(Article.content_hash == data["content_hash"]).first():
            continue
        db.add(Article(**data))
        new_count += 1

    if new_count > 0:
        db.commit()

    logger.info("ticker_news[%s]: +%d articles stored (from %d feeds, %d unique parsed)",
                ticker, new_count, len(feed_urls), len(unique))
    return new_count


async def get_or_fetch(ticker: str, db: Session) -> list[Article]:
    """
    Return DB articles for `ticker`.  Triggers a fresh fetch first if the
    cache is stale (>CACHE_MINUTES old or empty).
    """
    ticker = ticker.upper().strip()
    sid = _source_id_for(ticker)

    if _needs_refresh(ticker, db):
        _rss_cooldown[ticker] = time.time()
        await fetch_and_store(ticker, db)

    articles = (
        db.query(Article)
        .filter(Article.source_id == sid)
        .order_by(Article.published_at.desc())
        .limit(50)  # return up to 50 articles
        .all()
    )
    return articles
