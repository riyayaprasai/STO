"""
Market Data Service — Professional Refactor.

Primary:  Finviz scrape (fundamentals) + Yahoo Chart API (price/chart)
Fallback: yfinance (only if primary sources fail)

This architecture avoids Yahoo's aggressive IP-based rate limiting that
yfinance triggers due to its multiple internal HTTP calls per ticker.
"""
import logging
import asyncio
import time
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ── Cache ──────────────────────────────────────────────────────────────────────
_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 300  # 5 minutes

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

_EMPTY_RESULT: Dict[str, Any] = {
    "price": None, "change": 0.0, "change_percent": 0.0,
    "market_cap": None, "pe_ratio": None, "forward_pe": None,
    "dividend_yield": None, "volume": None, "avg_volume": None,
    "fifty_two_week_high": None, "fifty_two_week_low": None,
    "beta": None, "sector": None, "industry": None,
    "short_name": "", "description": None, "chart_data": [],
    "total_revenue": None, "profit_margins": None, "operating_margins": None,
    "return_on_equity": None, "debt_to_equity": None, "free_cash_flow": None,
    "enterprise_to_ebitda": None, "total_cash": None,
    "peg_ratio": None, "price_to_sales": None, "price_to_book": None,
    "price_to_cash": None, "price_to_free_cash_flow": None,
    "quick_ratio": None, "current_ratio": None, "lt_debt_to_equity": None,
    "return_on_assets": None, "gross_margin": None, "net_income": None,
    "eps_ttm": None, "eps_next_year": None, "eps_next_quarter": None,
    "sales_growth_qq": None, "eps_growth_qq": None, "payout_ratio": None,
    "enterprise_value": None, "roic": None, "target_price": None,
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_fv(val: Optional[str]) -> Optional[float]:
    """Parse a Finviz metric string like '4010.45B', '27.04%', or '288.62 -5.35%' into a float."""
    if not val or val == "-":
        return None
    val = val.split(' ')[0]  # Take only the first token to strip away secondary stats
    val = val.replace(",", "").replace("%", "")
    multiplier = 1.0
    if val.endswith("T"):
        multiplier = 1e12; val = val[:-1]
    elif val.endswith("B"):
        multiplier = 1e9; val = val[:-1]
    elif val.endswith("M"):
        multiplier = 1e6; val = val[:-1]
    elif val.endswith("K"):
        multiplier = 1e3; val = val[:-1]
    try:
        return float(val) * multiplier
    except ValueError:
        return None


# ── Primary Source: Finviz + Yahoo Chart ───────────────────────────────────────

def _fetch_nasdaq_chart(symbol: str) -> Dict[str, Any]:
    """
    Fetch 1-month historical chart from Nasdaq official API.
    This endpoint is incredibly reliable and does not rate-limit by IP like Yahoo.
    """
    result: Dict[str, Any] = {}
    try:
        import datetime
        start = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        url = f"https://api.nasdaq.com/api/quote/{symbol}/historical?assetclass=stocks&fromdate={start}&limit=30"
        
        # Nasdaq requires a non-default User-Agent
        nasdaq_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        
        resp = requests.get(url, headers=nasdaq_headers, timeout=8)
        if resp.status_code != 200:
            logger.warning("nasdaq_chart: HTTP %s for %s", resp.status_code, symbol)
            return result

        payload = resp.json().get("data", {})
        if not payload:
             return result
             
        rows = payload.get("tradesTable", {}).get("rows", [])
        
        chart_data = []
        for row in reversed(rows): # Reverse so chronological (oldest first)
            date_str = row.get("date") # "04/22/2026"
            close_price = row.get("close", "").replace("$", "").replace(",", "")
            
            if date_str and close_price:
                 dt_obj = datetime.datetime.strptime(date_str, "%m/%d/%Y")
                 formatted_date = dt_obj.strftime("%Y-%m-%d")
                 chart_data.append({
                     "date": formatted_date,
                     "price": float(close_price)
                 })
                 
        result["chart_data"] = chart_data
    except Exception as e:
         logger.warning("nasdaq_chart: failed for %s: %s", symbol, e)

    return result


def _fetch_finviz(symbol: str) -> Dict[str, Any]:
    """
    Scrape Finviz for fundamental data. This is a single HTTP request
    and is not rate-limited by Yahoo.
    """
    result: Dict[str, Any] = {}
    try:
        resp = requests.get(
            f"https://finviz.com/quote.ashx?t={symbol}",
            headers=_HEADERS, timeout=8,
        )
        if resp.status_code != 200:
            logger.warning("finviz: HTTP %s for %s", resp.status_code, symbol)
            return result

        soup = BeautifulSoup(resp.text, "html.parser")
        fv: Dict[str, str] = {}
        for row in soup.find_all("tr", class_="table-dark-row"):
            cols = row.find_all("td")
            for i in range(0, len(cols), 2):
                if i + 1 < len(cols):
                    fv[cols[i].text.strip()] = cols[i + 1].text.strip()

        # Extract Sector, Industry, Company Name
        links = soup.find_all("a", class_="tab-link")
        if len(links) >= 3:
            result["short_name"] = links[0].text.strip()
            result["sector"] = links[1].text.strip()
            result["industry"] = links[2].text.strip()

        result["market_cap"] = _parse_fv(fv.get("Market Cap"))
        result["pe_ratio"] = _parse_fv(fv.get("P/E"))
        result["forward_pe"] = _parse_fv(fv.get("Forward P/E"))
        result["beta"] = _parse_fv(fv.get("Beta"))
        result["avg_volume"] = _parse_fv(fv.get("Avg Volume"))
        result["volume"] = _parse_fv(fv.get("Volume"))
        
        # Price and Change metrics (crucial if Yahoo Chart is blocked)
        result["price"] = _parse_fv(fv.get("Price"))
        change_str = fv.get("Change")
        if change_str and result["price"] is not None:
             change_pct = float(change_str.replace('%', ''))
             result["change_percent"] = change_pct
             result["change"] = round(result["price"] * (change_pct / 100) / (1 + (change_pct / 100)), 2)
             
        result["fifty_two_week_high"] = _parse_fv(fv.get("52W High"))
        result["fifty_two_week_low"] = _parse_fv(fv.get("52W Low"))

        # Dividend
        div = _parse_fv(fv.get("Dividend %"))
        result["dividend_yield"] = (div / 100.0) if div is not None else None
        payout = _parse_fv(fv.get("Payout"))
        result["payout_ratio"] = (payout / 100.0) if payout is not None else None

        # Margins & Returns (convert % to decimal)
        pm = _parse_fv(fv.get("Profit Margin"))
        result["profit_margins"] = (pm / 100.0) if pm is not None else None
        om = _parse_fv(fv.get("Oper. Margin"))
        result["operating_margins"] = (om / 100.0) if om is not None else None
        gm = _parse_fv(fv.get("Gross Margin"))
        result["gross_margin"] = (gm / 100.0) if gm is not None else None
        roe = _parse_fv(fv.get("ROE"))
        result["return_on_equity"] = (roe / 100.0) if roe is not None else None
        roa = _parse_fv(fv.get("ROA"))
        result["return_on_assets"] = (roa / 100.0) if roa is not None else None
        roic = _parse_fv(fv.get("ROIC"))
        result["roic"] = (roic / 100.0) if roic is not None else None

        # Balance sheet & Valuation
        result["debt_to_equity"] = _parse_fv(fv.get("Debt/Eq"))
        result["lt_debt_to_equity"] = _parse_fv(fv.get("LT Debt/Eq"))
        result["total_revenue"] = _parse_fv(fv.get("Sales"))
        result["enterprise_to_ebitda"] = _parse_fv(fv.get("EV/EBITDA"))
        result["peg_ratio"] = _parse_fv(fv.get("PEG"))
        result["price_to_sales"] = _parse_fv(fv.get("P/S"))
        result["price_to_book"] = _parse_fv(fv.get("P/B"))
        result["price_to_cash"] = _parse_fv(fv.get("P/C"))
        result["price_to_free_cash_flow"] = _parse_fv(fv.get("P/FCF"))
        result["quick_ratio"] = _parse_fv(fv.get("Quick Ratio"))
        result["current_ratio"] = _parse_fv(fv.get("Current Ratio"))
        result["enterprise_value"] = _parse_fv(fv.get("Enterprise Value"))
        result["net_income"] = _parse_fv(fv.get("Income"))
        
        # Growth & EPS
        result["eps_ttm"] = _parse_fv(fv.get("EPS (ttm)"))
        eny = _parse_fv(fv.get("EPS next Y"))
        result["eps_next_year"] = (eny / 100.0) if eny is not None else None
        result["eps_next_quarter"] = _parse_fv(fv.get("EPS next Q"))
        sqq = _parse_fv(fv.get("Sales Q/Q"))
        result["sales_growth_qq"] = (sqq / 100.0) if sqq is not None else None
        eqq = _parse_fv(fv.get("EPS Q/Q"))
        result["eps_growth_qq"] = (eqq / 100.0) if eqq is not None else None
        result["target_price"] = _parse_fv(fv.get("Target Price"))

        # Calculate Free Cash Flow and Total Cash if possible
        if result["market_cap"] is not None and result["price_to_free_cash_flow"] is not None and result["price_to_free_cash_flow"] != 0:
            result["free_cash_flow"] = result["market_cap"] / result["price_to_free_cash_flow"]
        
        # Try to get shs_outstand and use it to calculate total_cash
        shs_out = _parse_fv(fv.get("Shs Outstand"))
        if shs_out is not None and result["price"] is not None and result["price_to_cash"] is not None and result["price_to_cash"] != 0:
             # Price / (Cash/Sh) = P/C  => Cash/Sh = Price / (P/C)
             # Total Cash = (Price / (P/C)) * Shs Outstand
             result["total_cash"] = (result["price"] / result["price_to_cash"]) * shs_out

        # Description from Finviz snapshot (first paragraph)
        desc_el = soup.find("td", class_="fullview-profile")
        if desc_el:
            result["description"] = desc_el.text.strip()[:600]

    except Exception as e:
        logger.warning("finviz: scrape failed for %s: %s", symbol, e)

    return result


# ── Sync Fetch (runs in thread) ───────────────────────────────────────────────

def _fetch_sync(symbol: str) -> Dict[str, Any]:
    """
    Assemble market data from non-rate-limited sources.
    1. Yahoo Chart API → price, chart, 52-week range
    2. Finviz → fundamentals (P/E, margins, sector, etc.)
    Merged into a single result dict and cached for 5 minutes.
    """
    cache_key = f"mkt:{symbol}"
    if cache_key in _cache:
        entry = _cache[cache_key]
        if time.time() - entry["ts"] < CACHE_TTL:
            logger.debug("market_data: cache HIT for %s", symbol)
            return entry["data"]

    logger.info("market_data: assembling data for %s (Finviz + Yahoo Chart)", symbol)

    # Start with empty template
    result = dict(_EMPTY_RESULT)

    # Layer 1: Nasdaq Chart (price + chart + volume)
    chart_data = _fetch_nasdaq_chart(symbol)
    result.update({k: v for k, v in chart_data.items() if v is not None})

    # Layer 2: Finviz (fundamentals)
    fv_data = _fetch_finviz(symbol)
    # Only overwrite None fields — chart data takes priority for price
    for k, v in fv_data.items():
        if v is not None and (result.get(k) is None or k not in chart_data):
            result[k] = v

    # Cache the merged result
    _cache[cache_key] = {"ts": time.time(), "data": result}
    logger.info(
        "market_data: cached %s — price=$%s, cap=%s, sector=%s",
        symbol, result.get("price"), result.get("market_cap"), result.get("sector"),
    )
    return result


# ── Async Public API ──────────────────────────────────────────────────────────

async def get_market_data(ticker: str) -> Dict[str, Any]:
    """Async entry point — offloads sync HTTP to a background thread."""
    symbol = ticker.upper().strip()

    # Fast-path: serve from cache without spawning a thread
    cache_key = f"mkt:{symbol}"
    if cache_key in _cache:
        entry = _cache[cache_key]
        if time.time() - entry["ts"] < CACHE_TTL:
            return entry["data"]

    try:
        return await asyncio.to_thread(_fetch_sync, symbol)
    except Exception as e:
        logger.warning("market_data: async wrapper failed for %s: %s", symbol, e)
        return dict(_EMPTY_RESULT)
