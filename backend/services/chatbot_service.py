"""
STO Chatbot Service — HuggingFace Transformers upgrade.

Uses zero-shot intent classification (BART-MNLI) and text generation
(FLAN-T5) to interpret user queries, identify intent, and return
context-aware responses using live sentiment data.
"""

import logging

from services.intent_classifier import classify_intent
from services.response_generator import generate_response
from services.sentiment_service import get_sentiment_for_symbol, get_sentiment_overview

log = logging.getLogger(__name__)


def chat(user_message: str) -> str:
    msg = (user_message or "").strip()
    if not msg:
        return "Please type a message."

    try:
        return _chat_with_ai(msg)
    except Exception as exc:
        log.exception("AI chatbot error, falling back: %s", exc)
        return _fallback(msg)


def _chat_with_ai(message: str) -> str:
    """Main AI pipeline: classify intent → fetch data → generate response."""

    # Step 1: Classify intent and extract ticker symbols
    classification = classify_intent(message)
    intent = classification["intent"]
    symbols = classification["symbols"]
    confidence = classification["confidence"]

    log.info("Intent: %s (%.2f), symbols: %s", intent, confidence, symbols)

    # Step 2: Fetch live data based on intent
    context = {"user_message": message, "symbols": symbols}

    if intent in ("symbol_sentiment", "stock_info", "compare"):
        symbols_data = []
        for sym in symbols:
            data = get_sentiment_for_symbol(sym)
            symbols_data.append(data)
        context["symbols_data"] = symbols_data

    if intent == "market_overview":
        context["overview"] = get_sentiment_overview()

    # If user mentioned symbols but intent was market_overview, fetch both
    if intent == "market_overview" and symbols:
        symbols_data = [get_sentiment_for_symbol(s) for s in symbols]
        context["symbols_data"] = symbols_data

    # Step 3: Generate context-aware response
    reply = generate_response(intent, context)
    return reply


def _fallback(message: str) -> str:
    """Simple keyword fallback if the AI pipeline fails."""
    msg = message.lower()

    if any(w in msg for w in ("hello", "hi", "hey")):
        return (
            "Hi! I'm the STO assistant. I can help with market sentiment "
            "and practice trading. What would you like to know?"
        )
    if "help" in msg:
        return (
            "I can help with: stock sentiment (try 'What's the sentiment for AAPL?'), "
            "market overview, and practice trading guidance."
        )
    return (
        "I'm the STO assistant — Social Trend Observant! "
        "Ask about sentiment, a stock ticker (e.g. AAPL, GME), "
        "or the practice trading simulator."
    )
