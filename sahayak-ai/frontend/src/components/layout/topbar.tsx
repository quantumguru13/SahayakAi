"use client";

import Link from "next/link";
import { CircleDot, LogOut, Upload } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { MobileNav } from "@/components/layout/mobile-nav";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { useHealth } from "@/lib/hooks";

export function Topbar({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  const { data: health } = useHealth();
  const { authEnabled, user, signOut } = useAuth();

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-border bg-background/80 px-4 backdrop-blur sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <MobileNav />
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold leading-tight sm:text-lg">
            {title}
          </h1>
          {subtitle && (
            <p className="hidden truncate text-xs text-muted-foreground sm:block">
              {subtitle}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        {health && (
          <Badge
            variant={health.active_mode === "LIVE" ? "success" : "warning"}
            className="gap-1.5"
            title={
              health.active_mode === "LIVE"
                ? `LIVE — real OCR (${(health.ocr_engines ?? []).join(", ") || "engine"}). Dashboard shows only uploaded cases.`
                : "DEMO — showing sample beneficiary data. No OCR is executed."
            }
          >
            <CircleDot className="h-3 w-3" />
            {health.active_mode === "LIVE" ? "Live AI" : "🟡 Demo Mode"}
          </Badge>
        )}
        <Link
          href="/intake"
          className={buttonVariants({ size: "sm", className: "gap-1.5" })}
        >
          <Upload className="h-4 w-4" />
          <span className="hidden sm:inline">New Intake</span>
        </Link>

        {authEnabled && user && (
          <div className="flex items-center gap-2 border-l border-border pl-3">
            <div
              className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/15 text-xs font-medium text-primary"
              title={user.email ?? undefined}
            >
              {(user.email ?? "?").charAt(0).toUpperCase()}
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => signOut()}
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}
