/** Hook for tracking a transcription job via WebSocket. */

import { useCallback, useRef, useState } from "react";
import type { JobResult, ProgressEvent } from "../api/types";
import { startTranscribe } from "../api/client";

export type JobPhase = "idle" | "running" | "completed" | "error";

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

  const submit = useCallback(
    async (data: {
      url: string;
      provider?: string;
      language?: string;
      diarize?: boolean;
      keep_media?: boolean;
    }) => {
      // Reset state
      setState({ phase: "running", events: [], result: null, error: null });

      try {
        const { job_id } = await startTranscribe(data);

        // Connect WebSocket for progress
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/api/ws/jobs/${job_id}`;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

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
          setState((prev) => ({
            ...prev,
            phase: "error",
            error: "WebSocket connection failed",
          }));
        };

        ws.onclose = () => {
          wsRef.current = null;
        };
      } catch (err) {
        setState({
          phase: "error",
          events: [],
          result: null,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    },
    []
  );

  const reset = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setState({ phase: "idle", events: [], result: null, error: null });
  }, []);

  return { ...state, submit, reset };
}
