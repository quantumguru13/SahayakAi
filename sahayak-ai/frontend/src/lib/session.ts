// Session-scoped memory of the login choice (Live vs Demo).
//
// The backend holds the authoritative active mode, but it is global and resets
// when uvicorn restarts. Persisting the choice per browser session lets a page
// refresh — or a backend restart mid-demo — restore the mode the user logged in
// with, instead of silently dropping them into the other pipeline.
//
// sessionStorage (not localStorage) on purpose: a fresh tab should show the
// login page again, which is what makes the demo reproducible.
import type { PipelineMode } from "./types";

const KEY = "sahayak.mode";

export function rememberMode(mode: PipelineMode): void {
  try {
    window.sessionStorage.setItem(KEY, mode);
  } catch {
    // Private mode / storage disabled — the app still works, just without recall.
  }
}

export function getRememberedMode(): PipelineMode | null {
  try {
    const v = window.sessionStorage.getItem(KEY);
    return v === "LIVE" || v === "DEMO" ? v : null;
  } catch {
    return null;
  }
}

export function clearRememberedMode(): void {
  try {
    window.sessionStorage.removeItem(KEY);
  } catch {
    // no-op
  }
}
