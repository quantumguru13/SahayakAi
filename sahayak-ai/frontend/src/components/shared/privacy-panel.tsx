"use client";

import { ShieldCheck } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const GUARANTEES = [
  "Offline OCR — no document ever leaves this machine",
  "Aadhaar masked to the last four digits everywhere",
  "Raw Aadhaar number never stored or transmitted",
  "Uploaded images discarded once fields are read",
  "Local AI processing — no external API, no paid service",
];

/** Trust summary shown alongside identity results. Each line reflects a real
 *  guarantee enforced in app/core/aadhaar.py and routes/documents.py. */
export function PrivacyPanel({ className }: { className?: string }) {
  return (
    <Card className={cn("border-success/30", className)}>
      <CardContent className="py-4">
        <div className="mb-2.5 flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-success/10 text-success">
            <ShieldCheck className="h-4 w-4" />
          </span>
          <span className="text-sm font-semibold">Privacy Protection</span>
        </div>
        <ul className="space-y-1.5">
          {GUARANTEES.map((g) => (
            <li
              key={g}
              className="flex items-start gap-2 text-xs leading-relaxed text-muted-foreground"
            >
              <span aria-hidden className="mt-0.5 shrink-0 font-semibold text-success">
                ✓
              </span>
              {g}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
