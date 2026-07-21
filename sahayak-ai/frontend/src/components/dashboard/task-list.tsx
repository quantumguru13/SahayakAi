"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Check, Circle, Loader2 } from "lucide-react";

import { ErrorState } from "@/components/shared/error-state";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useTasks, useUpdateTask } from "@/lib/hooks";
import { useToast } from "@/components/ui/toast";
import { cn, relativeDeadline, daysUntil } from "@/lib/utils";
import type { Task, TaskStatus } from "@/lib/types";

function nextStatus(status: TaskStatus): TaskStatus {
  if (status === "PENDING") return "IN_PROGRESS";
  if (status === "IN_PROGRESS") return "COMPLETED";
  return "PENDING";
}

function StatusButton({ task }: { task: Task }) {
  const { mutate, isPending } = useUpdateTask();
  const { toast } = useToast();
  const done = task.status === "COMPLETED";
  return (
    <button
      onClick={() =>
        mutate(
          { id: task.id, status: nextStatus(task.status) },
          {
            onSuccess: (updated) => {
              toast(
                `Task "${updated.title}" marked as ${updated.status.replace("_", " ")}`,
                "success"
              );
            },
            onError: (err) => {
              toast(`Failed to update task: ${err.message}`, "error");
            },
          }
        )
      }
      disabled={isPending}
      aria-label={`Mark task ${task.title} as ${nextStatus(task.status)}`}
      className={cn(
        "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors",
        done
          ? "border-success bg-success text-success-foreground"
          : task.status === "IN_PROGRESS"
            ? "border-primary text-primary"
            : "border-muted-foreground/40 text-transparent hover:border-primary"
      )}
    >
      {isPending ? (
        <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
      ) : done ? (
        <Check className="h-3 w-3" />
      ) : task.status === "IN_PROGRESS" ? (
        <Circle className="h-2 w-2 fill-current" />
      ) : (
        <Check className="h-3 w-3" />
      )}
    </button>
  );
}

export function TaskList() {
  const { data: tasks, isLoading, isError, refetch } = useTasks();
  const active = (tasks ?? []).filter((t) => t.status !== "COMPLETED");
  const completed = (tasks ?? []).filter((t) => t.status === "COMPLETED");
  const ordered = [...active, ...completed];

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm">Operational Checklist</CardTitle>
        {tasks && (
          <Badge variant="outline">
            {active.length} open
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-1">
        {isError ? (
          <ErrorState onRetry={() => refetch()} />
        ) : isLoading ? (
          <div className="space-y-4 py-2">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-3">
                <Skeleton className="h-5 w-5 rounded-full" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="h-4 w-2/3" />
                  <Skeleton className="h-3 w-1/4" />
                </div>
              </div>
            ))}
          </div>
        ) : ordered.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border py-12 text-center">
            <Check className="h-8 w-8 text-success" />
            <p className="text-sm font-semibold text-foreground">All Tasks Resolved</p>
            <p className="text-xs text-muted-foreground">
              NGO workers have completed all critical follow-up actions.
            </p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {ordered.map((task) => {
              const d = daysUntil(task.due_date);
              const overdue =
                d !== null && d < 0 && task.status !== "COMPLETED";
              const soon = d !== null && d >= 0 && d <= 3;
              return (
                <motion.div
                  key={task.id}
                  layout
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.25 }}
                  className="flex items-start gap-3 rounded-lg px-2 py-2.5 hover:bg-accent/50"
                >
                  <div className="pt-0.5">
                    <StatusButton task={task} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p
                      className={cn(
                        "text-sm font-medium leading-snug",
                        task.status === "COMPLETED" &&
                          "text-muted-foreground line-through"
                      )}
                    >
                      {task.title}
                    </p>
                    {task.due_date && task.status !== "COMPLETED" && (
                      <span
                        className={cn(
                          "mt-0.5 inline-block text-xs font-semibold",
                          overdue
                            ? "text-destructive"
                            : soon
                              ? "text-warning"
                              : "text-muted-foreground"
                        )}
                      >
                        {relativeDeadline(task.due_date)}
                      </span>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </CardContent>
    </Card>
  );
}
