"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login, user } = useAuth();
  const router = useRouter();

  if (user) {
    router.replace("/trading");
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const err = await login(email.trim(), password);
    setLoading(false);
    if (err) {
      setError(err);
      return;
    }
    router.push("/trading");
  }

  return (
    <div className="max-w-md mx-auto">
      <h1 className="text-3xl font-bold text-sto-text mb-2">Log in</h1>
      <p className="text-sto-muted mb-6">
        Use your account to access your portfolio and practice trading.
      </p>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-sto-text mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            className="w-full rounded-lg bg-sto-card border border-sto-cardBorder px-3 py-2.5 text-sto-text"
            placeholder="you@example.com"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-sto-text mb-1">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            className="w-full rounded-lg bg-sto-card border border-sto-cardBorder px-3 py-2.5 text-sto-text"
          />
        </div>
        {error && (
          <p className="text-sto-danger text-sm">{error}</p>
        )}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-sto-accent text-white font-medium py-2.5 px-4 hover:bg-sto-accent/90 disabled:opacity-50 transition"
        >
          {loading ? "Logging in…" : "Log in"}
        </button>
      </form>
      <p className="mt-4 text-sto-muted text-sm text-center">
        Don’t have an account?{" "}
        <Link href="/signup" className="text-sto-accent font-medium hover:underline">
          Sign up
        </Link>
      </p>
    </div>
  );
}
