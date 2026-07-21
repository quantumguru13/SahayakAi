"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Check, Loader2 } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { DocumentUploadResponse } from "@/lib/types";

/** The pipeline stages the backend actually runs, in order. */
const STAGES = [
  { key: "upload", label: "Upload complete", running: "Receiving document…" },
  { key: "ocr", label: "OCR complete", running: "Reading document…" },
  { key: "extract", label: "Beneficiary created", running: "Extracting beneficiary…" },
  { key: "schemes", label: "Recommendations ready", running: "Finding government schemes…" },
  { key: "tasks", label: "Complete", running: "Generating follow-up tasks…" },
] as const;

/** Advance one stage roughly every 450 ms while the request is in flight. The
 *  bar always settles on the REAL result — the detail lines below each completed
 *  stage come from the response, never from the animation. */
const STEP_MS = 450;

export function ProcessingTimeline({
  isPending,
  result,
}: {
  isPending: boolean;
  result: DocumentUploadResponse | null;
}) {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    if (!isPending) return;
    setStage(0);
    const id = setInterval(
      () => setStage((s) => Math.min(s + 1, STAGES.length - 1)),
      STEP_MS
    );
    return () => clearInterval(id);
  }, [isPending]);

  const done = !isPending && !!result;
  // Real facts from the response, attached to the stage they belong to.
  const detail: Record<string, string | null> = {
    upload: result ? result.debug?.mode ?? null : null,
    ocr: result?.debug
      ? `${result.debug.ocr_engine} · ${Math.round(result.debug.ocr_confidence * 100)}% confidence`
      : null,
    extract: result?.beneficiary?.name ?? null,
    schemes: result ? `${result.scheme_matches.length} scheme(s) matched` : null,
    tasks: result ? `${result.generated_tasks.length} task(s) generated` : null,
  };

  return (
    <Card>
      <CardContent className="py-4">
        <ol className="space-y-2.5">
          {STAGES.map((s, i) => {
            const complete = done || i < stage;
            const active = !done && i === stage;
            return (
              <li key={s.key} className="flex items-start gap-3">
                <span
                  className={cn(
                    "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors",
                    complete
                      ? "border-success bg-success/15 text-success"
                      : active
                      ? "border-primary text-primary"
                      : "border-border text-transparent"
                  )}
                >
                  {complete ? (
                    <Check className="h-3 w-3" />
                  ) : active ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <span className="h-1.5 w-1.5 rounded-full bg-border" />
                  )}
                </span>
                <div className="min-w-0 flex-1">
                  <motion.p
                    initial={false}
                    animate={{ opacity: complete || active ? 1 : 0.45 }}
                    className={cn(
                      "text-sm leading-snug",
                      complete
                        ? "font-medium text-foreground"
                        : active
                        ? "font-medium text-primary"
                        : "text-muted-foreground"
                    )}
                  >
                    {complete ? s.label : s.running}
                  </motion.p>
                  {complete && detail[s.key] && (
                    <motion.p
                      initial={{ opacity: 0, y: -2 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="mt-0.5 truncate text-[11px] text-muted-foreground"
                    >
                      {detail[s.key]}
                    </motion.p>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </CardContent>
    </Card>
  );
}
