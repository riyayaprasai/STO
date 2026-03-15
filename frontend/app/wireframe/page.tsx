"use client";

import Link from "next/link";

const sections = [
  {
    title: "1. Quick insights",
    desc: "Display top sentiment scores, highest momentum tickers, and source mix at a glance.",
    blocks: ["Overall sentiment", "Media source breakdown", "Top ticker list"],
  },
  {
    title: "2. Title + action cards",
    desc: "Use cards to define user goals: check sentiment, chat for explanation, practice trades.",
    blocks: ["Sentiment snapshot", "Chat assistant", "Practice trade order"],
  },
  {
    title: "3. Iterative flow",
    desc: "Prototype with guiding steps: choose ticker, view trend, place trade, review results.",
    blocks: ["Choose symbol", "Trend bars", "Buy/sell form", "Portfolio summary"],
  },
];

export default function WireframePage() {
  return (
    <div className="space-y-7">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-sto-accent font-semibold">Prototype</p>
        <h1 className="text-3xl font-bold text-sto-text mt-1">Wireframe & Prototype</h1>
        <p className="text-sto-muted mt-2 max-w-2xl">
          This prototype page reflects the wireframe layout for STO: simple, actionable blocks with a mobile-first information hierarchy. Use these sections to refine the UX before adding production data.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-sto-lg border border-sto-cardBorder bg-sto-card p-4 shadow-sto">
          <p className="text-xs uppercase tracking-wide text-sto-muted">Goal</p>
          <h2 className="text-xl font-semibold text-sto-text mt-2">See trends quickly</h2>
          <p className="text-sto-muted mt-2 text-sm">An at-a-glance hero section with score and trend indicators helps users make faster decisions.</p>
        </div>
        <div className="rounded-sto-lg border border-sto-cardBorder bg-sto-card p-4 shadow-sto">
          <p className="text-xs uppercase tracking-wide text-sto-muted">Goal</p>
          <h2 className="text-xl font-semibold text-sto-text mt-2">Act with confidence</h2>
          <p className="text-sto-muted mt-2 text-sm">A compact order form with clear buy/sell states and feedback lowers friction for first-time practice traders.</p>
        </div>
        <div className="rounded-sto-lg border border-sto-cardBorder bg-sto-card p-4 shadow-sto">
          <p className="text-xs uppercase tracking-wide text-sto-muted">Goal</p>
          <h2 className="text-xl font-semibold text-sto-text mt-2">Learn by asking</h2>
          <p className="text-sto-muted mt-2 text-sm">A contextual chat assistant for quick explanation supports trust and user onboarding.</p>
        </div>
      </div>

      <div className="space-y-4">
        {sections.map((s) => (
          <div key={s.title} className="rounded-sto-lg border border-sto-cardBorder bg-sto-card p-4 shadow-sto">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="text-lg font-semibold text-sto-text">{s.title}</h3>
                <p className="text-sto-muted text-sm mt-1">{s.desc}</p>
              </div>
              <span className="text-xs text-sto-accent uppercase tracking-wide font-semibold bg-sto-accent/10 px-2 py-1 rounded-full">MVP</span>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {s.blocks.map((b) => (
                <div
                  key={b}
                  className="rounded-lg border border-sto-cardBorder bg-sto-bg px-3 py-2 text-sm font-medium text-sto-text"
                >
                  {b}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-sto-lg border border-sto-cardBorder bg-sto-card p-4 shadow-sto">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-sto-text">Next steps</h2>
            <p className="text-sto-muted text-sm mt-1">Turn this wireframe into a clickable prototype by linking states and adding validation flows.</p>
          </div>
          <Link
            href="/"
            className="rounded-lg bg-sto-accent text-white px-3 py-1 text-sm font-medium hover:bg-sto-accent/90 transition"
          >
            Back to dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
