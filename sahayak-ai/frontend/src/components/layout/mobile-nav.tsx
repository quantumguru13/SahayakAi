"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  FileText,
  LayoutDashboard,
  Menu,
  RefreshCw,
  Sparkles,
  Upload,
  Users,
  X,
} from "lucide-react";

import { useResetDemo } from "@/lib/hooks";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/beneficiaries", label: "Beneficiaries", icon: Users },
  { href: "/intake", label: "New Intake", icon: Upload },
  { href: "/reports", label: "Impact Report", icon: FileText },
];

/** Hamburger + slide-in drawer navigation for screens below `md`. */
export function MobileNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const { mutate: reset, isPending } = useResetDemo();
  const { toast } = useToast();

  // Close the drawer whenever the route changes.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <div className="md:hidden">
      <button
        onClick={() => setOpen(true)}
        aria-label="Open navigation menu"
        className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card text-foreground transition-colors hover:bg-accent"
      >
        <Menu className="h-5 w-5" />
      </button>

      <AnimatePresence>
        {open && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setOpen(false)}
              className="fixed inset-0 z-40 bg-background/70 backdrop-blur-sm"
            />
            <motion.aside
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 26, stiffness: 260 }}
              className="fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-border bg-card"
              role="dialog"
              aria-label="Navigation"
            >
              <div className="flex h-16 items-center justify-between border-b border-border px-4">
                <div className="flex items-center gap-2.5">
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
                <button
                  onClick={() => setOpen(false)}
                  aria-label="Close navigation menu"
                  className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground"
                >
                  <X className="h-4 w-4" />
                </button>
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
                        "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
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

              <div className="border-t border-border p-4">
                <button
                  onClick={() =>
                    reset(undefined, {
                      onSuccess: () =>
                        toast("Demo database reset to default seed state!", "success"),
                      onError: (err) =>
                        toast(`Failed to reset: ${err.message}`, "error"),
                    })
                  }
                  disabled={isPending}
                  className={cn(
                    "flex w-full items-center justify-center gap-2 rounded-lg border border-primary/20 bg-primary/10 px-3 py-2.5 text-xs font-semibold text-primary transition-colors hover:bg-primary/20",
                    isPending && "opacity-70"
                  )}
                >
                  <RefreshCw className={cn("h-3.5 w-3.5", isPending && "animate-spin")} />
                  {isPending ? "Resetting…" : "Reset Demo Data"}
                </button>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
