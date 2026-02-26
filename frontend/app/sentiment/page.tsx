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
      <div>
        <h1 className="text-3xl font-bold text-sto-text mb-2">Sentiment at a glance</h1>
        <p className="text-sto-muted">
          See how social media and news are talking about the market. STO is social trend observant — we surface what people are saying so you can stay informed.
        </p>
      </div>

      {overview && (
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-sto-lg bg-sto-card border border-sto-cardBorder p-5 shadow-sto">
            <p className="text-sm text-sto-muted uppercase tracking-wider">
              Overall
            </p>
            <p className="text-2xl font-bold text-sto-accent mt-1">
              {(overview.overall_score * 100).toFixed(0)}%
            </p>
            <p className="text-sto-muted capitalize">{overview.label}</p>
          </div>
          {Object.entries(overview.sources).map(([name, v]) => (
            <div
              key={name}
              className="rounded-sto-lg bg-sto-card border border-sto-cardBorder p-5 shadow-sto"
            >
              <p className="text-sm text-sto-muted uppercase tracking-wider capitalize">
                {name}
              </p>
              <p className="text-2xl font-bold text-sto-accent mt-1">
                {(v.score * 100).toFixed(0)}%
              </p>
              <p className="text-sto-muted">{v.volume} mentions</p>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-sto-lg bg-sto-card border border-sto-cardBorder p-6 shadow-sto">
        <h2 className="text-lg font-semibold text-sto-text mb-4">
          How’s {symbolParam} doing?
        </h2>
        {loading ? (
          <p className="text-sto-muted">Loading…</p>
        ) : symbolData ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-4">
              <span className="text-sto-accent font-mono text-xl font-semibold">
                {(symbolData.score * 100).toFixed(0)}%
              </span>
              <span className="capitalize text-sto-muted">
                {symbolData.label}
              </span>
              <span className="text-sto-muted">
                {symbolData.mentions} mentions
              </span>
            </div>
            {trend.length > 0 && (
              <div>
                <p className="text-sm text-sto-muted mb-2">Last 7 days</p>
                <div className="flex items-end gap-1 h-24">
                  {trend.map((t, i) => (
                    <div
                      key={i}
                      className="flex-1 bg-sto-accent/30 rounded-t min-h-[4px]"
                      style={{
                        height: `${Math.max(10, t.score * 100)}%`,
                      }}
                      title={`${t.date}: ${(t.score * 100).toFixed(0)}%`}
                    />
                  ))}
                </div>
                <div className="flex justify-between text-xs text-sto-muted mt-1">
                  <span>{trend[0]?.date}</span>
                  <span>{trend[trend.length - 1]?.date}</span>
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sto-muted">No data for this ticker yet.</p>
        )}
        <div className="mt-4 flex gap-2 flex-wrap">
          {["AAPL", "GME", "GOOGL", "MSFT", "AMC"].map((s) => (
            <a
              key={s}
              href={`/sentiment?symbol=${s}`}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                s === symbolParam
                  ? "bg-sto-accent text-white"
                  : "bg-sto-bg text-sto-muted hover:bg-sto-cardBorder border border-sto-cardBorder"
              }`}
            >
              {s}
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
