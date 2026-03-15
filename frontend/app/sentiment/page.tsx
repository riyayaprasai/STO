"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

type Overview = {
  overall_score: number;
  label: string;
  sources: Record<string, { score: number; volume: number }>;
  top_symbols: { symbol: string; score: number; mentions: number }[];
};

type SymbolData = { symbol: string; score: number; label: string; mentions: number };

export default function SentimentPage() {
  const searchParams = useSearchParams();
  const symbolParam = searchParams.get("symbol") || "AAPL";
  const [overview, setOverview] = useState<Overview | null>(null);
  const [symbolData, setSymbolData] = useState<SymbolData | null>(null);
  const [trend, setTrend] = useState<{ date: string; score: number }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.sentimentOverview().then(setOverview).catch(() => setOverview(null));
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.sentimentSymbol(symbolParam),
      api.sentimentTrends(symbolParam, 7),
    ])
      .then(([sym, tr]) => {
        setSymbolData(sym);
        setTrend(tr.trend || []);
      })
      .catch(() => {
        setSymbolData(null);
        setTrend([]);
      })
      .finally(() => setLoading(false));
  }, [symbolParam]);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap justify-between gap-2 items-start">
        <div>
          <p className="text-xs uppercase tracking-[0.15em] text-sto-accent font-semibold">Tool design</p>
          <h1 className="text-3xl font-bold text-sto-text mt-1">Sentiment tools</h1>
          <p className="text-sto-muted mt-2 max-w-2xl">
            Explore market mood with quick insights, source breakdown, and symbol trend analysis.
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          {[
            "Audience sentiment",
            "News vs social",
            "Top mentions",
          ].map((s) => (
            <span key={s} className="rounded-full border border-sto-cardBorder bg-sto-bg px-3 py-1 text-xs font-medium text-sto-text">
              {s}
            </span>
          ))}
        </div>
      </div>

      {overview ? (
        <div className="grid gap-4 lg:grid-cols-4">
          <div className="rounded-sto-lg border border-sto-cardBorder bg-sto-card p-4 shadow-sto">
            <p className="text-xs uppercase tracking-wider text-sto-muted">Overall sentiment</p>
            <p className="text-3xl font-bold text-sto-accent mt-2">{(overview.overall_score * 100).toFixed(0)}%</p>
            <p className="text-sm text-sto-text capitalize mt-1">{overview.label}</p>
            <div className="mt-3 h-2 rounded-full bg-sto-cardBorder overflow-hidden">
              <div className="h-full bg-gradient-to-r from-emerald-500 to-lime-400" style={{ width: `${Math.min(100, Math.max(5, overview.overall_score * 100))}%` }} />
            </div>
          </div>
          {Object.entries(overview.sources).map(([name, v]) => (
            <div key={name} className="rounded-sto-lg border border-sto-cardBorder bg-sto-card p-4 shadow-sto">
              <p className="text-xs uppercase tracking-wider text-sto-muted">{name}</p>
              <p className="text-2xl font-bold text-sto-accent mt-2">{(v.score * 100).toFixed(0)}%</p>
              <p className="text-sm text-sto-muted mt-1">{v.volume.toLocaleString()} mentions</p>
              <div className="mt-3 h-2 rounded-full bg-sto-cardBorder">
                <div className="h-full bg-sto-accent" style={{ width: `${Math.min(100, Math.max(10, v.score * 100))}%` }} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-sto-lg border border-sto-cardBorder bg-sto-card p-4">No overview data yet.</div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-sto-lg border border-sto-cardBorder bg-sto-card p-4 shadow-sto">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-semibold text-sto-text">Symbol trend</h2>
              <p className="text-xs text-sto-muted">Current sentiment score and trend</p>
            </div>
            <span className="text-xs bg-sto-accent/15 text-sto-accent px-2 py-1 rounded-full">Realtime</span>
          </div>
          <div className="mt-3">
            <div className="flex items-center gap-2 flex-wrap">
              {['AAPL', 'GME', 'GOOGL', 'MSFT', 'AMC'].map((s) => (
                <a key={s} href={`/sentiment?symbol=${s}`} className={`rounded-full px-2.5 py-1 text-xs font-medium border ${s === symbolParam ? 'bg-sto-accent text-white border-transparent' : 'border-sto-cardBorder bg-sto-bg text-sto-text hover:border-sto-accent/30'}`}>
                  {s}
                </a>
              ))}
            </div>
            <div className="mt-4">
              {loading ? (
                <p className="text-sto-muted">Loading symbol details…</p>
              ) : symbolData ? (
                <div className="space-y-2">
                  <p className="text-xl font-semibold text-sto-accent">{symbolData.symbol} — {(symbolData.score * 100).toFixed(0)}%</p>
                  <p className="text-sm text-sto-muted">{symbolData.label} • {symbolData.mentions.toLocaleString()} mentions</p>
                  {trend.length > 0 ? (
                    <div className="mt-2 rounded-lg bg-sto-bg border border-sto-cardBorder p-2">
                      <div className="flex items-end gap-1 h-20">
                        {trend.map((t, i) => (
                          <div key={i} className="flex-1 rounded-t bg-sto-accent" style={{ height: `${Math.max(18, t.score * 100)}%` }} title={`${t.date}: ${(t.score * 100).toFixed(0)}%`} />
                        ))}
                      </div>
                      <div className="mt-1 flex justify-between text-xs text-sto-muted"><span>{trend[0]?.date}</span><span>{trend[trend.length - 1]?.date}</span></div>
                    </div>
                  ) : (
                    <p className="text-xs text-sto-muted">No trend data yet.</p>
                  )}
                </div>
              ) : (
                <p className="text-sto-muted">No data available for this symbol.</p>
              )}
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 rounded-sto-lg border border-sto-cardBorder bg-sto-card p-4 shadow-sto">
          <h2 className="text-lg font-semibold text-sto-text">Sentiment tool actions</h2>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <div className="rounded-lg border border-sto-cardBorder bg-white p-3">
              <p className="text-xs uppercase tracking-wide text-sto-muted">Use case</p>
              <p className="mt-1 text-sm text-sto-text font-medium">Compare Reddit vs News to spot momentum shifts.</p>
            </div>
            <div className="rounded-lg border border-sto-cardBorder bg-white p-3">
              <p className="text-xs uppercase tracking-wide text-sto-muted">Use case</p>
              <p className="mt-1 text-sm text-sto-text font-medium">Pick a watchlist ticker then place a simulated trade in the trading page.</p>
            </div>
            <div className="rounded-lg border border-sto-cardBorder bg-white p-3">
              <p className="text-xs uppercase tracking-wide text-sto-muted">Use case</p>
              <p className="mt-1 text-sm text-sto-text font-medium">Track daily sentiment trends to avoid overreacting to short-term noise.</p>
            </div>
            <div className="rounded-lg border border-sto-cardBorder bg-white p-3">
              <p className="text-xs uppercase tracking-wide text-sto-muted">Use case</p>
              <p className="mt-1 text-sm text-sto-text font-medium">Ask the chatbot for context when sentiment turns extreme.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
