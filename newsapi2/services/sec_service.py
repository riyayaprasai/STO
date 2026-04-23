"""
SEC EDGAR integration.

Fetches recent regulatory filings (8-K, 10-K, 10-Q) for any public company
using SEC's free, open REST API, and runs sentiment analysis on filing
descriptions.

Key endpoints used:
  https://www.sec.gov/files/company_tickers.json  — ticker → CIK mapping (cached)
  https://data.sec.gov/submissions/CIK{cik}.json  — all filings for a company

SEC requires a descriptive User-Agent header:
  "User-Agent: AppName/Version contact@example.com"
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import aiohttp


logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

SEC_HEADERS = {
    "User-Agent": "STO-App/1.0 sto-contact@example.com",
    "Accept": "application/json",
}

SEC_TICKERS_URL    = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

# How many recent filings to return
MAX_FILINGS = 15

# 8-K item codes that matter most to investors
_NOTABLE_ITEMS = {
    "1.01": "Material Agreement",
    "1.02": "Agreement Terminated",
    "1.03": "Bankruptcy Filed",
    "2.01": "Acquisition / Disposition",
    "2.02": "Earnings / Results",
    "2.05": "Restructuring / Costs",
    "2.06": "Asset Impairment",
    "3.01": "Exchange Delisting",
    "4.01": "Auditor Changes",
    "4.02": "Financial Restatement",
    "5.01": "Control Changed",
    "5.02": "Executive Change",
    "5.03": "Amendment to Charter",
    "7.01": "Regulation FD Disclosure",
    "8.01": "Other Material Events",
    "9.01": "Financial Exhibits",
}

# ── In-memory cache ────────────────────────────────────────────────────────────

_ticker_to_cik: dict[str, str] = {}   # ticker.upper() -> zero-padded 10-digit CIK
_cik_map_loaded: bool = False
_filings_cache: dict[str, tuple[list, datetime]] = {}  # ticker -> (filings, fetched_at)
_CACHE_TTL_HOURS = 6


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _load_cik_map(session: aiohttp.ClientSession) -> None:
    global _cik_map_loaded
    if _cik_map_loaded:
        return
    try:
        async with session.get(
            SEC_TICKERS_URL,
            headers=SEC_HEADERS,
            timeout=aiohttp.ClientTimeout(total=20),
            ssl=False,
        ) as resp:
            data: dict = await resp.json(content_type=None)
            for entry in data.values():
                t = str(entry.get("ticker", "")).upper()
                cik = str(entry.get("cik_str", "")).zfill(10)
                if t:
                    _ticker_to_cik[t] = cik
            _cik_map_loaded = True
            logger.info("SEC: loaded %d ticker→CIK mappings", len(_ticker_to_cik))
    except Exception as exc:
        logger.warning("SEC: failed to load CIK map: %s", exc)


def _fmt_items(raw: str) -> str:
    """Turn '2.02,9.01' into human-readable labels."""
    if not raw:
        return ""
    parts = []
    for code in raw.split(","):
        code = code.strip()
        label = _NOTABLE_ITEMS.get(code)
        if label:
            parts.append(label)
    return ", ".join(parts) if parts else raw


def _filing_url(cik_int: int, accession: str) -> str:
    """Build the EDGAR filing index URL."""
    acc_clean = accession.replace("-", "")
    return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_int}&type=8-K&dateb=&owner=include&count=10"


def _accession_url(cik_int: int, accession: str) -> str:
    """Direct link to the filing index on EDGAR."""
    acc_clean = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/"


# ── Public API ─────────────────────────────────────────────────────────────────

async def get_filings(ticker: str, forms: list[str] | None = None) -> list[dict]:
    """
    Return recent SEC filings for `ticker`.

    `forms` defaults to ["8-K", "10-K", "10-Q"].
    Each returned dict has: form, filing_date, period, description, url, items, company.
    """
    ticker = ticker.upper().strip()

    # Check in-memory cache
    if ticker in _filings_cache:
        filings, fetched_at = _filings_cache[ticker]
        if datetime.utcnow() - fetched_at < timedelta(hours=_CACHE_TTL_HOURS):
            return filings

    want_forms = set(forms or ["8-K", "10-K", "10-Q"])
    results: list[dict] = []

    try:
        async with aiohttp.ClientSession() as session:
            await _load_cik_map(session)

            cik = _ticker_to_cik.get(ticker)
            if not cik:
                logger.info("SEC: no CIK found for %s", ticker)
                return []

            url = SEC_SUBMISSIONS_URL.format(cik=cik)
            async with session.get(
                url,
                headers=SEC_HEADERS,
                timeout=aiohttp.ClientTimeout(total=15),
                ssl=False,
            ) as resp:
                data: dict = await resp.json(content_type=None)

            company_name: str = data.get("name", ticker)
            cik_int = int(cik)
            recent: dict = data.get("filings", {}).get("recent", {})

            accessions   = recent.get("accessionNumber", [])
            filing_dates = recent.get("filingDate", [])
            report_dates = recent.get("reportDate", [])
            form_types   = recent.get("form", [])
            items_list   = recent.get("items", [])
            descriptions = recent.get("primaryDocDescription", [])
            primary_docs = recent.get("primaryDocument", [])

            for acc, filed, period, form, items, desc, doc in zip(
                accessions, filing_dates, report_dates,
                form_types, items_list, descriptions, primary_docs,
            ):
                if form not in want_forms:
                    continue

                human_items = _fmt_items(str(items))
                acc_clean   = acc.replace("-", "")
                view_url    = (
                    f"https://www.sec.gov/Archives/edgar/data/"
                    f"{cik_int}/{acc_clean}/{doc}"
                    if doc else
                    f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
                    f"&CIK={cik_int}&type={form}&dateb=&owner=include&count=10"
                )

                results.append({
                    "form":         form,
                    "filing_date":  filed,
                    "period":       period,
                    "company":      company_name,
                    "description":  human_items or desc or form,
                    "url":          view_url,
                    "items":        human_items,
                })

                if len(results) >= MAX_FILINGS:
                    break

    except Exception as exc:
        logger.warning("SEC: failed for %s: %s", ticker, exc)

    _filings_cache[ticker] = (results, datetime.utcnow())
    logger.info("SEC: %d filings returned for %s", len(results), ticker)
    return results


async def get_filings_with_sentiment(ticker: str, forms: list[str] | None = None) -> dict:
    """
    Return SEC filings for `ticker`. 
    (Legacy function preserved for API compatibility, but sentiment is now handled by Ollama).
    """
    filings = await get_filings(ticker, forms)

    if not filings:
        return {
            "ticker": ticker.upper(),
            "company": ticker.upper(),
            "filings": [],
        }

    company = filings[0].get("company", ticker.upper())

    return {
        "ticker": ticker.upper(),
        "company": company,
        "filings": filings,
    }

    company = filings[0].get("company", ticker.upper())

