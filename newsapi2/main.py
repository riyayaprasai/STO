"""
News API – main application entry point.

v1 endpoints (API-key auth):
  GET /v1/articles          Search & filter articles
  GET /v1/articles/{id}     Single article with related stubs
  GET /v1/headlines         Top headlines (last 24 h, cached 60 s)
  GET /v1/sources           Available news sources (cached 1 h)
  GET /v1/trending          Trending topics (cached 5 min)

STO Frontend endpoints (JWT Bearer auth):
  GET  /api/health                     Liveness + article-count check
  POST /api/auth/signup                Create account, receive JWT
  POST /api/auth/login                 Log in, receive JWT
  GET  /api/sentiment/overview         Aggregate sentiment from recent articles
  GET  /api/sentiment/symbol/{symbol}  Sentiment for a specific ticker
  GET  /api/sentiment/trends           Daily sentiment trend for a ticker
  GET  /api/sec/filings/{symbol}       SEC filings for a ticker
  GET  /api/sec/filings/{symbol}/analysis  SEC filings with sentiment
  GET  /api/research/{symbol}          Unified stock research (articles + SEC + sentiment)
  GET  /api/trading/portfolio          User's virtual portfolio
  GET  /api/trading/portfolio/positions Holdings list
  POST /api/trading/portfolio/order    Place a buy/sell order
  GET  /api/trading/prices             Simulated current prices
  POST /api/chatbot/message            AI-assisted chat reply

Management:
  POST /users/register      Self-serve API key generation
  GET  /admin/              Admin dashboard (HTTP Basic Auth)
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import Base, engine, get_db
from models import Article
from routers import admin, users
from routers.v1 import articles, headlines, sources, trending
from routers.api import health as api_health
from routers.api import app_auth, chatbot, news as api_news, sentiment, trading
from routers.api import sec as api_sec, research as api_research
from routers.api import llm as api_llm
from services.news_aggregator import refresh_articles, seed_sources

logger = logging.getLogger(__name__)

# ── Background periodic refresh ───────────────────────────────────────────────

_REFRESH_INTERVAL_SECONDS = 10 * 60  # refresh every 10 minutes


async def _background_refresh():
    """Continuously re-fetches articles every 10 minutes."""
    while True:
        await asyncio.sleep(_REFRESH_INTERVAL_SECONDS)
        db = next(get_db())
        try:
            count = await refresh_articles(db)
            logger.info("Background refresh: +%d articles", count)
        except Exception as exc:
            logger.error("Background refresh failed: %s", exc)
        finally:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create / migrate tables (also creates new AppUser / Portfolio / Position tables)
    Base.metadata.create_all(bind=engine)

    # Seed sources then do an initial article fetch
    db = next(get_db())
    try:
        seed_sources(db)
        count = await refresh_articles(db)
        logger.info("Startup refresh: %d articles fetched", count)
    except Exception as exc:
        logger.error("Startup refresh failed (will retry in background): %s", exc)
    finally:
        db.close()

    # Start the background refresh loop
    task = asyncio.create_task(_background_refresh())

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


_DESCRIPTION = """
## News API + STO Backend

A RESTful service that aggregates, indexes, and serves news articles from
multiple publishers — and powers the STO (Social Trend Observant) frontend.

### Authentication

**v1 endpoints** (`/v1/*`) use API-key auth:
* Header (preferred): `X-Api-Key: YOUR_KEY`
* Query param: `?apiKey=YOUR_KEY`
Register for a free key at `POST /users/register`.

**Frontend endpoints** (`/api/*`) use JWT Bearer auth:
* Sign up at `POST /api/auth/signup`, log in at `POST /api/auth/login`
* Pass the returned token as `Authorization: Bearer <token>`

### Rate limits (v1)

| Tier       | Requests / day | Requests / min |
|------------|---------------:|---------------:|
| Free       | 1,000          | 10             |
| Developer  | 10,000         | 60             |
| Business   | 100,000        | 300            |
| Enterprise | Unlimited      | Custom         |
"""

app = FastAPI(
    title="News API + STO Backend",
    description=_DESCRIPTION,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────────────────

origins = [
    "https://stock-search-three.vercel.app","https://stock-search-three.vercel.app/",
    "http://localhost:3000", # Good for local testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,             # Use the list, not ["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Custom exception handler ──────────────────────────────────────────────────
# Flatten HTTPException detail so the frontend can read body.error directly.

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail)},
    )


# ── v1 API routes (API-key auth) ──────────────────────────────────────────────

app.include_router(articles.router, prefix="/v1")
app.include_router(headlines.router, prefix="/v1")
app.include_router(sources.router,   prefix="/v1")
app.include_router(trending.router,  prefix="/v1")

# ── STO frontend routes (JWT Bearer auth) ────────────────────────────────────

app.include_router(api_health.router, prefix="/api", tags=["frontend"])
app.include_router(app_auth.router,   prefix="/api", tags=["frontend"])
app.include_router(sentiment.router,  prefix="/api", tags=["frontend"])
app.include_router(trading.router,    prefix="/api", tags=["frontend"])
app.include_router(chatbot.router,    prefix="/api", tags=["frontend"])
app.include_router(api_news.router,   prefix="/api", tags=["frontend"])
app.include_router(api_sec.router,    prefix="/api", tags=["frontend"])
app.include_router(api_research.router, prefix="/api", tags=["frontend"])
app.include_router(api_llm.router,    prefix="/api", tags=["frontend"])

# ── Management routes ─────────────────────────────────────────────────────────

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])


# ── Root ──────────────────────────────────────────────────────────────────────

@app.post("/api/refresh", tags=["frontend"])
async def manual_refresh():
    """Manually trigger an article refresh — useful after first install."""
    db = next(get_db())
    try:
        count = await refresh_articles(db)
        total = db.query(Article).count()
        return {"status": "ok", "new_articles": count, "total_articles": total}
    except Exception as exc:
        logger.error("Manual refresh failed: %s", exc)
        raise HTTPException(status_code=500, detail={"error": f"Refresh failed: {exc}"})
    finally:
        db.close()


@app.get("/", tags=["root"], response_model=dict[str, Any])
async def root() -> dict:
    return {
        "name": "News API + STO Backend",
        "version": "2.0.0",
        "documentation": {"swagger_ui": "/docs", "redoc": "/redoc"},
        "endpoints": {
            # v1 (API-key)
            "articles":  "/v1/articles",
            "headlines": "/v1/headlines",
            "sources":   "/v1/sources",
            "trending":  "/v1/trending",
            "register":  "/users/register",
            # Frontend (JWT)
            "health":             "/api/health",
            "signup":             "/api/auth/signup",
            "login":              "/api/auth/login",
            "sentiment_overview": "/api/sentiment/overview",
            "sec_filings":        "/api/sec/filings/{symbol}",
            "sec_analysis":       "/api/sec/filings/{symbol}/analysis",
            "stock_research":     "/api/research/{symbol}",
            "portfolio":          "/api/trading/portfolio",
            "prices":             "/api/trading/prices",
            "chat":               "/api/chatbot/message",
        },
    }
