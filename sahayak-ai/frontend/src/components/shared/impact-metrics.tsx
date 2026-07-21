"use client";

import { motion } from "framer-motion";
import {
  BadgeCheck,
  FileScan,
  Landmark,
  Timer,
  Users,
  WifiOff,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useBrief, useUploadHistory } from "@/lib/hooks";
import { cn } from "@/lib/utils";

/** Operational statistics derived entirely from data the app already returns —
 *  the dashboard brief and the upload audit trail. No new endpoint. */
export function ImpactMetrics() {
  const { data: brief, isLoading: briefLoading } = useBrief();
  const { data: history, isLoading: historyLoading } = useUploadHistory();

  const isLoading = briefLoading || historyLoading;
  const rows = history ?? [];
  const processed = rows.filter((h) => h.status === "SUCCESS");
  const avgMs = processed.length
    ? Math.round(
        processed.reduce((sum, h) => sum + h.processing_ms, 0) / processed.length
      )
    : null;
  const aadhaarRows = rows.filter((h) => h.verification_status);
  const verified = aadhaarRows.filter((h) => h.verification_status === "VERIFIED");
  const verifyRate = aadhaarRows.length
    ? Math.round((verified.length / aadhaarRows.length) * 100)
    : null;

  const items = [
    {
      icon: FileScan,
      label: "Documents Processed",
      value: String(processed.length),
      tone: "text-primary",
      chip: "bg-primary/10",
    },
    {
      icon: Users,
      label: "Beneficiaries Assisted",
      value: String(brief?.metrics.total_beneficiaries ?? 0),
      tone: "text-success",
      chip: "bg-success/10",
    },
    {
      icon: Landmark,
      label: "Schemes Available",
      value: String(brief?.metrics.schemes_available ?? 0),
      tone: "text-primary",
      chip: "bg-primary/10",
    },
    {
      icon: Timer,
      label: "Avg Processing Time",
      value: avgMs === null ? "—" : `${avgMs} ms`,
      tone: "text-foreground",
      chip: "bg-muted",
    },
    {
      icon: BadgeCheck,
      label: "Verification Success",
      value: verifyRate === null ? "—" : `${verifyRate}%`,
      tone: "text-success",
      chip: "bg-success/10",
    },
    {
      icon: WifiOff,
      label: "Offline Processing",
      value: "100%",
      tone: "text-warning",
      chip: "bg-warning/10",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {items.map((item, i) => {
        const Icon = item.icon;
        return (
          <motion.div
            key={item.label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04, duration: 0.3 }}
          >
            <Card className="p-4 transition-all hover:border-primary/30">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-muted-foreground">
                  {item.label}
                </span>
                <span
                  className={cn(
                    "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg",
                    item.chip
                  )}
                >
                  <Icon className={cn("h-4 w-4", item.tone)} />
                </span>
              </div>
              {isLoading ? (
                <Skeleton className="mt-2 h-7 w-16" />
              ) : (
                <div className="mt-1 text-2xl font-semibold tabular-nums">
                  {item.value}
                </div>
              )}
            </Card>
          </motion.div>
        );
      })}
    </div>
  );
}
