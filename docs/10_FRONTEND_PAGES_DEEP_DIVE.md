# STO — Frontend Pages Deep Dive & UI Patterns

> Detailed component-level breakdown of every page, state management patterns, data loading strategies, and UI implementation details.

---

## Page Architecture

```
app/
├── layout.tsx       → Root layout (AuthProvider → Header → {children} → Footer)
├── page.tsx         → Dashboard (13KB, 316 lines)
├── sentiment/
│   └── page.tsx     → Stock Research Terminal (63KB — largest file)
├── trading/
│   └── page.tsx     → Paper Trading Simulator (18KB, 421 lines)
├── chat/
│   └── page.tsx     → Rule-Based Chatbot (7KB, 160 lines)
├── login/
│   └── page.tsx     → Login Form (3KB, 84 lines)
├── signup/
│   └── page.tsx     → Registration Form (4KB, 106 lines)
└── wireframe/
    └── page.tsx     → UX Wireframe/Prototype (4KB, 93 lines)
```

---

## 1. Dashboard Page (`app/page.tsx`)

### State
```typescript
const [overview, setOverview]       = useState<Overview | null>(null);
const [headlines, setHeadlines]     = useState<NewsArticle[]>([]);
const [trending, setTrending]       = useState<TrendingTopic[]>([]);
const [totalArticles, setTotalArticles] = useState(0);
const [loading, setLoading]         = useState(true);
const [mockData, setMockData]       = useState(false);
const [searchQuery, setSearchQuery] = useState("");
```

### Data Loading (on mount)
```typescript
Promise.all([
  api.sentimentOverview(),
  api.health(),
  api.newsHeadlines(undefined, 1),
  api.newsTrending("24h"),
])
```
All 4 requests fire concurrently. Results merged on completion.

### UI Sections (top to bottom)
1. **Hero Search** — Input field + quick-ticker pill buttons (AAPL, TSLA, NVDA, MSFT, GME, META, AMZN, GOOGL). Submit navigates to `/sentiment?symbol=XXX`.
2. **Mock Data Banner** — Yellow alert if `health.mock_data === true` (DB empty).
3. **Sentiment Overview Cards** (3-column grid):
   - Overall sentiment score (0-100%) with gradient progress bar
   - By category breakdown (top 4 categories with scores + volumes)
   - Top tickers by mention count (linked to sentiment page)
4. **Trending Topics** — Only shows `rising` trends. Each topic is a clickable button that navigates to sentiment search.
5. **Latest Headlines** — 8 most recent articles. Each row: title (link), description, source, time ago, category, sentiment badge.
6. **Feature Cards** (3-column grid) — Sentinel, Trading, Chat promo cards.

### Helper Components
- `SentimentBadge({ s })` — Color-coded pill (emerald for positive, amber for neutral, red for negative).
- `timeAgo(iso)` — Converts ISO date to "5m ago", "3h ago", "2d ago".

---

## 2. Sentiment / Research Terminal (`app/sentiment/page.tsx`)

**The most complex page at 63KB.** Acts as a full stock research terminal.

### State (abridged)
```typescript
const [symbol, setSymbol]         = useState("");
const [research, setResearch]     = useState<StockResearch | null>(null);
const [activeTab, setActiveTab]   = useState("overview");
const [chartData, setChartData]   = useState([]);
const [chartRange, setChartRange] = useState("1mo");
const [llmReport, setLlmReport]   = useState("");
const [llmLoading, setLlmLoading] = useState(false);
const [chatHistory, setChatHistory] = useState([]);
const [uploadedText, setUploadedText] = useState<string | null>(null);
```

### Search Flow
1. User types query in search bar
2. `api.searchTicker(query)` → fuzzy match via Yahoo Finance
3. If found, sets `symbol` state
4. `api.stockResearch(symbol)` → loads all data sources
5. `api.fetchChartData(symbol, range)` → loads chart data
6. Data populates all 7 tabs

### 7 Tabs

**Tab 1: Overview**
- Price header with change % (green/red)
- Interactive line chart (Recharts `LineChart` + `Tooltip` + `ResponsiveContainer`)
- Chart range selector: 1D, 5D, 1M, 3M, 6M, YTD, 1Y, 2Y, 5Y, 10Y, MAX
- Market stats grid organized by: Price, Valuation, Profitability, Balance Sheet, Growth, Dividends
- Each metric formatted with `$` or `%` suffix as appropriate

**Tab 2: News**
- Article cards with sentiment badges
- Source name, published date, description
- External link to original article

**Tab 3: SEC Filings**
- Filing type badges (color-coded: 10-K=blue, 10-Q=teal, 8-K=amber)
- Filing date, period, description
- Direct link to EDGAR filing

**Tab 4: Social**
- Reddit posts section (score, comments, subreddit, relative time)
- StockTwits messages section (body text, username, sentiment label)

