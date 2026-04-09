"""
Intent classification using HuggingFace zero-shot classification.

Uses facebook/bart-large-mnli to classify user messages into predefined
intent categories without any fine-tuning.
"""

import re
from transformers import pipeline

# Lazy-loaded singleton so the model is only downloaded/loaded once
_classifier = None

INTENT_LABELS = [
    "asking about sentiment for a specific stock ticker",
    "asking about overall market sentiment",
    "asking about how to use practice trading",
    "greeting or saying hello",
    "asking for help or what the bot can do",
    "asking about a stock price or stock information",
    "comparing sentiment between multiple stocks",
    "general conversation or off-topic question",
]

# Friendly short names mapped from the descriptive labels above
INTENT_SHORT = {
    "asking about sentiment for a specific stock ticker": "symbol_sentiment",
    "asking about overall market sentiment": "market_overview",
    "asking about how to use practice trading": "trading_help",
    "greeting or saying hello": "greeting",
    "asking for help or what the bot can do": "help",
    "asking about a stock price or stock information": "stock_info",
    "comparing sentiment between multiple stocks": "compare",
    "general conversation or off-topic question": "general",
}

# Common tickers that might appear in user messages
KNOWN_TICKERS = {
    "AAPL", "TSLA", "MSFT", "GME", "NVDA", "GOOGL", "AMZN", "META",
    "AMC", "SPY", "QQQ", "AMD", "NFLX", "DIS", "INTC", "BA", "COIN",
    "PLTR", "SOFI", "NIO", "RIVN", "BABA",
}


def _get_classifier():
    global _classifier
    if _classifier is None:
        _classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
        )
    return _classifier


def classify_intent(message: str) -> dict:
    """
    Classify user message into an intent category.

    Returns:
        {
            "intent": str,          # short intent name
            "confidence": float,    # 0-1 confidence score
            "symbols": list[str],   # extracted ticker symbols
        }
    """
    clf = _get_classifier()
    result = clf(message, INTENT_LABELS, multi_label=False)

    top_label = result["labels"][0]
    top_score = result["scores"][0]
    intent = INTENT_SHORT.get(top_label, "general")

    symbols = extract_symbols(message)

    # If symbols were found but intent didn't catch it, override
    if symbols and intent in ("general", "help", "greeting"):
        intent = "symbol_sentiment"

    return {
        "intent": intent,
        "confidence": round(top_score, 3),
        "symbols": symbols,
    }


def extract_symbols(message: str) -> list[str]:
    """Extract stock ticker symbols from user message."""
    # Match $AAPL style or standalone uppercase 2-5 letter words
    dollar_tickers = re.findall(r"\$([A-Z]{2,5})\b", message.upper())
    word_tickers = re.findall(r"\b([A-Z]{2,5})\b", message)

    # Filter word_tickers to known tickers to avoid false positives
    candidates = set(dollar_tickers)
    for t in word_tickers:
        if t.upper() in KNOWN_TICKERS:
            candidates.add(t.upper())

    return sorted(candidates)
