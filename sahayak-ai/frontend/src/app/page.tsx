"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight,
  BadgeCheck,
  CheckCircle2,
  FlaskConical,
  Gauge,
  HeartHandshake,
  Loader2,
  ScanLine,
  ShieldCheck,
  Sparkles,
  WifiOff,
} from "lucide-react";

import { useHealth, useSetMode } from "@/lib/hooks";
import { rememberMode } from "@/lib/session";
import type { PipelineMode } from "@/lib/types";
import { cn } from "@/lib/utils";

/** The two ways into the workspace. Each one activates a pipeline mode. */
const OPTIONS = [
  {
    mode: "LIVE" as PipelineMode,
    title: "Live Login",
    tagline: "Use real uploaded documents with offline OCR.",
    icon: Sparkles,
    bullets: [
      "Reads your own scans with Tesseract — no internet, no API key",
      "Urgency and scheme matches derived from the actual document",
      "Starts empty; your uploads build the dashboard",
    ],
  },
  {
    mode: "DEMO" as PipelineMode,
    title: "Demo Login",
    tagline: "Load demonstration beneficiaries for presentation.",
    icon: FlaskConical,
    bullets: [
      "Six curated cases with tasks, deadlines and scheme matches",
      "Fully deterministic — identical every run, cannot fail on stage",
      "No OCR executed; every screen is populated instantly",
    ],
  },
];

