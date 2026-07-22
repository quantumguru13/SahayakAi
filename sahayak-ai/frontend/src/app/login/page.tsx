"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight,
  Eye,
  EyeOff,
  HeartHandshake,
  KeyRound,
  Loader2,
  Lock,
  Mail,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { loginDemoUser, loginLocal } from "@/lib/auth";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

export default function ProfessionalLoginPage() {
  const router = useRouter();
  const { toast } = useToast();

  const [email, setEmail] = useState("admin@sahayak.ai");
  const [password, setPassword] = useState("admin123");
  const [rememberMe, setRememberMe] = useState(true);
  const [showPassword, setShowPassword] = useState(false);

  const [loading, setLoading] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSignIn = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setLoading(true);

    setTimeout(() => {
      const res = loginLocal(email, password, rememberMe);
      if (res.success) {
        toast("Authenticated as NGO Administrator", "success");
        router.replace("/");
      } else {
        setErrorMsg(res.error || "Authentication failed.");
        setLoading(false);
      }
    }, 400);
  };

  const handleDemoSignIn = () => {
    setErrorMsg(null);
    setDemoLoading(true);

    setTimeout(() => {
      loginDemoUser();
      toast("Welcome to Sahayak AI Demo", "success");
      router.replace("/");
    }, 400);
  };

  const handleForgotPassword = () => {
    toast(
      "Demo Mode: Password reset link sent to admin@sahayak.ai (Pass: admin123)",
      "info"
    );
  };

  return (
    <div className="grid-bg relative min-h-screen overflow-hidden bg-background">
      {/* Ambient background glows */}
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -left-40 -top-40 h-[36rem] w-[36rem] rounded-full bg-primary/20 blur-[140px]"
        animate={{ opacity: [0.4, 0.7, 0.4], scale: [1, 1.06, 1] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -right-40 bottom-0 h-[32rem] w-[32rem] rounded-full bg-blue-600/15 blur-[140px]"
        animate={{ opacity: [0.3, 0.6, 0.3], scale: [1.05, 1, 1.05] }}
        transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="relative mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-8 sm:px-6">
        {/* Header / Branding */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-8 text-center"
        >
          <div className="mb-4 inline-flex items-center justify-center">
            <motion.div
              initial={{ scale: 0.8, rotate: -10 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: "spring", stiffness: 200, damping: 15 }}
              className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-xl shadow-primary/30"
            >
              <Sparkles className="h-7 w-7" />
            </motion.div>
          </div>

          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Sahayak{" "}
            <span className="bg-gradient-to-r from-primary via-blue-400 to-emerald-400 bg-clip-text text-transparent">
              AI
            </span>
          </h1>
          <p className="mt-2 text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground sm:text-sm">
            Humanitarian Case Intelligence Platform
          </p>
        </motion.div>

        {/* Main Glassmorphic Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
          className="rounded-2xl border border-border/70 bg-card/60 p-6 sm:p-8 backdrop-blur-xl shadow-2xl"
        >
          <div className="mb-6 flex items-center justify-between border-b border-border/50 pb-4">
            <div>
              <h2 className="text-lg font-semibold text-foreground">
                Sign In to Workspace
              </h2>
              <p className="text-xs text-muted-foreground">
                Authorized NGO Personnel Access
              </p>
            </div>
            <span className="flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-primary">
              <ShieldCheck className="h-3.5 w-3.5" />
              Secure
            </span>
          </div>

          {/* Validation Error Alert */}
          <AnimatePresence>
            {errorMsg && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="mb-5 overflow-hidden rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive"
              >
                {errorMsg}
              </motion.div>
            )}
          </AnimatePresence>

          <form onSubmit={handleSignIn} className="space-y-4">
            {/* Email Field */}
            <div className="space-y-1.5">
              <label
                htmlFor="email"
                className="text-xs font-medium text-muted-foreground"
              >
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@sahayak.ai"
                  className="w-full rounded-xl border border-border bg-background/50 py-2.5 pl-10 pr-4 text-sm font-medium text-foreground placeholder:text-muted-foreground/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label
                  htmlFor="password"
                  className="text-xs font-medium text-muted-foreground"
                >
                  Password
                </label>
                <button
                  type="button"
                  onClick={handleForgotPassword}
                  className="text-[11px] font-medium text-primary hover:underline focus:outline-none"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-xl border border-border bg-background/50 py-2.5 pl-10 pr-10 text-sm font-medium text-foreground placeholder:text-muted-foreground/60 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus:outline-none"
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Remember Me */}
            <div className="flex items-center justify-between pt-1">
              <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="h-4 w-4 rounded border-border bg-background text-primary focus:ring-primary focus:ring-offset-background"
                />
                Remember me on this device
              </label>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || demoLoading}
              className={cn(
                "group relative flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition-all hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2",
                (loading || demoLoading) && "opacity-75 cursor-not-allowed"
              )}
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Authenticating…
                </>
              ) : (
                <>
                  Sign In
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="my-5 flex items-center gap-3">
            <div className="h-px flex-1 bg-border/60" />
            <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              Or
            </span>
            <div className="h-px flex-1 bg-border/60" />
          </div>

          {/* Quick Demo Sign-in */}
          <button
            type="button"
            onClick={handleDemoSignIn}
            disabled={loading || demoLoading}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-border/80 bg-accent/40 py-2.5 text-xs font-semibold text-foreground transition-all hover:bg-accent hover:border-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            {demoLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
            ) : (
              <KeyRound className="h-4 w-4 text-primary" />
            )}
            Quick Demo Sign-In (1-Click)
          </button>

          {/* Credential Hint */}
          <div className="mt-5 rounded-xl border border-border/50 bg-muted/30 p-3 text-center text-[11px] text-muted-foreground">
            <span className="font-semibold text-foreground">Demo Credentials:</span>{" "}
            <code className="text-primary">admin@sahayak.ai</code> /{" "}
            <code className="text-primary">admin123</code>
          </div>
        </motion.div>

        {/* Footer */}
        <motion.footer
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="mt-8 text-center text-xs text-muted-foreground"
        >
          <div className="inline-flex items-center gap-1.5">
            <HeartHandshake className="h-3.5 w-3.5 text-primary" />
            <span>Built for grassroots humanitarian operations</span>
          </div>
        </motion.footer>
      </div>
    </div>
  );
}
