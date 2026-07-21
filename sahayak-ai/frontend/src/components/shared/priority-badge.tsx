import { AlertTriangle, ArrowDown, Minus, Zap } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { PriorityLevel } from "@/lib/types";

const CONFIG: Record<
  PriorityLevel,
  { variant: "destructive" | "warning" | "default" | "secondary"; icon: typeof Zap; label: string }
> = {
  CRITICAL: { variant: "destructive", icon: AlertTriangle, label: "Critical" },
  HIGH: { variant: "warning", icon: Zap, label: "High" },
  MEDIUM: { variant: "default", icon: Minus, label: "Medium" },
  LOW: { variant: "secondary", icon: ArrowDown, label: "Low" },
};

export function PriorityBadge({
  priority,
  className,
  showIcon = true,
}: {
  priority: PriorityLevel;
  className?: string;
  showIcon?: boolean;
}) {
  const c = CONFIG[priority];
  const Icon = c.icon;
  return (
    <Badge variant={c.variant} className={cn("gap-1", className)}>
      {showIcon && <Icon className="h-3 w-3" />}
      {c.label}
    </Badge>
  );
}

export function priorityDotColor(priority: PriorityLevel): string {
  return {
    CRITICAL: "bg-destructive",
    HIGH: "bg-warning",
    MEDIUM: "bg-primary",
    LOW: "bg-muted-foreground",
  }[priority];
}
