# STO — Error Handling, Logging & Middleware

> Complete documentation of the exception hierarchy, logging infrastructure, middleware stack, CORS configuration, and request lifecycle.

---

## Exception Hierarchy (`exceptions.py`)

STO defines a structured exception system that returns consistent JSON error bodies across all endpoints.

```
APIException (base)
  ├── ParameterInvalidError     → 400, code: "parameterInvalid"
  ├── ParametersMissingError    → 400, code: "parametersMissing"
  ├── ApiKeyMissingError        → 401, code: "apiKeyMissing"
  ├── ApiKeyInvalidError        → 401, code: "apiKeyInvalid"
  ├── ApiKeyDisabledError       → 403, code: "apiKeyDisabled"
  ├── ApiKeyExhaustedError      → 429, code: "apiKeyExhausted"
  ├── RateLimitError            → 429, code: "rateLimited"
  ├── ServerError               → 500, code: "serverError"
  ├── DataFetchError            → 502, code: "dataFetchError"
  ├── TickerValidationError     → 400, code: "parameterInvalid"
  └── InvalidDataError          → 500, code: "invalidData"
```

### `APIException` Base Class

```python
class APIException(HTTPException):
    def __init__(self, status_code, code, message):
        super().__init__(
            status_code=status_code,
            detail={
                "status": "error",
                "code": code,
                "message": message,
            },
        )
```

### Standard Error Response Shape
```json
{
  "status": "error",
  "code": "apiKeyMissing",
  "message": "Your API key is missing. Provide it via the X-Api-Key header or the apiKey query parameter."
}
```

### Exception Usage Patterns

| Exception | Raised By | Trigger |
|-----------|-----------|---------|
| `ApiKeyMissingError` | `auth.py` → `get_current_user()` | No API key in request |
| `ApiKeyInvalidError` | `auth.py` → `get_current_user()` | Key not found in DB |
| `ApiKeyDisabledError` | `auth.py` → `get_current_user()` | `user.is_active == False` |
| `ApiKeyExhaustedError` | `auth.py` → `get_current_user()` | Daily rate limit exceeded |
| `RateLimitError` | `auth.py` → `get_current_user()` | Per-minute rate limit exceeded |
| `ParameterInvalidError` | v1 routers | Bad `sortBy`, `window`, future `from` date |
| `TickerValidationError` | `yahoo.py`, `news.py` | Invalid ticker format |
| `DataFetchError` | `yahoo.py` | yfinance network failure |
| `InvalidDataError` | `yahoo.py` | Empty/corrupt response data |

---

## Logging Infrastructure (`logging_config.py`)

### Configuration

```python
LOG_DIR = "logs"
LOG_FILE = "logs/finance_api.log"

# File handler — captures everything
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10 * 1024 * 1024,    # 10 MB
    backupCount=5,                 # Keep 5 rotated files
    encoding="utf-8",
)
file_handler.setLevel(logging.DEBUG)

# Console handler — warnings and above only
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)

# Format
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
```

### Log Levels by Module

| Module | Typical Log Level | Example Messages |
|--------|-------------------|------------------|
| `news_aggregator` | INFO | `+15 new articles from BBC News` |
| `ticker_news` | INFO/WARNING | `Fetching ticker AAPL from 14 sources`, `RSS cooldown active` |
| `sec_service` | INFO/WARNING | `SEC: loaded 13000 ticker→CIK mappings`, `SEC: failed for XYZ` |
| `market_data` | INFO/WARNING | `Finviz: fetched 42 metrics for AAPL`, `Finviz scrape failed` |
| `social_service` | DEBUG/WARNING | `reddit cache hit for AAPL`, `reddit rate limited on r/stocks` |
| `congress_service` | ERROR | `Congress service error for AAPL: ...` |
| `llm_analyst` | INFO/WARNING | `Starting analysis stream for AAPL`, `Ollama connection refused` |
| `content_extractor` | INFO/WARNING | `Extracted 5000 chars from URL`, `Extraction failed` |
| `auth` | WARNING | `Invalid API key attempt` |
| `main` | INFO | `Starting background article refresh`, `Refresh complete` |

### Log File Location
```
newsapi2/
  └── logs/
      ├── finance_api.log          # Current log
      ├── finance_api.log.1        # Previous rotation
      ├── finance_api.log.2
      ├── finance_api.log.3
      ├── finance_api.log.4
      └── finance_api.log.5        # Oldest rotation
```

---

## Middleware Stack

### CORS Middleware

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # ⚠️ Wide open — restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Rate Limit Headers (v1 API only)

Injected by `auth.py` → `get_current_user()` into the `Response` object:

