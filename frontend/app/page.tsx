"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

type Overview = {
  overall_score: number;
  label: string;
  sources: Record<string, { score: number; volume: number }>;
  top_symbols: { symbol: string; score: number; mentions: number }[];
};

export default function DashboardPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [mockData, setMockData] = useState(false);

  useEffect(() => {
    Promise.all([api.sentimentOverview(), api.health()])
      .then(([data, health]) => {
        setOverview(data);
        setMockData(!!health.mock_data);
      })
      .catch(() => setOverview(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <p className="text-sto-muted">Loading your dashboard…</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-sto-text mb-2">
          Hi — here’s what’s trending
        </h1>
        <p className="text-sto-muted text-lg">
          See how people are feeling about the market and try out trading with play money.
        </p>
        {mockData && (
          <p className="mt-3 text-amber-600 text-sm bg-amber-50 px-3 py-2 rounded-lg inline-block">
            Showing sample data. Add API keys in the backend for live social trends.
          </p>
        )}
      </div>

      {overview && (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-sto-lg bg-sto-card border border-sto-cardBorder p-6 shadow-sto hover:shadow-sto-hover transition">
            <h2 className="text-sm font-medium text-sto-muted uppercase tracking-wider mb-2">
              Overall sentiment
            </h2>
            <p className="text-3xl font-bold text-sto-accent">
              {(overview.overall_score * 100).toFixed(0)}%
            </p>
            <p className="text-sto-muted capitalize mt-1">{overview.label}</p>
          </div>
          <div className="rounded-sto-lg bg-sto-card border border-sto-cardBorder p-6 shadow-sto hover:shadow-sto-hover transition">
            <h2 className="text-sm font-medium text-sto-muted uppercase tracking-wider mb-2">
              By source
            </h2>
            <ul className="space-y-2 text-sm">
              {Object.entries(overview.sources).map(([name, v]) => (
                <li key={name} className="flex justify-between">
                  <span className="capitalize text-sto-text">{name}</span>
                  <span className="text-sto-accent font-medium">
                    {(v.score * 100).toFixed(0)}% ({v.volume} mentions)
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-sto-lg bg-sto-card border border-sto-cardBorder p-6 shadow-sto hover:shadow-sto-hover transition">
            <h2 className="text-sm font-medium text-sto-muted uppercase tracking-wider mb-2">
              Top tickers
            </h2>
            <ul className="space-y-2 text-sm">
              {overview.top_symbols.slice(0, 5).map((s) => (
                <li key={s.symbol} className="flex justify-between">
                  <Link
                    href={`/sentiment?symbol=${s.symbol}`}
                    className="text-sto-accent font-medium hover:underline"
                  >
                    {s.symbol}
                  </Link>
                  <span className="text-sto-muted">{(s.score * 100).toFixed(0)}% · {s.mentions}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <Link
          href="/sentiment"
          className="block rounded-sto-lg bg-sto-card border border-sto-cardBorder p-6 shadow-sto hover:shadow-sto-hover hover:border-sto-accent/40 transition"
        >
          <h2 className="text-lg font-semibold text-sto-text mb-2">
            Sentiment dashboard
          </h2>
          <p className="text-sto-muted">
            See how Reddit, Twitter, and news are talking about different stocks.
          </p>
        </Link>
        <Link
          href="/trading"
          className="block rounded-sto-lg bg-sto-card border border-sto-cardBorder p-6 shadow-sto hover:shadow-sto-hover hover:border-sto-accent/40 transition"
        >
          <h2 className="text-lg font-semibold text-sto-text mb-2">
            Practice trading
          </h2>
          <p className="text-sto-muted">
            Use a virtual portfolio to try ideas — no real money involved.
          </p>
        </Link>
      </div>

      <div className="rounded-sto-lg bg-sto-card border border-sto-cardBorder p-6 shadow-sto">
        <h2 className="text-lg font-semibold text-sto-text mb-2">Need help? Ask here</h2>
        <p className="text-sto-muted mb-4">
          Get quick answers about sentiment and how to use STO in plain language.
        </p>
        <Link
          href="/chat"
          className="inline-flex items-center gap-2 text-sto-accent font-medium hover:underline"
        >
          Open chat →
        </Link>
      </div>
    </div>
  );
}
