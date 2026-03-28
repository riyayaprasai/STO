from config import Config
from services.nlp import score_split
from services.reddit_fetcher import fetch_reddit_posts
from services.twitter_fetcher import fetch_tweets

# Mock sentiment for development when Reddit/Twitter/NewsAPI are not configured
MOCK_OVERVIEW = {
    "overall_score": 0.42,
    "label": "neutral",
    "sources": {
        "reddit": {"score": 0.38, "volume": 1240},
        "twitter": {"score": 0.45, "volume": 3200},
        "news": {"score": 0.44, "volume": 89},
    },
    "top_symbols": [
        {"symbol": "AAPL", "score": 0.52, "mentions": 450},
        {"symbol": "GME", "score": 0.61, "mentions": 890},
        {"symbol": "AMC", "score": 0.55, "mentions": 320},
        {"symbol": "GOOGL", "score": 0.41, "mentions": 210},
        {"symbol": "MSFT", "score": 0.48, "mentions": 180},
    ],
}

MOCK_BY_SYMBOL = {
    "AAPL": {"symbol": "AAPL", "score": 0.52, "label": "positive", "mentions": 450},
    "GME": {"symbol": "GME", "score": 0.61, "label": "positive", "mentions": 890},
    "AMC": {"symbol": "AMC", "score": 0.55, "label": "positive", "mentions": 320},
    "GOOGL": {"symbol": "GOOGL", "score": 0.41, "label": "neutral", "mentions": 210},
    "MSFT": {"symbol": "MSFT", "score": 0.48, "label": "neutral", "mentions": 180},
}


def get_sentiment_overview():
    if Config.USE_MOCK_DATA:
        return MOCK_OVERVIEW

    watchlist = ["AAPL", "TSLA", "MSFT", "GME", "NVDA"]

    symbol_results = []
    total_any_mentions = 0
    reddit_score_values = []
    twitter_score_values = []
    reddit_mentions_total = 0
    twitter_mentions_total = 0

    for symbol in watchlist:
        reddit_posts = fetch_reddit_posts(symbol, 20)
        tweets = fetch_tweets(symbol, 20)

        total_any_mentions += len(reddit_posts) + len(tweets)

        reddit_texts = [p["title"] + " " + p["body"] for p in reddit_posts]
        twitter_texts = [t["text"] for t in tweets]

        scored = score_split(reddit_texts, twitter_texts)

        symbol_results.append(
            {
                "symbol": symbol,
                "score": scored["overall_score"],
                "label": scored["label"],
                "mentions": scored["volume"],
            }
        )

        reddit_mentions_total += len(reddit_texts)
        twitter_mentions_total += len(twitter_texts)

        if scored.get("reddit_score") is not None:
            reddit_score_values.append(scored["reddit_score"])
        if scored.get("twitter_score") is not None:
            twitter_score_values.append(scored["twitter_score"])

    # If everything came back empty, keep the development mock.
    if total_any_mentions == 0:
        return MOCK_OVERVIEW

    def _label_from_overall_score(overall_score: float) -> str:
        compound = overall_score * 2 - 1
        if compound > 0.05:
            return "positive"
        if compound < -0.05:
            return "negative"
        return "neutral"

    overall_score = (
        sum(r["score"] for r in symbol_results) / len(symbol_results)
        if symbol_results
        else 0.5
    )
    label = _label_from_overall_score(overall_score)

    avg_reddit_score = sum(reddit_score_values) / len(reddit_score_values) if reddit_score_values else 0.5
    avg_twitter_score = sum(twitter_score_values) / len(twitter_score_values) if twitter_score_values else 0.5

    top_symbols = sorted(symbol_results, key=lambda x: x["score"], reverse=True)

    return {
        "overall_score": float(overall_score),
        "label": label,
        "sources": {
            "reddit": {"score": float(avg_reddit_score), "volume": reddit_mentions_total},
            "twitter": {"score": float(avg_twitter_score), "volume": twitter_mentions_total},
            # No news aggregation yet; keep key for frontend shape compatibility.
            "news": {"score": 0.5, "volume": 0},
        },
        "top_symbols": [
            {"symbol": s["symbol"], "score": float(s["score"]), "mentions": s["mentions"]}
            for s in top_symbols
        ],
    }


def get_sentiment_for_symbol(symbol):
    if Config.USE_MOCK_DATA:
        return MOCK_BY_SYMBOL.get(
            symbol,
            {"symbol": symbol, "score": 0.5, "label": "neutral", "mentions": 0},
        )

    reddit_posts = fetch_reddit_posts(symbol, 50)
    tweets = fetch_tweets(symbol, 50)

    if len(reddit_posts) == 0 and len(tweets) == 0:
        return MOCK_BY_SYMBOL.get(
            symbol,
            {"symbol": symbol, "score": 0.5, "label": "neutral", "mentions": 0},
        )

    reddit_texts = [p["title"] + " " + p["body"] for p in reddit_posts]
    twitter_texts = [t["text"] for t in tweets]

    scored = score_split(reddit_texts, twitter_texts)

    return {
        "symbol": symbol,
        "score": scored["overall_score"],
        "label": scored["label"],
        "mentions": scored["volume"],
    }
