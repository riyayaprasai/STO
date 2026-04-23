"""
GET /api/research/{symbol}  — Unified stock research endpoint

Returns a combined response with:
  - News articles (triggers live fetch if cache is stale)
  - SEC filings
  - Market data (yfinance)
  - Reddit social mentions
  - Congressional trades
"""
import logging
import asyncio

import httpx
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services.ticker_news import get_or_fetch, TICKER_NAMES
from services.sec_service import get_filings
from services.market_data import get_market_data
from services.social_service import get_reddit_mentions, get_stocktwits_mentions
from services.congress_service import get_congress_trades

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/research/{symbol}")
async def stock_research(symbol: str, db: Session = Depends(get_db)):
    """
    Comprehensive stock research: fetches articles + SEC filings + market data
    + Reddit mentions + congressional trades. All in one response.
    """
    ticker = symbol.upper().strip()

    # Fetch ALL sources concurrently (market_data now runs via thread executor)
    articles_task = get_or_fetch(ticker, db)
    sec_task = get_filings(ticker)
    reddit_task = get_reddit_mentions(ticker)
    stocktwits_task = get_stocktwits_mentions(ticker)
    congress_task = get_congress_trades(ticker)
    market_task = get_market_data(ticker)

    results = await asyncio.gather(
        articles_task, sec_task, reddit_task, stocktwits_task, congress_task, market_task,
        return_exceptions=True,
    )

    articles = results[0] if not isinstance(results[0], Exception) else []
    sec_data = results[1] if not isinstance(results[1], Exception) else []
    reddit_posts = results[2] if not isinstance(results[2], Exception) else []
    stocktwits_posts = results[3] if not isinstance(results[3], Exception) else []
    congress_trades = results[4] if not isinstance(results[4], Exception) else []
    market_data = results[5] if not isinstance(results[5], Exception) else {"price": None, "change": 0.0, "change_percent": 0.0, "market_cap": None, "pe_ratio": None, "forward_pe": None, "dividend_yield": None, "volume": None, "avg_volume": None, "fifty_two_week_high": None, "fifty_two_week_low": None, "beta": None, "sector": None, "industry": None, "short_name": "", "description": None, "chart_data": []}

    if isinstance(results[0], Exception):
        logger.warning("research[%s]: article fetch failed: %s", ticker, results[0])
    if isinstance(results[1], Exception):
        logger.warning("research[%s]: SEC fetch failed: %s", ticker, results[1])
    if isinstance(results[2], Exception):
        logger.warning("research[%s]: Reddit fetch failed: %s", ticker, results[2])
    if isinstance(results[3], Exception):
        logger.warning("research[%s]: Stocktwits fetch failed: %s", ticker, results[3])
    if isinstance(results[4], Exception):
        logger.warning("research[%s]: Congress fetch failed: %s", ticker, results[4])
    if isinstance(results[5], Exception):
        logger.warning("research[%s]: Market data fetch failed: %s", ticker, results[5])

    # Format articles for JSON response
    formatted_articles = []
    for a in articles:
        formatted_articles.append({
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "url": a.url,
            "source": a.source_name,
            "category": a.category,
            "published_at": a.published_at.isoformat() if a.published_at else None,
        })

    total_articles = len(formatted_articles)
    total_filings = len(sec_data)

    return {
        "ticker": ticker,
        "company": TICKER_NAMES.get(ticker, market_data.get("short_name", ticker)),
        "market_data": market_data,

        # News articles
        "articles": formatted_articles,
        "total_articles": total_articles,

        # SEC filings
        "filings": sec_data,
        "total_filings": total_filings,

        # Social media
        "reddit_posts": reddit_posts,
        "total_reddit": len(reddit_posts),
        "stocktwits_posts": stocktwits_posts,
        "total_stocktwits": len(stocktwits_posts),

        # Congressional trades
        "congress_trades": congress_trades,
        "total_congress": len(congress_trades),

        # Data availability
        "data_sources": {
            "articles_available": total_articles > 0,
            "filings_available": total_filings > 0,
            "reddit_available": len(reddit_posts) > 0,
            "tweets_available": len(stocktwits_posts) > 0,
            "congress_available": len(congress_trades) > 0,
            "limited_data": total_articles < 5 and total_filings < 2,
        },
    }

@router.get("/search")
async def search_ticker(q: str = Query(..., min_length=1)):
    """
    Fuzzy search for a ticker symbol using Yahoo Finance.
    Example: 'apple' -> 'AAPL'
    """
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={q}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            quotes = data.get("quotes", [])
            
            # 1. Primary check: Exact Equity matches
            for quote in quotes:
                if quote.get("quoteType") == "EQUITY" and quote.get("symbol"):
                    # Avoid non-US symbols if possible, or just take the first
                    return {"symbol": quote.get("symbol"), "shortname": quote.get("shortname")}
            
            # 2. Secondary check: Any quote found
            if quotes:
                return {"symbol": quotes[0].get("symbol"), "shortname": quotes[0].get("shortname")}

            # 3. Fallback: Simplify query (e.g. "Spirit Airlines" -> "Spirit")
            words = q.strip().split()
            if len(words) > 1:
                # Try again with just the primary keyword
                return await search_ticker(words[0])

            # 4. Fallback: Parse 'news' related tickers (Great for news-heavy delisted/renamed stocks)
            news = data.get("news", [])
            ticker_counts = {}
            for item in news:
                for t in item.get("relatedTickers", []):
                    # Prioritize US tickers (usually no dots or just simple symbols)
                    weight = 2 if "." not in t else 1
                    ticker_counts[t] = ticker_counts.get(t, 0) + weight
            
            if ticker_counts:
                # Pick the most frequent/weighted ticker mentioned in news
                most_likely = max(ticker_counts, key=ticker_counts.get)
                return {"symbol": most_likely, "shortname": q}

            return {"symbol": None}
    except Exception as e:
        logger.warning(f"Search API failed for '{q}': {e}")
        return {"symbol": None}

@router.get("/chart/{symbol}")
async def get_chart_history(symbol: str, chart_range: str = Query("1mo", alias="range")):
    """
    Fetch historical chart data from Yahoo Finance.
    Supported ranges: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    """
    ticker = symbol.upper().strip()
    
    # Map range to a reasonable interval
    interval_map = {
        "1d": "5m",
        "5d": "15m",
        "1mo": "1d",
        "3mo": "1d",
        "6mo": "1d",
        "ytd": "1d",
        "1y": "1d",
        "2y": "1wk",
        "5y": "1wk",
        "10y": "1mo",
        "max": "1mo"
    }
    interval = interval_map.get(chart_range.lower(), "1d")
    
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={chart_range}&interval={interval}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            result = data.get("chart", {}).get("result", [])
            if not result:
                return {"chart_data": []}
                
            timestamps = result[0].get("timestamp", [])
            indicators = result[0].get("indicators", {}).get("quote", [{}])[0]
            closes = indicators.get("close", [])
            
            chart_data = []
            for i in range(len(timestamps)):
                if closes[i] is not None:
                    # Convert timestamp to ISO format string
                    import datetime
                    dt = datetime.datetime.fromtimestamp(timestamps[i], tz=datetime.timezone.utc)
                    chart_data.append({
                        "date": dt.isoformat(),
                        "price": round(closes[i], 2)
                    })
                    
            return {"chart_data": chart_data}
            
    except Exception as e:
        logger.warning(f"Chart API failed for '{ticker}': {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chart data")
