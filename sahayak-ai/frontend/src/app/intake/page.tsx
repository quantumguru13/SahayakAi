"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowRight,
  Braces,
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  Cpu,
  FileScan,
  Fingerprint,
  FlaskConical,
  Gauge,
  Image as ImageIcon,
  Loader2,
  RefreshCw,
  ScanLine,
  Sparkles,
  Stethoscope,
  User,
} from "lucide-react";

import { Topbar } from "@/components/layout/topbar";
import { AadhaarPanel } from "@/components/intake/aadhaar-panel";
import { BeneficiarySummary } from "@/components/intake/beneficiary-summary";
import { ProcessingTimeline } from "@/components/intake/processing-timeline";
import { PrivacyPanel } from "@/components/shared/privacy-panel";
import { UrgencyPanel } from "@/components/beneficiary/urgency-panel";
import { SchemeMatchList } from "@/components/schemes/scheme-match-list";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { DocumentUploader } from "@/components/intake/document-uploader";
import { useHealth, useSetMode, useUploadDocument } from "@/lib/hooks";
import { rememberMode } from "@/lib/session";
import { formatINR, formatDate, relativeDeadline, cn } from "@/lib/utils";
import {
  isOcrUnavailable,
  type DocumentUploadResponse,
  type PipelineMode,
} from "@/lib/types";

