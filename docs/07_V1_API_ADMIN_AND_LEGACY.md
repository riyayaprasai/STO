# STO — v1 Public API & Legacy Router Documentation

> Detailed breakdown of the v1 API-key-authenticated endpoints, legacy news router, admin panel, and user registration — the parts not covered in the frontend API reference.

---

## v1 API Router Architecture

The v1 API is the **public-facing, API-key-authenticated** layer designed for third-party consumers. It follows NewsAPI.org conventions.

```
/v1/
├── articles.py      GET /v1/articles, GET /v1/articles/{id}
├── headlines.py     GET /v1/headlines
├── sources.py       GET /v1/sources
├── trending.py      GET /v1/trending
└── _helpers.py      article_to_schema() converter
```

All v1 endpoints require `get_current_user` dependency which:
1. Extracts API key from `X-Api-Key` header or `apiKey` query param
2. Validates key against DB
3. Checks `is_active` flag
4. Runs rate limit check via `RateLimitStore`
5. Injects `X-RateLimit-*` headers into response
6. Returns `User` object (used for tier-based filtering)

---

### `GET /v1/articles` — Full Search

**File:** `routers/v1/articles.py` (130 lines)

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | null | Full-text search on title + description |
| `sources` | string | null | Comma-separated source IDs (e.g., `bbc-news,techcrunch`) |
| `category` | string | null | `technology`, `business`, `health`, `sports`, `science`, `entertainment`, `general` |
| `language` | string | null | ISO 639-1 code (e.g., `en`) |
| `country` | string | null | ISO 3166-1 alpha-2 (e.g., `us`) |
| `from` | datetime | null | Oldest article date (ISO 8601). Cannot be in the future |
| `to` | datetime | null | Newest article date |
| `sortBy` | string | `publishedAt` | `relevancy`, `publishedAt`, or `popularity` |
| `page` | int | 1 | Page number (≥1) |
| `pageSize` | int | 20 | Results per page (1–100) |

**Response:** `ArticlesResponse`
```json
{
  "status": "ok",
  "total_results": 245,
  "page": 1,
  "page_size": 20,
  "articles": [...]
}
```

**Caching:** TTL from `config.CACHE_TTL["articles"]`. Key: `articles:{MD5(all_params+tier)}`.

**Auto-bootstrap:** If DB has < 10 articles, triggers `refresh_articles()` inline.

**Tier enforcement:** `user_tier` is passed to `search_articles()` which enforces `TIER_LIMITS[tier]["max_history_days"]`.

---

### `GET /v1/articles/{article_id}` — Single Article

Returns the full article plus up to 5 related articles from the same category.

**Response:** `ArticleDetailResponse`
```json
{
  "status": "ok",
  "article": {
    "id": "art_k3xm9vp2qr4t",
    "source": { "id": "bbc-news", "name": "BBC News" },
    "title": "...",
    "related_articles": [
      { "id": "art_xxx", "title": "...", "url": "...", "published_at": "..." }
    ]
  }
}
```

---

### `GET /v1/headlines` — Top Headlines

**File:** `routers/v1/headlines.py` (67 lines)

Same parameters as `/v1/articles` plus:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `headlinesLimit` | int | 10 | Max top stories (1–100) |

**Caching:** `config.CACHE_TTL["headlines"]` (60 seconds).

Returns only articles from the last 24 hours, sorted by recency.

---

### `GET /v1/sources` — Source Listing

**File:** `routers/v1/sources.py` (48 lines)

**Parameters:** `category`, `language`, `country` (all optional filters).

**Response:** `SourcesResponse`
```json
{
  "status": "ok",
  "sources": [
    {
      "id": "bbc-news",
      "name": "BBC News",
      "description": "BBC News - World",
      "url": "https://www.bbc.com/news",
      "category": "general",
      "language": "en",
      "country": "gb"
    }
  ]
}
```

**Caching:** `config.CACHE_TTL["sources"]` (3600 seconds = 1 hour).

Only returns sources with `is_active=True`, ordered by name.

---

### `GET /v1/trending` — Trending Topics

**File:** `routers/v1/trending.py` (54 lines)

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `window` | string | `24h` | Must be: `1h`, `6h`, `24h`, `7d` |
| `category` | string | null | Category filter |
| `country` | string | null | Country filter |

