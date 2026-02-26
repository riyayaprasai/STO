"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import type { AuthUser } from "@/lib/auth";
import * as auth from "@/lib/auth";
import { api } from "@/lib/api";

type AuthContextValue = {
  user: AuthUser;
  loading: boolean;
  login: (email: string, password: string) => Promise<string | null>;
  signup: (email: string, password: string) => Promise<string | null>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setUser(auth.getUser());
    setLoading(false);
  }, []);

  const login = async (email: string, password: string): Promise<string | null> => {
    try {
      const res = await api.login(email, password);
      auth.setToken(res.token);
      auth.setUser(res.user);
      setUser(res.user);
      return null;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Something went wrong. Try again.";
      return msg.startsWith("API error") ? "Invalid email or password." : msg;
    }
  };

  const signup = async (email: string, password: string): Promise<string | null> => {
    try {
      const res = await api.signup(email, password);
      auth.setToken(res.token);
      auth.setUser(res.user);
      setUser(res.user);
      return null;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Something went wrong. Try again.";
      return msg.startsWith("API error") ? "Email may already be in use or use a password with at least 6 characters." : msg;
    }
  };

  const logout = () => {
    auth.removeToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
