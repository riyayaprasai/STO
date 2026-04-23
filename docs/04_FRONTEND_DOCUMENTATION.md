# STO — Frontend Documentation

> Complete breakdown of the Next.js 16 frontend: pages, components, state management, API integration, and design system.

---

## Tech Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| Next.js | 16.2.4 | App Router framework |
| React | 18.2 | UI library |
| TypeScript | 5.0 | Type safety |
| TailwindCSS | 3.4 | Utility-first styling |
| Recharts | 3.8.1 | Interactive charts |
| react-markdown | 10.1.0 | Markdown rendering (AI reports) |

---

## Design System (`tailwind.config.js`)

Custom `sto-*` design tokens:

| Token | Value | Usage |
|-------|-------|-------|
| `sto-bg` | `#f5f4f0` | Page background (warm off-white) |
| `sto-card` | `#ffffff` | Card backgrounds |
| `sto-cardBorder` | `#e8e6e1` | Card/input borders |
| `sto-accent` | `#0d9488` | Primary teal accent (buttons, links) |
| `sto-accentLight` | `#2dd4bf` | Light accent for highlights |
| `sto-muted` | `#6b7280` | Secondary text |
| `sto-text` | `#374151` | Primary text |
| `sto-danger` | `#dc2626` | Error/sell indicators |
| `sto-positive` | `#16a34a` | Success/buy indicators |

Custom border radius: `sto` (1rem), `sto-lg` (1.25rem).
Custom shadows: `sto` (subtle), `sto-hover` (elevated).

---

## State Management

### AuthContext (`contexts/AuthContext.tsx`)
React Context providing authentication state across the app.

**State:**
- `user: AuthUser | null` — current user (`{ id, email }`)
- `loading: boolean` — initial hydration check

**Actions:**
- `login(email, password)` → calls `api.login()`, stores token + user in localStorage, returns error string or null
- `signup(email, password)` → calls `api.signup()`, seeds portfolio, same flow
- `logout()` → clears localStorage, resets user state

**Token Storage** (`lib/auth.ts`):
- `sto_token` → JWT string in localStorage
- `sto_user` → JSON-serialized `{ id, email }` in localStorage
- `getAuthHeaders()` → returns `{ Authorization: "Bearer <token>" }` for API calls

---

## API Client (`lib/api.ts`)

