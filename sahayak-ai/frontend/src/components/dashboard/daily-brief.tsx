"use client";

import { motion } from "framer-motion";
import { RefreshCw, Sparkles } from "lucide-react";

import { ErrorState } from "@/components/shared/error-state";
import { Markdown } from "@/components/shared/markdown";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useBrief } from "@/lib/hooks";

export function DailyBrief() {
  const { data, isLoading, isError, isFetching, refetch } = useBrief();

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <Card className="overflow-hidden">
        <div className="h-1 w-full bg-gradient-to-r from-primary via-primary/50 to-transparent" />
        <CardHeader className="flex-row items-start justify-between space-y-0">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-lg bg-primary/15 text-primary">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <div className="text-sm font-semibold">AI Daily Brief</div>
              {isLoading ? (
                <Skeleton className="mt-1 h-4 w-64" />
              ) : (
                <p className="mt-0.5 text-sm text-muted-foreground">
                  {data?.headline}
                </p>
              )}
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => refetch()}
            aria-label="Regenerate brief"
          >
            <RefreshCw
              className={isFetching ? "animate-spin" : undefined}
            />
          </Button>
        </CardHeader>
        <CardContent>
          {isError ? (
            <ErrorState
              message="Couldn't load the daily brief."
              onRetry={() => refetch()}
            />
          ) : isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-11/12" />
              <Skeleton className="h-4 w-4/5" />
            </div>
          ) : (
            <Markdown>{data?.summary_markdown ?? ""}</Markdown>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
