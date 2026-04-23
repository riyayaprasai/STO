# STO — Data Models, Schemas & ORM Deep Dive

> Complete breakdown of every SQLAlchemy model, Pydantic schema, helper function, and model relationship.

---

## ORM Models (`models.py`)

### Model Relationships

```
User (v1 API users)          AppUser (frontend users)
  │                            │
  │ one-to-many                │ one-to-one      one-to-many
  │ (conceptual)               ├──────────────► Portfolio
  │                            │                   │
  ▼                            │                   │ one-to-many
Source ──one-to-many──► Article │                   │
                               └──────────────► Position
```

### `User` — API-Key Users (v1 Endpoints)

```python
class User(Base):
    __tablename__ = "users"
    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String, unique=True, index=True)
    email      = Column(String, unique=True, index=True)
    api_key    = Column(String, unique=True, default=generate_api_key)
    tier       = Column(String, default="free")          # free|developer|business|enterprise
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Helper function:** `generate_api_key()` → `secrets.token_urlsafe(32)` (43-char URL-safe string)
**Factory function:** `create_user(db, username, email)` → creates user + auto-generates API key

---

### `Source` — RSS Feed Registry

```python
class Source(Base):
    __tablename__ = "sources"
    id          = Column(String, primary_key=True)        # e.g. "bbc-news", "ticker-aapl"
    name        = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    url         = Column(String, nullable=True)           # Publisher homepage
    rss_url     = Column(String, nullable=True)           # RSS feed URL
    category    = Column(String, nullable=True)
    language    = Column(String, default="en")
    country     = Column(String, nullable=True)
    is_active   = Column(Boolean, default=True)
```

**Special behavior:** Ticker-specific sources (e.g., `ticker-aapl`) are dynamically created by `ticker_news.py` and marked `is_active=True`.

---

### `Article` — Aggregated News

```python
class Article(Base):
    __tablename__ = "articles"
    id           = Column(String, primary_key=True)       # art_<12 random chars>
    source_id    = Column(String, index=True)
    source_name  = Column(String, nullable=True)          # Denormalized for read speed
    author       = Column(String, nullable=True)
    title        = Column(String, nullable=False)
    description  = Column(Text, nullable=True)
    url          = Column(String, unique=True)
    url_to_image = Column(String, nullable=True)
    published_at = Column(DateTime, index=True)
    sentiment    = Column(String, nullable=True)          # "very positive"|"positive"|"neutral"|"negative"|"very negative"
    content_hash = Column(String, unique=True)            # MD5(url) for dedup
    category     = Column(String, nullable=True)
    language     = Column(String, nullable=True)
    country      = Column(String, nullable=True)
```

**Deduplication:** `content_hash = hashlib.md5(url.encode()).hexdigest()`. Before insert, queries for existing hash. If found, skips.

**ID generation:** `utils/id_generator.py` → `art_` + 12 random lowercase+digits via `secrets.choice()`.

---

### `AppUser` — JWT-Authenticated Frontend Users

```python
class AppUser(Base):
    __tablename__ = "app_users"
    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)        # bcrypt via passlib
    created_at    = Column(DateTime, default=datetime.utcnow)
```

---

### `Portfolio` — Virtual Trading Account

```python
class Portfolio(Base):
    __tablename__ = "portfolios"
    id      = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)             # FK to app_users
    cash    = Column(Float, default=100_000.0)            # Starts at $100K
```

**Auto-created:** On signup via `app_auth.py` → `signup()`, or lazily via `trading.py` → `_get_or_create_portfolio()`.

---

### `Position` — Stock Holdings

```python
class Position(Base):
    __tablename__ = "positions"
    id        = Column(Integer, primary_key=True, index=True)
    user_id   = Column(Integer, nullable=False)           # FK to app_users
    symbol    = Column(String, nullable=False)             # e.g. "AAPL"
    quantity  = Column(Integer, default=0)
    avg_price = Column(Float, default=0.0)                # Weighted average
