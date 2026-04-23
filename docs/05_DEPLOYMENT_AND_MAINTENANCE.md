# STO — Deployment, Maintenance & Operations Guide

> How to run, configure, monitor, and maintain the STO platform.

---

## Quick Start

### One-Command Launch
```bash
bash start.sh
```
This script:
1. Installs backend dependencies (`pip install -r requirements.txt`)
2. Starts backend on `http://localhost:8000` (uvicorn with `--reload`)
3. Installs frontend dependencies (`npm install`)
4. Starts frontend on `http://localhost:3000` (`next dev`)
5. Traps `Ctrl+C` to kill both processes

### Manual Launch

**Backend:**
```bash
cd newsapi2
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Ollama (for AI features):**
```bash
ollama serve                    # Start Ollama server on port 11434
ollama pull llama3.2:3b        # Download the model (one-time)
```

---

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| npm | 9+ | Package management |
| Ollama | Latest | Local LLM inference (optional, for AI tab) |

### Python Dependencies (`requirements.txt`)
```
fastapi, uvicorn[standard]          # Web framework
sqlalchemy                          # ORM
pydantic[email]                     # Validation
aiohttp, requests, certifi, httpx   # HTTP clients
textblob                            # Sentiment analysis
beautifulsoup4                      # Web scraping
python-jose[cryptography]           # JWT
passlib[bcrypt]                     # Password hashing
python-dotenv                       # Env vars
jinja2                              # Admin templates
trafilatura                         # HTML text extraction
PyPDF2                              # PDF text extraction
yfinance                            # Legacy stock data
feedparser                          # RSS parsing
playwright                          # Browser automation (legacy)
```

### Frontend Dependencies (`package.json`)
```
next: ^16.2.4, react: ^18.2.0, react-dom: ^18.2.0
react-markdown: ^10.1.0, recharts: ^3.8.1
tailwindcss: ^3.4.0, typescript: ^5.0.0
```

---

## Environment Variables

### Backend (`newsapi2/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./users.db` | SQLAlchemy database URL |
| `ADMIN_USERNAME` | `admin` | Admin panel login |
| `ADMIN_PASSWORD` | (required) | Admin panel password |
| `JWT_SECRET` | `sto-jwt-secret-key-change-in-production-2024` | JWT signing key |
| `NEWSAPI_KEY` | (optional) | Legacy API key |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:5000` | Backend API base URL |

> **Note:** The `start.sh` script launches the backend on port 8000, but the frontend default points to port 5000. Update `.env.local` to match: `NEXT_PUBLIC_API_URL=http://localhost:8000`

---

## Database Management

### Location
SQLite database at `newsapi2/users.db` (auto-created on first run).

### Auto-Migration
Tables are created automatically via `Base.metadata.create_all(bind=engine)` in the lifespan handler. New columns/tables added to `models.py` will be created on next startup.

### Schema Changes
SQLAlchemy's `create_all` only creates new tables — it does NOT alter existing ones. For schema changes to existing tables:
1. Delete `users.db` to rebuild from scratch (loses data), OR
2. Use Alembic migrations (not currently configured)

### Backup
```bash
cp newsapi2/users.db newsapi2/users.db.backup
```

### Database Reset
```bash
rm newsapi2/users.db
# Restart the backend — fresh DB will be created and seeded
```

---

## Monitoring & Logging