**Tab 5: Politics**
- Congressional trades table
- Party badge (D=blue, R=red)
- Trade type (Buy=green, Sell=red)
- Amount range, date, committee
- Impact score bar

**Tab 6: AI Analyst**
- "Generate Report" button triggers SSE stream
- Streaming implementation:
  ```typescript
  const response = await fetch(url, { method: "POST", body: JSON.stringify(payload) });
  const reader = response.body?.getReader();
  // Read chunks, parse SSE "data: {...}" lines
  // Extract tokens, append to report string
  // Render via react-markdown
  ```
- File upload (PDF/HTML) via `/api/llm/upload/{symbol}`
- Follow-up chat input with conversation history
- All messages displayed with markdown rendering

**Tab 7: Financials**
- Full financial data grid
- 7 categories: Overview, Valuation, Profitability, Balance Sheet, Growth, Cash Flow, Dividends
- Each metric with label and formatted value

---

## 3. Trading Page (`app/trading/page.tsx`)

### Auth Guard
If `user` is null (not logged in), renders a centered CTA card with login/signup buttons instead of the trading interface.

### State
```typescript
const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
const [prices, setPrices]       = useState<Record<string, number>>({});
const [symbol, setSymbol]       = useState("AAPL");  // or URL param
const [side, setSide]           = useState<"buy" | "sell">("buy");
const [quantity, setQuantity]   = useState(10);
const [news, setNews]           = useState<NewsArticle[]>([]);
const [symbolSentiment, setSymbolSentiment] = useState(null);
```

### Supported Symbols
```typescript
const ALL_SYMBOLS = ["AAPL","GOOGL","MSFT","GME","AMC","NVDA","TSLA","META","AMZN","NFLX"];
```

### Data Loading
- On mount: `api.portfolio()` + `api.prices(ALL_SYMBOLS)` concurrently
- On symbol change: `api.newsSearch(symbol, 1, 4)` + `api.sentimentSymbol(symbol)` concurrently

### Layout (3-column)
- **Left (2/3):** Portfolio summary card → Order form → Price grid (10 symbols)
- **Right (1/3):** Sentiment card for selected symbol → Latest news (4 articles) → Tip card

### Order Form
- Stock selector (dropdown with live prices)
- Buy/Sell toggle
- Quantity input (min 1)
- Cost estimate (price × quantity)
- Current position display (if holding)
- Success/error feedback messages

### Suspense Boundary
Wrapped in `<Suspense>` because it uses `useSearchParams()` (Next.js requirement).

---

## 4. Chat Page (`app/chat/page.tsx`)

### Initial State
Pre-seeded with a welcome message from the bot.

### Layout (2-column)
- **Left (2/3):** Chat window with bubble messages
  - User messages: right-aligned, teal background
  - Bot messages: left-aligned, white with border
  - Loading state: pulsing "Thinking..." bubble
  - Auto-scroll to bottom on new messages
- **Right (1/3):** Three sidebar cards:
  - Use-case cards (clickable, sends the text as message)
  - Quick prompts grid (4 topics)
  - "How it works" numbered list

### Message Flow
```typescript
async function sendMessage(text: string) {
  setMessages(m => [...m, { role: "user", text }]);
  const res = await api.chat(text);
  setMessages(m => [...m, { role: "bot", text: res.reply }]);
}
```

---

## 5. Wireframe Page (`app/wireframe/page.tsx`)

Static prototype/documentation page with:
- 3 goal cards (See trends, Act with confidence, Learn by asking)
- 3 wireframe sections with component blocks
- "Next steps" card with back-to-dashboard link

---

## Shared UI Patterns

### Sentiment Color Mapping
Used across Dashboard, Trading, and Sentiment pages:
```typescript
const SENTIMENT_COLOR = {
  "very positive": "text-emerald-600 bg-emerald-50",
  "positive":      "text-emerald-600 bg-emerald-50",
  "neutral":       "text-amber-600  bg-amber-50",
  "negative":      "text-red-600    bg-red-50",
  "very negative": "text-red-700    bg-red-100",
};
```

### Time Ago Helper
```typescript
function timeAgo(iso: string | null): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}
```

### Card Pattern
Every data card follows:
```html
<div class="rounded-sto-lg border border-sto-cardBorder bg-sto-card p-4 shadow-sto">
  <p class="text-xs uppercase tracking-wider text-sto-muted mb-2">Section Label</p>
  <!-- Content -->
</div>
```

### Loading State Pattern
- Skeleton pulse: `animate-pulse` with gray bars
- Centered message: `"Loading your dashboard…"` / `"Loading your portfolio…"`
- All data loading uses `Promise.all()` for concurrent fetches

### Auth Redirect Pattern
Login/Signup pages check `if (user) router.replace("/trading")` to prevent re-rendering auth forms for logged-in users.

### Error Handling Pattern
All API calls wrapped in try/catch with fallback:
```typescript
.catch(() => setData(null))  // or setData([])
```
No error toasts — failed data sections simply show "no data" states.
