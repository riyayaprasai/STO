const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

import { getAuthHeaders } from "./auth";

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

export const api = {
  health: () => fetchApi<{ status: string; mock_data?: boolean }>("/api/health"),
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
  chat: (message: string) =>
    fetchApi<{ reply: string }>("/api/chatbot/message", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};
