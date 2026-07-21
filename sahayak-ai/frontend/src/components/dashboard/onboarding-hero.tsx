"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, FlaskConical, ScanLine, Sparkles, Upload } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useSetMode } from "@/lib/hooks";
import { cn } from "@/lib/utils";

const STEPS = [
  { icon: Upload, title: "Upload a document", body: "Aadhaar, blood report, income or disability certificate — a photo or PDF." },
  { icon: ScanLine, title: "AI reads it offline", body: "OCR + extraction pull out name, ID, dates, income and medical findings." },
  { icon: Sparkles, title: "Get a prioritized case", body: "Urgency score, matched welfare schemes and follow-up tasks appear here." },
];

/** Shown on an empty LIVE dashboard — turns a blank slate into guided onboarding. */
export function OnboardingHero() {
  const setMode = useSetMode();

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Card className="grid-bg relative overflow-hidden p-6 sm:p-8">
        <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-primary/10 blur-3xl" />
        <div className="relative">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
            <Sparkles className="h-3.5 w-3.5" />
            Live AI · your workspace is ready
          </div>
          <h2 className="mt-3 text-xl font-semibold sm:text-2xl">
            No cases yet — let&apos;s onboard your first beneficiary
          </h2>
          <p className="mt-1.5 max-w-2xl text-sm text-muted-foreground">
            Live mode shows only the documents you upload — no sample data. Upload one
            document and this dashboard fills with a real, prioritized case.
          </p>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            {STEPS.map((s, i) => {
              const Icon = s.icon;
              return (
                <div
                  key={s.title}
                  className="rounded-xl border border-border bg-card/60 p-4"
                >
                  <div className="flex items-center gap-2">
                    <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <Icon className="h-4 w-4" />
                    </span>
                    <span className="text-xs font-semibold text-muted-foreground">
                      Step {i + 1}
                    </span>
                  </div>
                  <h3 className="mt-2 text-sm font-medium">{s.title}</h3>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    {s.body}
                  </p>
                </div>
              );
            })}
          </div>

          <div className="mt-6 flex flex-col gap-2 sm:flex-row">
            <Link href="/intake" className={buttonVariants({ className: "gap-2" })}>
              <Upload className="h-4 w-4" />
              Upload a document
              <ArrowRight className="h-4 w-4" />
            </Link>
            <button
              onClick={() => setMode.mutate("DEMO")}
              className={cn(
                buttonVariants({ variant: "outline", className: "gap-2" })
              )}
            >
              <FlaskConical className="h-4 w-4 text-warning" />
              Or explore Demo data
            </button>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
