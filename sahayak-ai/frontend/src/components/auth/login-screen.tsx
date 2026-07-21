"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Loader2, LogIn, Sparkles } from "lucide-react";

import { useAuth } from "./auth-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function LoginScreen() {
  const { signInWithGoogle, signInWithEmail, signUpWithEmail } = useAuth();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState<null | "google" | "email">(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function handleEmail(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setBusy("email");
    const fn = mode === "signin" ? signInWithEmail : signUpWithEmail;
    const { error } = await fn(email, password);
    setBusy(null);
    if (error) setError(error);
    else if (mode === "signup")
      setNotice("Check your email to confirm your account, then sign in.");
  }

  async function handleGoogle() {
    setError(null);
    setBusy("google");
    const { error } = await signInWithGoogle();
    if (error) {
      setError(error);
      setBusy(null);
    }
    // On success the browser redirects to Google.
  }

  return (
    <div className="grid-bg flex min-h-screen items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-sm"
      >
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Sparkles className="h-6 w-6" />
          </div>
          <h1 className="mt-3 text-xl font-semibold">Sahayak AI</h1>
          <p className="text-sm text-muted-foreground">
            Humanitarian Case Intelligence
          </p>
        </div>

        <Card className="glow-primary">
          <CardContent className="space-y-4 pt-6">
            <Button
              variant="outline"
              className="w-full gap-2"
              onClick={handleGoogle}
              disabled={busy !== null}
            >
              {busy === "google" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <GoogleIcon />
              )}
              Continue with Google
            </Button>

            <div className="flex items-center gap-3">
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs text-muted-foreground">or</span>
              <div className="h-px flex-1 bg-border" />
            </div>

            <form onSubmit={handleEmail} className="space-y-3">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@ngo.org"
                autoComplete="email"
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:border-primary"
              />
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                autoComplete={
                  mode === "signin" ? "current-password" : "new-password"
                }
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:border-primary"
              />
              <Button type="submit" className="w-full gap-2" disabled={busy !== null}>
                {busy === "email" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <LogIn className="h-4 w-4" />
                )}
                {mode === "signin" ? "Sign in" : "Create account"}
              </Button>
            </form>

            {error && <p className="text-sm text-destructive">{error}</p>}
            {notice && <p className="text-sm text-success">{notice}</p>}

            <p className="text-center text-xs text-muted-foreground">
              {mode === "signin" ? "New here?" : "Already have an account?"}{" "}
              <button
                type="button"
                className="font-medium text-primary hover:underline"
                onClick={() => {
                  setMode(mode === "signin" ? "signup" : "signin");
                  setError(null);
                  setNotice(null);
                }}
              >
                {mode === "signin" ? "Create an account" : "Sign in"}
              </button>
            </p>
          </CardContent>
        </Card>

        <p className="mt-4 text-center text-xs text-muted-foreground">
          Secured by Supabase Auth · single-tenant NGO workspace
        </p>
      </motion.div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1Z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84Z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A11 11 0 0 0 2.18 7.06l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38Z"
      />
    </svg>
  );
}
