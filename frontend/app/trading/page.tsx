"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";

const SYMBOLS = ["AAPL", "GOOGL", "MSFT", "GME", "AMC"];

type Portfolio = {
  user_id: string;
  cash: number;
  positions: { symbol: string; quantity: number; avg_price?: number }[];
  total_value: number;
};

type Prices = Record<string, number>;

export default function TradingPage() {
  const { user, loading: authLoading } = useAuth();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [prices, setPrices] = useState<Prices>({});
  const [symbol, setSymbol] = useState("AAPL");
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [quantity, setQuantity] = useState(10);
  const [loading, setLoading] = useState(true);
  const [orderLoading, setOrderLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  function load() {
    if (!user) {
      setLoading(false);
      return;
    }
    Promise.all([api.portfolio(), api.prices(SYMBOLS)])
      .then(([p, pr]) => {
        setPortfolio(p);
        setPrices(pr);
      })
      .catch(() => setPortfolio(null))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (!authLoading) load();
  }, [authLoading, user]);

  async function handleOrder(e: React.FormEvent) {
    e.preventDefault();
    if (!user) return;
    setMessage(null);
    setOrderLoading(true);
    try {
      const res = await api.placeOrder(symbol, side, quantity);
      if (res.success && res.portfolio) {
        setPortfolio(res.portfolio as Portfolio);
        setMessage(`${side === "buy" ? "Bought" : "Sold"} ${quantity} ${symbol} — done!`);
      } else {
        setMessage(res.error || "Couldn’t place order");
      }
    } catch (err) {
      setMessage("Something went wrong. Is the backend running?");
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
      <div className="max-w-md mx-auto text-center space-y-4">
        <h1 className="text-3xl font-bold text-sto-text">Practice trading</h1>
        <p className="text-sto-muted">
          Log in or sign up to get your own portfolio and add stocks with play money.
        </p>
        <div className="flex gap-4 justify-center flex-wrap">
          <Link
            href="/login"
            className="rounded-lg bg-sto-accent text-white font-medium py-2.5 px-4 hover:bg-sto-accent/90 transition"
          >
            Log in
          </Link>
          <Link
            href="/signup"
            className="rounded-lg bg-sto-card border border-sto-cardBorder text-sto-text font-medium py-2.5 px-4 hover:border-sto-accent/50 transition"
          >
            Sign up
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-sto-text mb-2">Practice trading</h1>
        <p className="text-sto-muted">
          Use play money to try ideas — no real cash at risk. This is your own portfolio.
        </p>
      </div>

      {portfolio && (
        <div className="grid gap-6 md:grid-cols-2">
          <div className="rounded-sto-lg bg-sto-card border border-sto-cardBorder p-6 shadow-sto">
            <h2 className="text-sm font-medium text-sto-muted uppercase tracking-wider mb-4">
              Your portfolio
            </h2>
            <p className="text-2xl font-bold text-sto-accent">
              ${portfolio.total_value.toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </p>
            <p className="text-sto-muted mt-1">
              Cash: ${portfolio.cash.toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </p>
            <ul className="mt-4 space-y-2">
              {portfolio.positions.length === 0 ? (
                <li className="text-sto-muted">No positions yet. Place a buy to add stocks.</li>
              ) : (
                portfolio.positions.map((p) => (
                  <li key={p.symbol} className="flex justify-between text-sm text-sto-text">
                    <span className="font-mono font-medium">{p.symbol}</span>
                    <span>{p.quantity} @ ${(prices[p.symbol] ?? p.avg_price ?? 0).toFixed(2)}</span>
                  </li>
                ))
              )}
            </ul>
          </div>
          <div className="rounded-sto-lg bg-sto-card border border-sto-cardBorder p-6 shadow-sto">
            <h2 className="text-sm font-medium text-sto-muted uppercase tracking-wider mb-4">
              Add to portfolio (buy) or sell
            </h2>
            <form onSubmit={handleOrder} className="space-y-4">
              <div>
                <label className="block text-sm text-sto-muted mb-1 font-medium">Symbol</label>
                <select
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  className="w-full rounded-lg bg-sto-bg border border-sto-cardBorder px-3 py-2.5 text-sto-text"
                >
                  {SYMBOLS.map((s) => (
                    <option key={s} value={s}>
                      {s} (${(prices[s] ?? 0).toFixed(2)})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-sto-muted mb-1 font-medium">Buy or sell</label>
                <select
                  value={side}
                  onChange={(e) => setSide(e.target.value as "buy" | "sell")}
                  className="w-full rounded-lg bg-sto-bg border border-sto-cardBorder px-3 py-2.5 text-sto-text"
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
                  onChange={(e) => setQuantity(parseInt(e.target.value, 10) || 1)}
                  className="w-full rounded-lg bg-sto-bg border border-sto-cardBorder px-3 py-2.5 text-sto-text"
                />
              </div>
              {message && (
                <p
                  className={
                    message.includes("done")
                      ? "text-sto-positive font-medium"
                      : "text-sto-danger"
                  }
                >
                  {message}
                </p>
              )}
              <button
                type="submit"
                disabled={orderLoading}
                className="w-full rounded-lg bg-sto-accent text-white font-medium py-2.5 px-4 hover:bg-sto-accent/90 disabled:opacity-50 transition"
              >
                {orderLoading ? "Placing…" : `${side === "buy" ? "Buy" : "Sell"} ${symbol}`}
              </button>
            </form>
          </div>
        </div>
      )}

      <div className="rounded-sto-lg bg-sto-card border border-sto-cardBorder p-6 shadow-sto">
        <h2 className="text-sm font-medium text-sto-muted uppercase tracking-wider mb-4">
          Current prices (simulated)
        </h2>
        <div className="flex flex-wrap gap-4">
          {SYMBOLS.map((s) => (
            <span key={s} className="font-mono text-sto-accent font-medium">
              {s}: ${(prices[s] ?? 0).toFixed(2)}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