### Log Files
- **Location:** `newsapi2/logs/finance_api.log`
- **Rotation:** 10MB max, 5 backup files
- **Format:** `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- **Console:** WARNING and above only

### Health Check
```bash
curl http://localhost:8000/api/health
# {"status":"ok","mock_data":false,"recent_articles":245,"total_articles":1200}
```

### Key Metrics to Monitor
| Metric | Source | Healthy Value |
|--------|--------|---------------|
| `total_articles` | `/api/health` | > 0 after first refresh |
| `recent_articles` | `/api/health` | > 0 (articles from last 48h) |
| `mock_data` | `/api/health` | `false` (true = empty DB) |
| Background refresh | Logs | `+N articles` every 10 min |
| RSS feed failures | Logs | < 50% of feeds failing |

### Manual Article Refresh
```bash
curl -X POST http://localhost:8000/api/refresh
# {"status":"ok","new_articles":15,"total_articles":1200}
```

---

## Caching Strategy

All caching is **in-memory** (module-level dicts). Caches are lost on server restart.

| Cache | TTL | Key Pattern | Location |
|-------|-----|-------------|----------|
| Market data | 5 min | `mkt:{symbol}` | `services/market_data.py` |
| Ticker news | 15 min | DB query + cooldown dict | `services/ticker_news.py` |
| SEC filings | 6 hours | `{ticker}` | `services/sec_service.py` |
| Reddit posts | 5 min | `reddit:{ticker}` | `services/social_service.py` |
| StockTwits | 5 min | `stocktwits:{ticker}` | `services/social_service.py` |
| Congress trades | 1 hour | `congress_v2:{ticker}` | `services/congress_service.py` |
| Content extraction | Forever | `{url}` | `services/content_extractor.py` |
| CIK map | Forever | Global dict | `services/sec_service.py` |
| v1 API responses | Configurable | `{namespace}:{hash}` | `utils/cache.py` |
| Rate limits | Sliding window | `{api_key}` | `utils/rate_limit.py` |

---

## Background Tasks

### Article Refresh Loop
- **Interval:** Every 10 minutes (`_REFRESH_INTERVAL_SECONDS = 600`)
- **Startup:** Seeds 20 RSS sources, does initial fetch
- **Per-cycle:** Fetches all active feeds concurrently, parses, deduplicates, analyzes sentiment
- **Error handling:** Individual feed failures don't crash the loop
- **Lifecycle:** Managed via `asyncio.create_task()`, cancelled on shutdown

---

## Security Considerations

### Current Security Posture
| Feature | Status | Notes |
|---------|--------|-------|
| Password hashing | ✅ bcrypt | Via passlib, truncated to 72 bytes |
| JWT tokens | ✅ HS256 | 30-day expiry |
| CORS | ⚠️ Wide open | `allow_origins=["*"]` — restrict in production |
| Admin auth | ✅ HTTP Basic | Constant-time comparison via `secrets.compare_digest` |
| SSL verification | ⚠️ Disabled | `ssl=False` on RSS/SEC fetches for compatibility |
| JWT secret | ⚠️ Hardcoded default | Must set `JWT_SECRET` env var in production |
| Rate limiting | ✅ In-memory | Single-process only; use Redis for multi-process |
| Input validation | ✅ Pydantic | Email validation via `EmailStr` |

### Production Hardening Checklist
- [ ] Set strong `JWT_SECRET` environment variable
- [ ] Set strong `ADMIN_PASSWORD`
- [ ] Restrict CORS origins to your domain
- [ ] Enable SSL/TLS (reverse proxy)
- [ ] Switch from SQLite to PostgreSQL for concurrency
- [ ] Add Redis-backed rate limiting and caching
- [ ] Configure Ollama authentication if exposed
- [ ] Add request logging middleware
- [ ] Set up health check monitoring/alerting
- [ ] Enable SSL verification on outbound requests

---

## Scaling Considerations

### Current Limitations (Single-Process SQLite)
- SQLite: single-writer, no concurrent writes
- In-memory caches: not shared across processes
- Rate limiter: per-process only
- Background tasks: single asyncio loop

### Scaling Path
1. **Database:** Migrate to PostgreSQL (`DATABASE_URL=postgresql://...`)
2. **Caching:** Replace in-memory dicts with Redis
3. **Rate Limiting:** Redis-backed sliding window
4. **Workers:** Use Gunicorn with multiple Uvicorn workers
5. **Background Jobs:** Celery or APScheduler with Redis broker
6. **LLM:** Deploy Ollama on dedicated GPU server
7. **Static Assets:** CDN for frontend (Next.js static export)

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Frontend shows "mock data" | Backend not running or DB empty | Start backend, wait for initial refresh, or `POST /api/refresh` |
| No articles appearing | RSS feeds blocked or SSL errors | Check logs for feed failures; some feeds have geo-restrictions |
| 429 errors from Yahoo | yfinance rate limiting | Market data now uses Finviz+Nasdaq; check for legacy Yahoo calls |
| AI tab shows "Could not connect" | Ollama not running | Run `ollama serve` and ensure model is pulled |
| Login fails | Wrong backend URL | Check `NEXT_PUBLIC_API_URL` matches backend port |
| Admin panel 401 | Wrong credentials | Check `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `.env` |
| SEC filings empty | CIK map not loaded | Check network access to `sec.gov`; may be geo-blocked |
| Reddit data empty | Rate limited | Reddit limits unauthenticated requests; wait 5 min |

---

## File Size Reference

| File | Size | Purpose |
|------|------|---------|
| `frontend/app/sentiment/page.tsx` | 63KB | Largest file — full stock research terminal |
| `newsapi2/services/news_aggregator.py` | 21KB | RSS pipeline + 20 source definitions |
| `newsapi2/services/ticker_news.py` | 14KB | On-demand ticker news + 65 ticker mappings |
| `newsapi2/services/news_sources.py` | 14KB | Legacy + active Google RSS fetcher |
| `newsapi2/services/market_data.py` | 13KB | Finviz scraping + Nasdaq chart |
| `frontend/app/trading/page.tsx` | 18KB | Paper trading interface |
| `frontend/lib/api.ts` | 11KB | API client with 18 types + 20 methods |
| `newsapi2/services/llm_analyst.py` | 10KB | LLM prompt engineering + streaming |
| `newsapi2/main.py` | 9KB | App entry point |
