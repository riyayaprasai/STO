const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

import { getAuthHeaders } from "./auth";

// ── Shared types ──────────────────────────────────────────────────────────────

export type NewsArticle = {
  id: string;
  title: string;
  description: string | null;
  url: string;
  source: string;
  category: string | null;
  sentiment: "very positive" | "positive" | "neutral" | "negative" | "very negative";
  published_at: string | null;
};

export type TrendingTopic = {
  term: string;
  count: number;
  trend: "rising" | "stable" | "declining";
};

export type SECFiling = {
  form: string;
  filing_date: string;
  period: string;
  company: string;
  description: string;
  url: string;
  items: string;
};

export type SECFilingsResponse = {
  ticker: string;
  total: number;
  filings: SECFiling[];
};

export type SECAnalysisResponse = {
  ticker: string;
  company: string;
  filings: SECFiling[];
  sentiment_summary: {
    overall_score: number;
    overall_label: string;
    total_filings: number;
    distribution: Record<string, number>;
  };
};

export type MarketStats = {
  price: number | null;
  change: number;
  change_percent: number;
  market_cap: number | null;
  pe_ratio: number | null;
  dividend_yield: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  volume: number | null;
  description: string | null;
  sector: string | null;
  industry: string | null;
  beta: number | null;
  forward_pe: number | null;
  chart_data: { date: string; price: number }[];
  // Fundamental Metrics
  total_revenue: number | null;
  profit_margins: number | null;
  operating_margins: number | null;
  return_on_equity: number | null;
  debt_to_equity: number | null;
  free_cash_flow: number | null;
  enterprise_to_ebitda: number | null;
  total_cash: number | null;
  peg_ratio: number | null;
  price_to_sales: number | null;
  price_to_book: number | null;
  price_to_cash: number | null;
  price_to_free_cash_flow: number | null;
  quick_ratio: number | null;
  current_ratio: number | null;
  lt_debt_to_equity: number | null;
  return_on_assets: number | null;
  gross_margin: number | null;
  net_income: number | null;
  eps_ttm: number | null;
  eps_next_year: number | null;
  eps_next_quarter: number | null;
  sales_growth_qq: number | null;
  eps_growth_qq: number | null;
  payout_ratio: number | null;
  enterprise_value: number | null;
  roic: number | null;
  target_price: number | null;
};

export type RedditPost = {
  title: string;
  score: number;
  num_comments: number;
  subreddit: string;
  url: string;
  created_utc: number;
  upvote_ratio: number;
};

export type CongressTrade = {
  politician: string;
  party: string;
  trade_type: string;
  amount_range: string;
  trade_date: string;
  ticker: string;
  committee?: string;
  impact_score?: number;
};

export type StocktwitPost = {
  id: number;
  created_at: string;
  body: string;
  username: string;
  avatar_url: string;
  sentiment: string | null;
};

export type StockResearch = {
  ticker: string;
  company: string;
  market_data: MarketStats;
  articles: NewsArticle[];
  total_articles: number;
  filings: SECFiling[];
  total_filings: number;
  reddit_posts: RedditPost[];
  total_reddit: number;
  stocktwits_posts: StocktwitPost[];
  total_stocktwits: number;
  congress_trades: CongressTrade[];
  total_congress: number;
  data_sources: {
    articles_available: boolean;
    filings_available: boolean;
    reddit_available: boolean;
    tweets_available: boolean;
    congress_available: boolean;
    limited_data: boolean;
  };
};

// ── HTTP helper ───────────────────────────────────────────────────────────────

