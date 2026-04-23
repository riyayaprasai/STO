"use client";

import { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { api, NewsArticle } from "@/lib/api";

const ALL_SYMBOLS = ["AAPL", "GOOGL", "MSFT", "GME", "AMC", "NVDA", "TSLA", "META", "AMZN", "NFLX"];

type Portfolio = {
  user_id: string;
  cash: number;
  positions: { symbol: string; quantity: number; avg_price?: number }[];
  total_value: number;
};
type Prices = Record<string, number>;

// ── Helpers ───────────────────────────────────────────────────────────────────

const SENTIMENT_BADGE: Record<string, string> = {
  "very positive": "bg-emerald-50 text-emerald-700",
  positive:        "bg-emerald-50 text-emerald-600",
  neutral:         "bg-amber-50   text-amber-700",
  negative:        "bg-red-50     text-red-600",
  "very negative": "bg-red-100    text-red-700",
};

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ── Main ──────────────────────────────────────────────────────────────────────

function TradingContent() {
  const searchParams = useSearchParams();
  const { user, loading: authLoading } = useAuth();

  const urlSymbol = searchParams.get("symbol")?.toUpperCase() ?? "";
  const defaultSymbol = ALL_SYMBOLS.includes(urlSymbol) ? urlSymbol : "AAPL";

  const [portfolio, setPortfolio]   = useState<Portfolio | null>(null);
  const [prices, setPrices]         = useState<Prices>({});
  const [symbol, setSymbol]         = useState(defaultSymbol);
  const [side, setSide]             = useState<"buy" | "sell">("buy");
  const [quantity, setQuantity]     = useState(10);
  const [loading, setLoading]       = useState(true);
  const [orderLoading, setOrderLoading] = useState(false);
  const [message, setMessage]       = useState<string | null>(null);

  // News for the selected symbol
  const [news, setNews]           = useState<NewsArticle[]>([]);
  const [newsLoading, setNewsLoading] = useState(false);
  const [symbolSentiment, setSymbolSentiment] = useState<{ score: number; label: string; mentions: number } | null>(null);

  function loadPortfolio() {
    if (!user) { setLoading(false); return; }
    Promise.all([api.portfolio(), api.prices(ALL_SYMBOLS)])
      .then(([p, pr]) => { setPortfolio(p); setPrices(pr); })
      .catch(() => setPortfolio(null))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (!authLoading) loadPortfolio();
  }, [authLoading, user]);

  // Load news + sentiment whenever symbol changes
  useEffect(() => {
    setNewsLoading(true);
    Promise.all([
      api.newsSearch(symbol, 1, 4),
      api.sentimentSymbol(symbol),
    ])
      .then(([r, s]) => {
        setNews(r.articles);
        setSymbolSentiment({ score: s.score, label: s.label, mentions: s.mentions });
      })
      .catch(() => { setNews([]); setSymbolSentiment(null); })
      .finally(() => setNewsLoading(false));
  }, [symbol]);

  async function handleOrder(e: React.FormEvent) {
    e.preventDefault();
    if (!user) return;
    setMessage(null);
    setOrderLoading(true);
    try {
      const res = await api.placeOrder(symbol, side, quantity);
      if (res.success && res.portfolio) {
        setPortfolio(res.portfolio as Portfolio);
        setMessage(`${side === "buy" ? "✅ Bought" : "✅ Sold"} ${quantity} × ${symbol} — done!`);
      } else {
        setMessage(res.error || "Couldn't place order");
      }
    } catch {
      setMessage("Something went wrong — is the backend running?");
    } finally {
      setOrderLoading(false);
    }
  }

  if (authLoading || (user && loading)) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <p className="text-sto-muted">Loading your portfolio…</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="max-w-md mx-auto text-center space-y-4 pt-16">
        <div className="text-4xl">💼</div>
        <h1 className="text-3xl font-bold text-sto-text">Practice trading</h1>
        <p className="text-sto-muted">
          Log in or sign up to get a $100,000 virtual portfolio and start trading with no real money.
        </p>
        <div className="flex gap-4 justify-center flex-wrap">
          <Link href="/login" className="rounded-lg bg-sto-accent text-white font-semibold py-2.5 px-5 hover:bg-sto-accent/90 transition">
            Log in
          </Link>
          <Link href="/signup" className="rounded-lg bg-sto-card border border-sto-cardBorder text-sto-text font-semibold py-2.5 px-5 hover:border-sto-accent/50 transition">
            Sign up free
          </Link>
        </div>
      </div>
    );
  }

  const position = portfolio?.positions.find((p) => p.symbol === symbol);
  const currentPrice = prices[symbol] ?? 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-sto-text mb-1">Practice trading</h1>
        <p className="text-sto-muted text-sm">
          $100,000 virtual portfolio — buy and sell stocks risk-free.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">

        {/* ── Left col: portfolio + order form ─────────────────────────────── */}
        <div className="lg:col-span-2 space-y-6">

          {/* Portfolio summary */}
          {portfolio && (
            <div className="rounded-sto-lg bg-sto-card border border-sto-cardBorder p-5 shadow-sto">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <p className="text-xs font-medium text-sto-muted uppercase tracking-wider mb-1">
                    Portfolio value
                  </p>
                  <p className="text-3xl font-bold text-sto-accent">
                    ${portfolio.total_value.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </p>
                  <p className="text-sm text-sto-muted mt-0.5">
                    Cash: ${portfolio.cash.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </p>
                </div>

                {/* Positions */}
                {portfolio.positions.length > 0 && (
                  <div className="min-w-[180px]">
                    <p className="text-xs font-medium text-sto-muted uppercase tracking-wider mb-2">
                      Holdings
                    </p>
                    <ul className="space-y-1">
                      {portfolio.positions.map((p) => {
                        const price = prices[p.symbol] ?? p.avg_price ?? 0;
                        const value = p.quantity * price;
                        return (
                          <li key={p.symbol} className="flex justify-between text-sm gap-3">
                            <button
                              className="font-mono font-semibold text-sto-accent hover:underline"
                              onClick={() => setSymbol(p.symbol)}
                            >
                              {p.symbol}
                            </button>
                            <span className="text-sto-muted">
                              {p.quantity} @ ${price.toFixed(2)}
                              <span className="ml-1 text-sto-text font-medium">= ${value.toFixed(0)}</span>
                            </span>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Order form */}
          <div className="rounded-sto-lg bg-sto-card border border-sto-cardBorder p-5 shadow-sto">
            <h2 className="text-sm font-semibold text-sto-muted uppercase tracking-wider mb-4">
              Place order
            </h2>
            <form onSubmit={handleOrder} className="space-y-4">
              {/* Symbol */}
              <div>
                <label className="block text-sm text-sto-muted mb-1 font-medium">Stock</label>
                <select
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  className="w-full rounded-lg bg-sto-bg border border-sto-cardBorder px-3 py-2.5 text-sm text-sto-text"
                >
                  {ALL_SYMBOLS.map((s) => (
                    <option key={s} value={s}>
                      {s} — ${(prices[s] ?? 0).toFixed(2)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Side + quantity */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-sto-muted mb-1 font-medium">Action</label>
                  <select
                    value={side}
                    onChange={(e) => setSide(e.target.value as "buy" | "sell")}
                    className="w-full rounded-lg bg-sto-bg border border-sto-cardBorder px-3 py-2.5 text-sm text-sto-text"
                  >
                    <option value="buy">Buy</option>
                    <option value="sell">Sell</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-sto-muted mb-1 font-medium">Quantity</label>
                  <input
                    type="number"
                    min={1}
                    value={quantity}
                    onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                    className="w-full rounded-lg bg-sto-bg border border-sto-cardBorder px-3 py-2.5 text-sm text-sto-text"
                  />
                </div>
              </div>

              {/* Cost estimate */}
              <div className="rounded-lg bg-sto-bg border border-sto-cardBorder px-4 py-2.5 text-sm flex justify-between">
                <span className="text-sto-muted">Estimated {side === "buy" ? "cost" : "proceeds"}</span>
                <span className="font-semibold text-sto-text">
                  ${(currentPrice * quantity).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </span>
              </div>

              {/* Position info */}
              {position && (
                <p className="text-xs text-sto-muted">
                  You hold <span className="font-semibold text-sto-text">{position.quantity} shares</span> of {symbol} @ avg ${position.avg_price?.toFixed(2)}
                </p>
              )}

              {message && (
                <p className={message.startsWith("✅") ? "text-emerald-600 font-medium text-sm" : "text-red-600 text-sm"}>
                  {message}
                </p>
              )}

              <button
                type="submit"
                disabled={orderLoading}
                className="w-full rounded-lg bg-sto-accent text-white font-semibold py-2.5 hover:bg-sto-accent/90 disabled:opacity-50 transition text-sm"
              >
                {orderLoading ? "Placing…" : `${side === "buy" ? "Buy" : "Sell"} ${quantity} × ${symbol}`}
              </button>
            </form>
          </div>

          {/* Live prices strip */}
          <div className="rounded-sto-lg bg-sto-card border border-sto-cardBorder p-4 shadow-sto">
            <p className="text-xs font-medium text-sto-muted uppercase tracking-wider mb-3">
              Simulated prices (update hourly)
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
              {ALL_SYMBOLS.map((s) => (
                <button
                  key={s}
                  onClick={() => setSymbol(s)}
                  className={`rounded-lg border px-2 py-1.5 text-xs font-mono text-left transition ${
                    s === symbol
                      ? "border-sto-accent bg-sto-accent/5 text-sto-accent"
                      : "border-sto-cardBorder bg-sto-bg text-sto-text hover:border-sto-accent/40"
                  }`}
                >
                  <div className="font-semibold">{s}</div>
                  <div className="text-sto-muted">${(prices[s] ?? 0).toFixed(2)}</div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ── Right col: sentiment + news ────────────────────────────────────── */}
        <div className="space-y-5">
          {/* Sentiment card for selected stock */}
          <div className="rounded-sto-lg border border-sto-cardBorder bg-sto-card p-4 shadow-sto">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-medium text-sto-muted uppercase tracking-wider">
                {symbol} sentiment
              </p>
              <Link
                href={`/sentiment?symbol=${symbol}`}
                className="text-xs text-sto-accent hover:underline"
              >
                Full analysis →
              </Link>
            </div>
            {symbolSentiment ? (
              <div>
                <div className="flex items-baseline gap-2 mb-1">
                  <span className="text-2xl font-bold text-sto-accent">
                    {(symbolSentiment.score * 100).toFixed(0)}%
                  </span>
                  <span className={`text-sm font-medium capitalize ${
                    SENTIMENT_BADGE[symbolSentiment.label]?.split(" ")[1] ?? "text-sto-muted"
                  }`}>
                    {symbolSentiment.label}
                  </span>
                </div>
                <div className="h-2 rounded-full bg-sto-cardBorder overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-sto-accent to-emerald-400 transition-all"
                    style={{ width: `${Math.max(5, symbolSentiment.score * 100)}%` }}
                  />
                </div>
                <p className="text-xs text-sto-muted mt-1.5">
                  Based on {symbolSentiment.mentions} recent articles
                </p>
              </div>
            ) : (
              <p className="text-sm text-sto-muted">
                No sentiment data for {symbol} yet.
              </p>
            )}
          </div>

          {/* News for selected stock */}
          <div className="rounded-sto-lg border border-sto-cardBorder bg-sto-card overflow-hidden shadow-sto">
            <div className="px-4 py-3 border-b border-sto-cardBorder">
              <p className="text-xs font-medium text-sto-muted uppercase tracking-wider">
                Latest {symbol} news
              </p>
            </div>
            {newsLoading ? (
              <div className="p-4 space-y-3 animate-pulse">
                {[1, 2, 3].map((i) => (
                  <div key={i}>
                    <div className="h-3 bg-sto-bg rounded w-full mb-1" />
                    <div className="h-3 bg-sto-bg rounded w-2/3" />
                  </div>
                ))}
              </div>
            ) : news.length === 0 ? (
              <p className="p-4 text-sm text-sto-muted">
                No recent news for {symbol}.
              </p>
            ) : (
              <ul className="divide-y divide-sto-cardBorder">
                {news.map((a) => (
                  <li key={a.id} className="p-3 hover:bg-sto-bg transition">
                    <a
                      href={a.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs font-medium text-sto-text hover:text-sto-accent line-clamp-2 leading-snug"
                    >
                      {a.title}
                    </a>
                    <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
                      <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium capitalize ${SENTIMENT_BADGE[a.sentiment] ?? "bg-sto-bg text-sto-muted"}`}>
                        {a.sentiment}
                      </span>
                      <span className="text-xs text-sto-muted">{timeAgo(a.published_at)}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Tip card */}
          <div className="rounded-sto-lg border border-sto-cardBorder bg-sto-bg p-4">
            <p className="text-xs font-semibold text-sto-muted uppercase tracking-wider mb-2">
              💡 Tip
            </p>
            <p className="text-xs text-sto-muted leading-relaxed">
              Check the sentiment and news for a stock before placing a trade. High bullish coverage + rising trend can signal a good moment to practice buying.
            </p>
            <Link href="/chat" className="mt-2 block text-xs text-sto-accent hover:underline">
              Ask the assistant about {symbol} →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function TradingPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[40vh]">
        <p className="text-sto-muted">Loading…</p>
      </div>
    }>
      <TradingContent />
    </Suspense>
  );
}
