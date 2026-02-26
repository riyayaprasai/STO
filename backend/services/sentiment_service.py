from config import Config

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
    # TODO: aggregate from Reddit, Twitter, NewsAPI + NLP (e.g. FinBERT)
    return MOCK_OVERVIEW


def get_sentiment_for_symbol(symbol):
    if Config.USE_MOCK_DATA:
        return MOCK_BY_SYMBOL.get(
            symbol,
            {"symbol": symbol, "score": 0.5, "label": "neutral", "mentions": 0},
        )
    # TODO: fetch and score posts for symbol
    return MOCK_BY_SYMBOL.get(
        symbol,
        {"symbol": symbol, "score": 0.5, "label": "neutral", "mentions": 0},
    )
