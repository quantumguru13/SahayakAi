"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { Session, User } from "@supabase/supabase-js";

import { authEnabled, setAccessToken, supabase } from "@/lib/supabase";

interface AuthContextValue {
  authEnabled: boolean;
  loading: boolean;
  session: Session | null;
  user: User | null;
  signInWithGoogle: () => Promise<{ error?: string }>;
  signInWithEmail: (
    email: string,
    password: string
  ) => Promise<{ error?: string }>;
  signUpWithEmail: (
    email: string,
    password: string
  ) => Promise<{ error?: string }>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState<boolean>(authEnabled);

  useEffect(() => {
    if (!authEnabled || !supabase) {
      setLoading(false);
      return;
    }
    let active = true;
    supabase.auth.getSession().then(({ data }) => {
      if (!active) return;
      setSession(data.session);
      setAccessToken(data.session?.access_token ?? null);
      setLoading(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s);
      setAccessToken(s?.access_token ?? null);
    });
    return () => {
      active = false;
      sub.subscription.unsubscribe();
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      authEnabled,
      loading,
      session,
      user: session?.user ?? null,
      signInWithGoogle: async () => {
        if (!supabase) return { error: "Auth is not configured." };
        const { error } = await supabase.auth.signInWithOAuth({
          provider: "google",
          options: { redirectTo: window.location.origin },
        });
        return { error: error?.message };
      },
      signInWithEmail: async (email, password) => {
        if (!supabase) return { error: "Auth is not configured." };
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        return { error: error?.message };
      },
      signUpWithEmail: async (email, password) => {
        if (!supabase) return { error: "Auth is not configured." };
        const { error } = await supabase.auth.signUp({ email, password });
        return { error: error?.message };
      },
      signOut: async () => {
        await supabase?.auth.signOut();
        setAccessToken(null);
      },
    }),
    [loading, session]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
