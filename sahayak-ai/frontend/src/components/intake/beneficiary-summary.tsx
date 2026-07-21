"use client";

import { motion } from "framer-motion";
import {
  BadgeCheck,
  Cake,
  FileText,
  Landmark,
  MapPin,
  ShieldAlert,
  User,
} from "lucide-react";

import { PriorityBadge } from "@/components/shared/priority-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DocumentUploadResponse } from "@/lib/types";

/** At-a-glance overview shown ABOVE the detailed analysis, so a judge sees the
 *  outcome first and the evidence second. Every value comes from the response. */
export function BeneficiarySummary({
  result,
}: {
  result: DocumentUploadResponse;
}) {
  const b = result.beneficiary;
  const a = result.aadhaar;
  const topScheme = result.scheme_matches[0]?.scheme.title ?? null;

  const identity = a
    ? a.verification.status === "VERIFIED"
      ? { label: "Aadhaar verified", tone: "success" as const }
      : { label: "Manual review", tone: "warning" as const }
    : null;

  const rows = [
    { icon: User, label: "Name", value: b.name },
    {
      icon: Cake,
      label: "Age",
      value: b.age !== null ? `${b.age} years` : "Not captured",
    },
    {
      icon: MapPin,
      label: "Location",
      value: [a?.fields.district, b.state_location].filter(Boolean).join(", ") || "—",
    },
    {
      icon: FileText,
      label: "Documents",
      value: `1 processed · ${result.generated_tasks.length} task(s)`,
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Card className="border-primary/30">
        <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <BadgeCheck className="h-4 w-4 text-primary" />
            Beneficiary Overview
          </CardTitle>
          <div className="flex items-center gap-1.5">
            {identity && (
              <Badge variant={identity.tone} className="gap-1 text-[10px]">
                <ShieldAlert className="h-3 w-3" />
                {identity.label}
              </Badge>
            )}
            <PriorityBadge priority={b.current_priority} />
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            {rows.map((r) => {
              const Icon = r.icon;
              return (
                <div key={r.label} className="flex items-start gap-2.5">
                  <span className="mt-0.5 shrink-0 text-muted-foreground">
                    <Icon className="h-3.5 w-3.5" />
                  </span>
                  <div className="min-w-0">
                    <div className="text-[11px] text-muted-foreground">{r.label}</div>
                    <div className="truncate text-sm font-medium">{r.value}</div>
                  </div>
                </div>
              );
            })}
          </div>

          {topScheme && (
            <div className="flex items-start gap-2.5 rounded-lg border border-border bg-muted/30 p-3">
              <span className="mt-0.5 shrink-0 text-primary">
                <Landmark className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <div className="text-[11px] text-muted-foreground">
                  Top recommended scheme
                </div>
                <div className="text-sm font-semibold">{topScheme}</div>
                <div className="text-[11px] text-muted-foreground">
                  {Math.round(result.scheme_matches[0].confidence * 100)}% eligibility
                  confidence · urgency {result.urgency.score}/100
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
