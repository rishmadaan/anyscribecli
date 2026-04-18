/** API client for the scribe backend. */

import type {
  Config,
  Provider,
  ProviderLanguagesResponse,
  ProviderTestResult,
  LocalStatusResponse,
  LocalModelsResponse,
  OnboardingStatus,
  OnboardingPayload,
  OnboardingResult,
  SetupLogResponse,
  TranscriptMeta,
  TranscriptDetail,
  WorkspaceInfo,
} from "./types";

const BASE = "/api";

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

// ── Config ───────────────────────────────────────────

export const getConfig = () => fetchJSON<Config>("/config");

export const updateConfig = (data: Partial<Config>) =>
  fetchJSON<Config>("/config", {
    method: "PUT",
    body: JSON.stringify(data),
  });

// ── Providers ────────────────────────────────────────

export const getProviders = () => fetchJSON<Provider[]>("/providers");

export const getProviderLanguages = (name: string) =>
  fetchJSON<ProviderLanguagesResponse>(`/providers/${name}/languages`);

export const testProvider = (name: string) =>
  fetchJSON<ProviderTestResult>(`/providers/${name}/test`, {
    method: "POST",
  });

export const getKeysStatus = () =>
  fetchJSON<Record<string, boolean>>("/keys/status");

export const updateKey = (provider_name: string, api_key: string) =>
  fetchJSON<{ success: boolean }>("/keys", {
    method: "PUT",
    body: JSON.stringify({ provider_name, api_key }),
  });

// ── Transcription ────────────────────────────────────

export const startTranscribe = (data: {
  url: string;
  provider?: string;
  language?: string;
  diarize?: boolean;
  keep_media?: boolean;
  output_format?: string;
}) =>
  fetchJSON<{ job_id: string }>("/transcribe", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const uploadFile = async (file: File): Promise<{ path: string; filename: string }> => {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
};

// ── History ──────────────────────────────────────────

export const getTranscripts = (platform?: string, limit = 50, offset = 0) => {
  const params = new URLSearchParams();
  if (platform) params.set("platform", platform);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return fetchJSON<{ items: TranscriptMeta[]; total: number; offset: number; limit: number }>(
    `/transcripts?${params}`
  );
};

export const getTranscript = (id: string) =>
  fetchJSON<TranscriptDetail>(`/transcripts/${id}`);

export const getWorkspaceInfo = () =>
  fetchJSON<WorkspaceInfo>("/workspace/info");

// ── Health ───────────────────────────────────────────

export const getHealth = () =>
  fetchJSON<{ ok: boolean; version: string; dependencies: Record<string, boolean> }>("/health");

// ── Local transcription ──────────────────────────────

export const getLocalStatus = () =>
  fetchJSON<LocalStatusResponse>("/local/status");

export const setupLocal = (model: string) =>
  fetchJSON<{ status: string; model: string }>("/local/setup", {
    method: "POST",
    body: JSON.stringify({ model }),
  });

export const teardownLocal = () =>
  fetchJSON<{
    status: string;
    models_deleted: string[];
    bytes_freed: number;
    provider_reset: boolean;
  }>("/local/teardown", { method: "POST" });

// ── Local model cache ────────────────────────────────

export const listLocalModels = () =>
  fetchJSON<LocalModelsResponse>("/models/local");

export const pullLocalModel = (size: string) =>
  fetchJSON<{ status: string; size: string }>(`/models/local/${size}/pull`, {
    method: "POST",
  });

export const deleteLocalModel = (size: string) =>
  fetchJSON<{ status: string; size: string; bytes_freed: number }>(
    `/models/local/${size}`,
    { method: "DELETE" }
  );

export const reinstallLocalModel = (size: string) =>
  fetchJSON<{
    status: string;
    size: string;
    bytes_freed: number;
    bytes_downloaded: number;
  }>(`/models/local/${size}/reinstall`, { method: "POST" });

export const getSetupLog = (since: number) =>
  fetchJSON<SetupLogResponse>(`/local/setup/log?since=${since}`);

// ── Onboarding ───────────────────────────────────────

export const getOnboardingStatus = () =>
  fetchJSON<OnboardingStatus>("/onboarding/status");

export const saveOnboarding = (payload: OnboardingPayload) =>
  fetchJSON<OnboardingResult>("/onboarding/save", {
    method: "POST",
    body: JSON.stringify(payload),
  });
