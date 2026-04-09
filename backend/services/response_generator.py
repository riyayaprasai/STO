"""
Context-aware response generation using HuggingFace FLAN-T5.

Generates natural language responses by combining a structured prompt
(intent + live sentiment data) with a text-to-text generation model.
FLAN-T5 works best with short, directive Q&A-style prompts.
"""

from typing import Optional

from transformers import pipeline

_generator = None


def _get_generator():
    global _generator
    if _generator is None:
        _generator = pipeline(
            "text2text-generation",
            model="google/flan-t5-small",
            max_new_tokens=200,
        )
    return _generator


def generate_response(intent: str, context: dict) -> str:
    """
    Generate a context-aware response using FLAN-T5.

    Uses the model for data-driven intents (sentiment, comparison) where it
    can summarize live data, and falls back to curated templates for simple
    intents (greeting, help) where the model adds little value.
    """
    template = _get_template(intent, context)

    # Only use the model for data-driven sentiment intents where it can
    # summarize concrete numbers. Templates are more reliable for everything else.
    if intent not in ("symbol_sentiment", "market_overview"):
        return template

    prompt = _build_prompt(intent, context)
    if prompt is None:
        return template

    gen = _get_generator()
    result = gen(prompt)
    raw = result[0]["generated_text"].strip()

    # Validate model output: reject if it echoes the prompt or is too short
    if _is_valid_response(raw, prompt):
        if intent in ("symbol_sentiment", "market_overview", "compare"):
            if "not financial advice" not in raw.lower():
                raw += " This is based on social media analysis and is not financial advice."
        return raw

    # Fall back to data-enriched template
    return template


def _is_valid_response(raw: str, prompt: str) -> bool:
    """Check if the model output is a genuine response, not a prompt echo."""
    if len(raw) < 20:
        return False
    # Detect prompt echoing: if >60% of the output words appear in the prompt
    raw_words = set(raw.lower().split())
    prompt_words = set(prompt.lower().split())
    if not raw_words:
        return False
    overlap = len(raw_words & prompt_words) / len(raw_words)
    if overlap > 0.6:
        return False
    # Reject if it starts with instruction-like patterns
    if raw.lower().startswith(("you are", "the user", "explain that", "give a")):
        return False
    return True


def _build_prompt(intent: str, context: dict) -> Optional[str]:
    """Build a FLAN-T5-friendly prompt. Returns None if no data to summarize."""

    if intent == "symbol_sentiment":
        symbols_data = context.get("symbols_data", [])
        if not symbols_data:
            return None
        data_lines = "; ".join(
            f"{sd['symbol']} is {sd['label']} with score {sd['score']:.2f} and {sd['mentions']} mentions"
            for sd in symbols_data
        )
        return f"Summarize this stock sentiment data in a helpful way: {data_lines}"

    if intent == "market_overview":
        overview = context.get("overview", {})
        score = overview.get("overall_score", 0.5)
        label = overview.get("label", "neutral")
        top = overview.get("top_symbols", [])
        top_str = ", ".join(f"{s['symbol']} ({s['score']:.2f})" for s in top[:3])
        return (
            f"Summarize this market sentiment: overall mood is {label} with score {score:.2f}. "
            f"Top stocks by sentiment: {top_str}."
        )

    if intent == "compare":
        symbols_data = context.get("symbols_data", [])
        if len(symbols_data) < 2:
            return None
        data_lines = "; ".join(
            f"{sd['symbol']} is {sd['label']} (score {sd['score']:.2f}, {sd['mentions']} mentions)"
            for sd in symbols_data
        )
        return f"Compare these stocks by sentiment and explain which is more positive: {data_lines}"

    if intent == "stock_info":
        symbols = context.get("symbols", [])
        if symbols:
            return f"The user asked about {', '.join(symbols)}. Explain that STO tracks social media sentiment, not prices. Offer to look up sentiment."
        return None

    # general
    user_msg = context.get("user_message", "")
    return f"Answer this question about a stock market sentiment app: {user_msg}"


