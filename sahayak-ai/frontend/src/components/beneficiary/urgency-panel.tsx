"use client";

import { Activity, CalendarClock, ShieldAlert, Sparkles } from "lucide-react";

import { PriorityBadge } from "@/components/shared/priority-badge";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import type { UrgencyAssessment } from "@/lib/types";

export function UrgencyPanel({
  urgency,
  className,
}: {
  urgency: UrgencyAssessment;
  className?: string;
}) {
  // Parse semicolon-separated factors
  const factors = urgency.reasoning
    ? urgency.reasoning.split(";").map((f) => f.trim()).filter(Boolean)
    : [];

  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card p-5 shadow-sm",
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
          <Sparkles className="h-3 w-3 text-primary animate-pulse" />
          Urgency Scoring
        </span>
        <PriorityBadge priority={urgency.priority} />
      </div>

      <div className="mt-4 flex items-baseline gap-2">
        <span className="text-4xl font-extrabold tabular-nums tracking-tight">
          {urgency.score}
        </span>
        <span className="text-xs font-medium text-muted-foreground">/ 100 severity index</span>
      </div>

      <div className="mt-5 space-y-4">
        <Metric
          icon={<Activity className="h-4 w-4 text-destructive" />}
          label="Medical Condition Severity"
          value={urgency.medical_severity}
          bar="bg-destructive"
        />
        <Metric
          icon={<CalendarClock className="h-4 w-4 text-warning" />}
          label="Time-Sensitive Deadlines"
          value={urgency.deadline_pressure}
          bar="bg-warning"
        />
      </div>

      {factors.length > 0 && (
        <div className="mt-5 pt-4 border-t border-border/60">
          <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1 mb-2.5">
            <ShieldAlert className="h-3.5 w-3.5 text-primary" />
            AI Decision Logic Breakdown
          </span>
          <ul className="space-y-2">
            {factors.map((f, i) => {
              const isCritical =
                f.toUpperCase().startsWith("CRITICAL") ||
                f.toUpperCase().includes("CANCER") ||
                f.toUpperCase().includes("RENAL");
              return (
                <li
                  key={i}
                  className={cn(
                    "flex items-start gap-2.5 text-xs rounded-lg p-2.5 border leading-relaxed",
                    isCritical
                      ? "bg-destructive/5 border-destructive/20 text-foreground"
                      : "bg-muted/30 border-border/40 text-muted-foreground"
                  )}
                >
                  <span
                    className={cn(
                      "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                      isCritical ? "bg-destructive animate-ping" : "bg-primary"
                    )}
                  />
                  <span className="flex-1">{f}</span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

function Metric({
  icon,
  label,
  value,
  bar,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  bar: string;
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-xs">
        <span className="flex items-center gap-2 font-medium text-muted-foreground">
          {icon}
          {label}
        </span>
        <span className="tabular-nums font-semibold text-foreground">{value}%</span>
      </div>
      <Progress value={value} indicatorClassName={bar} className="h-1.5" />
    </div>
  );
}