### Configuration
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";
```

### `fetchApi<T>(path, options?)` — Core HTTP Helper
- Auto-attaches JWT auth headers (opt-out with `{ auth: false }`)
- Sets `Content-Type: application/json`
- Parses error bodies for user-friendly messages
- Throws `Error` on non-2xx responses

### Type Definitions (18 types exported)
| Type | Fields |
|------|--------|
| `NewsArticle` | id, title, description, url, source, category, sentiment, published_at |
| `TrendingTopic` | term, count, trend |
| `SECFiling` | form, filing_date, period, company, description, url, items |
| `MarketStats` | price, change, change_percent, market_cap, pe_ratio, ... (30+ fields) |
| `RedditPost` | title, score, num_comments, subreddit, url, created_utc, upvote_ratio |
| `CongressTrade` | politician, party, trade_type, amount_range, trade_date, ticker, committee, impact_score |
| `StocktwitPost` | id, created_at, body, username, avatar_url, sentiment |
| `StockResearch` | ticker, company, market_data, articles, filings, reddit_posts, stocktwits_posts, congress_trades, data_sources |

### API Methods (20 methods)
| Method | Endpoint | Auth |
|--------|----------|------|
| `api.health()` | `GET /api/health` | Yes |
| `api.sentimentOverview()` | `GET /api/sentiment/overview` | Yes |
| `api.sentimentSymbol(sym)` | `GET /api/sentiment/symbol/{sym}` | Yes |
| `api.sentimentTrends(sym, days)` | `GET /api/sentiment/trends` | Yes |
| `api.newsHeadlines(cat?, page)` | `GET /api/news/headlines` | No |
| `api.newsSearch(q, page, size)` | `GET /api/news/search` | No |
| `api.newsTrending(window)` | `GET /api/news/trending` | No |
| `api.secFilings(sym)` | `GET /api/sec/filings/{sym}` | No |
| `api.secFilingsAnalysis(sym)` | `GET /api/sec/filings/{sym}/analysis` | No |
| `api.stockResearch(sym)` | `GET /api/research/{sym}` | No |
| `api.searchTicker(query)` | `GET /api/search` | No |
| `api.fetchChartData(sym, range)` | `GET /api/chart/{sym}` | No |
| `api.signup(email, pass)` | `POST /api/auth/signup` | No |
| `api.login(email, pass)` | `POST /api/auth/login` | No |
| `api.portfolio()` | `GET /api/trading/portfolio` | Yes |
| `api.positions()` | `GET /api/trading/portfolio/positions` | Yes |
| `api.placeOrder(sym, side, qty)` | `POST /api/trading/portfolio/order` | Yes |
| `api.prices(symbols[])` | `GET /api/trading/prices` | Yes |
| `api.chat(message)` | `POST /api/chatbot/message` | Yes |
| `api.llmAnalyzeStreamUrl(sym)` | Returns raw URL for SSE | N/A |

---

## Pages

### 1. Dashboard (`app/page.tsx` — 13KB)
The home page. Displays:
- Health status indicator (live/mock data badge)
- Sentiment overview (overall score, source breakdown)
- Top tracked symbols with sentiment scores
- Latest headlines carousel
- Trending topics (bigrams from recent articles)
- News search with category filters

### 2. Sentiment Research (`app/sentiment/page.tsx` — 63KB)
**The largest and most complex page.** A comprehensive stock research terminal:

**Search Bar:** Ticker search with fuzzy matching (via Yahoo Finance API), natural language queries.

**7 Tabs:**
1. **Overview** — Price header, 30-day chart (Recharts LineChart), market stats grid (30+ metrics organized by category: Price, Valuation, Profitability, Balance Sheet, Growth, Dividends)
2. **News** — Article cards with sentiment badges, source attribution, published dates
3. **SEC Filings** — Filing type badges (10-K, 10-Q, 8-K), dates, descriptions, EDGAR links
4. **Social** — Reddit posts (score, comments, subreddit) + StockTwits messages with sentiment labels
5. **Politics** — Congressional trades (politician, party, buy/sell, amount range, committee, impact score)
6. **AI Analyst** — Streams institutional research memo from Ollama via SSE, renders markdown in real-time, supports file upload (PDF/HTML) for deep-dive analysis, follow-up chat
7. **Financials** — Full financial data grid organized in 7 categories

**Key Implementation Details:**
- Uses `EventSource`-like fetch with `text/event-stream` parsing for LLM streaming
- Uploaded files are sent to `/api/llm/upload/{symbol}`, extracted text returned, then fed to analysis
- Chat history maintained in component state, sent with each follow-up request

### 3. Trading Simulator (`app/trading/page.tsx` — 18KB)
Paper trading with virtual $100K:
- Portfolio overview (cash, total value, positions table)
- Order form (symbol, side, quantity)
- Simulated prices (deterministic-random, hourly rotation)
- Position P&L tracking
- Requires authentication (redirects to login if not signed in)

### 4. Chat (`app/chat/page.tsx` — 7KB)
Rule-based chatbot interface:
- Chat bubble UI (user messages right-aligned, bot left-aligned)
- Pre-built use-case cards and quick prompts
- Auto-scroll to latest message
- "How it works" sidebar

### 5. Login (`app/login/page.tsx` — 3KB)
- Email/password form
- Error display
- Link to signup
- Redirects to `/trading` on success
- Auto-redirects if already logged in

### 6. Signup (`app/signup/page.tsx` — 4KB)
- Email/password/confirm form
- Client-side validation (password match, 6-char minimum)
- Link to login
- Same redirect behavior as login

### 7. Wireframe (`app/wireframe/page.tsx` — 4KB)
Visual documentation/wireframe of the application layout and features.

---

## Components

### Header (`components/Header.tsx`)
Global navigation bar rendered in root layout:
- **Left:** STO logo + "Social Trend Observant" tagline
- **Center:** Nav links — Dashboard, Sentiment, Practice Trading, Chat, Wireframe
- **Right:** User email + Logout button (if authenticated) OR Login + Sign up buttons
- Glassmorphism effect (`bg-sto-card/95 backdrop-blur`)

### Root Layout (`app/layout.tsx`)
```
<html>
  <body>
    <AuthProvider>
      <Header />
      <main>{children}</main>
      <footer>STO — For learning only; not financial advice.</footer>
    </AuthProvider>
  </body>
</html>
```

---

## Environment Configuration

### Frontend (`frontend/.env.local`)
```bash
NEXT_PUBLIC_API_URL=http://localhost:5000  # Backend URL
```

### Backend (`newsapi2/.env`)
```bash
ADMIN_USERNAME=admin
ADMIN_PASSWORD=1234
NEWSAPI_KEY=vp3BRS...        # Legacy key
JWT_SECRET=sto-jwt-secret... # JWT signing key (defaults if not set)
DATABASE_URL=sqlite:///./users.db  # Database path
```