export async function fetchApi<T>(
  path: string,
  options?: RequestInit & { auth?: boolean }
): Promise<T> {
  const auth = options?.auth !== false;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(auth ? getAuthHeaders() : {}),
    ...(options?.headers as Record<string, string>),
  };
  const { auth: _omit, ...rest } = options || {};
  const res = await fetch(`${API_URL}${path}`, {
    ...rest,
    headers,
  });
  if (!res.ok) {
    let msg = `API error: ${res.status}`;
    try {
      const body = (await res.json()) as { error?: string };
      if (body?.error) msg = body.error;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

// ── API surface ───────────────────────────────────────────────────────────────

export const api = {
  // ── Health ──────────────────────────────────────────────────────────────────
  health: () =>
    fetchApi<{ status: string; mock_data?: boolean; total_articles?: number }>(
      "/api/health"
    ),

  // ── Sentiment ───────────────────────────────────────────────────────────────
  sentimentOverview: () =>
    fetchApi<{
      overall_score: number;
      label: string;
      sources: Record<string, { score: number; volume: number }>;
      top_symbols: { symbol: string; score: number; mentions: number }[];
    }>("/api/sentiment/overview"),

  sentimentSymbol: (symbol: string) =>
    fetchApi<{ symbol: string; score: number; label: string; mentions: number }>(
      `/api/sentiment/symbol/${symbol}`
    ),

  sentimentTrends: (symbol: string, days = 7) =>
    fetchApi<{ symbol: string; trend: { date: string; score: number }[] }>(
      `/api/sentiment/trends?symbol=${symbol}&days=${days}`
    ),

  // ── News (public — no auth required) ────────────────────────────────────────
  newsHeadlines: (category?: string, page = 1) =>
    fetchApi<{ total: number; page: number; articles: NewsArticle[] }>(
      `/api/news/headlines?page=${page}${category ? `&category=${encodeURIComponent(category)}` : ""}`,
      { auth: false }
    ),

  newsSearch: (q: string, page = 1, pageSize = 10) =>
    fetchApi<{ total: number; query: string; page: number; articles: NewsArticle[] }>(
      `/api/news/search?q=${encodeURIComponent(q)}&page=${page}&page_size=${pageSize}`,
      { auth: false }
    ),

  newsTrending: (window = "24h") =>
    fetchApi<{ window: string; topics: TrendingTopic[] }>(
      `/api/news/trending?window=${encodeURIComponent(window)}`,
      { auth: false }
    ),

  // ── SEC Filings ─────────────────────────────────────────────────────────────
  secFilings: (symbol: string) =>
    fetchApi<SECFilingsResponse>(
      `/api/sec/filings/${encodeURIComponent(symbol)}`,
      { auth: false }
    ),

  secFilingsAnalysis: (symbol: string) =>
    fetchApi<SECAnalysisResponse>(
      `/api/sec/filings/${encodeURIComponent(symbol)}/analysis`,
      { auth: false }
    ),

  // ── Stock Research (combined articles + SEC + market data) ─────────────────────
  stockResearch: (symbol: string) =>
    fetchApi<StockResearch>(
      `/api/research/${encodeURIComponent(symbol)}`,
      { auth: false }
    ),
    
  searchTicker: (query: string) =>
    fetchApi<{ symbol: string | null; shortname: string | null }>(
      `/api/search?q=${encodeURIComponent(query)}`,
      { auth: false }
    ),
    
  fetchChartData: (symbol: string, range: string) =>
    fetchApi<{ chart_data: { date: string; price: number }[] }>(
      `/api/chart/${encodeURIComponent(symbol)}?range=${encodeURIComponent(range)}`,
      { auth: false }
    ),

  // Returns raw URL for raw SSE EventSource connections
  llmAnalyzeStreamUrl: (symbol: string) => 
    `${API_URL}/api/llm/analyze/${encodeURIComponent(symbol)}`,
  llmChatStreamUrl: (symbol: string) => 
    `${API_URL}/api/llm/chat/${encodeURIComponent(symbol)}`,
  llmUploadUrl: (symbol: string) => 
    `${API_URL}/api/llm/upload/${encodeURIComponent(symbol)}`,

  // ── Auth ─────────────────────────────────────────────────────────────────────
  signup: (email: string, password: string) =>
    fetchApi<{ token: string; user: { id: string; email: string } }>(
      "/api/auth/signup",
      { method: "POST", body: JSON.stringify({ email, password }), auth: false }
    ),

  login: (email: string, password: string) =>
    fetchApi<{ token: string; user: { id: string; email: string } }>(
      "/api/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }), auth: false }
    ),

  // ── Trading ──────────────────────────────────────────────────────────────────
  portfolio: () =>
    fetchApi<{
      user_id: string;
      cash: number;
      positions: { symbol: string; quantity: number; avg_price?: number }[];
      total_value: number;
    }>("/api/trading/portfolio"),

  positions: () =>
    fetchApi<{
      positions: { symbol: string; quantity: number; avg_price?: number }[];
    }>("/api/trading/portfolio/positions"),

  placeOrder: (symbol: string, side: "buy" | "sell", quantity: number) =>
    fetchApi<{ success: boolean; error?: string; portfolio?: unknown }>(
      "/api/trading/portfolio/order",
      {
        method: "POST",
        body: JSON.stringify({ symbol, side, quantity }),
      }
    ),

  prices: (symbols: string[]) =>
    fetchApi<Record<string, number>>(
      `/api/trading/prices?symbols=${symbols.join(",")}`
    ),

  // ── Chatbot ──────────────────────────────────────────────────────────────────
  chat: (message: string) =>
    fetchApi<{ reply: string }>("/api/chatbot/message", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};