export default function LoginPage() {
  const router = useRouter();
  const { data: health } = useHealth();
  const setMode = useSetMode();
  const [entering, setEntering] = useState<PipelineMode | null>(null);

  const liveReady = health?.live_ocr_available ?? false;
  const engines = health?.ocr_engines ?? [];

  // Warm the dashboard route so the post-login transition is instant.
  useEffect(() => {
    router.prefetch("/dashboard");
  }, [router]);

  function login(mode: PipelineMode) {
    setEntering(mode);
    rememberMode(mode);
    setMode.mutate(mode, {
      onSettled: () => router.push("/dashboard"),
    });
  }

  return (
    <div className="grid-bg relative min-h-screen overflow-hidden bg-background">
      {/* Ambient gradient field */}
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -left-40 -top-40 h-[34rem] w-[34rem] rounded-full bg-primary/20 blur-[130px]"
        animate={{ opacity: [0.45, 0.75, 0.45], scale: [1, 1.08, 1] }}
        transition={{ duration: 9, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -right-40 bottom-0 h-[30rem] w-[30rem] rounded-full bg-success/10 blur-[130px]"
        animate={{ opacity: [0.35, 0.65, 0.35], scale: [1.05, 1, 1.05] }}
        transition={{ duration: 11, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="relative mx-auto flex min-h-screen max-w-5xl flex-col justify-center px-5 py-10 sm:px-6">
        {/* ---------------- Branding ---------------- */}
        <motion.header
          initial={{ opacity: 0, y: -14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-10 text-center"
        >
          <div className="mb-5 flex items-center justify-center gap-3">
            <motion.div
              initial={{ scale: 0.7, rotate: -8 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: "spring", stiffness: 220, damping: 16 }}
              className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/30"
            >
              <Sparkles className="h-6 w-6" />
            </motion.div>
          </div>

          <h1 className="text-balance text-4xl font-bold tracking-tight sm:text-5xl">
            Sahayak{" "}
            <span className="bg-gradient-to-r from-primary via-primary to-success bg-clip-text text-transparent">
              AI
            </span>
          </h1>
          <p className="mt-2.5 text-sm font-medium uppercase tracking-[0.2em] text-muted-foreground sm:text-base">
            Humanitarian Case Intelligence Platform
          </p>

          <div className="mt-5 inline-flex items-center gap-2 rounded-full border border-border bg-card/60 px-4 py-1.5 text-xs text-muted-foreground backdrop-blur">
            <HeartHandshake className="h-3.5 w-3.5 text-primary" />
            Built for grassroots NGOs · Choose how you want to sign in
          </div>
        </motion.header>

        {/* ---------------- Login options ---------------- */}
        <motion.div
          initial="hidden"
          animate="show"
          variants={{
            hidden: {},
            show: { transition: { staggerChildren: 0.12, delayChildren: 0.2 } },
          }}
          className="grid gap-4 sm:grid-cols-2"
        >
          {OPTIONS.map((opt) => {
            const Icon = opt.icon;
            const isLive = opt.mode === "LIVE";
            const disabled = entering !== null;
            return (
              <motion.button
                key={opt.mode}
                type="button"
                variants={{
                  hidden: { opacity: 0, y: 22 },
                  show: { opacity: 1, y: 0 },
                }}
                whileHover={disabled ? undefined : { y: -4 }}
                transition={{ type: "spring", stiffness: 300, damping: 22 }}
                onClick={() => login(opt.mode)}
                disabled={disabled}
                aria-label={`${opt.title} — ${opt.tagline}`}
                className={cn(
                  "group relative flex flex-col rounded-2xl border bg-card/60 p-6 text-left backdrop-blur transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  isLive
                    ? "border-primary/40 hover:border-primary"
                    : "border-border hover:border-warning/60",
                  disabled && "pointer-events-none opacity-60"
                )}
              >
                <div className="flex items-center justify-between">
                  <span
                    className={cn(
                      "flex h-11 w-11 items-center justify-center rounded-xl",
                      isLive
                        ? "bg-primary/15 text-primary"
                        : "bg-warning/15 text-warning"
                    )}
                  >
                    {entering === opt.mode ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                      <Icon className="h-5 w-5" />
                    )}
                  </span>
                  {isLive &&
                    (liveReady ? (
                      <span className="flex items-center gap-1.5 rounded-full border border-success/40 bg-success/10 px-2.5 py-1 text-[10px] font-medium text-success">
                        <ShieldCheck className="h-3 w-3" />
                        Offline ready
                      </span>
                    ) : (
                      <span className="flex items-center gap-1.5 rounded-full border border-warning/40 bg-warning/10 px-2.5 py-1 text-[10px] font-medium text-warning">
                        <WifiOff className="h-3 w-3" />
                        OCR not installed
                      </span>
                    ))}
                </div>

                <h2 className="mt-4 text-lg font-semibold">{opt.title}</h2>
                <p className="mt-1 text-sm text-muted-foreground">{opt.tagline}</p>

                <ul className="mt-4 flex-1 space-y-2">
                  {opt.bullets.map((b) => (
                    <li
                      key={b}
                      className="flex items-start gap-2 text-xs leading-relaxed text-muted-foreground"
                    >
                      <CheckCircle2
                        className={cn(
                          "mt-0.5 h-3.5 w-3.5 shrink-0",
                          isLive ? "text-primary" : "text-warning"
                        )}
                      />
                      {b}
                    </li>
                  ))}
                </ul>

                <span
                  className={cn(
                    "mt-5 inline-flex items-center gap-1.5 text-sm font-semibold",
                    isLive ? "text-primary" : "text-warning"
                  )}
                >
                  {entering === opt.mode
                    ? "Signing in…"
                    : `Continue with ${opt.title}`}
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </span>
              </motion.button>
            );
          })}
        </motion.div>

        {/* ---------------- Engine status ---------------- */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.55 }}
          className="mt-6 text-center text-xs text-muted-foreground"
        >
          {liveReady ? (
            <>
              Offline OCR engine:{" "}
              <span className="font-medium text-foreground">
                {engines.join(" → ")}
              </span>{" "}
              · no internet required
            </>
          ) : (
            <>
              No OCR engine detected — install Tesseract to enable Live mode:{" "}
              <span className="font-medium text-foreground">
                winget install --id UB-Mannheim.TesseractOCR
              </span>
            </>
          )}
        </motion.p>

        {/* ---------------- Pipeline strip ---------------- */}
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.5 }}
          className="mt-10 flex flex-wrap items-center justify-center gap-2 sm:gap-3"
        >
          {[
            { icon: ScanLine, label: "Upload" },
            { icon: Sparkles, label: "OCR" },
            { icon: Gauge, label: "Urgency" },
            { icon: BadgeCheck, label: "Schemes" },
          ].map((step, i, arr) => {
            const Icon = step.icon;
            return (
              <div key={step.label} className="flex items-center gap-2 sm:gap-3">
                <div className="flex flex-col items-center gap-1.5">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-border bg-card/70 text-primary backdrop-blur">
                    <Icon className="h-4 w-4" />
                  </div>
                  <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                    {step.label}
                  </span>
                </div>
                {i < arr.length - 1 && (
                  <span className="h-px w-4 bg-gradient-to-r from-primary/60 to-border sm:w-8" />
                )}
              </div>
            );
          })}
        </motion.div>

        <footer className="mt-10 text-center text-xs text-muted-foreground">
          No vulnerable individual should fall through the cracks.
        </footer>
      </div>

      {/* ---------------- Sign-in transition ---------------- */}
      <AnimatePresence>
        {entering && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-background/85 backdrop-blur"
          >
            <motion.div
              animate={{ scale: [1, 1.14, 1] }}
              transition={{ duration: 1.2, repeat: Infinity }}
              className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/40"
            >
              <Sparkles className="h-7 w-7" />
            </motion.div>
            <p className="text-sm text-muted-foreground">
              Entering {entering === "LIVE" ? "Live" : "Demo"} workspace…
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
