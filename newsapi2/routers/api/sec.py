"""
GET /api/sec/filings/{symbol}            — Recent SEC filings for a ticker
GET /api/sec/filings/{symbol}/analysis   — SEC filings with sentiment analysis

Public endpoints (no auth required) that expose SEC EDGAR data.
"""
import logging

from fastapi import APIRouter, Query
from typing import Optional

from services.sec_service import get_filings, get_filings_with_sentiment

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/sec/filings/{symbol}")
async def sec_filings(
    symbol: str,
    forms: Optional[str] = Query(
        None,
        description="Comma-separated filing types, e.g. '8-K,10-K,10-Q'. Defaults to all three.",
    ),
):
    """
    Return recent SEC filings (8-K, 10-K, 10-Q) for a given ticker symbol.
    Data comes from SEC EDGAR's free public API.
    """
    ticker = symbol.upper().strip()
    form_list = [f.strip() for f in forms.split(",")] if forms else None

    filings = await get_filings(ticker, form_list)

    return {
        "ticker": ticker,
        "total": len(filings),
        "filings": filings,
    }


@router.get("/sec/filings/{symbol}/analysis")
async def sec_filings_analysis(
    symbol: str,
    forms: Optional[str] = Query(
        None,
        description="Comma-separated filing types, e.g. '8-K,10-K,10-Q'. Defaults to all three.",
    ),
):
    """
    Return SEC filings with sentiment analysis on each filing's description.
    Includes aggregate sentiment summary across all filings.
    """
    ticker = symbol.upper().strip()
    form_list = [f.strip() for f in forms.split(",")] if forms else None

    result = await get_filings_with_sentiment(ticker, form_list)
    return result
