"""
Social Media Service — Reddit Stock Mentions

Scrapes Reddit's public .json endpoints for stock ticker mentions
from r/wallstreetbets and r/stocks. Uses in-memory caching to avoid rate limits.
"""
import logging
import time
from typing import Dict, Any, List
import httpx
import asyncio
import urllib.request
import json

logger = logging.getLogger(__name__)

# ── Cache ──────────────────────────────────────────────────────────────────────
_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 300  # 5 minutes

SUBREDDITS = ["wallstreetbets", "stocks", "investing"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9"
}


async def get_reddit_mentions(ticker: str) -> List[Dict[str, Any]]:
    """
    Fetch recent Reddit posts mentioning the given ticker.
    Returns a list of post dicts with title, score, comments, subreddit, url, created.
    """
    cache_key = f"reddit:{ticker.upper()}"
    
    # Check cache
    if cache_key in _cache:
        entry = _cache[cache_key]
        if time.time() - entry["ts"] < CACHE_TTL:
            logger.debug(f"reddit cache hit for {ticker}")
            return entry["data"]

    all_posts = []
    
    for sub in SUBREDDITS:
        try:
            url = f"https://www.reddit.com/r/{sub}/search.json"
            params = {
                "q": ticker.upper(),
                "sort": "new",
                "restrict_sr": "on",
                "limit": "8",
                "t": "month"
            }
            
            async with httpx.AsyncClient(timeout=15.0, headers=HEADERS, follow_redirects=True) as client:
                resp = await client.get(url, params=params)
                
                if resp.status_code == 429:
                    logger.warning(f"reddit rate limited on r/{sub}")
                    continue
                if resp.status_code != 200:
                    logger.warning(f"reddit r/{sub} returned {resp.status_code}")
                    continue
                    
                data = resp.json()
                children = data.get("data", {}).get("children", [])
                
                for child in children:
                    post = child.get("data", {})
                    title = post.get("title", "")
                    
                    # Only include posts that actually mention the ticker  
                    if ticker.upper() not in title.upper():
                        # Check selftext too
                        if ticker.upper() not in (post.get("selftext", "") or "").upper():
                            continue
                    
                    all_posts.append({
                        "title": title[:200],
                        "score": post.get("score", 0),
                        "num_comments": post.get("num_comments", 0),
                        "subreddit": post.get("subreddit", sub),
                        "url": f"https://reddit.com{post.get('permalink', '')}",
                        "created_utc": post.get("created_utc", 0),
                        "upvote_ratio": post.get("upvote_ratio", 0.5),
                    })
            
            # Be polite — 1 second gap between subreddit requests
            import asyncio
            await asyncio.sleep(1.0)
            
        except Exception as e:
            logger.warning(f"reddit scrape failed for r/{sub} + {ticker}: {e}")
            continue

    # Sort by score (engagement) descending
    all_posts.sort(key=lambda x: x["score"], reverse=True)
    
    # Deduplicate by title
    seen_titles = set()
    unique_posts = []
    for p in all_posts:
        short = p["title"][:80].lower()
        if short not in seen_titles:
            seen_titles.add(short)
            unique_posts.append(p)

    result = unique_posts[:15]
    
    # Cache the result
    _cache[cache_key] = {"ts": time.time(), "data": result}
    
    return result

async def get_stocktwits_mentions(ticker: str) -> List[Dict[str, Any]]:
    """
    Fetch recent 'tweets' (messages) from StockTwits for the ticker.
    This effectively substitutes Twitter APIs with high precision for financial data.
    """
    cache_key = f"stocktwits:{ticker.upper()}"
    if cache_key in _cache:
        entry = _cache[cache_key]
        if time.time() - entry["ts"] < CACHE_TTL:
            return entry["data"]

    url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker.upper()}.json"
    
    def _fetch_stocktwits():
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        })
        try:
            with urllib.request.urlopen(req, timeout=10.0) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    return data.get("messages", [])
                else:
                    logger.warning(f"StockTwits got {response.status} for {ticker}")
                    return []
        except Exception as e:
            logger.warning(f"StockTwits urllib error for {ticker}: {e}")
            return []

    try:
        messages = await asyncio.to_thread(_fetch_stocktwits)
        if not messages:
            return []
            
        formatted_tweets = []
        for msg in messages[:15]:
            user = msg.get("user", {})
            formatted_tweets.append({
                "id": msg.get("id"),
                "created_at": msg.get("created_at"),
                "body": msg.get("body", ""),
                "username": user.get("username", ""),
                "avatar_url": user.get("avatar_url", ""),
                "sentiment": (msg.get("entities", {}).get("sentiment") or {}).get("basic", None)
            })
        
        _cache[cache_key] = {"ts": time.time(), "data": formatted_tweets}
        return formatted_tweets
        
    except Exception as e:
        logger.warning(f"StockTwits parser failed for {ticker}: {e}")
        
    return []