**Response:** `TrendingResponse`
```json
{
  "window": "24h",
  "topics": [
    { "term": "Federal Reserve", "count": 12, "trend": "rising" },
    { "term": "Earnings Report", "count": 8, "trend": "stable" }
  ]
}
```

**Caching:** `config.CACHE_TTL["trending"]` (300 seconds = 5 min).

---

### `_helpers.py` — Shared Converter

`article_to_schema(art: Article) → ArticleSchema`: Converts SQLAlchemy ORM `Article` to Pydantic `ArticleSchema`. Maps nullable fields with defaults (`language` → `"en"`, `sentiment` → `"neutral"`).

---

## Legacy News Router (`routers/news.py`)

**Prefix:** `/news` → e.g., `GET /news/AAPL`

This is the **original v1-era ticker news endpoint** that predates the `/api/research/` system. It's still mounted but largely superseded.

### `GET /news/{ticker}`

**Auth:** Requires API key (v1 auth).

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_company_info` | bool | true | Fetch yfinance company data |
| `sentiment_threshold` | float | null | Min sentiment score filter (-1 to 1) |
| `time_range_hours` | int | null | Filter to last N hours |
| `sources` | list[str] | `[yahoo, reuters, bloomberg, marketwatch, seekingalpha]` | Sources to query |
| `custom_domains` | list[str] | `[]` | Custom news domains |
| `custom_names` | list[str] | `[]` | Display names for custom domains |

**Pipeline:**
1. Validate ticker format (1-5 uppercase alpha via regex)
2. Fetch company info from yfinance (optional)
3. Fetch Yahoo Finance RSS news
4. Fetch all other sources via Google News RSS `site:` operator
5. Enrich each source's articles with TextBlob sentiment
6. Apply sentiment threshold filter
7. Calculate overall weighted sentiment

**Response:**
```json
{
  "ticker": "AAPL",
  "timestamp": "2026-04-23T12:00:00",
  "company_info": { "company_info": {...}, "market_data": {...}, "analyst_data": {...} },
  "market_sentiment": {
    "overall_score": 0.35,
    "total_articles": 42,
    "sources": { "reuters": { "overall_sentiment": 0.4, ... } }
  },
  "news": {
    "yahoo": [...],
    "reuters": [...],
    "bloomberg": [...]
  }
}
```

---

## Admin Panel (`routers/admin.py`)

**Prefix:** `/admin` — Protected by HTTP Basic Auth.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET /admin/` | Renders Jinja2 admin dashboard HTML |
| `GET /admin/users` | List all API-key users |
| `POST /admin/users` | Create new user (username, email, tier) |
| `PATCH /admin/users/{user_id}/tier` | Update user's tier |
| `DELETE /admin/users/{user_id}` | Delete user |
| `POST /admin/logout` | Force 401 to clear browser credentials |

**Legacy backfill:** `GET /admin/users` auto-generates API keys and sets tier to `"free"` for any legacy users missing those fields.

**Admin auth flow:** Browser sends `Authorization: Basic base64(username:password)` → `verify_admin()` uses `secrets.compare_digest()` for constant-time comparison → credentials checked against `ADMIN_USERNAME` / `ADMIN_PASSWORD` env vars.

---

## User Registration (`routers/users.py`)

**File:** 19 lines. Minimal self-serve endpoint.

### `POST /users/register`
```json
{ "username": "john", "email": "john@example.com" }
```
Returns full user object including auto-generated API key. No password required — this creates v1 API users only.

---

## Configuration Deep Dive (`config.py`)

```python
TIER_LIMITS = {
    "free":       {"per_minute": 10,  "daily": 1_000,   "max_history_days": 30},
    "developer":  {"per_minute": 60,  "daily": 10_000,  "max_history_days": 365},
    "business":   {"per_minute": 300, "daily": 100_000, "max_history_days": None},
    "enterprise": {"per_minute": None,"daily": None,     "max_history_days": None},
}

CACHE_TTL = {
    "articles":  120,    # 2 minutes
    "headlines": 60,     # 1 minute
    "sources":   3600,   # 1 hour
    "trending":  300,    # 5 minutes
}
```

`max_history_days=None` means unlimited access. Enterprise tier has no rate limits at all (`per_minute=None`, `daily=None`).
