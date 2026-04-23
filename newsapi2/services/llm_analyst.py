"""
AI Analyst Service.

Streams RAG-like contextual generation from either:
  - A local Ollama server (default for local dev)
  - Groq cloud API (free tier, for production deployment)

Set the GROQ_API_KEY environment variable to use Groq instead of Ollama.
"""
import json
import logging
import os
import httpx
from typing import AsyncGenerator, Dict, Any

logger = logging.getLogger(__name__)

# ── LLM Provider Configuration ────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
USE_GROQ = bool(GROQ_API_KEY)

OLLAMA_URL = "http://localhost:11434/api/chat"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Using the user-confirmed available model
DEFAULT_MODEL = "llama3.2:3b"
GROQ_MODEL = "llama-3.1-8b-instant"  # Free on Groq

SYSTEM_PROMPT = """You are an elite quantitative and fundamental equity research analyst at a tier-1 hedge fund. 
Your objective is to synthesize quantitative metrics, recent news, SEC filings, social media sentiment, and congressional trading activity into an institutional-grade investment memo.

You will be provided with:
1. QUANTITATIVE DATA (Price, Market Cap, P/E, volume, etc.)
2. RECENT NEWS (Headlines and summaries)
3. SEC FILINGS (Recent regulatory disclosures)
4. SOCIAL MEDIA SENTIMENT (Reddit discussion activity and engagement)
5. CONGRESSIONAL TRADES (Recent trades by US politicians)

INSTRUCTIONS:
- You must output your thoughts in a highly structured, professional, and dense format.
- Format your response EXACTLY with the following markdown headers:

# 📊 {Symbol} — Institutional Research Memo

### 1. Executive Thesis
[Dense 2-3 paragraph summary: bullish, bearish, or neutral — and WHY. Reference specific data points.]

### 2. 🟢 Strategic Catalysts (The Bull Case)
- [Bullet 1: Growth drivers, margin expansion, or market tailwinds]
- [Bullet 2: Competitive positioning]
- [Bullet 3: Regulatory or macro catalysts]

### 3. 🔴 Critical Vulnerabilities (The Bear Case)
- [Bullet 1: Competition and market share risks]
- [Bullet 2: Regulation, legal, or macro headwinds]
- [Bullet 3: Valuation or balance sheet concerns]

### 4. 📂 SEC Filing Deep Dive
[What the recent SEC filings (10-K, 10-Q, 8-K) reveal about risks, internal controls, or forward guidance.]

### 5. 💰 Valuation & Financial Health
[P/E analysis, Market Cap relative to peers, Dividend sustainability, 52-week positioning.]

### 6. 📱 Social Pulse & Retail Sentiment
[What Reddit and retail investor communities are saying. Highlight bullish vs bearish narratives and engagement levels.]

### 7. 🏛️ Political Signal
[Any recent congressional trades in this stock. Note if politicians are buying or selling, and the significance.]

Keep the tone strictly analytical and objective. No introductory fluff. Be dense and cite specific numbers.
"""

CHAT_SYSTEM_PROMPT = """You are the same elite hedge fund analyst. You have just provided a research report for {ticker}.
The user is asking follow-up questions. Answer using the full context previously provided (Market Data, News, SEC Filings, Reddit Sentiment, Congressional Trades) and your financial expertise.
Maintain your professional, analytical persona. Be concise but thorough.
"""

def _build_context(ticker: str, market_data: Dict[str, Any], articles: list, filings: list, reddit_posts: list = None, congress_trades: list = None, source_contents: Dict[str, str] = None, uploaded_content: str = None) -> str:
    """Combines all the fetched data into a formatted string context for the LLM."""
    if reddit_posts is None: reddit_posts = []
    if congress_trades is None: congress_trades = []
    if source_contents is None: source_contents = {}
    
    # 1. Market Data
    ctx = f"--- QUANTITATIVE DATA FOR {ticker} ---\n"
    ctx += f"Price: ${market_data.get('price')} (Change: {market_data.get('change_percent')}%)\n"
    ctx += f"Market Cap: {market_data.get('market_cap')}\n"
    ctx += f"P/E Ratio: {market_data.get('pe_ratio')} (Forward P/E: {market_data.get('forward_pe')})\n"
    ctx += f"52-Week Range: ${market_data.get('fifty_two_week_low')} - ${market_data.get('fifty_two_week_high')}\n"
    ctx += f"Sector: {market_data.get('sector')} | Industry: {market_data.get('industry')}\n"
    ctx += f"Dividend Yield: {market_data.get('dividend_yield')} | Beta: {market_data.get('beta')}\n"
    ctx += f"Revenue: {market_data.get('total_revenue')} | FCF: {market_data.get('free_cash_flow')}\n"
    ctx += f"Profit Margin: {market_data.get('profit_margins')} | Operating Margin: {market_data.get('operating_margins')}\n"
    ctx += f"ROE: {market_data.get('return_on_equity')} | Debt/Equity: {market_data.get('debt_to_equity')}\n"
    ctx += f"Company Description: {(market_data.get('description') or '')[:500]}...\n\n"

    # 2. Articles (Top 15 max to save context)
    ctx += f"--- RECENT NEWS ARTICLES ---\n"
    for i, a in enumerate(articles[:15]):
        title = a.get("title", "")
        source = a.get("source", "")
        desc = (a.get("description") or "")[:200]
        ctx += f"{i+1}. [{source}] {title}\n   Summary: {desc}...\n"
    ctx += "\n"

    # 3. SEC Filings (Top 5 max)
    ctx += f"--- RECENT SEC FILINGS ---\n"
    for i, f in enumerate(filings[:5]):
        form = f.get("form", "")
        date = f.get("filing_date", "")
        desc = f.get("description", "")
        items = f.get("items", "")
        ctx += f"{i+1}. Form {form} (Filed on {date})\n   Description: {desc}\n   Items: {items}\n"
    ctx += "\n"

    # 4. DEEP DIVE CONTENT (The "Meat" of the documents)
    if source_contents:
        ctx += f"--- FULL-TEXT DEEP DIVE DISCLOSURES ---\n"
        for url, content in source_contents.items():
            # Increase limit for deep dives to 15,000 characters if it's a specific manual link
            limit = 15000 if len(source_contents) == 1 else 3000
            trunc_content = content[:limit] + "\n\n[...Content truncated for context window...]" if len(content) > limit else content
            label = "SEC Filing" if "sec.gov" in url or "edgar" in url else "News Article"
            ctx += f"### SOURCE: {label} ({url})\n\n```markdown\n{trunc_content}\n```\n\n"
        ctx += "\n"

    # 4.5 MANUALLY UPLOADED DOCUMENT
    if uploaded_content:
        ctx += f"--- MANUALLY UPLOADED DOCUMENT ---\n"
        # Support up to 30k characters for user-uploaded files
        limit = 30000
        trunc_uploaded = uploaded_content[:limit] + "\n\n[...Uploaded file truncated...]" if len(uploaded_content) > limit else uploaded_content
        ctx += f"### UPLOADED FILE CONTENT\n\n```markdown\n{trunc_uploaded}\n```\n\n"

    # 5. Reddit Social Sentiment (Top 5 to save tokens)
    ctx += f"--- REDDIT SOCIAL SENTIMENT ---\n"
    if reddit_posts:
        for i, p in enumerate(reddit_posts[:5]):
            ctx += f"{i+1}. r/{p.get('subreddit','')} | Score: {p.get('score',0)} | Comments: {p.get('num_comments',0)}\n   {p.get('title','')}\n"
    else:
        ctx += "No recent Reddit mentions found.\n"
    ctx += "\n"

    # 6. Congressional Trades (Top 3 to save tokens)
    ctx += f"--- CONGRESSIONAL TRADES ---\n"
    if congress_trades:
        for i, t in enumerate(congress_trades[:3]):
            ctx += f"{i+1}. {t.get('politician','')} ({t.get('party','')}) — {t.get('trade_type','').upper()} — {t.get('amount_range','')} on {t.get('trade_date','')}\n"
    else:
        ctx += "No recent congressional trades found for this ticker.\n"

    return ctx


