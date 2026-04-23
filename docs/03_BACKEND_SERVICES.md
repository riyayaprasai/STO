# STO — Backend Services Deep Dive

> Detailed breakdown of every service module in `newsapi2/services/`, covering data sources, caching strategies, and implementation details.

---

## Service Architecture Overview

```
routers/api/*  ──►  services/*  ──►  External APIs / DB
                                      │
                    ┌─────────────────┼─────────────────────┐
                    │                 │                     │
              news_aggregator    market_data          llm_analyst
              ticker_news        sec_service          content_extractor
              sentiment          social_service
                                 congress_service
```

All services are stateless functions (no class instances). Caching is in-memory via module-level dicts.

---

## 1. `news_aggregator.py` (624 lines)

**Purpose:** Core RSS article pipeline — seed sources, fetch feeds, parse, deduplicate, persist.

### Key Functions

| Function | Description |
|----------|-------------|
| `seed_sources(db)` | Inserts 20 curated RSS sources on first run; patches RSS URLs on code changes |
| `refresh_articles(db, source_ids?)` | Fetches all active feeds concurrently, parses, deduplicates, runs sentiment, persists |
| `search_articles(db, q?, sources?, category?, language?, country?, from_dt?, to_dt?, sort_by, page, page_size, user_tier)` | Full-text search with tier-based history enforcement |
| `get_headlines(db, ...)` | Last 24h articles wrapper around `search_articles` |
| `get_trending_topics(db, window?, category?, country?)` | Bigram/proper-noun extraction from titles, trend direction vs previous window |

### 20 Curated RSS Sources

| Category | Sources |
|----------|---------|
| General | BBC News, Reuters, Google News (Top), NPR News, Al Jazeera |
| Technology | TechCrunch, The Verge, Ars Technica, Wired, Engadget, Google News (Tech) |
| Business | Forbes Business, MarketWatch, Google News (Business) |
| Sports | ESPN, BBC Sport |
| Science | Science Daily, NASA |
| Entertainment | Variety |
| Health | WHO News |

### Deduplication
- Each article URL is hashed via `MD5(url)` → stored as `content_hash`
- Before insert, checks `Article.content_hash` for duplicates
- Max 20 articles per feed per refresh cycle

### Trending Algorithm
1. Extract bigrams from article titles (stopwords removed)
2. Extract capitalized proper nouns > 4 chars
3. Compare current window vs previous window counts
4. Classify as `rising` (>20% increase), `declining` (<80%), or `stable`

---

## 2. `ticker_news.py` (436 lines)

**Purpose:** On-demand ticker-specific news. When a user searches `AAPL`, this builds 14+ RSS feed URLs across Google News and Bing News.

