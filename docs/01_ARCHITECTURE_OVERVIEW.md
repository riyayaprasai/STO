# STO — Architecture Overview & System Design

> **STO (Social Trend Observant)** is a full-stack financial intelligence platform that aggregates news from 20+ RSS sources, performs real-time sentiment analysis, integrates SEC EDGAR filings, Reddit/StockTwits social data, congressional trading activity, and provides AI-powered research memos via a local Ollama LLM — all wrapped in a Next.js frontend with JWT auth and virtual paper trading.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 16)                    │
│  Port 3000 │ React 18 │ TailwindCSS │ Recharts │ TypeScript    │
│                                                                 │
│  Pages: Dashboard │ Sentiment │ Trading │ Chat │ Wireframe      │
│  Auth: JWT tokens stored in localStorage                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / SSE (Server-Sent Events)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI + Uvicorn)                   │
│  Port 8000 │ Python 3.11+ │ SQLAlchemy ORM │ SQLite            │
│                                                                 │
│  Auth Layers:                                                   │
│    • /v1/*  → API-Key auth (X-Api-Key header)                   │
│    • /api/* → JWT Bearer auth (email + password)                │
│    • /admin → HTTP Basic Auth                                   │
│                                                                 │
│  Background: 10-min article refresh loop (asyncio task)         │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
   ┌───────┐ ┌────────┐ ┌───────┐ ┌────────┐ ┌────────┐
   │  RSS  │ │  SEC   │ │Reddit │ │Capitol │ │ Ollama │
   │ Feeds │ │ EDGAR  │ │  API  │ │ Trades │ │  LLM   │
   │(20+)  │ │  REST  │ │ .json │ │Scraper │ │llama3.2│
   └───────┘ └────────┘ └───────┘ └────────┘ └────────┘
```

---

## Repository Structure

```
STO-repo/
├── start.sh                    # One-command launcher for both servers
├── frontend/                   # Next.js 16 application
│   ├── app/                    # App Router pages
│   │   ├── layout.tsx          # Root layout (AuthProvider + Header)
│   │   ├── page.tsx            # Dashboard (home page)
│   │   ├── sentiment/page.tsx  # Sentiment analysis dashboard (63KB)
│   │   ├── trading/page.tsx    # Paper trading simulator
│   │   ├── chat/page.tsx       # Rule-based chatbot
│   │   ├── login/page.tsx      # Login form
│   │   ├── signup/page.tsx     # Registration form
│   │   └── wireframe/page.tsx  # App wireframe/documentation
│   ├── components/Header.tsx   # Global nav bar
│   ├── contexts/AuthContext.tsx # React context for JWT auth state
│   ├── lib/
│   │   ├── api.ts              # API client (fetchApi + typed methods)
│   │   └── auth.ts             # Token/user localStorage helpers
│   ├── tailwind.config.js      # Custom STO design tokens
│   └── package.json            # Dependencies
│
├── newsapi2/                   # FastAPI backend
│   ├── main.py                 # App entry, router registration, lifespan
│   ├── config.py               # Tier limits, cache TTLs, env vars
│   ├── database.py             # SQLAlchemy engine + session factory
│   ├── models.py               # 6 ORM models
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── auth.py                 # API-key auth + rate-limit enforcement
│   ├── app_auth_utils.py       # JWT auth (bcrypt + python-jose)
│   ├── exceptions.py           # Structured error hierarchy
│   ├── logging_config.py       # Rotating file + console logging
│   ├── routers/
│   │   ├── api/                # Frontend endpoints (JWT auth)
│   │   │   ├── app_auth.py     # POST /api/auth/signup, /login
│   │   │   ├── health.py       # GET /api/health
│   │   │   ├── sentiment.py    # GET /api/sentiment/*
│   │   │   ├── trading.py      # GET/POST /api/trading/*
│   │   │   ├── chatbot.py      # POST /api/chatbot/message
│   │   │   ├── research.py     # GET /api/research/{symbol}
│   │   │   ├── sec.py          # GET /api/sec/filings/{symbol}
│   │   │   ├── news.py         # GET /api/news/* (public)
│   │   │   └── llm.py          # POST /api/llm/* (Ollama SSE)
│   │   ├── v1/                 # Public API (API-key auth)
│   │   ├── admin.py            # Admin dashboard (HTTP Basic)
│   │   └── users.py            # POST /users/register
│   ├── services/               # Business logic layer (12 files)
│   ├── middleware/admin_auth.py # HTTP Basic auth
│   ├── utils/                  # Cache, rate limiter, ID generator
│   ├── templates/admin.html    # Jinja2 admin dashboard
│   └── requirements.txt        # Python dependencies
```

---

## Database Schema (SQLite — `users.db`)

### Table: `users` (API-key users for v1 endpoints)
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | Auto-increment |
| username | String (unique) | |
| email | String (unique) | |
| api_key | String (unique) | Generated via `secrets.token_urlsafe(32)` |
| tier | String | `free` / `developer` / `business` / `enterprise` |
| is_active | Boolean | Default `True` |
| created_at | DateTime | UTC |

### Table: `sources` (RSS feed registry)
| Column | Type | Notes |
|--------|------|-------|
| id | String PK | e.g. `bbc-news`, `ticker-aapl` |
| name | String | Display name |
| description | Text | |
| url | String | Publisher homepage |
| rss_url | String (nullable) | RSS feed URL |
| category | String | `general` / `technology` / `business` / `sports` / `science` / `entertainment` / `health` |
| language | String | Default `en` |
| country | String | ISO country code |
| is_active | Boolean | Whether included in background refresh |

### Table: `articles` (aggregated news)
| Column | Type | Notes |
|--------|------|-------|
| id | String PK | Format: `art_<12-char random>` |
| source_id | String (indexed) | FK to sources |
| source_name | String | Denormalized for speed |
| title | String | |
| description | Text (nullable) | Stripped HTML, max 500 chars |
| url | String (unique) | |
| published_at | DateTime (indexed) | |
| sentiment | String | `very positive` / `positive` / `neutral` / `negative` / `very negative` |
| content_hash | String (unique) | `MD5(url)` for deduplication |
| category | String | Inherited from source |

### Table: `app_users` (JWT-authenticated frontend users)
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| email | String (unique) | |
| password_hash | String | bcrypt hash |
| created_at | DateTime | |

### Table: `portfolios` (virtual trading accounts)
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| user_id | Integer FK → app_users | One-to-one |
| cash | Float | Starts at $100,000 |

### Table: `positions` (stock holdings)
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| user_id | Integer FK → app_users | |
| symbol | String | e.g. `AAPL` |
| quantity | Integer | |
| avg_price | Float | Weighted average purchase price |

---

## Authentication Architecture

| Layer | Scope | Mechanism | Implementation |
|-------|-------|-----------|----------------|
| **v1 API** | `/v1/*` | API Key (`X-Api-Key` header or `?apiKey=` query) | `auth.py` → `get_current_user()` |
| **Frontend API** | `/api/*` | JWT Bearer token (`Authorization: Bearer <token>`) | `app_auth_utils.py` → `get_required_app_user()` |
| **Admin Panel** | `/admin/*` | HTTP Basic Auth | `middleware/admin_auth.py` → `verify_admin()` |

### Rate Limiting (v1 API only)

| Tier | Daily Limit | Per-Minute | History Access |
|------|-------------|------------|----------------|
| Free | 1,000 | 10 | 30 days |
| Developer | 10,000 | 60 | 365 days |
| Business | 100,000 | 300 | Unlimited |
| Enterprise | Unlimited | Custom | Unlimited |

---

## Core Data Flows

### 1. Article Ingestion Pipeline
```
Startup → seed_sources(20 RSS feeds) → refresh_articles()
  ↓
Every 10 min → fetch RSS XML concurrently (aiohttp, 15s timeout)
             → parse XML (stdlib ElementTree, RSS 2.0 + Atom)
             → deduplicate by MD5(url) content_hash
             → sentiment analysis via TextBlob on title
             → persist new articles to SQLite
```

### 2. Stock Research Request (`GET /api/research/{symbol}`)
```
Request → asyncio.gather(6 concurrent tasks):
  1. ticker_news.get_or_fetch()     → 14+ Google/Bing RSS feeds
  2. sec_service.get_filings()      → SEC EDGAR REST API
  3. market_data.get_market_data()  → Finviz scrape + Nasdaq chart
  4. social_service.get_reddit()    → Reddit .json search API
  5. social_service.get_stocktwits()→ StockTwits stream API
  6. congress_service.get_trades()  → Capitol Trades scrape
→ merge into single JSON response
```

### 3. AI Analysis (`POST /api/llm/analyze/{symbol}`)
```
Request → gather all 5 data sources concurrently
        → extract full text from top 3 articles + 2 filings (trafilatura/PyPDF2)
        → build institutional research prompt (system + user context)
        → stream tokens from local Ollama (llama3.2:3b) via SSE
        → frontend renders markdown in real-time
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend Framework | Next.js 16 (App Router) |
| UI Library | React 18 + TypeScript |
| Styling | TailwindCSS 3.4 with custom `sto-*` design tokens |
| Charts | Recharts 3.8 |
| Markdown Rendering | react-markdown 10.1 |
| Backend Framework | FastAPI 2.0 with Uvicorn |
| Database | SQLite via SQLAlchemy ORM |
| Auth (JWT) | python-jose + passlib (bcrypt) |
| Sentiment NLP | TextBlob |
| AI/LLM | Ollama (llama3.2:3b) — local inference |
| Content Extraction | trafilatura (HTML) + PyPDF2 (PDF) |
| HTTP Clients | aiohttp (async RSS), httpx (async REST), requests (sync) |
| Web Scraping | BeautifulSoup4 |
| RSS Parsing | stdlib `xml.etree.ElementTree` + `feedparser` |