async def stream_analysis(ticker: str, market_data: Dict[str, Any], articles: list, filings: list, reddit_posts: list = None, congress_trades: list = None, source_contents: Dict[str, str] = None, uploaded_content: str = None) -> AsyncGenerator[str, None]:
    """Initial research report generation."""
    context_str = _build_context(ticker, market_data, articles, filings, reddit_posts, congress_trades, source_contents, uploaded_content)

    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.replace("{Symbol}", ticker)},
            {"role": "user", "content": context_str}
        ],
        "stream": True,
        "options": {"temperature": 0.3}
    }

    async for token in _ollama_stream(payload):
        yield token


async def stream_chat(ticker: str, market_data: Dict[str, Any], articles: list, filings: list, history: list, reddit_posts: list = None, congress_trades: list = None, source_contents: Dict[str, str] = None, uploaded_content: str = None) -> AsyncGenerator[str, None]:
    """Handles follow-up chat turns."""
    context_str = _build_context(ticker, market_data, articles, filings, reddit_posts, congress_trades, source_contents, uploaded_content)
    
    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT.format(ticker=ticker)},
        {"role": "user", "content": f"Here is the data context for {ticker}:\n{context_str}"},
        {"role": "assistant", "content": "Acknowledged. I have the full context and am ready for your follow-up questions."}
    ]
    
    messages.extend(history[-10:])

    payload = {
        "model": DEFAULT_MODEL,
        "messages": messages,
        "stream": True,
        "options": {"temperature": 0.5}
    }

    async for token in _ollama_stream(payload):
        yield token


async def _ollama_stream(payload: dict) -> AsyncGenerator[str, None]:
    """Core streaming logic — routes to Groq or Ollama based on config."""
    if USE_GROQ:
        async for token in _groq_stream(payload):
            yield token
    else:
        async for token in _ollama_stream_local(payload):
            yield token


async def _groq_stream(payload: dict) -> AsyncGenerator[str, None]:
    """Stream from Groq cloud API (OpenAI-compatible)."""
    groq_payload = {
        "model": GROQ_MODEL,
        "messages": payload["messages"],
        "stream": True,
        "temperature": payload.get("options", {}).get("temperature", 0.3),
        "max_tokens": 4096,
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", GROQ_URL, json=groq_payload, headers=headers) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    yield f"Error: Groq API returned status {response.status_code}: {body.decode()}"
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
    except httpx.ConnectError:
        yield "\n\n**Error:** Could not connect to Groq API. Check your GROQ_API_KEY."
    except Exception as e:
        logger.error(f"Groq stream error: {e}")
        yield f"\n\n**Error:** AI session interrupted: {e}"


async def _ollama_stream_local(payload: dict) -> AsyncGenerator[str, None]:
    """Stream from local Ollama server."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", OLLAMA_URL, json=payload) as response:
                if response.status_code != 200:
                    yield f"Error: Ollama server returned status {response.status_code}."
                    return

                async for chunk in response.aiter_lines():
                    if chunk:
                        try:
                            data = json.loads(chunk)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                        except json.JSONDecodeError:
                            continue
    except httpx.ConnectError:
         yield "\n\n**Error:** Could not connect to local Ollama server. Please ensure `ollama serve` is active."
    except Exception as e:
         logger.error(f"Ollama stream error: {e}")
         yield f"\n\n**Error:** AI session interrupted: {e}"

