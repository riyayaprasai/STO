"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { signup, user } = useAuth();
  const router = useRouter();

  if (user) {
    router.replace("/trading");
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError("Passwords don’t match.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    setLoading(true);
    const err = await signup(email.trim(), password);
    setLoading(false);
    if (err) {
      setError(err);
      return;
    }
    router.push("/trading");
  }

  return (
    <div className="max-w-md mx-auto">
      <h1 className="text-3xl font-bold text-sto-text mb-2">Sign up</h1>
      <p className="text-sto-muted mb-6">
        Create an account to get your own portfolio and practice trading with play money.
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
            minLength={6}
            autoComplete="new-password"
            className="w-full rounded-lg bg-sto-card border border-sto-cardBorder px-3 py-2.5 text-sto-text"
            placeholder="At least 6 characters"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-sto-text mb-1">Confirm password</label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            autoComplete="new-password"
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
          {loading ? "Creating account…" : "Sign up"}
        </button>
      </form>
      <p className="mt-4 text-sto-muted text-sm text-center">
        Already have an account?{" "}
        <Link href="/login" className="text-sto-accent font-medium hover:underline">
          Log in
        </Link>
      </p>
    </div>
  );
}
