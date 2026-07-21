"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  BadgeCheck,
  CalendarDays,
  Check,
  Fingerprint,
  MapPin,
  Phone,
  QrCode,
  ShieldAlert,
  ShieldCheck,
  User,
  X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import type { AadhaarAnalysis, VerificationStatus } from "@/lib/types";

const STATUS: Record<
  VerificationStatus,
  { label: string; variant: "success" | "warning" | "destructive"; icon: typeof ShieldCheck }
> = {
  VERIFIED: { label: "Verified", variant: "success", icon: ShieldCheck },
  MANUAL_REVIEW: {
    label: "Manual Review Recommended",
    variant: "warning",
    icon: ShieldAlert,
  },
  NOT_AADHAAR: {
    label: "Not an Aadhaar document",
    variant: "destructive",
    icon: AlertTriangle,
  },
};

/** Human labels for the verification checks returned by app/core/aadhaar.py. */
const CHECK_LABELS: Record<string, string> = {
  number_present: "Aadhaar number found",
  length_12: "12-digit length",
  numeric_only: "Numeric pattern",
  checksum_valid: "Verhoeff checksum",
  valid_prefix: "Valid number prefix",
  ocr_confidence_ok: "OCR confidence",
  layout_consistent: "Government layout markers",
  mandatory_fields_present: "Mandatory fields present",
};

