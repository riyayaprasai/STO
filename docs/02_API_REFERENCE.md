# STO — Backend API Reference

> Complete endpoint documentation for all 25+ routes across three authentication layers.

---

## API Base URLs

| Environment | URL |
|-------------|-----|
| Backend API | `http://localhost:8000` |
| Swagger Docs | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| OpenAPI JSON | `http://localhost:8000/openapi.json` |

---

## 1. Frontend Endpoints (`/api/*`) — JWT Bearer Auth

### Authentication

#### `POST /api/auth/signup`
Create a new account. Auto-seeds a $100K virtual portfolio.

**Request:**
```json
{ "email": "user@example.com", "password": "secret123" }
```
**Response (200):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": { "id": "1", "email": "user@example.com" }
}
```
**Errors:** `400` password < 6 chars, email already in use.

**File:** `routers/api/app_auth.py` — `signup()`

---

#### `POST /api/auth/login`
**Request:** `{ "email": "...", "password": "..." }`
**Response:** Same as signup.
**Errors:** `401` invalid credentials.

**File:** `routers/api/app_auth.py` — `login()`

---

### Health

#### `GET /api/health`
Liveness check with article count stats.
```json
{
  "status": "ok",
  "mock_data": false,
  "recent_articles": 245,
  "total_articles": 1200
}
```
`mock_data` is `true` only when DB has zero articles (first boot).

**File:** `routers/api/health.py`

---

### Sentiment Analysis

#### `GET /api/sentiment/overview`
Aggregate sentiment from last 7 days of articles.
```json
{
  "overall_score": 0.5823,
  "label": "positive",
  "sources": {
    "technology": { "score": 0.62, "volume": 120 },
    "business": { "score": 0.55, "volume": 85 }
  },
  "top_symbols": [
    { "symbol": "AAPL", "score": 0.65, "mentions": 23 }
  ]
}
```
Scoring: `very positive=0.85`, `positive=0.65`, `neutral=0.50`, `negative=0.35`, `very negative=0.15`.

**File:** `routers/api/sentiment.py` — `sentiment_overview()`

---

#### `GET /api/sentiment/symbol/{symbol}`
Sentiment for a specific ticker (last 7 days, max 100 articles).
```json
{ "symbol": "AAPL", "score": 0.65, "label": "positive", "mentions": 23 }
```

#### `GET /api/sentiment/trends?symbol=AAPL&days=7`
Daily sentiment trend. Returns one score per day.
```json
{
  "symbol": "AAPL",
  "trend": [
    { "date": "2026-04-16", "score": 0.62 },
    { "date": "2026-04-17", "score": 0.58 }
  ]
}
```

---

### Stock Research

#### `GET /api/research/{symbol}`
**The main endpoint.** Returns ALL data sources merged into one response.

**Response shape:**
```json
{
  "ticker": "AAPL",
  "company": "Apple",
  "market_data": {
    "price": 175.50, "change": -2.30, "change_percent": -1.29,
    "market_cap": 2750000000000, "pe_ratio": 27.04,
    "forward_pe": 25.12, "dividend_yield": 0.0055,
    "beta": 1.24, "sector": "Technology",
    "industry": "Consumer Electronics",
    "chart_data": [{"date": "2026-04-01", "price": 170.25}],
    "profit_margins": 0.264, "return_on_equity": 1.47,
    "debt_to_equity": 1.76, "free_cash_flow": 111000000000,
    "eps_ttm": 6.42, "target_price": 195.0
  },
  "articles": [{"id": "art_xxx", "title": "...", "source": "Reuters", "published_at": "..."}],
  "total_articles": 35,
  "filings": [{"form": "10-K", "filing_date": "2026-01-15", "description": "Annual Report"}],
  "total_filings": 12,
  "reddit_posts": [{"title": "...", "score": 450, "subreddit": "wallstreetbets"}],
  "total_reddit": 8,
  "stocktwits_posts": [{"body": "...", "sentiment": "Bullish"}],
  "total_stocktwits": 15,
  "congress_trades": [{"politician": "Nancy Pelosi", "party": "D", "trade_type": "buy"}],
  "total_congress": 2,
  "data_sources": {
    "articles_available": true, "filings_available": true,
    "reddit_available": true, "tweets_available": true,
    "congress_available": true, "limited_data": false
  }
}
```

**File:** `routers/api/research.py` — `stock_research()`

---

#### `GET /api/search?q=apple`
Fuzzy ticker search via Yahoo Finance. Returns `{ "symbol": "AAPL", "shortname": "Apple Inc." }`.

#### `GET /api/chart/{symbol}?range=1mo`
Historical price chart data. Ranges: `1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max`.

---

### SEC Filings

#### `GET /api/sec/filings/{symbol}?forms=8-K,10-K,10-Q`
Recent SEC filings from EDGAR. Default forms: `8-K, 10-K, 10-Q`. Max 15 filings.

#### `GET /api/sec/filings/{symbol}/analysis`
Same filings with sentiment metadata wrapper.

**File:** `routers/api/sec.py`

---

### News (Public — No Auth)

#### `GET /api/news/headlines?category=technology&page=1&page_size=10`
Recent headlines from last 24 hours.

#### `GET /api/news/search?q=AAPL&page=1&page_size=10`
Full-text search across article titles and descriptions.

#### `GET /api/news/trending?window=24h`
Trending phrases extracted from recent article titles. Windows: `1h, 6h, 24h, 7d`.

**File:** `routers/api/news.py`

---

### AI/LLM (Ollama Streaming)

#### `POST /api/llm/analyze/{symbol}`
Generates an institutional research memo via SSE streaming.
**Request:** `{ "manual_url": "https://...", "uploaded_content": "..." }`
**Response:** `text/event-stream` — each line: `data: {"token": "..."}`

#### `POST /api/llm/chat/{symbol}`
Follow-up chat with context from the initial analysis.
**Request:** `{ "history": [{"role": "user", "content": "..."}], "uploaded_content": "..." }`

#### `POST /api/llm/upload/{symbol}`
Upload PDF/HTML file for specialized analysis. Returns extracted text.

**File:** `routers/api/llm.py`

---

### Trading (Requires JWT)

#### `GET /api/trading/portfolio`
User's portfolio: cash balance, positions, total value.

#### `GET /api/trading/portfolio/positions`
Just the positions list.

#### `POST /api/trading/portfolio/order`
Place a buy/sell order.
**Request:** `{ "symbol": "AAPL", "side": "buy", "quantity": 10 }`
**Response:** `{ "success": true, "portfolio": {...} }`

#### `GET /api/trading/prices?symbols=AAPL,MSFT,GOOGL`
Simulated current prices. Deterministic-random, rotates hourly.

**File:** `routers/api/trading.py`

---

### Chatbot

#### `POST /api/chatbot/message`
Rule-based chatbot. Auth optional.
**Request:** `{ "message": "What's the sentiment for AAPL?" }`
**Response:** `{ "reply": "Based on 23 recent articles, **AAPL** sentiment is **positive** at 65%..." }`

**File:** `routers/api/chatbot.py`

---

## 2. v1 Public API (`/v1/*`) — API-Key Auth

All v1 endpoints require `X-Api-Key` header or `?apiKey=` query parameter.
Rate-limit headers are injected: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

#### `GET /v1/articles?q=...&sources=...&category=...&language=...&country=...&from=...&to=...&sortBy=publishedAt&page=1&pageSize=20`
Full-text search with pagination.

#### `GET /v1/articles/{id}`
Single article with related article stubs.

#### `GET /v1/headlines?category=...&page=1&pageSize=10`
Top headlines from last 24 hours.

#### `GET /v1/sources`
Available news sources (cached 1 hour).

#### `GET /v1/trending?window=24h&category=...&country=...`
Trending topics (cached 5 min).

---

## 3. Management Endpoints

#### `POST /users/register`
Self-serve API key generation. Returns user with API key.
**Request:** `{ "username": "john", "email": "john@example.com" }`

#### `GET /admin/` (HTTP Basic Auth)
Admin dashboard HTML page. CRUD for API-key users, tier management.

#### `POST /api/refresh`
Manually trigger article refresh. Returns `{ "status": "ok", "new_articles": 15, "total_articles": 1200 }`.

---

## Error Response Format

All errors follow this structure:
```json
{
  "status": "error",
  "code": "apiKeyMissing",
  "message": "Your API key is missing."
}
```

Error codes: `parameterInvalid`, `parametersMissing`, `apiKeyMissing`, `apiKeyInvalid`, `apiKeyDisabled`, `apiKeyExhausted`, `rateLimited`, `serverError`, `dataFetchError`.
