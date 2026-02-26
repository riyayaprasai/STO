import re
from services.sentiment_service import get_sentiment_for_symbol

# Preliminary rule-based responses (replace with GPT/LLM later)
KEYWORDS = {
    "sentiment": "You can check sentiment from the Sentiment page. STO is social trend observant — we pull in what people are saying on Reddit, Twitter, and news. Right now overall market sentiment is neutral to slightly positive.",
    "stock": "For a specific ticker, use the Sentiment page or ask me about a symbol like AAPL or GME. I'll look it up for you.",
    "trading": "STO has a practice trading area so you can try strategies with play money. Open the Practice trading tab to use your virtual portfolio.",
    "help": "I can help with: sentiment (overall or by ticker), how to use practice trading, and anything about STO. STO is social trend observant — we help you see what’s trending. Try asking 'What's the sentiment for AAPL?' or 'How does practice trading work?'",
    "hello": "Hi! I'm the STO assistant — STO is social trend observant. I can help with market sentiment and the practice trading simulator. What would you like to know?",
}


def chat(user_message):
    msg = (user_message or "").strip().lower()
    if not msg:
        return "Please type a message."

    # Ticker mention (e.g. AAPL, GME)
    ticker_match = re.search(r"\b([A-Z]{2,5})\b", user_message.strip(), re.I)
    if ticker_match:
        symbol = ticker_match.group(1).upper()
        data = get_sentiment_for_symbol(symbol)
        score = data.get("score", 0.5)
        label = data.get("label", "neutral")
        mentions = data.get("mentions", 0)
        return f"Sentiment for {symbol}: {label} (score {score:.2f}, {mentions} mentions in our sources). This is not financial advice — use the dashboard for full details."

    for keyword, response in KEYWORDS.items():
        if keyword in msg:
            return response

    return "I'm the STO assistant — we're social trend observant! Ask about sentiment, a stock ticker (e.g. AAPL, GME), or the practice trading simulator and I'll do my best to help."
