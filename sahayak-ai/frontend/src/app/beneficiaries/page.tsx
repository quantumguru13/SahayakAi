"use client";

import Link from "next/link";
import { useState } from "react";
import { motion } from "framer-motion";
import { ChevronRight, Search, Upload, Users } from "lucide-react";

import { Topbar } from "@/components/layout/topbar";
import { ErrorState } from "@/components/shared/error-state";
import { PriorityBadge } from "@/components/shared/priority-badge";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useBeneficiaries } from "@/lib/hooks";
import { cn, formatINR } from "@/lib/utils";
import type { PriorityLevel } from "@/lib/types";

const FILTERS: (PriorityLevel | "ALL")[] = [
  "ALL",
  "CRITICAL",
  "HIGH",
  "MEDIUM",
  "LOW",
];

export default function BeneficiariesPage() {
  const { data, isLoading, isError, refetch } = useBeneficiaries();
  const [filter, setFilter] = useState<PriorityLevel | "ALL">("ALL");
  const [query, setQuery] = useState("");

  const rows = (data ?? []).filter((b) => {
    const matchesFilter = filter === "ALL" || b.current_priority === filter;
    const matchesQuery =
      !query ||
      b.name.toLowerCase().includes(query.toLowerCase()) ||
      (b.state_location ?? "").toLowerCase().includes(query.toLowerCase());
    return matchesFilter && matchesQuery;
  });

  return (
    <>
      <Topbar
        title="Beneficiaries"
        subtitle="All active cases, auto-prioritized by the urgency matrix"
      />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap gap-1.5">
            {FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={cn(
                  "rounded-full px-3 py-1 text-xs font-medium transition-colors",
                  filter === f
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted/60 text-muted-foreground hover:bg-muted"
                )}
              >
                {f === "ALL" ? "All" : f.charAt(0) + f.slice(1).toLowerCase()}
              </button>
            ))}
          </div>
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search name or state..."
              className="h-9 w-full rounded-md border border-input bg-background pl-8 pr-3 text-sm outline-none focus:border-primary sm:w-64"
            />
          </div>
        </div>

        <Card className="divide-y divide-border overflow-hidden">
          <div className="hidden grid-cols-12 gap-4 px-5 py-2.5 text-xs font-medium uppercase tracking-wide text-muted-foreground md:grid">
            <div className="col-span-4">Beneficiary</div>
            <div className="col-span-2">Priority</div>
            <div className="col-span-2">Income</div>
            <div className="col-span-3">Flags</div>
            <div className="col-span-1 text-right">Score</div>
          </div>

          {isError ? (
            <div className="px-5 py-8">
              <ErrorState onRetry={() => refetch()} />
            </div>
          ) : isLoading ? (
            [0, 1, 2, 3, 4].map((i) => (
              <div key={i} className="flex items-center gap-4 px-5 py-4">
                <Skeleton className="h-9 w-9 rounded-full shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="h-4 w-1/3" />
                  <Skeleton className="h-3 w-1/4" />
                </div>
                <div className="hidden md:flex gap-1.5">
                  <Skeleton className="h-5 w-16 rounded-full" />
                  <Skeleton className="h-5 w-20" />
                </div>
                <Skeleton className="h-4 w-12" />
                <Skeleton className="h-4 w-8 text-right ml-auto" />
              </div>
            ))
          ) : rows.length === 0 ? (
            (data ?? []).length === 0 ? (
              <div className="flex flex-col items-center gap-3 px-5 py-16 text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <Users className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-sm font-medium">No beneficiaries yet</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Upload a document in Live mode and the extracted case will appear here.
                  </p>
                </div>
                <Link
                  href="/intake"
                  className={buttonVariants({ size: "sm", className: "gap-1.5" })}
                >
                  <Upload className="h-4 w-4" />
                  New intake
                </Link>
              </div>
            ) : (
              <div className="px-5 py-12 text-center text-sm text-muted-foreground">
                No beneficiaries match your filters.
              </div>
            )
          ) : (
            rows.map((b, i) => (
              <motion.div
                key={b.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(i * 0.03, 0.3) }}
              >
                <Link
                  href={`/beneficiaries/${b.id}`}
                  className="group grid grid-cols-12 items-center gap-4 px-5 py-3.5 transition-colors hover:bg-accent/40"
                >
                  <div className="col-span-12 md:col-span-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-medium text-primary">
                        {b.name.charAt(0)}
                      </div>
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">
                          {b.name}
                        </div>
                        <div className="truncate text-xs text-muted-foreground">
                          {[b.age ? `${b.age}y` : null, b.gender, b.state_location]
                            .filter(Boolean)
                            .join(" · ")}
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="col-span-6 md:col-span-2">
                    <PriorityBadge priority={b.current_priority} />
                  </div>
                  <div className="col-span-6 text-sm text-muted-foreground md:col-span-2">
                    {formatINR(b.annual_income)}
                  </div>
                  <div className="col-span-10 flex flex-wrap gap-1 md:col-span-3">
                    {b.is_disabled && (
                      <Badge variant="outline" className="text-[10px]">
                        Disability
                      </Badge>
                    )}
                    {b.medical_conditions.slice(0, 1).map((c) => (
                      <Badge
                        key={c}
                        variant="destructive"
                        className="max-w-[160px] truncate text-[10px]"
                      >
                        {c}
                      </Badge>
                    ))}
                    {b.medical_conditions.length > 1 && (
                      <Badge variant="secondary" className="text-[10px]">
                        +{b.medical_conditions.length - 1}
                      </Badge>
                    )}
                  </div>
                  <div className="col-span-2 flex items-center justify-end gap-2 md:col-span-1">
                    <span className="text-sm font-semibold tabular-nums">
                      {b.urgency?.score ?? "—"}
                    </span>
                    <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                  </div>
                </Link>
              </motion.div>
            ))
          )}
        </Card>
      </main>
    </>
  );
}
