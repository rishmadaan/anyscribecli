/** Hook for tracking a transcription job via WebSocket with reconnection. */

import { useCallback, useRef, useState } from "react";
import type { JobResult, ProgressEvent } from "../api/types";
import { startTranscribe } from "../api/client";

export type JobPhase = "idle" | "running" | "completed" | "error";

const MAX_RECONNECT = 5;
const POLL_INTERVAL_MS = 3000;

interface JobState {
  phase: JobPhase;
  events: ProgressEvent[];
  result: JobResult | null;
  error: string | null;
}

export function useJob() {
  const [state, setState] = useState<JobState>({
    phase: "idle",
    events: [],
    result: null,
    error: null,
  });
  const wsRef = useRef<WebSocket | null>(null);
  const jobIdRef = useRef<string | null>(null);
  const reconnectAttemptRef = useRef(0);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const pollForStatus = useCallback(
    (jobId: string) => {
      if (pollTimerRef.current) return; // Already polling
      pollTimerRef.current = setInterval(async () => {
        try {
          const res = await fetch(`/api/jobs/${jobId}`);
          const data = await res.json();
          if (data.status === "completed") {
            stopPolling();
            setState((prev) => ({
              ...prev,
              phase: "completed",
              result: data.result ?? null,
            }));
          } else if (data.status === "failed") {
            stopPolling();
            setState((prev) => ({
              ...prev,
              phase: "error",
              error: data.error ?? "Transcription failed",
            }));
          }
        } catch {
          // Ignore poll errors — will retry on next interval
        }
      }, POLL_INTERVAL_MS);
    },
    [stopPolling]
  );

  const connectWs = useCallback(
    (jobId: string) => {
      const protocol =
        window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/api/ws/jobs/${jobId}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttemptRef.current = 0;
        stopPolling(); // Stop polling if we reconnected
      };

      ws.onmessage = (e) => {
        const event: ProgressEvent = JSON.parse(e.data);
        setState((prev) => {
          if (event.step === "done") {
            return {
              ...prev,
              phase: "completed",
              events: [...prev.events, event],
              result: (event.data as unknown as JobResult) ?? null,
            };
          }
          if (event.step === "error") {
            return {
              ...prev,
              phase: "error",
              events: [...prev.events, event],
              error: event.message,
            };
          }
          return { ...prev, events: [...prev.events, event] };
        });
      };

      ws.onerror = () => {
        // Don't set error immediately — let onclose handle reconnection
      };

      ws.onclose = (event) => {
        wsRef.current = null;

        // If we got a clean close (done/error already handled), skip reconnect
        if (event.code === 1000) return;

        // Check if job is still running before reconnecting
        setState((prev) => {
          if (prev.phase !== "running") return prev;

          if (reconnectAttemptRef.current < MAX_RECONNECT) {
            const delay = Math.min(
              1000 * Math.pow(2, reconnectAttemptRef.current),
              30000
            );
            reconnectAttemptRef.current++;
            setTimeout(() => {
              if (jobIdRef.current) connectWs(jobIdRef.current);
            }, delay);
          } else {
            // Fall back to polling
            pollForStatus(jobId);
          }
          return prev;
        });
      };
    },
    [pollForStatus, stopPolling]
  );

  const submit = useCallback(
    async (data: {
      url: string;
      provider?: string;
      language?: string;
      diarize?: boolean;
      keep_media?: boolean;
      output_format?: string;
    }) => {
      // Reset state
      setState({ phase: "running", events: [], result: null, error: null });
      reconnectAttemptRef.current = 0;
      stopPolling();

      try {
        const { job_id } = await startTranscribe(data);
        jobIdRef.current = job_id;
        connectWs(job_id);
      } catch (err) {
        setState({
          phase: "error",
          events: [],
          result: null,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    },
    [connectWs, stopPolling]
  );

  const reset = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    jobIdRef.current = null;
    reconnectAttemptRef.current = 0;
    stopPolling();
    setState({ phase: "idle", events: [], result: null, error: null });
  }, [stopPolling]);

  return { ...state, submit, reset };
}
