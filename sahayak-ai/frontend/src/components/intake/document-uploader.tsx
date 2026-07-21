"use client";

import { useCallback, useRef, useState } from "react";
import { FileText, ImageIcon, UploadCloud } from "lucide-react";

import { cn } from "@/lib/utils";
import type { PipelineMode } from "@/lib/types";

const SAMPLES = [
  { label: "Medical report", file: "medical_report.png", icon: FileText },
  { label: "Aadhaar (scholarship)", file: "aadhaar_scholarship.png", icon: ImageIcon },
  { label: "Disability pension", file: "disability_pension.png", icon: FileText },
  { label: "Dialysis (urgent)", file: "dialysis_kidney.png", icon: FileText },
];

/** Build a lightweight in-memory File so demo uploads work with one click.
 *
 * These are synthetic placeholder bytes, not real scans — real OCR cannot read
 * them. Sample buttons therefore always run the DEMO pipeline (see the explicit
 * "DEMO" mode passed to `onFile` below) so a click always yields a full result. */
function makeSampleFile(name: string): File {
  const blob = new Blob([`sample-document::${name}::${Date.now()}`], {
    type: "image/png",
  });
  return new File([blob], name, { type: "image/png" });
}

export function DocumentUploader({
  onFile,
  disabled,
  mode,
}: {
  /** `forceMode` pins this upload to a pipeline regardless of the page toggle. */
  onFile: (file: File, forceMode?: PipelineMode) => void;
  disabled?: boolean;
  /** Current pipeline mode. Sample documents are DEMO-only — offering them in
   *  LIVE would put curated data into a pipeline that must only ever show real
   *  uploads, so they are hidden entirely outside DEMO. */
  mode: PipelineMode;
}) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      if (disabled) return;
      const file = e.dataTransfer.files?.[0];
      if (file) onFile(file);
    },
    [onFile, disabled]
  );

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === " ") && !disabled) {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        role="button"
        tabIndex={0}
        aria-label="Upload document"
        className={cn(
          "grid-bg flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-12 text-center transition-colors",
          dragging
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50",
          disabled && "pointer-events-none opacity-60"
        )}
      >
        <div
          className={cn(
            "flex h-14 w-14 items-center justify-center rounded-full transition-transform",
            dragging ? "scale-110 bg-primary text-primary-foreground" : "bg-primary/15 text-primary"
          )}
        >
          <UploadCloud className="h-7 w-7" />
        </div>
        <p className="mt-4 text-sm font-medium">
          Drag &amp; drop a document, or click to browse
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Aadhaar cards, medical reports, income certificates · JPG / PNG / PDF
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="image/*,application/pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onFile(file);
            e.target.value = "";
          }}
        />
      </div>

      {mode === "DEMO" && (
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Or try a sample document
        </p>
        <div className="grid grid-cols-2 gap-2">
          {SAMPLES.map((s) => {
            const Icon = s.icon;
            return (
              <button
                key={s.file}
                disabled={disabled}
                onClick={() => onFile(makeSampleFile(s.file), "DEMO")}
                className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-left text-xs transition-colors hover:border-primary/50 hover:bg-accent/40 disabled:opacity-50"
              >
                <Icon className="h-3.5 w-3.5 shrink-0 text-primary" />
                <span className="truncate">{s.label}</span>
              </button>
            );
          })}
        </div>
      </div>
      )}
    </div>
  );
}
