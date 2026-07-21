// Typed API client for the Sahayak AI FastAPI backend.
import type {
  Beneficiary,
  BriefAction,
  DailyBrief,
  DashboardMetrics,
  HealthResponse,
  ImpactReport,
  PipelineMode,
  SchemeMatch,
  Task,
  TaskStatus,
  UploadHistoryEntry,
  UploadResult,
  WelfareScheme,
} from "./types";
import { getAccessToken } from "./supabase";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";
const V1 = `${BASE_URL}/api/v1`;

function authHeaders(extra?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = { ...(extra as Record<string, string>) };
  const token = getAccessToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: authHeaders(init?.headers),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export interface CurrentUser {
  id: string;
  email: string | null;
  org_id: string;
  role: string;
  is_demo: boolean;
}

export const api = {
  health: () => req<HealthResponse>(`${BASE_URL}/health`),
  me: () => req<CurrentUser>(`${V1}/auth/me`),

  dashboardBrief: () => req<DailyBrief>(`${V1}/dashboard/brief`),
  dashboardMetrics: () => req<DashboardMetrics>(`${V1}/dashboard/metrics`),
  resetDemo: () => req<{ status: string }>(`${V1}/dashboard/reset`, { method: "POST" }),
  getMode: () => req<{ active_mode: PipelineMode }>(`${V1}/dashboard/mode`),
  setMode: (mode: PipelineMode) =>
    req<{ active_mode: PipelineMode }>(`${V1}/dashboard/mode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    }),

  listBeneficiaries: () => req<Beneficiary[]>(`${V1}/beneficiaries`),
  getBeneficiary: (id: string) => req<Beneficiary>(`${V1}/beneficiaries/${id}`),
  beneficiarySchemes: (id: string) =>
    req<SchemeMatch[]>(`${V1}/beneficiaries/${id}/schemes`),
  beneficiaryTasks: (id: string) =>
    req<Task[]>(`${V1}/beneficiaries/${id}/tasks`),

  uploadDocument: (
    file: File,
    mode?: PipelineMode,
    allowDuplicate = false,
  ) => {
    const form = new FormData();
    form.append("file", file);
    if (mode) form.append("mode", mode);
    if (allowDuplicate) form.append("allow_duplicate", "true");
    return req<UploadResult>(`${V1}/documents/upload`, {
      method: "POST",
      body: form,
    });
  },

  uploadHistory: (limit = 50) =>
    req<UploadHistoryEntry[]>(`${V1}/documents/history?limit=${limit}`),

  listTasks: () => req<Task[]>(`${V1}/tasks`),
  updateTask: (id: string, status: TaskStatus) =>
    req<Task>(`${V1}/tasks/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    }),

  listSchemes: () => req<WelfareScheme[]>(`${V1}/schemes`),
  impactReport: () => req<ImpactReport>(`${V1}/reports/impact`),
};

export type { BriefAction };
