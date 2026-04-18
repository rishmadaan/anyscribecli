/** Local transcription setup modal.
 *
 * Shown when the user clicks "Set up local transcription" on the local
 * provider card in Settings. Lets the user pick a model size (with the
 * backend-recommended size preselected and badged), kicks off the unified
 * setup flow, and polls status until done. Errors are shown verbatim so the
 * user (or the agent reading the page) can resolve install issues manually.
 */

import { useEffect, useState } from "react";
import { X, Loader2, AlertCircle, Check } from "lucide-react";
import { getLocalStatus, setupLocal } from "../api/client";
import type { LocalStatusResponse } from "../api/types";

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

  // Poll while a setup is in flight so the user sees the phase flip.
  useEffect(() => {
    if (!status?.setup_running) return;
    const id = setInterval(async () => {
      try {
        const s = await getLocalStatus();
        setStatus(s);
        if (!s.setup_running) {
          clearInterval(id);
          if (s.setup_error) {
            setError(s.setup_error);
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
    try {
      await setupLocal(selected);
      // Kick status re-fetch so setup_running flips and polling starts.
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
      <Modal onClose={onClose}>
        <div className="flex items-center justify-center py-10">
          <Loader2 className="w-5 h-5 animate-spin text-text-muted" />
        </div>
      </Modal>
    );
  }

  const running = status.setup_running;
  const phase = status.setup_phase;

  return (
    <Modal onClose={onClose} disableClose={running}>
      <div className="flex items-center justify-between mb-4">
        <h2
          className="text-lg font-bold text-text"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Set up local transcription
        </h2>
        {!running && (
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text transition-colors cursor-pointer p-0.5"
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
              <p className="text-xs text-red font-mono break-words">{error}</p>
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
            <p className="text-xs text-text font-mono">
              {describePhase(phase)}
            </p>
          </div>
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

function Modal({
  children,
  onClose,
  disableClose = false,
}: {
  children: React.ReactNode;
  onClose: () => void;
  disableClose?: boolean;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !disableClose) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, disableClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
      onClick={() => {
        if (!disableClose) onClose();
      }}
    >
      <div
        className="relative w-full max-w-lg rounded-xl border border-border-subtle bg-surface p-5 shadow-2xl animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
