"use client";

import { useState, useRef, useEffect } from "react";
import { api } from "@/lib/api";

export default function ChatPage() {
  const [messages, setMessages] = useState<{ role: "user" | "bot"; text: string }[]>([
    { role: "bot", text: "Hi! I’m the STO assistant — STO is social trend observant, so I can help you understand what people are saying about the market and how to use this app. Ask me about sentiment, a ticker like AAPL or GME, or practice trading." },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text }]);
    setLoading(true);
    try {
      const res = await api.chat(text);
      setMessages((m) => [...m, { role: "bot", text: res.reply }]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "bot", text: "Sorry, I couldn’t reach the server. Is the backend running?" },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-sto-text mb-2">Chat</h1>
        <p className="text-sto-muted">
          Ask about sentiment, tickers (e.g. AAPL, GME), or how to use STO. We’re social trend observant — so you can stay in the loop.
        </p>
      </div>

      <div className="rounded-sto-lg bg-sto-card border border-sto-cardBorder flex flex-col h-[480px] shadow-sto">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-xl px-4 py-2.5 ${
                  msg.role === "user"
                    ? "bg-sto-accent text-white"
                    : "bg-sto-bg text-sto-text border border-sto-cardBorder"
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="rounded-xl px-4 py-2.5 bg-sto-bg text-sto-muted border border-sto-cardBorder">
                …
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        <form onSubmit={handleSubmit} className="p-4 border-t border-sto-cardBorder">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about sentiment or trading..."
              className="flex-1 rounded-lg bg-sto-bg border border-sto-cardBorder px-4 py-2.5 text-sto-text placeholder-sto-muted"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="rounded-lg bg-sto-accent text-white font-medium px-4 py-2.5 hover:bg-sto-accent/90 disabled:opacity-50 transition"
            >
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
