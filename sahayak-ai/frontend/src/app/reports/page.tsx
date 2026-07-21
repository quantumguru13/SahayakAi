"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Download, FileText, Sparkles } from "lucide-react";

import { Topbar } from "@/components/layout/topbar";
import { ImpactMetrics } from "@/components/shared/impact-metrics";
import { Markdown } from "@/components/shared/markdown";
import { UploadHistory } from "@/components/shared/upload-history";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useImpactReport } from "@/lib/hooks";

export default function ReportsPage() {
  const [generated, setGenerated] = useState(false);
  const { data, isLoading, isFetching } = useImpactReport(generated);

  function download() {
    if (!data) return;
    const blob = new Blob([data.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sahayak-impact-report.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <Topbar
        title="Impact Report"
        subtitle="One-click, donor-ready summary of case progress"
      />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {/* Operational statistics — always visible, no generation required. */}
          <ImpactMetrics />

          {!generated ? (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center gap-4 py-16 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/15 text-primary">
                  <FileText className="h-8 w-8" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold">
                    Generate Impact Summary Report
                  </h2>
                  <p className="mt-1 max-w-md text-sm text-muted-foreground">
                    Compile verified case progress, operational metrics and
                    regional coverage into a presentation-ready report for donors
                    and CSR evaluators — instantly.
                  </p>
                </div>
                <Button
                  size="lg"
                  className="gap-2"
                  onClick={() => setGenerated(true)}
                >
                  <Sparkles className="h-4 w-4" />
                  Generate Report
                </Button>
              </CardContent>
            </Card>
          ) : (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <Card>
                <CardHeader className="flex-row items-center justify-between space-y-0">
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <FileText className="h-4 w-4 text-primary" />
                    {data?.title ?? "Impact Summary Report"}
                  </CardTitle>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5"
                    onClick={download}
                    disabled={!data}
                  >
                    <Download className="h-4 w-4" />
                    Download
                  </Button>
                </CardHeader>
                <CardContent>
                  {isLoading || isFetching || !data ? (
                    <div className="space-y-2">
                      {[...Array(8)].map((_, i) => (
                        <Skeleton key={i} className="h-4 w-full" />
                      ))}
                    </div>
                  ) : (
                    <Markdown className="max-w-none">{data.markdown}</Markdown>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Audit trail — session ids, engines, timings, verification outcomes. */}
          <UploadHistory />
        </div>
      </main>
    </>
  );
}
