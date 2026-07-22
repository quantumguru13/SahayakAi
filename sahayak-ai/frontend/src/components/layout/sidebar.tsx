"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  FileText,
  LayoutDashboard,
  LogOut,
  Sparkles,
  Upload,
  Users,
  RefreshCw,
} from "lucide-react";

import { useResetDemo } from "@/lib/hooks";
import { useToast } from "@/components/ui/toast";
import { clearRememberedMode } from "@/lib/session";
import { logoutLocal } from "@/lib/auth";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/beneficiaries", label: "Beneficiaries", icon: Users },
  { href: "/intake", label: "New Intake", icon: Upload },
  { href: "/reports", label: "Impact Report", icon: FileText },
];

function JudgeResetButton() {
  const { mutate, isPending } = useResetDemo();
  const { toast } = useToast();

  return (
    <button
      onClick={() =>
        mutate(undefined, {
          onSuccess: () => {
            toast("Demo database reset to default seed state!", "success");
          },
          onError: (err) => {
            toast(`Failed to reset demo: ${err.message}`, "error");
          },
        })
      }
      disabled={isPending}
      className={cn(
        "flex w-full items-center justify-center gap-2 rounded-lg bg-primary/10 border border-primary/20 hover:bg-primary/20 px-3 py-2 text-xs font-semibold text-primary transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 focus-visible:ring-offset-background",
        isPending && "opacity-70 cursor-not-allowed"
      )}
    >
      <RefreshCw className={cn("h-3.5 w-3.5", isPending && "animate-spin")} />
      {isPending ? "Resetting..." : "Reset Demo Data"}
    </button>
  );
}

/** Returns to the mode selection page. */
function SwitchModeButton() {
  const router = useRouter();
  return (
    <button
      onClick={() => {
        clearRememberedMode();
        router.push("/");
      }}
      className="flex w-full items-center justify-center gap-2 rounded-lg border border-border px-3 py-2 text-xs font-semibold text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 focus-visible:ring-offset-background"
    >
      <RefreshCw className="h-3.5 w-3.5" />
      Switch Mode
    </button>
  );
}

/** Clears authentication session and returns to /login. */
function LogoutButton() {
  const router = useRouter();
  return (
    <button
      onClick={() => {
        clearRememberedMode();
        logoutLocal();
        router.push("/login");
      }}
      className="flex w-full items-center justify-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs font-semibold text-destructive/90 transition-colors hover:bg-destructive/15 hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-destructive"
    >
      <LogOut className="h-3.5 w-3.5" />
      Sign Out
    </button>
  );
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-card/40 md:flex">
      <div className="flex h-16 items-center gap-2 border-b border-border px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Sparkles className="h-4 w-4" />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold">Sahayak AI</div>
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
            Case Intelligence
          </div>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 p-3">
        {NAV.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-3 space-y-2">
        <JudgeResetButton />
        <SwitchModeButton />
        <LogoutButton />
        <div className="rounded-lg bg-muted/40 p-2.5 text-xs text-muted-foreground">
          <p className="font-medium text-foreground">Hack4Humanity MVP</p>
          <p className="mt-0.5 text-[11px]">
            No vulnerable individual should fall through the cracks.
          </p>
        </div>
      </div>
    </aside>
  );
}
