"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/auth-provider";
import { LoginScreen } from "@/components/auth/login-screen";
import { BrandedLoader } from "@/components/shared/branded-loader";
import { useHealth, useSetMode } from "@/lib/hooks";
import { getRememberedMode } from "@/lib/session";
import type { PipelineMode } from "@/lib/types";
import { Sidebar } from "./sidebar";

// Routes that render full-screen without the workspace chrome (no sidebar/login gate).
const BARE_ROUTES = ["/"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { authEnabled, loading, session } = useAuth();
  const { data: health } = useHealth();
  const setMode = useSetMode();

  const isBare = BARE_ROUTES.includes(pathname);

  // Read sessionStorage after mount only — reading during render would produce
  // a server/client markup mismatch.
  const [remembered, setRemembered] = useState<PipelineMode | null>(null);
  const [resolved, setResolved] = useState(false);

  // Read storage FRESH on every route change and decide in the same pass. Using
  // the `remembered` state here instead would test the previous route's value —
  // which bounced a just-logged-in user straight back to the login page.
  useEffect(() => {
    if (isBare) {
      setResolved(true);
      return;
    }
    const current = getRememberedMode();
    if (current === null) {
      router.replace("/");
      return;
    }
    setRemembered(current);
    setResolved(true);
  }, [pathname, isBare, router]);

  // Re-apply the logged-in mode if the backend drifted from it (e.g. uvicorn was
  // restarted mid-demo, resetting its global active mode).
  useEffect(() => {
    if (
      resolved &&
      !isBare &&
      remembered !== null &&
      health?.active_mode &&
      health.active_mode !== remembered &&
      !setMode.isPending
    ) {
      setMode.mutate(remembered);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolved, isBare, remembered, health?.active_mode]);

  // Login page owns the whole viewport.
  if (isBare) {
    return <>{children}</>;
  }

  // Resolving the session choice, or redirecting — don't flash the workspace.
  if (!resolved || remembered === null) {
    return <BrandedLoader label="Loading your workspace…" />;
  }

  // Auth on, still resolving the session -> branded full-screen loader.
  if (authEnabled && loading) {
    return <BrandedLoader label="Securing your workspace…" />;
  }

  // Auth on, no session -> login gate replaces the whole app.
  if (authEnabled && !session) {
    return <LoginScreen />;
  }

  // Demo mode (auth off) or authenticated -> the normal workspace shell.
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">{children}</div>
    </div>
  );
}
