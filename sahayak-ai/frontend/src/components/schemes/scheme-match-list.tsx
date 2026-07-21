"use client";

import { Landmark } from "lucide-react";

import { SchemeMatchCard } from "./scheme-match-card";
import { ErrorState } from "@/components/shared/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { SchemeMatch } from "@/lib/types";

export function SchemeMatchList({
  matches,
  beneficiaryId,
  isLoading,
  isError,
  onRetry,
  compact,
}: {
  matches?: SchemeMatch[];
  beneficiaryId?: string;
  isLoading?: boolean;
  isError?: boolean;
  onRetry?: () => void;
  compact?: boolean;
}) {
  if (isError) {
    return (
      <ErrorState message="Couldn't load scheme matches." onRetry={onRetry} />
    );
  }
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-36 w-full" />
        ))}
      </div>
    );
  }

  if (!matches || matches.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border py-10 text-center">
        <Landmark className="h-6 w-6 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          No matching schemes found for this profile yet.
        </p>
      </div>
    );
  }

  return (
    <div className={compact ? "space-y-3" : "grid gap-3 sm:grid-cols-2"}>
      {matches.map((m, i) => (
        <SchemeMatchCard key={m.scheme.id} match={m} index={i} beneficiaryId={beneficiaryId} />
      ))}
    </div>
  );
}