export default function IntakePage() {
  const [fileName, setFileName] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [lastFile, setLastFile] = useState<File | null>(null);
  const [mode, setMode] = useState<PipelineMode>("LIVE");

  const { data: health } = useHealth();
  const { mutate, data, isPending, reset, error } = useUploadDocument();
  const setModeMutation = useSetMode();

  // Sync the toggle to the dashboard's currently-active scope on load (LIVE if
  // real OCR is available, else DEMO) — but only before the user has run anything.
  useEffect(() => {
    const initial = health?.active_mode ?? health?.default_mode;
    if (initial && !data && !isPending) {
      setMode(initial);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [health?.active_mode, health?.default_mode]);

  // The backend may downgrade a LIVE request to DEMO when no OCR engine is
  // available. Follow whatever it actually ran so the transcript is never
  // labelled "OCR" while showing sample text.
  useEffect(() => {
    if (data && !isOcrUnavailable(data) && data.mode !== mode) {
      setMode(data.mode);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  // Changing the toggle re-scopes the whole dashboard on the backend too, so the
  // Dashboard/Beneficiaries pages immediately reflect LIVE vs DEMO data.
  function changeMode(m: PipelineMode) {
    setMode(m);
    setModeMutation.mutate(m);
  }

  function run(file: File, useMode: PipelineMode, allowDuplicate = false) {
    setFileName(file.name);
    if (file.type.startsWith("image/")) {
      setPreview(URL.createObjectURL(file));
    } else {
      setPreview(null);
    }
    setLastFile(file);
    // Keep the toggle honest about what actually ran, so the badges, the
    // "Sample Transcript" label and the amber Demo notice all stay accurate.
    if (useMode !== mode) setMode(useMode);
    mutate({ file, mode: useMode, allowDuplicate });
  }

  /** `forceMode` is set by the sample-document buttons, which are synthetic files
   *  that real OCR cannot read — they always run DEMO so a click never dead-ends. */
  function handleFile(file: File, forceMode?: PipelineMode) {
    run(file, forceMode ?? mode);
  }

  function handleReset() {
    setFileName(null);
    setPreview(null);
    setLastFile(null);
    reset();
  }

  const showResults = isPending || !!data;
  const fallback = data && isOcrUnavailable(data) ? data : null;
  const result: DocumentUploadResponse | null =
    data && !isOcrUnavailable(data) ? data : null;

  return (
    <>
      <Topbar
        title="Beneficiary Intake"
        subtitle="Upload a document — AI extracts, prioritizes & matches in real time"
      />
      <main className="flex-1 overflow-y-auto p-6">
        {/* -------- Mode switch (LIVE AI / DEMO) -------- */}
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <ModeSwitch
            mode={mode}
            onChange={changeMode}
            liveAvailable={health?.live_ocr_available ?? true}
            engines={health?.ocr_engines ?? []}
            disabled={isPending}
          />
          {mode === "DEMO" && (
            <div className="flex items-center gap-2 rounded-lg border border-warning/40 bg-warning/10 px-3 py-2 text-xs text-warning">
              <span className="text-sm">🟡</span>
              <span>
                <strong>Demo Mode</strong> — showing sample beneficiary data. No OCR
                is executed; results are simulated for demonstration.
              </span>
            </div>
          )}
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* ---------------- LEFT: upload + document scan ---------------- */}
          <div className="space-y-4">
            {!showResults ? (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Upload Document</CardTitle>
                </CardHeader>
                <CardContent>
                  <DocumentUploader
                    onFile={handleFile}
                    disabled={isPending}
                    mode={mode}
                  />
                </CardContent>
              </Card>
            ) : (
              <Card className="overflow-hidden">
                <CardHeader className="flex-row items-center justify-between space-y-0">
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <ScanLine className="h-4 w-4 text-primary" />
                    {fileName ?? "Document"}
                  </CardTitle>
                  <Button variant="ghost" size="sm" onClick={handleReset}>
                    New upload
                  </Button>
                </CardHeader>
                <CardContent>
                  <div className="relative overflow-hidden rounded-lg border border-border bg-muted/30">
                    {preview ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={preview}
                        alt="Uploaded document preview"
                        className="max-h-64 w-full object-contain"
                        onError={() => setPreview(null)}
                      />
                    ) : (
                      <div className="flex h-40 items-center justify-center text-muted-foreground">
                        <Fingerprint className="mr-2 h-5 w-5" /> Document received
                      </div>
                    )}
                    {isPending && (
                      <motion.div
                        className="absolute inset-x-0 top-0 h-16 bg-gradient-to-b from-primary/40 to-transparent"
                        initial={{ y: 0 }}
                        animate={{ y: 240 }}
                        transition={{
                          repeat: Infinity,
                          duration: 1.2,
                          ease: "linear",
                        }}
                      />
                    )}
                  </div>

                  <div className="mt-4">
                    <div className="mb-1.5 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      <ScanLine className="h-3.5 w-3.5" />
                      {mode === "DEMO" ? "Sample Transcript" : "OCR Transcript"}
                    </div>
                    {isPending ? (
                      <div className="space-y-1.5">
                        {[0, 1, 2, 3, 4].map((i) => (
                          <Skeleton key={i} className="h-3 w-full" />
                        ))}
                      </div>
                    ) : result ? (
                      <pre className="max-h-56 overflow-auto whitespace-pre-wrap rounded-lg bg-muted/40 p-3 text-xs leading-relaxed text-muted-foreground">
                        {result.extracted_text}
                      </pre>
                    ) : null}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Debug panel lives under the scan card (LIVE mode) */}
            {result?.debug && <DebugPanel result={result} />}
          </div>

          {/* ---------------- RIGHT: extraction results ---------------- */}
          <div className="space-y-4">
            {!showResults ? (
              <EmptyState />
            ) : fallback ? (
              <FallbackCard
                message={fallback.message}
                engines={fallback.engines_attempted}
                onRetry={() => lastFile && run(lastFile, "LIVE")}
                onSwitchDemo={() => {
                  // Explicit, user-initiated switch — never automatic. Persist it
                  // so the rest of the session stays in the mode they chose.
                  rememberMode("DEMO");
                  changeMode("DEMO");
                  if (lastFile) run(lastFile, "DEMO");
                }}
              />
            ) : (
              <>
                {(isPending || result) && (
                  <PipelineStatusBar
                    isPending={isPending}
                    result={result}
                    mode={mode}
                  />
                )}

                {/* Live pipeline trace — replaces a bare spinner so the judge
                    can see exactly which stage the document is in. */}
                {(isPending || result) && (
                  <ProcessingTimeline isPending={isPending} result={result} />
                )}

                {!isPending && result?.debug && <LowConfidenceNote result={result} />}

                {/* Outcome first, evidence second. */}
                {!isPending && result && <BeneficiarySummary result={result} />}

                <Card>
                  <CardHeader className="flex-row items-center justify-between space-y-0">
                    <CardTitle className="text-sm">Extracted Profile</CardTitle>
                    {isPending ? (
                      <Badge variant="warning" className="gap-1.5">
                        <Loader2 className="h-3 w-3 animate-spin" /> Processing
                      </Badge>
                    ) : (
                      result && (
                        <Badge variant="success" className="gap-1.5">
                          <Gauge className="h-3 w-3" />
                          {result.processing_ms} ms
                        </Badge>
                      )
                    )}
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {isPending ? (
                      <ExtractionSkeleton />
                    ) : result ? (
                      <ExtractionFields data={result} />
                    ) : null}
                    {error && (
                      <UploadError
                        message={(error as Error).message}
                        onProcessAnyway={() =>
                          lastFile && run(lastFile, mode, true)
                        }
                      />
                    )}
                  </CardContent>
                </Card>

                {!isPending && result?.aadhaar && (
                  <AadhaarPanel analysis={result.aadhaar} />
                )}

                {!isPending && result?.urgency && (
                  <UrgencyPanel urgency={result.urgency} />
                )}

                {!isPending && result && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.15 }}
                  >
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-sm">
                          Matched Welfare Schemes
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <SchemeMatchList matches={result.scheme_matches} compact />
                      </CardContent>
                    </Card>
                  </motion.div>
                )}

                {!isPending && result?.aadhaar && <PrivacyPanel />}

                {!isPending && result && (
                  <Link
                    href={`/beneficiaries/${result.beneficiary.id}`}
                    className={buttonVariants({ className: "w-full gap-2" })}
                  >
                    Open full case file
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                )}
              </>
            )}
          </div>
        </div>
      </main>
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Mode switch                                                         */
/* ------------------------------------------------------------------ */
function ModeSwitch({
  mode,
  onChange,
  liveAvailable,
  engines,
  disabled,
}: {
  mode: PipelineMode;
  onChange: (m: PipelineMode) => void;
  liveAvailable: boolean;
  engines: string[];
  disabled?: boolean;
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="inline-flex rounded-lg border border-border bg-muted/40 p-1">
        <button
          onClick={() => onChange("LIVE")}
          disabled={disabled}
          className={cn(
            "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50",
            mode === "LIVE"
              ? "bg-primary text-primary-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          )}
          title="Real OCR + AI extraction on the uploaded document"
        >
          <Sparkles className="h-3.5 w-3.5" /> LIVE AI
        </button>
        <button
          onClick={() => onChange("DEMO")}
          disabled={disabled}
          className={cn(
            "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50",
            mode === "DEMO"
              ? "bg-warning text-warning-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          )}
          title="Offline sample data — no OCR, no API"
        >
          <FlaskConical className="h-3.5 w-3.5" /> DEMO
        </button>
      </div>
      <span className="text-xs text-muted-foreground">
        {mode === "LIVE" ? (
          liveAvailable ? (
            <>
              Real OCR ·{" "}
              <span className="font-medium text-foreground">
                {engines.length ? engines.join(" → ") : "engine ready"}
              </span>
            </>
          ) : (
            <span className="text-warning">
              No OCR engine detected — install Tesseract/EasyOCR or add an API key
            </span>
          )
        ) : (
          "Sample data · offline capable"
        )}
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Pipeline status bar — confidence, timing, statuses                 */
/* ------------------------------------------------------------------ */
function PipelineStatusBar({
  isPending,
  result,
  mode,
}: {
  isPending: boolean;
  result: DocumentUploadResponse | null;
  mode: PipelineMode;
}) {
  const d = result?.debug;
  const effectiveMode = d?.mode ?? mode;
  return (
    <Card>
      <CardContent className="flex flex-wrap items-center gap-2 py-3">
        <Badge
          variant={effectiveMode === "DEMO" ? "warning" : "success"}
          className="gap-1.5"
        >
          {effectiveMode === "DEMO" ? (
            <>🟡 Demo</>
          ) : (
            <>
              <Sparkles className="h-3 w-3" /> Live AI
            </>
          )}
        </Badge>
        <ConfChip
          icon={FileScan}
          label="OCR"
          value={isPending ? null : d?.ocr_confidence}
          sub={d?.ocr_engine}
        />
        <ConfChip
          icon={Braces}
          label="Extraction"
          value={isPending ? null : d?.extraction_confidence}
        />
        <StatusChip
          icon={Cpu}
          label="AI"
          value={isPending ? "running…" : d?.ai_status ?? "—"}
          ok={d?.ai_status === "ok" || d?.ai_status === "sample"}
        />
        <StatusChip
          icon={CheckCircle2}
          label="Schemes"
          value={isPending ? "…" : d?.scheme_matching_status ?? "—"}
          ok={d?.scheme_matching_status === "ok"}
        />
        {!isPending && result && (
          <Badge variant="secondary" className="gap-1.5">
            <Gauge className="h-3 w-3" />
            {result.processing_ms} ms
          </Badge>
        )}
      </CardContent>
    </Card>
  );
}

function ConfChip({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: typeof FileScan;
  label: string;
  value: number | null | undefined;
  sub?: string;
}) {
  const pct = value == null ? null : Math.round(value * 100);
  const tone =
    pct == null
      ? "text-muted-foreground"
      : pct >= 75
      ? "text-success"
      : pct >= 50
      ? "text-warning"
      : "text-destructive";
  return (
    <div className="flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs">
      <Icon className="h-3.5 w-3.5 text-muted-foreground" />
      <span className="text-muted-foreground">{label}</span>
      <span className={cn("font-semibold", tone)}>
        {pct == null ? "…" : `${pct}%`}
      </span>
      {sub && <span className="text-[10px] text-muted-foreground">· {sub}</span>}
    </div>
  );
}

function StatusChip({
  icon: Icon,
  label,
  value,
  ok,
}: {
  icon: typeof Cpu;
  label: string;
  value: string;
  ok?: boolean;
}) {
  return (
    <div className="flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs">
      <Icon className="h-3.5 w-3.5 text-muted-foreground" />
      <span className="text-muted-foreground">{label}</span>
      <span className={cn("font-medium", ok ? "text-success" : "text-foreground")}>
        {value}
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Low-confidence advisory — never fabricate, flag for manual review  */
/* ------------------------------------------------------------------ */
const LOW_OCR = 0.5;
const LOW_EXTRACT = 0.4;

function LowConfidenceNote({ result }: { result: DocumentUploadResponse }) {
  const d = result.debug!;
  if (d.mode === "DEMO") return null; // sample data is always "confident"
  const lowOcr = d.ocr_confidence < LOW_OCR;
  const lowExtract = d.extraction_confidence < LOW_EXTRACT;
  if (!lowOcr && !lowExtract) return null;

  const parts: string[] = [];
  if (lowOcr) parts.push(`OCR ${Math.round(d.ocr_confidence * 100)}%`);
  if (lowExtract) parts.push(`extraction ${Math.round(d.extraction_confidence * 100)}%`);

  return (
    <div className="flex items-start gap-2 rounded-lg border border-warning/40 bg-warning/10 px-3 py-2 text-xs text-warning">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>
        <strong>Low confidence</strong> ({parts.join(", ")}). Some fields may be
        incomplete — blank fields are shown as “Not found” rather than guessed.
        Please verify against the original document before acting.
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Debug panel — verify the AI pipeline end to end                    */
/* ------------------------------------------------------------------ */
function DebugPanel({ result }: { result: DocumentUploadResponse }) {
  const [open, setOpen] = useState(false);
  const d = result.debug!;
  return (
    <Card>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-6 py-3 text-left"
      >
        <span className="flex items-center gap-2 text-sm font-medium">
          <FileScan className="h-4 w-4 text-primary" />
          Pipeline Debug Panel
          <Badge variant="secondary" className="text-[10px]">
            {d.ocr_engine}
          </Badge>
        </span>
        <ChevronDown
          className={cn(
            "h-4 w-4 text-muted-foreground transition-transform",
            open && "rotate-180"
          )}
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <CardContent className="space-y-4 border-t border-border pt-4">
              {(d.original_image || d.preprocessed_image) && (
                <div className="grid grid-cols-2 gap-3">
                  <DebugImage
                    label="1 · Original"
                    src={d.original_image}
                    icon={ImageIcon}
                  />
                  <DebugImage
                    label="2 · Preprocessed"
                    src={d.preprocessed_image}
                    icon={ScanLine}
                  />
                </div>
              )}

              <DebugBlock label="3 · Raw OCR text">
                <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded-lg bg-muted/40 p-3 text-[11px] leading-relaxed text-muted-foreground">
                  {result.extracted_text || "(empty)"}
                </pre>
              </DebugBlock>

              <DebugBlock label="4 · Structured JSON">
                <pre className="max-h-56 overflow-auto rounded-lg bg-muted/40 p-3 text-[11px] leading-relaxed text-muted-foreground">
                  {JSON.stringify(result.extraction, null, 2)}
                </pre>
              </DebugBlock>

              {d.notes.length > 0 && (
                <DebugBlock label="Pipeline notes">
                  <ul className="space-y-1 text-[11px] text-muted-foreground">
                    {d.notes.map((n, i) => (
                      <li key={i} className="flex gap-1.5">
                        <span className="text-primary">›</span> {n}
                      </li>
                    ))}
                  </ul>
                </DebugBlock>
              )}

              <p className="text-[11px] text-muted-foreground">
                5 · Final dashboard →{" "}
                <Link
                  href={`/beneficiaries/${result.beneficiary.id}`}
                  className="text-primary underline-offset-2 hover:underline"
                >
                  {result.beneficiary.name}
                </Link>{" "}
                · engines attempted: {d.engines_attempted.join(", ") || "—"}
              </p>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

function DebugImage({
  label,
  src,
  icon: Icon,
}: {
  label: string;
  src: string | null;
  icon: typeof ImageIcon;
}) {
  return (
    <div>
      <div className="mb-1 flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
        <Icon className="h-3 w-3" /> {label}
      </div>
      <div className="flex h-40 items-center justify-center overflow-hidden rounded-lg border border-border bg-muted/30">
        {src ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={src} alt={label} className="max-h-40 w-full object-contain" />
        ) : (
          <span className="text-[11px] text-muted-foreground">not available</span>
        )}
      </div>
    </div>
  );
}

function DebugBlock({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      {children}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Upload errors — validation failures get actionable guidance         */
/* ------------------------------------------------------------------ */
function UploadError({
  message,
  onProcessAnyway,
}: {
  message: string;
  onProcessAnyway: () => void;
}) {
  // The API client prefixes failures with "API <status>: <body>".
  const isDuplicate = message.includes("409");
  const detail = (() => {
    const m = message.match(/API \d+: (.*)/s);
    if (!m) return message;
    try {
      return JSON.parse(m[1]).detail ?? m[1];
    } catch {
      return m[1];
    }
  })();

  return (
    <div
      role="alert"
      className={cn(
        "rounded-lg border px-3 py-2.5 text-xs",
        isDuplicate
          ? "border-warning/40 bg-warning/10 text-warning"
          : "border-destructive/40 bg-destructive/10 text-destructive"
      )}
    >
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
        <span className="leading-relaxed">{detail}</span>
      </div>
      {isDuplicate && (
        <Button
          variant="outline"
          size="sm"
          onClick={onProcessAnyway}
          className="mt-2.5 gap-1.5"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Process anyway
        </Button>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Automatic fallback card                                            */
/* ------------------------------------------------------------------ */
function FallbackCard({
  message,
  engines,
  onRetry,
  onSwitchDemo,
}: {
  message: string;
  engines: string[];
  onRetry: () => void;
  onSwitchDemo: () => void;
}) {
  return (
    <Card className="border-warning/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm text-warning">
          <AlertTriangle className="h-4 w-4" /> OCR unavailable
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* The backend sends multi-line install instructions — preserve the breaks. */}
        <p className="whitespace-pre-line text-sm leading-relaxed text-muted-foreground">
          {message}
        </p>
        {engines.length > 0 && (
          <p className="text-xs text-muted-foreground">
            Engines attempted: {engines.join(", ")}
          </p>
        )}
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button onClick={onRetry} className="gap-2">
            <RefreshCw className="h-4 w-4" /> Retry OCR
          </Button>
          <Button variant="outline" onClick={onSwitchDemo} className="gap-2">
            <FlaskConical className="h-4 w-4" /> Switch to Demo
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Existing pieces (unchanged behavior)                               */
/* ------------------------------------------------------------------ */
function EmptyState() {
  const fields = [
    { icon: User, label: "Beneficiary name" },
    { icon: Fingerprint, label: "Government ID" },
    { icon: Stethoscope, label: "Medical conditions" },
    { icon: CalendarClock, label: "Critical deadlines" },
  ];
  return (
    <Card className="border-dashed">
      <CardHeader>
        <CardTitle className="text-sm text-muted-foreground">
          Extraction results will appear here
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {fields.map((f) => {
          const Icon = f.icon;
          return (
            <div
              key={f.label}
              className="flex items-center gap-3 rounded-lg border border-dashed border-border/60 px-3 py-3 text-sm text-muted-foreground"
            >
              <Icon className="h-4 w-4" />
              {f.label}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

function ExtractionSkeleton() {
  return (
    <div className="space-y-3">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton className="h-8 w-8 rounded-lg" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-4 w-40" />
          </div>
        </div>
      ))}
    </div>
  );
}

function ExtractionFields({ data }: { data: DocumentUploadResponse }) {
  const e = data.extraction;
  const rows = [
    { icon: User, label: "Beneficiary name", value: e.beneficiary_name ?? "—" },
    {
      icon: Fingerprint,
      label: "Government ID",
      value: e.government_id_type
        ? `${e.government_id_type} · ${data.beneficiary.government_id_number_masked ?? "••••"}`
        : "Not found",
    },
    {
      icon: Gauge,
      label: "Estimated household income",
      value: formatINR(e.estimated_household_income),
    },
  ];
  if (e.dob) rows.push({ icon: CalendarClock, label: "Date of birth", value: e.dob });
  if (e.gender)
    rows.push({ icon: User, label: "Gender", value: e.gender });
  if (e.address)
    rows.push({ icon: ImageIcon, label: "Address", value: e.address });

  return (
    <motion.div
      initial="hidden"
      animate="show"
      variants={{
        hidden: {},
        show: { transition: { staggerChildren: 0.07 } },
      }}
      className="space-y-3"
    >
      {rows.map((r) => {
        const Icon = r.icon;
        return (
          <motion.div
            key={r.label}
            variants={{
              hidden: { opacity: 0, x: 12 },
              show: { opacity: 1, x: 0 },
            }}
            className="flex items-center gap-3"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Icon className="h-4 w-4" />
            </div>
            <div>
              <div className="text-xs text-muted-foreground">{r.label}</div>
              <div className="text-sm font-medium">{r.value}</div>
            </div>
          </motion.div>
        );
      })}

      <motion.div
        variants={{ hidden: { opacity: 0, x: 12 }, show: { opacity: 1, x: 0 } }}
        className="flex items-start gap-3"
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-destructive/10 text-destructive">
          <Stethoscope className="h-4 w-4" />
        </div>
        <div className="flex-1">
          <div className="text-xs text-muted-foreground">Medical conditions</div>
          {e.detected_medical_conditions.length === 0 ? (
            <div className="text-sm">None detected</div>
          ) : (
            <div className="mt-1 flex flex-wrap gap-1">
              {e.detected_medical_conditions.map((c) => (
                <Badge key={c} variant="destructive" className="text-[10px]">
                  {c}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </motion.div>

      {e.critical_deadlines.length > 0 && (
        <motion.div
          variants={{ hidden: { opacity: 0, x: 12 }, show: { opacity: 1, x: 0 } }}
          className="flex items-start gap-3"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-warning/10 text-warning">
            <CalendarClock className="h-4 w-4" />
          </div>
          <div className="flex-1">
            <div className="text-xs text-muted-foreground">Critical deadlines</div>
            <div className="mt-1 space-y-1">
              {e.critical_deadlines.map((d) => (
                <div key={d.date + d.context} className="text-sm">
                  <span className="font-medium">{d.context}</span>
                  <span className="ml-2 text-xs text-warning">
                    {formatDate(d.date)} · {relativeDeadline(d.date)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {data.generated_tasks.length > 0 && (
        <motion.div
          variants={{ hidden: { opacity: 0 }, show: { opacity: 1 } }}
          className="rounded-lg bg-muted/40 p-3"
        >
          <div className="mb-1.5 text-xs font-medium text-muted-foreground">
            Auto-generated follow-up tasks
          </div>
          <ul className="space-y-1">
            {data.generated_tasks.map((t) => (
              <li
                key={t.id}
                className="flex items-center gap-2 text-xs text-muted-foreground"
              >
                <CheckCircle2 className="h-3 w-3 text-success" />
                {t.title}
              </li>
            ))}
          </ul>
        </motion.div>
      )}
    </motion.div>
  );
}
