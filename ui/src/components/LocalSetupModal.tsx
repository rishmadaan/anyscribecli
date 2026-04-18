/** Local transcription setup modal.
 *
 * Lets the user pick a model size (recommended preselected + badged), kicks
 * off the unified backend setup flow, polls status until done, and streams
 * the install log into a collapsible panel so diagnostic output is visible
 * when something goes wrong.
 */

import { useEffect, useRef, useState } from "react";
import { X, Loader2, AlertCircle, Check, ChevronDown, ChevronRight } from "lucide-react";
import {
  getLocalStatus,
  setupLocal,
  getSetupLog,
} from "../api/client";
import type { LocalStatusResponse } from "../api/types";
import Modal from "./Modal";

const POLL_MS = 1500;

interface Props {
  onClose: () => void;
  onDone: () => void;
}

export default function LocalSetupModal({ onClose, onDone }: Props) {
  const [status, setStatus] = useState<LocalStatusResponse | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [logOpen, setLogOpen] = useState(false);
  const logCursorRef = useRef(0);

  // Initial status fetch + preselect recommended size.
  useEffect(() => {
    let cancelled = false;
    getLocalStatus()
      .then((s) => {
        if (cancelled) return;
        setStatus(s);
        setSelected((prev) => prev ?? s.recommended_model);
      })
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load status")
      );
    return () => {
      cancelled = true;
    };
  }, []);

  // Poll status + log while setup is in flight.
  useEffect(() => {
    if (!status?.setup_running) return;
    const id = setInterval(async () => {
      try {
        const [s, log] = await Promise.all([
          getLocalStatus(),
          getSetupLog(logCursorRef.current),
        ]);
        setStatus(s);
        if (log.lines.length > 0) {
          setLogLines((prev) => [...prev, ...log.lines]);
          logCursorRef.current = log.total;
        }
        if (!s.setup_running) {
          clearInterval(id);
          if (s.setup_error) {
            setError(s.setup_error);
            setLogOpen(true);
          } else if (s.set_up) {
            onDone();
          }
        }
      } catch {
        // transient — keep polling
      }
    }, POLL_MS);
    return () => clearInterval(id);
  }, [status?.setup_running, onDone]);

  const handleDownload = async () => {
    if (!selected) return;
    setStarting(true);
    setError(null);
    setLogLines([]);
    logCursorRef.current = 0;
    try {
      await setupLocal(selected);
      const s = await getLocalStatus();
      setStatus(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start setup");
    } finally {
      setStarting(false);
    }
  };

  if (!status) {
    return (
      <Modal onClose={onClose} ariaLabel="Set up local transcription" size="lg">
        <div className="flex items-center justify-center py-10">
          <Loader2 className="w-5 h-5 animate-spin text-text-muted" />
        </div>
      </Modal>
    );
  }

  const running = status.setup_running;
  const phase = status.setup_phase;

  return (
    <Modal
      onClose={onClose}
      disableClose={running}
      ariaLabelledBy="local-setup-title"
      size="lg"
    >
      <div className="flex items-center justify-between mb-4">
        <h2
          id="local-setup-title"
          className="text-lg font-bold text-text"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Set up local transcription
        </h2>
        {!running && (
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text transition-colors cursor-pointer p-0.5"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      <p className="text-sm text-text-muted mb-4">
        Runs Whisper offline on your machine via faster-whisper. Pick a model
        size — larger is more accurate but slower and bigger on disk.
      </p>

      {error && (
        <div className="rounded-md border border-red/30 bg-red/5 px-3 py-2 mb-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-red font-mono break-words">
                {error.length > 500 ? error.slice(0, 500) + "…" : error}
              </p>
              {error.length > 500 && (
                <details className="mt-2">
                  <summary className="text-[10px] font-mono text-red/70 cursor-pointer">
                    show full error
                  </summary>
                  <pre className="mt-2 text-[10px] font-mono text-red/80 whitespace-pre-wrap break-words">
                    {error}
                  </pre>
                </details>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="space-y-2 mb-5">
        {status.models.map((m) => {
          const isRecommended = m.size === status.recommended_model;
          const isSelected = selected === m.size;
          const isCached = m.cached;
          return (
            <button
              key={m.size}
              disabled={running}
              onClick={() => setSelected(m.size)}
              className={`w-full text-left rounded-lg border px-3 py-2.5 transition-colors cursor-pointer ${
                isSelected
                  ? "border-amber bg-amber/5"
                  : "border-border-subtle bg-surface hover:border-border"
              } ${running ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              <div className="flex items-center gap-2">
                <span className="text-sm font-mono text-text font-bold">
                  {m.size}
                </span>
                {isRecommended && (
                  <span className="text-[10px] font-mono text-amber bg-amber/10 border border-amber/30 rounded px-1.5 py-0.5">
                    recommended
                  </span>
                )}
                {isCached && (
                  <span className="text-[10px] font-mono text-green bg-green/10 border border-green/30 rounded px-1.5 py-0.5">
                    cached
                  </span>
                )}
                <span className="ml-auto text-xs text-text-muted font-mono">
                  ~{m.spec.download_mb} MB
                </span>
              </div>
              <p className="text-xs text-text-muted mt-1">
                {m.spec.quality} · {m.spec.relative_speed}
              </p>
            </button>
          );
        })}
      </div>

      {running && (
        <div className="rounded-md border border-border-subtle bg-surface-raised px-3 py-2 mb-4">
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-amber" />
            <p className="text-xs text-text font-mono">{describePhase(phase)}</p>
          </div>
        </div>
      )}

      {(running || logLines.length > 0) && (
        <div className="mb-4">
          <button
            onClick={() => setLogOpen(!logOpen)}
            className="flex items-center gap-1 text-xs font-mono text-text-muted hover:text-text transition-colors cursor-pointer"
          >
            {logOpen ? (
              <ChevronDown className="w-3 h-3" />
            ) : (
              <ChevronRight className="w-3 h-3" />
            )}
            Show install log{" "}
            {logLines.length > 0 && (
              <span className="text-[10px] text-text-muted">
                ({logLines.length} lines)
              </span>
            )}
          </button>
          {logOpen && (
            <pre className="mt-2 max-h-56 overflow-auto rounded-md border border-border-subtle bg-black/20 p-2 text-[10px] font-mono text-text-muted whitespace-pre-wrap break-all">
              {logLines.length > 0 ? logLines.join("\n") : "(no output yet)"}
            </pre>
          )}
        </div>
      )}

      <div className="flex items-center justify-end gap-2">
        {!running && (
          <button
            onClick={onClose}
            className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer"
          >
            Cancel
          </button>
        )}
        <button
          onClick={handleDownload}
          disabled={starting || running || !selected}
          className="rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-mono hover:bg-amber/80 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
        >
          {starting || running ? (
            <>
              <Loader2 className="w-3 h-3 animate-spin" />
              Setting up…
            </>
          ) : (
            <>
              <Check className="w-3 h-3" />
              Download & set up
            </>
          )}
        </button>
      </div>
    </Modal>
  );
}

function describePhase(phase: string | null): string {
  switch (phase) {
    case null:
    case "starting":
      return "Starting setup…";
    case "detecting_install_method":
      return "Detecting install method…";
    case "installing_package":
      return "Installing faster-whisper (this can take a minute)…";
    case "package_installed":
      return "faster-whisper installed. Preparing to download model…";
    case "downloading_model":
      return "Downloading model weights from HuggingFace…";
    case "model_downloaded":
      return "Model downloaded. Finishing up…";
    case "done":
      return "Done.";
    default:
      return phase;
  }
}
