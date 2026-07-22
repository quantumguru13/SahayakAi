"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { BrandedLoader } from "@/components/shared/branded-loader";
import { isAuthenticated } from "@/lib/auth";
import { useHealth, useSetMode } from "@/lib/hooks";
import { getRememberedMode } from "@/lib/session";
import type { PipelineMode } from "@/lib/types";
import { Sidebar } from "./sidebar";

const BARE_ROUTES = ["/login", "/"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: health } = useHealth();
  const setMode = useSetMode();

  const isLoginRoute = pathname === "/login";
  const isBare = BARE_ROUTES.includes(pathname);

  // Read auth state on client side to prevent SSR hydration mismatch
  const [authResolved, setAuthResolved] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [rememberedMode, setRememberedMode] = useState<PipelineMode | null>(null);

  // 1) Evaluate Local Authentication & Perform Required Redirects
  useEffect(() => {
    const isAuth = isAuthenticated();
    setAuthed(isAuth);
    setAuthResolved(true);

    if (!isAuth && !isLoginRoute) {
      router.replace("/login");
    } else if (isAuth && isLoginRoute) {
      router.replace("/");
    }
  }, [pathname, isLoginRoute, router]);

  // 2) For Workspace Routes (/dashboard, /beneficiaries, etc.), Check Pipeline Mode
  useEffect(() => {
    if (!authResolved || !authed || isBare) return;

    const currentMode = getRememberedMode();
    if (currentMode === null) {
      router.replace("/");
      return;
    }
    setRememberedMode(currentMode);
  }, [pathname, isBare, authResolved, authed, router]);

  // 3) Re-sync Backend Pipeline Mode if required
  useEffect(() => {
    if (
      authResolved &&
      authed &&
      !isBare &&
      rememberedMode !== null &&
      health?.active_mode &&
      health.active_mode !== rememberedMode &&
      !setMode.isPending
    ) {
      setMode.mutate(rememberedMode);
    }
  }, [authResolved, authed, isBare, rememberedMode, health?.active_mode, setMode]);

  // Initial loader while client verifies local storage auth state
  if (!authResolved) {
    return <BrandedLoader label="Securing workspace…" />;
  }

  // If unauthenticated and trying to access any page other than /login
  if (!authed && !isLoginRoute) {
    return <BrandedLoader label="Redirecting to login…" />;
  }

  // If authenticated and trying to access /login
  if (authed && isLoginRoute) {
    return <BrandedLoader label="Entering workspace…" />;
  }

  // Full-screen bare pages (/login when unauthenticated, / when authenticated)
  if (isBare) {
    return <>{children}</>;
  }

  // Workspace routes waiting for mode resolution
  if (rememberedMode === null) {
    return <BrandedLoader label="Loading workspace…" />;
  }

  // Workspace layout with sidebar (/dashboard, /beneficiaries, /intake, /reports)
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">{children}</div>
    </div>
  );
}
