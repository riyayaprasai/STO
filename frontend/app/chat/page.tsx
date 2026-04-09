"use client";

import { useState, useRef, useEffect } from "react";
import { api } from "@/lib/api";

export default function ChatPage() {
  const [messages, setMessages] = useState<{ role: "user" | "bot"; text: string }[]>([
    { role: "bot", text: "Hi! I'm the STO assistant — STO is social trend observant, so I can help you understand what people are saying about the market and how to use this app. Ask me about sentiment, a ticker like AAPL or GME, or practice trading." },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text: string) {
    if (!text || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text }]);
    setLoading(true);
    try {
      const res = await api.chat(text);
      setMessages((m) => [...m, { role: "bot", text: res.reply }]);
    } catch (_err) {
      setMessages((m) => [
        ...m,
        { role: "bot", text: "Sorry, I couldn't reach the server. Is the backend running?" },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    sendMessage(input.trim());
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex flex-wrap justify-between items-start gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-sto-accent font-semibold">Conversational UI</p>
            <h1 className="text-3xl font-bold text-sto-text mt-1">Chat with STO</h1>
            <p className="text-sto-muted mt-2 max-w-2xl">
              Ask about sentiment trends, stock symbols, and how to interpret social market mood.
            </p>
          </div>
          <div className="rounded-lg border border-sto-cardBorder bg-sto-card px-3 py-2 text-xs text-sto-muted font-medium">
            Tip: type "market sentiment AAPL" or "what does the trend mean?"
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-[2fr_1fr]">
        <div className="rounded-sto-lg border border-sto-cardBorder bg-sto-card p-4 shadow-sto flex flex-col h-[560px]">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-sto-muted">Live assistant</p>
              <p className="text-sm font-medium text-sto-text">Instant answers on sentiment and trading concepts</p>
            </div>
            <span className="text-xs bg-sto-accent/15 text-sto-accent px-2 py-1 rounded-full">AI powered</span>
          </div>
          <div className="flex-1 overflow-y-auto rounded-xl border border-sto-cardBorder bg-sto-bg p-3 space-y-3">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] rounded-xl px-4 py-2.5 text-sm ${msg.role === "user" ? "bg-sto-accent text-white" : "bg-white text-sto-text border border-sto-cardBorder"}`}>
                  {msg.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="rounded-xl px-4 py-2.5 bg-sto-bg text-sto-muted border border-sto-cardBorder animate-pulse">
                  Thinking...
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
          <form onSubmit={handleSubmit} className="mt-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about AAPL sentiment, trending stocks, or trade strategy..."
                className="flex-1 rounded-lg border border-sto-cardBorder bg-white px-3 py-2.5 text-sto-text focus:ring-2 focus:ring-sto-accent/30"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="rounded-lg bg-sto-accent text-white font-semibold px-4 py-2.5 hover:bg-sto-accent/90 disabled:opacity-50 transition"
              >
                Send
              </button>
            </div>
          </form>
        </div>

        <div className="space-y-3">
          <div className="rounded-sto-lg border border-sto-cardBorder bg-sto-card p-4 shadow-sto">
            <p className="text-xs uppercase tracking-wide text-sto-muted">Use-case cards</p>
            <div className="mt-2 space-y-2 text-sm text-sto-text">
              {[
                { emoji: "💡", text: "What's the sentiment for MSFT this week?" },
                { emoji: "📈", text: "Show me top tickers by mentions" },
                { emoji: "🎯", text: "How do I practice trading safely?" },
              ].map((card) => (
                <button
                  key={card.text}
                  type="button"
                  onClick={() => sendMessage(card.text)}
                  disabled={loading}
                  className="w-full text-left rounded-lg border border-sto-cardBorder bg-white p-2 hover:border-sto-accent/50 disabled:opacity-50 transition"
                >
                  {card.emoji} &quot;{card.text}&quot;
                </button>
              ))}
            </div>
          </div>
          <div className="rounded-sto-lg border border-sto-cardBorder bg-sto-card p-4 shadow-sto">
            <p className="text-xs uppercase tracking-wide text-sto-muted">Quick prompts</p>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
              {[
                "Sentiment by source",
                "Top stock mentions",
                "Interpret trend",
                "Risk guidance",
              ].map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => sendMessage(p)}
                  disabled={loading}
                  className="rounded-md border border-sto-cardBorder bg-white px-2 py-1.5 text-left hover:border-sto-accent/50 disabled:opacity-50 transition"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
          <div className="rounded-sto-lg border border-sto-cardBorder bg-sto-card p-4 shadow-sto">
            <p className="text-xs uppercase tracking-wide text-sto-muted">How it works</p>
            <ol className="mt-2 list-decimal list-inside text-sm text-sto-muted space-y-1">
              <li>Ask a question (ticker or market term).</li>
              <li>See a concise response plus next action.</li>
              <li>Open sentiment page to compare and trade in practice mode.</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
