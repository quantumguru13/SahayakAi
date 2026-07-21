// TanStack Query v5 hooks — API client caching pipelines.
"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "./api";
import type { PipelineMode, TaskStatus } from "./types";

export const qk = {
  health: ["health"] as const,
  brief: ["dashboard", "brief"] as const,
  metrics: ["dashboard", "metrics"] as const,
  beneficiaries: ["beneficiaries"] as const,
  beneficiary: (id: string) => ["beneficiaries", id] as const,
  schemes: (id: string) => ["beneficiaries", id, "schemes"] as const,
  bTasks: (id: string) => ["beneficiaries", id, "tasks"] as const,
  tasks: ["tasks"] as const,
  impact: ["reports", "impact"] as const,
  history: ["documents", "history"] as const,
};

export const useHealth = () =>
  useQuery({ queryKey: qk.health, queryFn: api.health });

export const useBrief = () =>
  useQuery({ queryKey: qk.brief, queryFn: api.dashboardBrief });

export const useBeneficiaries = () =>
  useQuery({ queryKey: qk.beneficiaries, queryFn: api.listBeneficiaries });

export const useBeneficiary = (id: string) =>
  useQuery({
    queryKey: qk.beneficiary(id),
    queryFn: () => api.getBeneficiary(id),
    enabled: !!id,
  });

export const useSchemes = (id: string) =>
  useQuery({
    queryKey: qk.schemes(id),
    queryFn: () => api.beneficiarySchemes(id),
    enabled: !!id,
  });

export const useBeneficiaryTasks = (id: string) =>
  useQuery({
    queryKey: qk.bTasks(id),
    queryFn: () => api.beneficiaryTasks(id),
    enabled: !!id,
  });

export const useTasks = () =>
  useQuery({ queryKey: qk.tasks, queryFn: api.listTasks });

export const useImpactReport = (enabled: boolean) =>
  useQuery({ queryKey: qk.impact, queryFn: api.impactReport, enabled });

export const useUploadHistory = () =>
  useQuery({ queryKey: qk.history, queryFn: () => api.uploadHistory() });

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      file,
      mode,
      allowDuplicate,
    }: {
      file: File;
      mode?: PipelineMode;
      allowDuplicate?: boolean;
    }) => api.uploadDocument(file, mode, allowDuplicate),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.beneficiaries });
      qc.invalidateQueries({ queryKey: qk.brief });
      qc.invalidateQueries({ queryKey: qk.metrics });
      qc.invalidateQueries({ queryKey: qk.tasks });
      qc.invalidateQueries({ queryKey: qk.health });
      qc.invalidateQueries({ queryKey: qk.history });
    },
  });
}

export function useUpdateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: TaskStatus }) =>
      api.updateTask(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.tasks });
      qc.invalidateQueries({ queryKey: qk.brief });
      qc.invalidateQueries({ queryKey: qk.metrics });
      qc.invalidateQueries({ queryKey: ["beneficiaries"] });
    },
  });
}


export function useResetDemo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.resetDemo(),
    onSuccess: () => {
      qc.invalidateQueries();
    },
  });
}

export function useSetMode() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (mode: PipelineMode) => api.setMode(mode),
    onSuccess: () => {
      // Re-scope every mode-dependent view to the newly selected mode.
      qc.invalidateQueries({ queryKey: qk.beneficiaries });
      qc.invalidateQueries({ queryKey: qk.tasks });
      qc.invalidateQueries({ queryKey: qk.brief });
      qc.invalidateQueries({ queryKey: qk.metrics });
      qc.invalidateQueries({ queryKey: qk.health });
    },
  });
}
