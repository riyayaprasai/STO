"""
POST /api/chatbot/message

A rule-based chatbot that draws on live article data from the database
to answer sentiment / trading questions about the STO app.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app_auth_utils import get_optional_app_user
from database import get_db
from models import AppUser, Article

router = APIRouter()

_SCORE: dict[str, float] = {
    "very positive": 0.85,
    "positive":      0.65,
    "neutral":       0.50,
    "negative":      0.35,
    "very negative": 0.15,
}

_TICKERS = [
    "AAPL", "GOOGL", "MSFT", "GME", "AMC",
    "NVDA", "TSLA", "META", "AMZN", "NFLX",
    "SNAP", "UBER", "COIN", "HOOD",
]

# ── Schema ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


# ── Reply logic ───────────────────────────────────────────────────────────────

def _avg_score(articles: list[Article]) -> float:
    if not articles:
        return 0.50
    scores = [_SCORE.get(a.sentiment, 0.50) for a in articles]
    return sum(scores) / len(scores)


def _sentiment_label(avg: float) -> str:
    if avg >= 0.70:
        return "bullish"
    if avg >= 0.57:
        return "positive"
    if avg >= 0.43:
        return "neutral"
    if avg >= 0.30:
        return "negative"
    return "bearish"


def _generate_reply(message: str, db: Session) -> str:
    msg = message.strip()
    msg_lower = msg.lower()
    cutoff_7d = datetime.utcnow() - timedelta(days=7)
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)

    # ── Ticker lookup ──────────────────────────────────────────────────────────
    mentioned = next(
        (t for t in _TICKERS if t.lower() in msg_lower or t in msg.upper()),
        None,
    )

    if mentioned:
        arts: list[Article] = (
            db.query(Article)
            .filter(
                Article.published_at >= cutoff_7d,
                or_(
                    Article.title.ilike(f"%{mentioned}%"),
                    Article.description.ilike(f"%{mentioned}%"),
                ),
            )
            .order_by(Article.published_at.desc())
            .limit(50)
            .all()
        )
        if arts:
            avg = _avg_score(arts)
            pct = int(avg * 100)
            label = _sentiment_label(avg)
            snippet = arts[0].title[:90] + "…" if len(arts[0].title) > 90 else arts[0].title
            return (
                f"Based on {len(arts)} recent articles, **{mentioned}** sentiment is "
                f"**{label}** at {pct}%. "
                f'Latest headline: "{snippet}" — '
                f"Head to the Sentiment page for trend charts, or practice buying "
                f"{mentioned} on the Trading page."
            )
        return (
            f"I don't have recent news mentioning {mentioned} yet — "
            f"the RSS feed refreshes in the background. "
            f"Try checking the Sentiment page in a minute, or ask about another ticker."
        )

    # ── Overall market sentiment ───────────────────────────────────────────────
    if any(w in msg_lower for w in ["market", "overall", "general", "overview", "today"]):
        arts24h: list[Article] = (
            db.query(Article)
            .filter(Article.published_at >= cutoff_24h)
            .limit(200)
            .all()
        )
        if arts24h:
            avg = _avg_score(arts24h)
            pct = int(avg * 100)
            label = _sentiment_label(avg)
            return (
                f"Today's overall market sentiment from {len(arts24h)} recent articles "
                f"is **{label}** ({pct}%). "
                f"Open the Sentiment dashboard for a full breakdown by source and ticker."
            )
        return (
            "Market sentiment data is loading — the backend fetches news from multiple "
            "RSS sources in the background. Check back shortly or open the Sentiment page."
        )

    # ── Trending topics ────────────────────────────────────────────────────────
    if any(w in msg_lower for w in ["trend", "trending", "top", "popular", "mention", "hot"]):
        count = db.query(Article).filter(Article.published_at >= cutoff_24h).count()
        return (
            f"I'm tracking {count} articles published in the last 24 hours from sources "
            f"like BBC News, Reuters, TechCrunch, and more. "
            f"Visit the Sentiment page to see which tickers are being mentioned most and "
            f"whether their coverage is positive or negative."
        )

    # ── Trading / portfolio questions ──────────────────────────────────────────
    if any(w in msg_lower for w in ["trade", "trading", "buy", "sell", "portfolio", "practice", "stock", "invest"]):
        return (
            "The **Practice Trading** page gives you $100,000 in virtual money to "
            "simulate trades on AAPL, GOOGL, MSFT, GME, and AMC (plus more). "
            "Prices update every hour so they feel live — but no real cash is involved. "
            "Log in or sign up, then head to the Trading page to place your first order!"
        )

    # ── Sentiment concept questions ────────────────────────────────────────────
    if any(w in msg_lower for w in ["sentiment", "score", "bullish", "bearish", "mood", "feeling"]):
        return (
            "**Sentiment** measures how positive or negative recent news coverage is. "
            "STO uses TextBlob to score each article title and aggregates scores by "
            "source category and ticker. A score above 60% is positive/bullish; "
            "below 40% is negative/bearish; 40–60% is neutral. "
            "You can dig in by symbol on the Sentiment page."
        )

    # ── Help / about ───────────────────────────────────────────────────────────
    if any(w in msg_lower for w in ["help", "what", "how", "explain", "sto", "work", "app", "use"]):
        return (
            "**STO** (Social Trend Observant) aggregates news from publishers like BBC, "
            "Reuters, TechCrunch, and others, then runs sentiment analysis to show how "
            "the media feels about different stocks. Here's what you can do:\n\n"
            "1. **Sentiment dashboard** — view overall mood and search by ticker\n"
            "2. **Practice trading** — simulate buy/sell orders with $100k play money\n"
            "3. **Chat (here)** — ask about any ticker or market concept\n\n"
            "Try asking: *What's the sentiment for AAPL?* or *How do I start trading?*"
        )

    # ── Source / news questions ────────────────────────────────────────────────
    if any(w in msg_lower for w in ["source", "news", "rss", "feed", "publisher"]):
        return (
            "STO pulls news from over a dozen sources including BBC News, Reuters, "
            "NPR, TechCrunch, The Verge, Wired, Forbes Business, MarketWatch, ESPN, "
            "Science Daily, and more. Articles are fetched every few minutes and "
            "analysed for sentiment automatically."
        )

    # ── Default ────────────────────────────────────────────────────────────────
    return (
        "I can help with market sentiment for specific tickers (try *AAPL* or *GME*), "
        "explain how the app works, or guide you through practice trading. "
        "What would you like to know?"
    )


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/chatbot/message")
def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    user: Optional[AppUser] = Depends(get_optional_app_user),
):
    if not req.message.strip():
        return {"reply": "Please type a message and I'll do my best to help!"}
    reply = _generate_reply(req.message, db)
    return {"reply": reply}
