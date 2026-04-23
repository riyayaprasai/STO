"""
GET /api/llm/analyze/{symbol}
POST /api/llm/chat/{symbol}

Streams institutional research reports and follow-up chat via Ollama (SSE).
Now passes ALL data sources (articles, filings, Reddit, Congress) to the LLM.
"""
import logging
import asyncio
import re
from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from services.ticker_news import get_or_fetch
from services.sec_service import get_filings
from services.market_data import get_market_data
from services.social_service import get_reddit_mentions
from services.congress_service import get_congress_trades
from services.llm_analyst import stream_analysis, stream_chat
from services.content_extractor import extract_text, extract_from_pdf, extract_from_html

logger = logging.getLogger(__name__)

router = APIRouter()

def _extract_urls(text: str) -> list[str]:
    """Helper to find URLs in a string."""
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
    # Strip trailing punctuation that might get caught by the general regex
    return [u.rstrip('.,;:"\'()') for u in urls]

async def _gather_all_context(ticker: str, db: Session, manual_urls: list[str] | None = None):
    """Gather all data sources concurrently for the LLM context."""
    articles_task = get_or_fetch(ticker, db)
    sec_task = get_filings(ticker)
    reddit_task = get_reddit_mentions(ticker)
    congress_task = get_congress_trades(ticker)
    market_task = get_market_data(ticker)

    results = await asyncio.gather(
        articles_task, sec_task, reddit_task, congress_task, market_task,
        return_exceptions=True,
    )

    articles_raw = results[0] if not isinstance(results[0], Exception) else []
    filings = results[1] if not isinstance(results[1], Exception) else []
    reddit_posts = results[2] if not isinstance(results[2], Exception) else []
    congress_trades = results[3] if not isinstance(results[3], Exception) else []
    market_data = results[4] if not isinstance(results[4], Exception) else {}

    # Convert DB-mapped article objects to dicts for the LLM
    articles = []
    if isinstance(articles_raw, list):
        articles = [
            {"title": getattr(a, "title", ""), "description": getattr(a, "description", ""), "source": getattr(a, "source_name", ""), "url": getattr(a, "url", "")}
            for a in articles_raw
        ]

    # --- DEEP READ CONTENT EXTRACTION ---
    # 1. Automatic: Top 3 news articles + Top 2 SEC filings
    deep_read_urls = [a["url"] for a in articles[:3] if a.get("url")]
    if isinstance(filings, list):
        deep_read_urls += [f.get("url", "") for f in filings[:2] if isinstance(f, dict) and f.get("url")]
    
    # 2. Manual: Add any user-specified URLs
    if manual_urls:
        deep_read_urls.extend(manual_urls)

    # Fetch all full texts concurrently
    unique_urls = list(set(u for u in deep_read_urls if u))
    content_tasks = [extract_text(u) for u in unique_urls]
    content_results = await asyncio.gather(*content_tasks, return_exceptions=True)
    
    # Map URLs to their extracted content
    source_contents = {}
    for url, content in zip(unique_urls, content_results):
        if content and isinstance(content, str):
            source_contents[url] = content

    return market_data, articles, filings, reddit_posts, congress_trades, source_contents


@router.post("/llm/analyze/{symbol}")
async def analyze_stock_llm(symbol: str, payload: dict, db: Session = Depends(get_db)):
    """
    Kicks off an asynchronous streaming pipeline. Accepts 'manual_url' and 'uploaded_content'.
    """
    ticker = symbol.upper().strip()
    manual_url = payload.get("manual_url")
    uploaded_content = payload.get("uploaded_content")
    manual_urls = [manual_url] if manual_url else []

    try:
        market_data, articles, filings, reddit_posts, congress_trades, source_contents = await _gather_all_context(ticker, db, manual_urls)
    except Exception as e:
        logger.warning(f"Error gathering data: {e}")
        market_data, articles, filings, reddit_posts, congress_trades, source_contents = {}, [], [], [], [], {}

    async def sse_generator():
        yield "data: {\"token\": \"\"}\n\n"
        async for token in stream_analysis(ticker, market_data, articles, filings, reddit_posts, congress_trades, source_contents, uploaded_content):
            clean_token = token.replace('\n', '\\n').replace('"', '\\"')
            yield f"data: {{\"token\": \"{clean_token}\"}}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@router.post("/llm/chat/{symbol}")
async def chat_with_stock_llm(symbol: str, payload: dict, db: Session = Depends(get_db)):
    """
    Handles follow-up chat turns. Accepts 'history' and 'uploaded_content'.
    """
    ticker = symbol.upper().strip()
    history = payload.get("history", [])
    uploaded_content = payload.get("uploaded_content")
    
    # Extract URLs from the last user message for "on-the-fly" deep reading
    manual_urls = []
    if history:
        last_msg = history[-1].get("content", "")
        manual_urls = _extract_urls(last_msg)

    try:
        market_data, articles, filings, reddit_posts, congress_trades, source_contents = await _gather_all_context(ticker, db, manual_urls)
    except Exception as e:
        logger.warning(f"Error gathering chat context: {e}")
        market_data, articles, filings, reddit_posts, congress_trades, source_contents = {}, [], [], [], [], {}

    async def sse_generator():
        async for token in stream_chat(ticker, market_data, articles, filings, history, reddit_posts, congress_trades, source_contents, uploaded_content):
            clean_token = token.replace('\n', '\\n').replace('"', '\\"')
            yield f"data: {{\"token\": \"{clean_token}\"}}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@router.post("/llm/upload/{symbol}")
async def upload_document_for_analysis(symbol: str, file: UploadFile = File(...)):
    """
    Accepts a file upload, extracts text, and returns the content for specialized analysis.
    """
    ticker = symbol.upper().strip()
    filename = file.filename or "uploaded_file"
    content = await file.read()
    
    extracted_text = None
    if filename.lower().endswith(".pdf"):
        extracted_text = extract_from_pdf(content)
    else:
        # Assume text/html
        try:
            decoded = content.decode("utf-8")
            if "<html>" in decoded.lower():
                extracted_text = extract_from_html(decoded)
            else:
                extracted_text = decoded
        except:
            extracted_text = "Could not decode text file."

    if not extracted_text:
        return {"error": "Failed to extract text from file."}

    # Return the extracted text so the frontend can trigger an analysis turn
    return {
        "ticker": ticker,
        "filename": filename,
        "content_preview": extracted_text[:200] + "...",
        "full_text": extracted_text
    }