### Feed URL Strategy (per ticker)
1. Google News — `{ticker} stock` search
2. Google News — `{company_name} stock market` search
3. Google News — `{ticker} earnings OR revenue OR quarterly`
4. Google News — `{ticker} SEC filing OR 10-K OR 10-Q`
5. Google News `site:` operator for 8 financial domains (Reuters, CNBC, MarketWatch, Seeking Alpha, Bloomberg, WSJ, Investopedia, Barron's)
6. Bing News — `{ticker} stock`
7. Bing News — `{company_name} stock`

**Total: 14 concurrent RSS fetches per ticker.**

### Caching
- `CACHE_MINUTES = 15` — won't re-fetch if articles exist within 15 min
- `_rss_cooldown` dict — blocks re-fetch attempts within 5 min even on failure
- Returns up to 50 articles per ticker from DB

### Ticker → Company Name Mapping
Contains 65+ hardcoded mappings (AAPL→Apple, TSLA→Tesla, etc.) for better search queries.

---

## 3. `sentiment.py` (88 lines)

**Purpose:** TextBlob-based sentiment analysis.

### Classification
| Polarity Range | Category |
|----------------|----------|
| > 0.5 | very positive |
| > 0.1 | positive |
| -0.1 to 0.1 | neutral |
| < -0.1 | negative |
| < -0.5 | very negative |

### Subjectivity Classification
| Range | Category |
|-------|----------|
| > 0.7 | very subjective |
| > 0.3 | somewhat subjective |
| ≤ 0.3 | objective |

**`analyze_sentiment(text)`** — Runs TextBlob in thread pool (CPU-bound). Returns category + scores.
**`enrich_news_with_sentiment(news_items)`** — Batch analysis with aggregate distribution stats.

---

## 4. `market_data.py` (299 lines)

**Purpose:** Stock fundamentals and price charts from non-rate-limited sources.

### Data Sources (layered, in priority order)
1. **Nasdaq Chart API** — 1-month historical price data (reliable, no rate limits)
2. **Finviz Scrape** — 40+ fundamental metrics (single HTTP request, no rate limits)

Yahoo Finance / yfinance intentionally avoided due to aggressive IP-based rate limiting.

### Finviz Metrics Extracted
- **Price:** current price, change, change %
- **Valuation:** P/E, Forward P/E, PEG, P/S, P/B, P/C, P/FCF, EV/EBITDA
- **Profitability:** Profit Margin, Operating Margin, Gross Margin, ROE, ROA, ROIC
- **Balance Sheet:** Debt/Equity, LT Debt/Equity, Quick Ratio, Current Ratio
- **Growth:** EPS (TTM), EPS Next Year, Sales Q/Q, EPS Q/Q
- **Other:** Market Cap, Beta, Dividend Yield, Payout Ratio, Target Price, Sector, Industry

### Caching
- `CACHE_TTL = 300` seconds (5 minutes)
- Key format: `mkt:{symbol}`
- Fast-path: serves from cache without spawning thread

---

## 5. `sec_service.py` (228 lines)

**Purpose:** SEC EDGAR integration for regulatory filings.

### Data Flow
1. Load ticker→CIK mapping from `https://www.sec.gov/files/company_tickers.json` (cached in-memory, loaded once)
2. Fetch submissions from `https://data.sec.gov/submissions/CIK{cik}.json`
3. Parse recent filings (8-K, 10-K, 10-Q)
4. Translate 8-K item codes to human-readable labels

### 8-K Item Codes (15 mapped)
`1.01` Material Agreement, `2.02` Earnings/Results, `2.05` Restructuring, `4.02` Financial Restatement, `5.02` Executive Change, `7.01` Regulation FD Disclosure, etc.

### Caching
- `_CACHE_TTL_HOURS = 6` — filings cached per-ticker for 6 hours
- Max 15 filings returned

**SEC requires:** `User-Agent: STO-App/1.0 sto-contact@example.com`

---

## 6. `social_service.py` (171 lines)

**Purpose:** Reddit and StockTwits social sentiment data.

### Reddit Integration
- Searches 3 subreddits: `r/wallstreetbets`, `r/stocks`, `r/investing`
- Uses Reddit's public `.json` endpoints (no API key needed)
- Strict filtering: post title OR selftext must contain ticker
- 1-second delay between subreddit requests (rate limit politeness)
- Results sorted by score, deduplicated by title, max 15

### StockTwits Integration
- Fetches from `https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json`
- Uses `urllib.request` (sync, run in thread via `asyncio.to_thread`)
- Returns sentiment labels (Bullish/Bearish) from StockTwits' own analysis
- Max 15 messages

### Caching: Both use `CACHE_TTL = 300` seconds (5 minutes).

---

## 7. `congress_service.py` (177 lines)

**Purpose:** Congressional stock trading activity from Capitol Trades.

### Data Flow
1. Scrape `https://www.capitoltrades.com/trades?q={ticker}`
2. Parse HTML rows with strict ticker validation (row text must contain ticker)
3. Extract: politician name, party (R/D), trade type (buy/sell), amount range, date
4. Enrich with committee assignments from hardcoded mapping
5. Generate `impact_score` (60-95 for buys, 20-50 for sells)

### Fallback System
If scraping fails, provides curated historical data for major tickers (AAPL, TSLA, NVDA).

### Caching: `CACHE_TTL = 3600` seconds (1 hour).

---

## 8. `llm_analyst.py` (209 lines)

**Purpose:** AI-powered research memo generation via local Ollama server.

### Architecture
- Model: `llama3.2:3b` (local Ollama instance at `http://localhost:11434`)
- Streaming: SSE via `httpx.AsyncClient.stream()`
- Temperature: 0.3 (analysis) / 0.5 (chat follow-ups)
- Timeout: 120 seconds

### Prompt Structure
**System prompt** defines the analyst persona and enforces structured output:
1. Executive Thesis
2. Strategic Catalysts (Bull Case)
3. Critical Vulnerabilities (Bear Case)
4. SEC Filing Deep Dive
5. Valuation & Financial Health
6. Social Pulse & Retail Sentiment
7. Political Signal

**User context** is built from all 6 data sources: market data, articles (top 15), SEC filings (top 5), source full-texts, Reddit posts (top 5), and congressional trades (top 3).

### Chat Mode
Follow-up questions use the same data context but with conversation history (last 10 messages).

---

## 9. `content_extractor.py` (92 lines)

**Purpose:** Extract clean text from HTML pages and PDF documents.

| Format | Library | Max Pages |
|--------|---------|-----------|
| HTML | trafilatura | N/A |
| PDF | PyPDF2 | 15 pages |

- In-memory cache by URL
- SEC EDGAR requests use special `User-Agent: Research Tool research@example.com`
- Text cleaned (whitespace normalized) before caching

---

## 10. `yahoo.py` (157 lines) — Legacy

**Purpose:** Original yfinance-based stock data fetcher. Largely superseded by `market_data.py`.
- `get_yahoo_news(ticker)` — Yahoo Finance RSS feed
- `get_ticker_info(ticker)` — Full company info via yfinance (30-day history, analyst data)
- Has custom exception handling: `TickerValidationError`, `DataFetchError`, `InvalidDataError`

---

## 11. `google.py` (31 lines) — Legacy

**Purpose:** Simple Google News HTML scraper. Uses `aiohttp` + BeautifulSoup to parse article elements.

---

## 12. `news_sources.py` (351 lines) — Hybrid

**Purpose:** Google News RSS with site-specific search. Main active function:
- `get_news_from_google_rss(session, ticker, source_domain, source_name)` — fetches `news.google.com/rss/search?q={ticker}+site:{domain}`
- `get_all_news(ticker, sources?, custom_sources?)` — concurrent fetch from Reuters, MarketWatch, Bloomberg, Seeking Alpha

Upper half of file is commented-out Playwright/browser-based scrapers (legacy).

---

## Utility Modules

### `utils/cache.py` — TTL Cache
- `TTLCache` class with `make_key(namespace, **params)`, `get(key)`, `set(key, value, ttl)`, `delete(key)`, `clear()`
- Key generation: `{namespace}:{MD5(json(params))}`
- Used by v1 API routers for response caching

### `utils/rate_limit.py` — Sliding Window Rate Limiter
- Tracks per-minute and per-day windows per API key
- Returns `(allowed: bool, rate_info: dict)` with remaining quota and reset timestamps
- Single-process only (in-memory); for multi-process, replace with Redis

### `utils/id_generator.py` — Article ID Generator
- Format: `art_{12 random lowercase+digits}` (e.g., `art_k3xm9vp2qr4t`)
- Uses `secrets.choice()` for cryptographic randomness
