"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  ListChecks,
  ShieldCheck,
  Users,
} from "lucide-react";

import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { DashboardMetrics } from "@/lib/types";

const ITEMS: {
  key: keyof DashboardMetrics;
  label: string;
  icon: typeof Users;
  tone: string;
  chip: string;
}[] = [
  { key: "total_beneficiaries", label: "Beneficiaries", icon: Users, tone: "text-primary", chip: "bg-primary/10" },
  { key: "critical_cases", label: "Critical", icon: AlertTriangle, tone: "text-destructive", chip: "bg-destructive/10" },
  { key: "high_cases", label: "High Priority", icon: ShieldCheck, tone: "text-warning", chip: "bg-warning/10" },
  { key: "pending_tasks", label: "Open Tasks", icon: ListChecks, tone: "text-foreground", chip: "bg-muted" },
  { key: "overdue_tasks", label: "Overdue", icon: Clock, tone: "text-destructive", chip: "bg-destructive/10" },
  { key: "schemes_available", label: "Schemes", icon: CheckCircle2, tone: "text-success", chip: "bg-success/10" },
];

export function MetricCards({
  metrics,
  isLoading,
  isError,
}: {
  metrics?: DashboardMetrics;
  isLoading?: boolean;
  isError?: boolean;
}) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {ITEMS.map((item, i) => {
        const Icon = item.icon;
        return (
          <motion.div
            key={item.key}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04, duration: 0.3 }}
          >
            <Card className="p-4 transition-all hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground">
                  {item.label}
                </span>
                <span
                  className={cn(
                    "flex h-7 w-7 items-center justify-center rounded-lg",
                    item.chip
                  )}
                >
                  <Icon className={cn("h-4 w-4", item.tone)} />
                </span>
              </div>
              {isError ? (
                <div className="mt-1 text-2xl font-semibold tabular-nums text-muted-foreground">
                  —
                </div>
              ) : isLoading || !metrics ? (
                <Skeleton className="mt-2 h-8 w-12" />
              ) : (
                <motion.div
                  key={metrics[item.key]}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-1 text-2xl font-semibold tabular-nums"
                >
                  {metrics[item.key]}
                </motion.div>
              )}
            </Card>
          </motion.div>
        );
      })}
    </div>
  );
}