def _get_template(intent: str, context: dict) -> str:
    """Get a curated, data-enriched template response for the given intent."""

    if intent == "symbol_sentiment":
        symbols_data = context.get("symbols_data", [])
        if symbols_data:
            parts = []
            for sd in symbols_data:
                parts.append(
                    f"**{sd['symbol']}**: sentiment is **{sd['label']}** "
                    f"(score: {sd['score']:.2f}, {sd['mentions']} mentions)"
                )
            return (
                "Here's what I found from social media:\n\n"
                + "\n".join(parts)
                + "\n\nThis is based on social media analysis and is not financial advice."
            )
        return "I don't have sentiment data for that ticker right now. Try a popular one like AAPL, TSLA, or GME."

    if intent == "market_overview":
        overview = context.get("overview", {})
        label = overview.get("label", "neutral")
        score = overview.get("overall_score", 0.5)
        sources = overview.get("sources", {})
        top = overview.get("top_symbols", [])
        top_str = ", ".join(f"{s['symbol']} ({s['score']:.2f})" for s in top[:3])
        reddit_score = sources.get("reddit", {}).get("score", "N/A")
        twitter_score = sources.get("twitter", {}).get("score", "N/A")
        return (
            f"The overall market sentiment is **{label}** (score: {score:.2f}).\n\n"
            f"- Reddit sentiment: {reddit_score}\n"
            f"- Twitter sentiment: {twitter_score}\n"
            f"- Top trending: {top_str}\n\n"
            f"This is based on social media analysis and is not financial advice."
        )

    if intent == "compare":
        symbols_data = context.get("symbols_data", [])
        if len(symbols_data) >= 2:
            sorted_data = sorted(symbols_data, key=lambda x: x["score"], reverse=True)
            parts = [
                f"**{sd['symbol']}**: {sd['label']} (score: {sd['score']:.2f}, {sd['mentions']} mentions)"
                for sd in sorted_data
            ]
            top = sorted_data[0]
            return (
                "Here's a sentiment comparison:\n\n"
                + "\n".join(parts)
                + f"\n\n**{top['symbol']}** has the most positive sentiment. "
                + "This is based on social media analysis and is not financial advice."
            )
        return "Please mention at least two stock tickers to compare (e.g., 'Compare AAPL and TSLA')."

    if intent == "greeting":
        return (
            "Hi! I'm the STO assistant — Social Trend Observant. "
            "I can help you check market sentiment from social media, "
            "look up specific stock tickers, or guide you through the practice trading simulator. "
            "What would you like to know?"
        )

    if intent == "help":
        return (
            "Here's what I can help with:\n\n"
            "- **Stock sentiment** — Ask about any ticker (e.g., \"What's the sentiment for AAPL?\")\n"
            "- **Market overview** — Get the overall market mood from social media\n"
            "- **Compare stocks** — Compare sentiment between tickers (e.g., \"Compare AAPL and TSLA\")\n"
            "- **Practice trading** — Learn about the virtual portfolio simulator\n\n"
            "Just ask away!"
        )

    if intent == "trading_help":
        return (
            "STO has a practice trading simulator where you start with $100,000 in virtual money. "
            "You can buy and sell stocks to test strategies with zero risk. "
            "Head to the Practice Trading tab to get started!"
        )

    if intent == "stock_info":
        symbols = context.get("symbols", [])
        if symbols:
            sym_str = ", ".join(symbols)
            return (
                f"STO focuses on sentiment analysis rather than real-time prices. "
                f"I can check what people on social media are saying about {sym_str}. "
                f"Want me to look up the sentiment?"
            )
        return "Which stock are you interested in? Give me a ticker symbol (e.g., AAPL, TSLA, GME) and I'll check the sentiment."

    return (
        "I'm the STO assistant — Social Trend Observant! "
        "I can help with stock sentiment analysis, market overviews, and practice trading. "
        "Try asking about a specific stock like AAPL or GME, or ask for the overall market sentiment."
    )
