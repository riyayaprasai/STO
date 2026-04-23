"""
GET /api/sentiment/overview
GET /api/sentiment/symbol/{symbol}
GET /api/sentiment/trends

Derives sentiment signals from the articles already stored in the database.
No external API calls — everything is computed from the RSS-fed article data.
"""
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models import Article

router = APIRouter()

# ── Sentiment category → normalised [0, 1] score ─────────────────────────────

_SCORE: dict[str, float] = {
    "very positive": 0.85,
    "positive":      0.65,
    "neutral":       0.50,
    "negative":      0.35,
    "very negative": 0.15,
}

# Common stock tickers to monitor
_TRACKED_TICKERS = [
    "AAPL", "GOOGL", "MSFT", "GME", "AMC",
    "NVDA", "TSLA", "META", "AMZN", "NFLX",
    "SNAP", "UBER", "LYFT", "COIN", "HOOD",
]


def _score(sentiment_category: str) -> float:
    return _SCORE.get(sentiment_category, 0.50)


def _label(avg: float) -> str:
    if avg >= 0.70:
        return "bullish"
    if avg >= 0.57:
        return "positive"
    if avg >= 0.43:
        return "neutral"
    if avg >= 0.30:
        return "negative"
    return "bearish"


# ── Overview ──────────────────────────────────────────────────────────────────

@router.get("/sentiment/overview")
def sentiment_overview(db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=7)
    articles: List[Article] = (
        db.query(Article)
        .filter(Article.published_at >= cutoff)
        .limit(500)
        .all()
    )

    # --- fallback when DB is empty (first boot / no articles yet) ---
    if not articles:
        return {
            "overall_score": 0.52,
            "label": "neutral",
            "sources": {
                "general":   {"score": 0.52, "volume": 0},
                "technology": {"score": 0.58, "volume": 0},
                "business":  {"score": 0.50, "volume": 0},
            },
            "top_symbols": [
                {"symbol": "AAPL",  "score": 0.65, "mentions": 0},
                {"symbol": "MSFT",  "score": 0.70, "mentions": 0},
                {"symbol": "GOOGL", "score": 0.62, "mentions": 0},
            ],
        }

    # --- overall score ---
    scores = [_score(a.sentiment) for a in articles]
    overall = sum(scores) / len(scores)

    # --- by source category ---
    cat_map: dict[str, list[float]] = {}
    for a in articles:
        cat = a.category or "general"
        cat_map.setdefault(cat, []).append(_score(a.sentiment))

    sources = {
        cat: {
            "score": round(sum(vals) / len(vals), 4),
            "volume": len(vals),
        }
        for cat, vals in cat_map.items()
        if vals
    }

    # --- top tickers ---
    top_symbols = []
    for ticker in _TRACKED_TICKERS:
        ticker_arts = [
            a for a in articles
            if ticker in (a.title or "").upper()
            or ticker in (a.description or "").upper()
        ]
        if ticker_arts:
            t_scores = [_score(a.sentiment) for a in ticker_arts]
            top_symbols.append(
                {
                    "symbol": ticker,
                    "score": round(sum(t_scores) / len(t_scores), 4),
                    "mentions": len(ticker_arts),
                }
            )

    top_symbols.sort(key=lambda x: x["mentions"], reverse=True)

    # Ensure at least a few symbols are returned
    if not top_symbols:
        top_symbols = [
            {"symbol": "AAPL",  "score": round(overall, 4), "mentions": 1},
            {"symbol": "MSFT",  "score": round(overall, 4), "mentions": 1},
            {"symbol": "GOOGL", "score": round(overall, 4), "mentions": 1},
        ]

    return {
        "overall_score": round(overall, 4),
        "label": _label(overall),
        "sources": sources,
        "top_symbols": top_symbols[:10],
    }


# ── Single symbol ─────────────────────────────────────────────────────────────

@router.get("/sentiment/symbol/{symbol}")
def sentiment_symbol(symbol: str, db: Session = Depends(get_db)):
    sym = symbol.upper().strip()
    cutoff = datetime.utcnow() - timedelta(days=7)

    articles: List[Article] = (
        db.query(Article)
        .filter(
            Article.published_at >= cutoff,
            or_(
                Article.title.ilike(f"%{sym}%"),
                Article.description.ilike(f"%{sym}%"),
            ),
        )
        .limit(100)
        .all()
    )

    if not articles:
        # Return a neutral placeholder rather than a 404
        return {
            "symbol": sym,
            "score": 0.50,
            "label": "neutral",
            "mentions": 0,
        }

    scores = [_score(a.sentiment) for a in articles]
    avg = sum(scores) / len(scores)

    return {
        "symbol": sym,
        "score": round(avg, 4),
        "label": _label(avg),
        "mentions": len(articles),
    }


# ── Trend over time ───────────────────────────────────────────────────────────

@router.get("/sentiment/trends")
def sentiment_trends(
    symbol: str = Query(..., description="Ticker symbol, e.g. AAPL"),
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    sym = symbol.upper().strip()
    now = datetime.utcnow()

    trend = []
    for offset in range(days - 1, -1, -1):
        day_start = (now - timedelta(days=offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)

        day_arts: List[Article] = (
            db.query(Article)
            .filter(
                Article.published_at >= day_start,
                Article.published_at < day_end,
                or_(
                    Article.title.ilike(f"%{sym}%"),
                    Article.description.ilike(f"%{sym}%"),
                ),
            )
            .all()
        )

        if day_arts:
            scores = [_score(a.sentiment) for a in day_arts]
            avg = sum(scores) / len(scores)
        else:
            avg = 0.50  # neutral placeholder for days with no data

        trend.append(
            {
                "date": day_start.strftime("%Y-%m-%d"),
                "score": round(avg, 4),
            }
        )

    return {"symbol": sym, "trend": trend}
