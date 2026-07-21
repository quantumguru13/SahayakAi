"use client";

import { motion } from "framer-motion";
import { History } from "lucide-react";

import { ErrorState } from "@/components/shared/error-state";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useUploadHistory } from "@/lib/hooks";
import { cn } from "@/lib/utils";

function statusVariant(status: string) {
  if (status === "SUCCESS") return "success" as const;
  if (status === "REJECTED") return "destructive" as const;
  return "warning" as const;
}

/** Audit trail of every upload attempt — session id, engine, timing, outcome. */
export function UploadHistory() {
  const { data, isLoading, isError, refetch } = useUploadHistory();

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="flex items-center gap-2 text-sm">
          <History className="h-4 w-4 text-primary" />
          Upload History
        </CardTitle>
        {data && data.length > 0 && (
          <Badge variant="outline">{data.length} logged</Badge>
        )}
      </CardHeader>
      <CardContent>
        {isError ? (
          <ErrorState
            message="Couldn't load upload history."
            onRetry={() => refetch()}
          />
        ) : isLoading ? (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : !data || data.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border py-10 text-center">
            <History className="h-6 w-6 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No uploads recorded yet this session.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-xs">
              <thead>
                <tr className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  <th className="pb-2 pr-3 font-medium">Session</th>
                  <th className="pb-2 pr-3 font-medium">Time</th>
                  <th className="pb-2 pr-3 font-medium">Document</th>
                  <th className="pb-2 pr-3 font-medium">Mode</th>
                  <th className="pb-2 pr-3 font-medium">Engine</th>
                  <th className="pb-2 pr-3 font-medium">Duration</th>
                  <th className="pb-2 pr-3 font-medium">Role</th>
                  <th className="pb-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {data.map((h, i) => (
                  <motion.tr
                    key={h.session_id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: Math.min(i * 0.02, 0.2) }}
                  >
                    <td className="py-2 pr-3 font-mono text-[10px] text-muted-foreground">
                      {h.session_id}
                    </td>
                    <td className="py-2 pr-3 text-muted-foreground">
                      {new Date(h.created_at).toLocaleTimeString("en-IN", {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </td>
                    <td className="max-w-[160px] truncate py-2 pr-3">
                      <span className="font-medium">{h.file_name}</span>
                      {h.document_type === "aadhaar" && (
                        <Badge
                          variant="secondary"
                          className="ml-1.5 text-[9px] px-1 py-0"
                        >
                          Aadhaar
                        </Badge>
                      )}
                    </td>
                    <td className="py-2 pr-3">
                      <span
                        className={cn(
                          "font-medium",
                          h.mode === "LIVE" ? "text-success" : "text-warning"
                        )}
                      >
                        {h.mode}
                      </span>
                    </td>
                    <td className="py-2 pr-3 text-muted-foreground">
                      {h.ocr_engine}
                    </td>
                    <td className="py-2 pr-3 tabular-nums text-muted-foreground">
                      {h.processing_ms} ms
                    </td>
                    <td className="py-2 pr-3 text-muted-foreground">
                      {h.user_role}
                    </td>
                    <td className="py-2">
                      <Badge
                        variant={statusVariant(h.status)}
                        className="text-[9px] px-1.5 py-0"
                      >
                        {h.verification_status ?? h.status}
                      </Badge>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
