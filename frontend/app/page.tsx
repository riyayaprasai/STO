"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, NewsArticle, TrendingTopic } from "@/lib/api";

type Overview = {
  overall_score: number;
  label: string;
  sources: Record<string, { score: number; volume: number }>;
  top_symbols: { symbol: string; score: number; mentions: number }[];
};

const SENTIMENT_COLOR: Record<string, string> = {
  "very positive": "text-emerald-600 bg-emerald-50",
  positive:        "text-emerald-600 bg-emerald-50",
  neutral:         "text-amber-600  bg-amber-50",
  negative:        "text-red-600    bg-red-50",
  "very negative": "text-red-700    bg-red-100",
};

function SentimentBadge({ s }: { s: string }) {
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full capitalize ${SENTIMENT_COLOR[s] ?? "text-sto-muted bg-sto-bg"}`}>
      {s}
    </span>
  );
}

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function DashboardPage() {
  const router = useRouter();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [headlines, setHeadlines] = useState<NewsArticle[]>([]);
  const [trending, setTrending] = useState<TrendingTopic[]>([]);
  const [totalArticles, setTotalArticles] = useState(0);
  const [loading, setLoading] = useState(true);
  const [mockData, setMockData] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    Promise.all([
      api.sentimentOverview(),
      api.health(),
      api.newsHeadlines(undefined, 1),
      api.newsTrending("24h"),
    ])
      .then(([data, health, hl, tr]) => {
        setOverview(data);
        setMockData(!!health.mock_data);
        setTotalArticles(health.total_articles ?? 0);
        setHeadlines(hl.articles);
        setTrending(tr.topics.filter((t) => t.trend === "rising").slice(0, 8));
      })
      .catch(() => setOverview(null))
      .finally(() => setLoading(false));
  }, []);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const q = searchQuery.trim().toUpperCase();
    if (!q) return;
    router.push(`/sentiment?symbol=${q}`);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <p className="text-sto-muted">Loading your dashboard…</p>
      </div>
    );
  }

  return (
    <div className="space-y-10">

      {/* ── Hero search ─────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-3xl font-bold text-sto-text mb-1">
          What&apos;s the market saying?
        </h1>
        <p className="text-sto-muted text-lg mb-4">
          Search any stock to see sentiment, news, and trade with play money.
        </p>

        <form onSubmit={handleSearch} className="flex gap-2 max-w-lg">
          <input
            ref={searchRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search a ticker — AAPL, TSLA, NVDA…"
            className="flex-1 rounded-lg border border-sto-cardBorder bg-sto-card px-4 py-3 text-sto-text placeholder:text-sto-muted focus:outline-none focus:ring-2 focus:ring-sto-accent/40 text-sm"
          />
          <button
            type="submit"
            className="rounded-lg bg-sto-accent text-white font-semibold px-5 py-3 hover:bg-sto-accent/90 transition text-sm"
          >
            Search
          </button>
        </form>

        {/* Quick tickers */}
        <div className="flex flex-wrap gap-2 mt-3">
          {["AAPL", "TSLA", "NVDA", "MSFT", "GME", "META", "AMZN", "GOOGL"].map((s) => (
            <Link
              key={s}
              href={`/sentiment?symbol=${s}`}
              className="text-xs font-mono font-medium px-2.5 py-1 rounded-full border border-sto-cardBorder bg-sto-card text-sto-text hover:border-sto-accent/50 hover:text-sto-accent transition"
            >
              {s}
            </Link>
          ))}
        </div>

        {mockData && (
          <p className="mt-3 text-amber-600 text-sm bg-amber-50 px-3 py-2 rounded-lg inline-block">
            News data is loading — the backend is fetching live RSS feeds in the background.
          </p>
        )}
      </div>

      {/* ── Sentiment overview cards ──────────────────────────────────────── */}
      {overview && (
        <div className="grid gap-5 md:grid-cols-3">
          <div className="rounded-sto-lg bg-sto-card border border-sto-cardBorder p-5 shadow-sto">
            <p className="text-xs font-medium text-sto-muted uppercase tracking-wider mb-2">
              Overall sentiment
            </p>
            <p className="text-4xl font-bold text-sto-accent">
              {(overview.overall_score * 100).toFixed(0)}%
            </p>
            <p className="text-sto-muted capitalize mt-1 text-sm">{overview.label}</p>
            <div className="mt-3 h-2 rounded-full bg-sto-cardBorder overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-sto-accent to-emerald-400 transition-all"
                style={{ width: `${Math.max(5, overview.overall_score * 100)}%` }}
              />
            </div>
          </div>

          <div className="rounded-sto-lg bg-sto-card border border-sto-cardBorder p-5 shadow-sto">
            <p className="text-xs font-medium text-sto-muted uppercase tracking-wider mb-2">
              By category
            </p>
            <ul className="space-y-1.5 text-sm">
              {Object.entries(overview.sources).slice(0, 4).map(([name, v]) => (
                <li key={name} className="flex items-center justify-between gap-2">
                  <span className="capitalize text-sto-text truncate">{name}</span>
                  <span className="text-sto-accent font-medium shrink-0">
                    {(v.score * 100).toFixed(0)}%
                    <span className="text-sto-muted font-normal"> ({v.volume})</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-sto-lg bg-sto-card border border-sto-cardBorder p-5 shadow-sto">
            <p className="text-xs font-medium text-sto-muted uppercase tracking-wider mb-2">
              Top tickers
            </p>
            <ul className="space-y-1.5 text-sm">
              {overview.top_symbols.slice(0, 5).map((s) => (
                <li key={s.symbol} className="flex items-center justify-between gap-2">
                  <Link
                    href={`/sentiment?symbol=${s.symbol}`}
                    className="font-mono font-semibold text-sto-accent hover:underline"
                  >
                    {s.symbol}
                  </Link>
                  <span className="text-sto-muted text-xs">
                    {(s.score * 100).toFixed(0)}% · {s.mentions} articles
                  </span>
                </li>
              ))}
              {overview.top_symbols.length === 0 && (
                <li className="text-sto-muted">No ticker mentions yet</li>
              )}
            </ul>
          </div>
        </div>
      )}

      {/* ── Trending topics ───────────────────────────────────────────────── */}
      {trending.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-sto-muted uppercase tracking-wider mb-3">
            🔥 Trending right now
          </h2>
          <div className="flex flex-wrap gap-2">
            {trending.map((t) => (
              <button
                key={t.term}
                onClick={() => router.push(`/sentiment?symbol=${encodeURIComponent(t.term)}`)}
                className="group flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-sto-cardBorder bg-sto-card text-sm text-sto-text hover:border-sto-accent/50 transition"
              >
                <span className="font-medium group-hover:text-sto-accent">{t.term}</span>
                <span className="text-xs text-sto-muted">{t.count}</span>
                {t.trend === "rising" && <span className="text-emerald-500 text-xs">↑</span>}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Latest headlines ──────────────────────────────────────────────── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-sto-text">
            Latest headlines
            {totalArticles > 0 && (
              <span className="ml-2 text-xs text-sto-muted font-normal">
                {totalArticles} articles indexed
              </span>
            )}
          </h2>
          <Link href="/sentiment" className="text-sm text-sto-accent hover:underline">
            Full analysis →
          </Link>
        </div>

        {headlines.length === 0 ? (
          <div className="rounded-sto-lg border border-sto-cardBorder bg-sto-card p-6 text-center text-sto-muted">
            Headlines are loading — the backend is fetching live news feeds.
          </div>
        ) : (
          <div className="divide-y divide-sto-cardBorder rounded-sto-lg border border-sto-cardBorder bg-sto-card overflow-hidden shadow-sto">
            {headlines.slice(0, 8).map((a) => (
              <div key={a.id} className="p-4 hover:bg-sto-bg transition group">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <a
                      href={a.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-medium text-sto-text group-hover:text-sto-accent line-clamp-2 leading-snug"
                    >
                      {a.title}
                    </a>
                    {a.description && (
                      <p className="mt-1 text-xs text-sto-muted line-clamp-1">
                        {a.description}
                      </p>
                    )}
                    <div className="mt-1.5 flex items-center gap-2 flex-wrap">
                      <span className="text-xs text-sto-muted">{a.source}</span>
                      <span className="text-sto-muted text-xs">·</span>
                      <span className="text-xs text-sto-muted">{timeAgo(a.published_at)}</span>
                      {a.category && (
                        <>
                          <span className="text-sto-muted text-xs">·</span>
                          <span className="text-xs text-sto-muted capitalize">{a.category}</span>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="shrink-0 mt-0.5">
                    <SentimentBadge s={a.sentiment} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Feature cards ─────────────────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Link
          href="/sentiment"
          className="block rounded-sto-lg bg-sto-card border border-sto-cardBorder p-5 shadow-sto hover:shadow-sto-hover hover:border-sto-accent/40 transition"
        >
          <div className="text-2xl mb-2">📊</div>
          <h3 className="font-semibold text-sto-text mb-1">Sentiment analysis</h3>
          <p className="text-sto-muted text-sm">
            Search any ticker and see how news coverage is trending.
          </p>
        </Link>
        <Link
          href="/trading"
          className="block rounded-sto-lg bg-sto-card border border-sto-cardBorder p-5 shadow-sto hover:shadow-sto-hover hover:border-sto-accent/40 transition"
        >
          <div className="text-2xl mb-2">💼</div>
          <h3 className="font-semibold text-sto-text mb-1">Practice trading</h3>
          <p className="text-sto-muted text-sm">
            $100k virtual portfolio — buy and sell stocks risk-free.
          </p>
        </Link>
        <Link
          href="/chat"
          className="block rounded-sto-lg bg-sto-card border border-sto-cardBorder p-5 shadow-sto hover:shadow-sto-hover hover:border-sto-accent/40 transition"
        >
          <div className="text-2xl mb-2">💬</div>
          <h3 className="font-semibold text-sto-text mb-1">Ask the assistant</h3>
          <p className="text-sto-muted text-sm">
            Ask about any stock, sentiment trends, or how to trade.
          </p>
        </Link>
      </div>

    </div>
  );
}