```

**Avg price calculation** (on buy):
```python
total_qty = position.quantity + new_quantity
position.avg_price = (position.avg_price * position.quantity + price * new_quantity) / total_qty
```

---

## Pydantic Schemas (`schemas.py`)

### v1 API Schemas

| Schema | Purpose | Key Fields |
|--------|---------|------------|
| `ArticleSourceRef` | Nested source reference | `id`, `name` |
| `ArticleSchema` | Full article representation | `id`, `source`, `author`, `title`, `description`, `url`, `url_to_image`, `published_at`, `category`, `language`, `country`, `sentiment` |
| `ArticleDetailSchema` | Extended with related | Inherits ArticleSchema + `related_articles: list[RelatedArticleStub]` |
| `RelatedArticleStub` | Compact related article | `id`, `title`, `url`, `published_at` |
| `ArticlesResponse` | Paginated article list | `status="ok"`, `total_results`, `page`, `page_size`, `articles: list[ArticleSchema]` |
| `ArticleDetailResponse` | Single article wrapper | `status="ok"`, `article: ArticleDetailSchema` |
| `HeadlinesResponse` | Headlines list | Same as ArticlesResponse |
| `SourceSchema` | Source metadata | `id`, `name`, `description`, `url`, `category`, `language`, `country` |
| `SourcesResponse` | Source list wrapper | `status="ok"`, `sources: list[SourceSchema]` |
| `TopicSchema` | Trending topic | `term`, `count`, `trend: Literal["rising","stable","declining"]` |
| `TrendingResponse` | Trending wrapper | `window`, `topics: list[TopicSchema]` |

### Admin Schemas

| Schema | Purpose | Key Fields |
|--------|---------|------------|
| `UserCreate` | Self-registration | `username`, `email` |
| `AdminUserCreate` | Admin user creation | `username`, `email`, `tier` (default `"free"`) |
| `UserTierUpdate` | Tier change | `tier: Literal["free","developer","business","enterprise"]` |
| `UserResponse` | User display | `id`, `username`, `email`, `api_key`, `tier`, `is_active`, `created_at` |

### Frontend Auth Schemas (in `routers/api/app_auth.py`)

| Schema | Purpose | Key Fields |
|--------|---------|------------|
| `AuthRequest` | Login/signup body | `email: EmailStr`, `password: str` |
| `UserOut` | Returned user data | `id: str`, `email: str` |
| `AuthResponse` | Auth response | `token: str`, `user: UserOut` |

### Trading Schemas (in `routers/api/trading.py`)

| Schema | Purpose | Key Fields |
|--------|---------|------------|
| `OrderRequest` | Buy/sell order | `symbol: str`, `side: str` ("buy"\|"sell"), `quantity: int` |

### Chatbot Schema (in `routers/api/chatbot.py`)

| Schema | Purpose | Key Fields |
|--------|---------|------------|
| `ChatRequest` | Chat message | `message: str` |

---

## Schema Validation Rules

| Field | Validation |
|-------|-----------|
| `email` | Pydantic `EmailStr` — RFC-compliant email validation |
| `password` | Minimum 6 characters (checked in signup endpoint) |
| `tier` | Must be one of: `free`, `developer`, `business`, `enterprise` |
| `page` | `ge=1` (minimum 1) |
| `page_size` / `pageSize` | `ge=1, le=100` (1-100 range) |
| `sort_by` / `sortBy` | Must be: `relevancy`, `publishedAt`, or `popularity` |
| `from` date | Cannot be in the future |
| `window` | Must be one of: `1h`, `6h`, `24h`, `7d` |
| `chart_range` | Must be: `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, `max` |

---

## Database Session Management (`database.py`)

```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./users.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Required for SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI dependency — yields a DB session, ensures close on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**`check_same_thread=False`** is required because SQLite doesn't allow cross-thread access by default, but FastAPI's dependency injection may use different threads.
