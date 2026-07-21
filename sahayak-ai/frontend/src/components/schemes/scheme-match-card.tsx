"use client";

import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, LifeBuoy, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useBeneficiary } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import type { SchemeMatch } from "@/lib/types";

function confidenceTone(c: number) {
  if (c >= 0.7) return { label: "Strong match", bar: "bg-success", text: "text-success" };
  if (c >= 0.45) return { label: "Likely eligible", bar: "bg-primary", text: "text-primary" };
  return { label: "Possible", bar: "bg-warning", text: "text-warning" };
}

export function SchemeMatchCard({
  match,
  index = 0,
  beneficiaryId,
}: {
  match: SchemeMatch;
  index?: number;
  beneficiaryId?: string;
}) {
  const { data: beneficiary } = useBeneficiary(beneficiaryId ?? "");
  const pct = Math.round(match.confidence * 100);
  const tone = confidenceTone(match.confidence);

  // Dynamic eligibility checks to flag missing/uncertain information
  const warnings: string[] = [];
  if (beneficiary) {
    const isRAN = match.scheme.id === "scheme-ran" || match.scheme.title.includes("RAN") || match.scheme.title.includes("Arogya Nidhi");
    const isPMJAY = match.scheme.id === "scheme-pmjay" || match.scheme.title.includes("PM-JAY") || match.scheme.title.includes("Ayushman");
    const isDisability = match.scheme.id === "scheme-disability-pension" || match.scheme.title.toLowerCase().includes("disability");
    const isOldAge = match.scheme.id === "scheme-oldage-pension" || match.scheme.title.toLowerCase().includes("old age") || match.scheme.title.toLowerCase().includes("senior");
    const isWidow = match.scheme.id === "scheme-widow-pension" || match.scheme.title.toLowerCase().includes("widow");

    if (beneficiary.annual_income === null) {
      warnings.push("Annual household income is missing. Income proof certificate verification required.");
    }
    if (beneficiary.age === null) {
      warnings.push("Beneficiary age is missing. Birth Certificate / Aadhaar verification required.");
    }
    if (isDisability && !beneficiary.is_disabled) {
      warnings.push("Registered disability status proof (40%+) is required to qualify.");
    }
    if ((isRAN || isPMJAY) && (!beneficiary.medical_conditions || beneficiary.medical_conditions.length === 0)) {
      warnings.push("Diagnostic medical report (cancer, renal, or surgical) is required.");
    }
    if (isOldAge && beneficiary.age !== null && beneficiary.age < 60) {
      warnings.push(`Beneficiary age (${beneficiary.age}) is below the required 60 years limit.`);
    }
    if (isWidow && beneficiary.age !== null && (beneficiary.age < 40 || beneficiary.age > 59)) {
      warnings.push(`Widow pension age window is 40-59 years (beneficiary is ${beneficiary.age}).`);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, duration: 0.3 }}
      className={cn(
        "flex flex-col justify-between rounded-xl border bg-card p-5 shadow-sm transition-all",
        match.is_alternative ? "border-dashed border-border/80" : "border-border"
      )}
    >
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-2.5">
            <div
              className={cn(
                "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                match.is_alternative
                  ? "bg-muted text-muted-foreground"
                  : "bg-primary/15 text-primary"
              )}
            >
              {match.is_alternative ? (
                <LifeBuoy className="h-4 w-4" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
            </div>
            <div>
              <h3 className="text-sm font-semibold leading-snug">
                {match.scheme.title}
              </h3>
              <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                  {match.scheme.category}
                </Badge>
                {match.is_alternative && (
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                    Alternative Support
                  </Badge>
                )}
              </div>
            </div>
          </div>
          <div className="text-right shrink-0">
            <div className={cn("text-2xl font-extrabold tabular-nums leading-none", tone.text)}>
              {pct}%
            </div>
            <div className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground mt-1">
              confidence
            </div>
          </div>
        </div>

        <p className="mt-3.5 text-xs leading-relaxed text-muted-foreground">
          {match.scheme.description}
        </p>

        {match.matched_reasons.length > 0 && (
          <div className="mt-4">
            <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground block mb-2">
              Why Recommended (Matched Rules)
            </span>
            <ul className="space-y-1.5">
              {match.matched_reasons.map((r) => (
                <li
                  key={r}
                  className="flex items-start gap-2 text-xs text-muted-foreground leading-normal"
                >
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {warnings.length > 0 && (
          <div className="mt-4 rounded-lg bg-warning/5 border border-warning/20 p-3">
            <span className="text-[9px] font-bold uppercase tracking-wider text-warning flex items-center gap-1 mb-1.5">
              <AlertTriangle className="h-3.5 w-3.5" />
              Missing / Uncertain Verification Gaps
            </span>
            <ul className="space-y-1">
              {warnings.map((w, i) => (
                // Amber hue, not `warning-foreground` — that token is near-black
                // and unreadable on this translucent panel in the dark theme.
                <li key={i} className="text-[11px] leading-relaxed text-warning">
                  • {w}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="mt-5 pt-3 border-t border-border/50">
        <div className="mb-2 flex items-center justify-between text-[10px] font-medium">
          <span className={tone.text}>{tone.label}</span>
          <span className="text-muted-foreground">
            rules: {Math.round(match.rule_score * 100)}% · semantic:{" "}
            {Math.round(match.semantic_similarity * 100)}%
          </span>
        </div>
        <Progress value={pct} indicatorClassName={tone.bar} className="h-1" />
      </div>
    </motion.div>
  );
}
