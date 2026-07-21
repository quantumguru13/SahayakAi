"use client";

import { AlertCircle, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function ErrorState({
  message = "Couldn't reach the server.",
  hint = "Is the backend running on :8000?",
  onRetry,
  className,
}: {
  message?: string;
  hint?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center gap-3 rounded-xl border border-dashed border-destructive/40 bg-destructive/5 py-8 text-center",
        className
      )}
    >
      <AlertCircle className="h-6 w-6 text-destructive" />
      <div>
        <p className="text-sm font-medium text-foreground">{message}</p>
        <p className="text-xs text-muted-foreground">{hint}</p>
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} className="gap-1.5">
          <RefreshCw className="h-3.5 w-3.5" />
          Retry
        </Button>
      )}
    </div>
  );
}
