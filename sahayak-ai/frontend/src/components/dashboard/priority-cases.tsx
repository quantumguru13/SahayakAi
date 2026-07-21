"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ChevronRight, HeartPulse, ShieldCheck } from "lucide-react";

import { ErrorState } from "@/components/shared/error-state";
import { PriorityBadge } from "@/components/shared/priority-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useBeneficiaries } from "@/lib/hooks";

export function PriorityCases() {
  const { data, isLoading, isError, refetch } = useBeneficiaries();
  const urgent = (data ?? [])
    .filter((b) => b.current_priority === "CRITICAL" || b.current_priority === "HIGH")
    .slice(0, 5);

  return (
    <Card className="shadow-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <HeartPulse className="h-4 w-4 text-destructive" />
          Urgent Cases
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {isError ? (
          <ErrorState onRetry={() => refetch()} />
        ) : isLoading ? (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="flex items-center gap-3 rounded-lg border border-border/40 p-3"
              >
                <div className="flex-1 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-4 w-12 rounded-full" />
                  </div>
                  <Skeleton className="h-3 w-36" />
                </div>
                <Skeleton className="h-6 w-8 rounded" />
              </div>
            ))}
          </div>
        ) : urgent.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border py-8 text-center">
            <ShieldCheck className="h-6 w-6 text-success" />
            <p className="text-sm font-medium text-muted-foreground">
              No critical or high-priority cases right now.
            </p>
          </div>
        ) : (
          urgent.map((b, i) => (
            <motion.div
              key={b.id}
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Link
                href={`/beneficiaries/${b.id}`}
                className="group flex items-center gap-3 rounded-lg border border-border/60 bg-background/40 p-3 transition-colors hover:border-primary/40 hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 focus-visible:ring-offset-background"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-medium">
                      {b.name}
                    </span>
                    <PriorityBadge priority={b.current_priority} showIcon={false} />
                  </div>
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">
                    {b.medical_conditions[0] ??
                      b.state_location ??
                      "Case under review"}
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold tabular-nums text-foreground">
                    {b.urgency?.score ?? "—"}
                  </div>
                  <div className="text-[10px] uppercase text-muted-foreground font-medium">
                    score
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
              </Link>
            </motion.div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