/** Restates the confidence score as a verdict plus the evidence behind it. */
function ConfidenceSummary({ analysis }: { analysis: AadhaarAnalysis }) {
  const f = analysis.fields;
  const pct = Math.round(analysis.ocr_confidence * 100);
  const tone =
    pct >= 75
      ? { label: "High Confidence", cls: "text-success", border: "border-success/30 bg-success/5" }
      : pct >= 55
      ? { label: "Moderate Confidence", cls: "text-warning", border: "border-warning/30 bg-warning/5" }
      : { label: "Low Confidence", cls: "text-destructive", border: "border-destructive/30 bg-destructive/5" };

  const found: string[] = [];
  const absent: string[] = [];
  ([
    ["Name detected", f.full_name],
    ["Aadhaar number read", f.aadhaar_number],
    ["Date of birth extracted", f.date_of_birth],
    ["Gender identified", f.gender],
    ["Address extracted", f.address],
    ["District & PIN resolved", f.district && f.pin_code],
    ["QR code readable", f.qr_detected || null],
  ] as const).forEach(([label, value]) => (value ? found : absent).push(label));

  if (analysis.verification.checks.checksum_valid) {
    found.unshift("Aadhaar checksum validated");
  }

  return (
    <div className={cn("rounded-lg border p-3", tone.border)}>
      <div className="mb-2 flex items-center justify-between">
        <span className={cn("text-sm font-semibold", tone.cls)}>{tone.label}</span>
        <span className={cn("text-sm font-bold tabular-nums", tone.cls)}>{pct}%</span>
      </div>
      <div className="grid gap-1.5 sm:grid-cols-2">
        {found.map((r) => (
          <div key={r} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Check className="h-3.5 w-3.5 shrink-0 text-success" />
            {r}
          </div>
        ))}
        {absent.map((r) => (
          <div key={r} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <X className="h-3.5 w-3.5 shrink-0 text-muted-foreground/60" />
            <span className="line-through decoration-muted-foreground/40">{r}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function AadhaarPanel({ analysis }: { analysis: AadhaarAnalysis }) {
  const f = analysis.fields;
  const v = analysis.verification;
  const status = STATUS[v.status];
  const StatusIcon = status.icon;
  const confidencePct = Math.round(analysis.ocr_confidence * 100);

  const rows: { icon: typeof User; label: string; value: string | null }[] = [
    { icon: User, label: "Full name", value: f.full_name },
    { icon: Fingerprint, label: "Aadhaar number", value: f.aadhaar_number },
    { icon: CalendarDays, label: "Date of birth", value: f.date_of_birth },
    {
      icon: CalendarDays,
      label: "Year of birth",
      value: f.year_of_birth ? String(f.year_of_birth) : null,
    },
    { icon: User, label: "Gender", value: f.gender },
    { icon: MapPin, label: "Address", value: f.address },
    { icon: MapPin, label: "District", value: f.district },
    { icon: MapPin, label: "State", value: f.state },
    { icon: MapPin, label: "PIN code", value: f.pin_code },
    { icon: Phone, label: "Mobile", value: f.mobile },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle className="flex items-center gap-2 text-sm">
            <BadgeCheck className="h-4 w-4 text-primary" />
            Aadhaar Analysis
            <Badge variant="secondary" className="text-[10px] capitalize">
              {f.side}
            </Badge>
          </CardTitle>
          <Badge variant={status.variant} className="gap-1.5">
            <StatusIcon className="h-3 w-3" />
            {status.label}
          </Badge>
        </CardHeader>

        <CardContent className="space-y-5">
          {/* Confidence stated in words, with the evidence behind it — a bare
              percentage tells a caseworker nothing actionable. */}
          <ConfidenceSummary analysis={analysis} />

          {/* Low-confidence advisory — never silently trust a poor read. */}
          {analysis.low_confidence && (
            <div className="flex items-start gap-2 rounded-lg border border-warning/40 bg-warning/10 px-3 py-2 text-xs text-warning">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                <strong>Low Confidence</strong> — OCR read this document at{" "}
                {confidencePct}%. Fields shown are what was actually read; blanks are
                left blank rather than guessed. Verify against the original card.
              </span>
            </div>
          )}

          {/* Extracted fields */}
          <div className="grid gap-2.5 sm:grid-cols-2">
            {rows.map((r) => {
              const Icon = r.icon;
              return (
                <div key={r.label} className="flex items-start gap-2.5">
                  <span className="mt-0.5 shrink-0 text-muted-foreground">
                    <Icon className="h-3.5 w-3.5" />
                  </span>
                  <div className="min-w-0">
                    <div className="text-[11px] text-muted-foreground">{r.label}</div>
                    <div
                      className={cn(
                        "break-words text-sm font-medium",
                        r.value ? "text-foreground" : "text-muted-foreground"
                      )}
                    >
                      {r.value ?? "Not found"}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* QR + confidence */}
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-border bg-muted/30 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                <QrCode className="h-3.5 w-3.5" /> QR code
              </div>
              <div className="text-sm">
                {f.qr_detected ? (
                  <span className="text-success">Detected &amp; readable</span>
                ) : (
                  <span className="text-muted-foreground">Not detected</span>
                )}
              </div>
              {f.qr_preview && (
                <p className="mt-1 truncate text-[11px] text-muted-foreground">
                  {f.qr_preview}
                </p>
              )}
            </div>
            <div className="rounded-lg border border-border bg-muted/30 p-3">
              <div className="mb-1.5 flex items-center justify-between text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                <span>OCR confidence</span>
                <span
                  className={cn(
                    "tabular-nums font-semibold",
                    confidencePct >= 75
                      ? "text-success"
                      : confidencePct >= 55
                      ? "text-warning"
                      : "text-destructive"
                  )}
                >
                  {confidencePct}%
                </span>
              </div>
              <Progress value={confidencePct} className="h-1.5" />
            </div>
          </div>

          {/* Verification checks */}
          <div>
            <div className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Verification checks
            </div>
            <div className="grid gap-1.5 sm:grid-cols-2">
              {Object.entries(v.checks).map(([key, passed]) => (
                <div key={key} className="flex items-center gap-2 text-xs">
                  {passed ? (
                    <Check className="h-3.5 w-3.5 shrink-0 text-success" />
                  ) : (
                    <X className="h-3.5 w-3.5 shrink-0 text-destructive" />
                  )}
                  <span
                    className={passed ? "text-muted-foreground" : "text-foreground"}
                  >
                    {CHECK_LABELS[key] ?? key.replace(/_/g, " ")}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Why manual review / what is missing */}
          {v.reasons.length > 0 && (
            <div className="rounded-lg border border-warning/20 bg-warning/5 p-3">
              <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-warning">
                <AlertTriangle className="h-3.5 w-3.5" />
                {v.manual_review ? "Why manual review" : "Notes"}
              </div>
              <ul className="space-y-1">
                {v.reasons.map((r) => (
                  <li key={r} className="text-[11px] leading-relaxed text-warning">
                    • {r}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {v.front_back_conflicts.length > 0 && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3">
              <div className="mb-1.5 text-[11px] font-bold uppercase tracking-wider text-destructive">
                Front / back mismatch
              </div>
              <ul className="space-y-1">
                {v.front_back_conflicts.map((c) => (
                  <li key={c} className="text-[11px] text-destructive">
                    • {c}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="text-[11px] text-muted-foreground">
            The full Aadhaar number is never stored or transmitted — only the masked
            value above and a one-way hash used to detect duplicate uploads.
          </p>
        </CardContent>
      </Card>
    </motion.div>
  );
}
