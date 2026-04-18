/** API client for the scribe backend. */

import type {
  Config,
  Provider,
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

export const testProvider = (name: string) =>
  fetchJSON<{ success: boolean; message: string }>(`/providers/${name}/test`, {
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
