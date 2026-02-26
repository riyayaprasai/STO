"use client";

import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";

export default function Header() {
  const { user, loading, logout } = useAuth();

  return (
    <header className="border-b border-sto-cardBorder bg-sto-card/95 backdrop-blur shadow-sto">
      <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between flex-wrap gap-4">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-sto-accent">STO</span>
          <span className="text-sm text-sto-muted font-medium hidden sm:inline">
            Social Trend Observant
          </span>
        </Link>
        <nav className="flex items-center gap-6 text-sm font-medium">
          <Link href="/" className="text-sto-muted hover:text-sto-accent transition">
            Dashboard
          </Link>
          <Link href="/sentiment" className="text-sto-muted hover:text-sto-accent transition">
            Sentiment
          </Link>
          <Link href="/trading" className="text-sto-muted hover:text-sto-accent transition">
            Practice trading
          </Link>
          <Link href="/chat" className="text-sto-muted hover:text-sto-accent transition">
            Chat
          </Link>
          {!loading && (
            user ? (
              <span className="flex items-center gap-3">
                <span className="text-sto-text truncate max-w-[140px]" title={user.email}>
                  {user.email}
                </span>
                <button
                  type="button"
                  onClick={logout}
                  className="text-sto-muted hover:text-sto-accent transition"
                >
                  Log out
                </button>
              </span>
            ) : (
              <>
                <Link href="/login" className="text-sto-muted hover:text-sto-accent transition">
                  Log in
                </Link>
                <Link
                  href="/signup"
                  className="rounded-lg bg-sto-accent text-white px-3 py-1.5 hover:bg-sto-accent/90 transition"
                >
                  Sign up
                </Link>
              </>
            )
          )}
        </nav>
      </div>
    </header>
  );
}
