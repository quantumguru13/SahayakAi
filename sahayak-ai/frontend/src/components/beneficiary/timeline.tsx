"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Check, Circle, Loader2, ListTodo } from "lucide-react";

import { ErrorState } from "@/components/shared/error-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { useBeneficiaryTasks, useUpdateTask } from "@/lib/hooks";
import { useToast } from "@/components/ui/toast";
import { cn, formatDate, relativeDeadline, daysUntil } from "@/lib/utils";
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
        "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border bg-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        done
          ? "border-success bg-success/15 text-success hover:bg-success/20"
          : task.status === "IN_PROGRESS"
            ? "border-primary text-primary hover:bg-primary/10"
            : "border-muted-foreground/40 text-transparent hover:border-primary"
      )}
    >
      {isPending ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
      ) : done ? (
        <Check className="h-3.5 w-3.5" />
      ) : task.status === "IN_PROGRESS" ? (
        <Circle className="h-1.5 w-1.5 fill-current" />
      ) : (
        <Check className="h-3.5 w-3.5 opacity-0 hover:opacity-100 hover:text-muted-foreground/60" />
      )}
    </button>
  );
}

export function Timeline({ beneficiaryId }: { beneficiaryId: string }) {
  const { data: tasks, isLoading, isError, refetch } = useBeneficiaryTasks(
    beneficiaryId
  );

  const total = tasks?.length ?? 0;
  const completed = tasks?.filter((t) => t.status === "COMPLETED").length ?? 0;
  const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <Card className="shadow-sm">
      <CardHeader className="flex flex-col gap-2 space-y-0 pb-4">
        <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle className="text-sm font-semibold">Case Timeline</CardTitle>
          {total > 0 && (
            <span className="text-xs font-semibold tabular-nums text-muted-foreground">
              {completed}/{total} resolved ({percentage}%)
            </span>
          )}
        </div>
        {total > 0 && (
          <div className="mt-0.5">
            <Progress value={percentage} className="h-1.5 transition-all" />
          </div>
        )}
      </CardHeader>
      <CardContent>
        {isError ? (
          <ErrorState onRetry={() => refetch()} />
        ) : isLoading ? (
          <div className="space-y-4">
            {[0, 1, 2].map((i) => (
              <div key={i} className="flex gap-4">
                <Skeleton className="h-6 w-6 rounded-full" />
                <div className="flex-1 space-y-1.5 pt-1">
                  <Skeleton className="h-4 w-1/3" />
                  <Skeleton className="h-3 w-2/3" />
                </div>
              </div>
            ))}
          </div>
        ) : !tasks || tasks.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border py-12 text-center">
            <ListTodo className="h-6 w-6 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No follow-up actions scheduled.
            </p>
          </div>
        ) : (
          <ol className="relative border-l border-border pl-6 ml-3 space-y-5">
            <AnimatePresence initial={false}>
              {tasks.map((t, idx) => {
                const d = daysUntil(t.due_date);
                const overdue = d !== null && d < 0 && t.status !== "COMPLETED";
                return (
                  <motion.li
                    key={t.id}
                    layout
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.25, delay: Math.min(idx * 0.05, 0.3) }}
                    className="relative"
                  >
                    <span className="absolute -left-[37px] top-0 flex h-6 w-6 items-center justify-center rounded-full bg-background">
                      <StatusButton task={t} />
                    </span>
                    <div className="min-w-0 pt-0.5">
                      <p
                        className={cn(
                          "text-sm font-medium leading-snug text-foreground transition-all",
                          t.status === "COMPLETED" &&
                            "text-muted-foreground line-through"
                        )}
                      >
                        {t.title}
                      </p>
                      {t.description && (
                        <p className="mt-1 text-xs text-muted-foreground leading-normal">
                          {t.description}
                        </p>
                      )}
                      {t.due_date && (
                        <span
                          className={cn(
                            "mt-1.5 inline-block text-xs font-medium",
                            overdue
                              ? "text-destructive font-semibold"
                              : "text-muted-foreground"
                          )}
                        >
                          {formatDate(t.due_date)} · {relativeDeadline(t.due_date)}
                        </span>
                      )}
                    </div>
                  </motion.li>
                );
              })}
            </AnimatePresence>
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