```
X-RateLimit-Limit: 10              # Per-minute limit for this tier
X-RateLimit-Remaining: 7           # Requests remaining in current window
X-RateLimit-Reset: 1714060800      # Unix timestamp when window resets
X-RateLimit-Limit-Day: 1000        # Daily limit
X-RateLimit-Remaining-Day: 950     # Daily remaining
X-RateLimit-Reset-Day: 1714147200  # Daily reset timestamp
```

### Admin Auth Middleware (`middleware/admin_auth.py`)

HTTP Basic authentication for `/admin/*` routes:

```python
async def verify_admin(credentials: HTTPBasicCredentials):
    admin_username, admin_password = get_admin_credentials()

    is_username_correct = secrets.compare_digest(
        credentials.username.encode("utf8"),
        admin_username.encode("utf8")
    )
    is_password_correct = secrets.compare_digest(
        credentials.password.encode("utf8"),
        admin_password.encode("utf8")
    )

    if not (is_username_correct and is_password_correct):
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})
```

**Security:** Uses `secrets.compare_digest()` for constant-time comparison (prevents timing attacks).

---

## Request Lifecycle

### Frontend API Request (`/api/*`)

```
1. Client sends request with Authorization: Bearer <JWT>
2. FastAPI middleware: CORS headers added
3. Route handler called
4. Dependency injection:
   a. get_db() → SQLAlchemy session
   b. get_required_app_user() → decode JWT → query AppUser from DB
5. Business logic executes
6. Response serialized as JSON
7. DB session closed (finally block in get_db)
```

### v1 API Request (`/v1/*`)

```
1. Client sends request with X-Api-Key header or ?apiKey= query
2. FastAPI middleware: CORS headers added
3. Route handler called
4. Dependency injection:
   a. get_db() → SQLAlchemy session
   b. get_current_user():
      i.   Extract API key from header/query
      ii.  Validate key against DB
      iii. Check is_active flag
      iv.  Run rate_limit_store.check_and_record()
      v.   Inject X-RateLimit-* headers
      vi.  Return User object
5. Check cache (TTLCache.get)
6. Execute query/service call
7. Cache result (TTLCache.set)
8. Return response
```

### Background Task Lifecycle

```
1. App startup (lifespan context manager):
   a. Base.metadata.create_all() → create DB tables
   b. seed_sources(db) → insert/update 20 RSS sources
   c. refresh_articles(db) → initial fetch
   d. asyncio.create_task(bg_loop) → start refresh loop

2. bg_loop runs every 600 seconds:
   a. refresh_articles(db)
   b. asyncio.sleep(600)

3. App shutdown:
   a. bg_task.cancel()
   b. await bg_task (suppresses CancelledError)
```

---

## JWT Authentication Details (`app_auth_utils.py`)

### Token Generation

```python
SECRET_KEY = os.getenv("JWT_SECRET", "sto-jwt-secret-key-change-in-production-2024")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30

def create_access_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
```

### Token Validation

```python
def get_required_app_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> AppUser:
    # 1. Extract token from "Bearer <token>"
    # 2. jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    # 3. Extract user_id from "sub" claim
    # 4. Query AppUser from DB
    # 5. Raise 401 if user not found
```

### Password Hashing

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

**bcrypt note:** Silently truncates passwords to 72 bytes. This is standard bcrypt behavior.

### Optional Auth

`get_optional_app_user()` — Same flow but returns `None` instead of raising 401. Used by chatbot endpoint.

---

## Rate Limiting Deep Dive (`utils/rate_limit.py`)

### Algorithm: Sliding Window

```
For each API key, maintain two lists of timestamps:
  - minute_window: [t1, t2, t3, ...]    (last 60 seconds)
  - day_window:    [t1, t2, t3, ...]    (last 86,400 seconds)

On each request:
  1. Prune expired timestamps from both lists
  2. Check minute_window length < per_minute limit
  3. Check day_window length < daily limit
  4. If allowed, append current timestamp to both lists
  5. Return (allowed, rate_info_dict)
```

### Rate Info Dict Shape
```python
{
    "limit": 10,              # Per-minute limit
    "remaining": 7,           # Remaining in current minute window
    "reset": 1714060860,      # Unix timestamp when minute window resets
    "limit_day": 1000,        # Daily limit
    "remaining_day": 993,     # Remaining in daily window
    "reset_day": 1714147200,  # Unix timestamp when daily window resets
    "exhausted_type": "minute"  # Only present on denial
}
```

### Thread Safety
In-memory dict — safe for single-process/single-worker deployments only. For multi-worker, must migrate to Redis.
