import { Check, Circle, Loader2 } from "lucide-react";
import type { ProgressEvent } from "../api/types";

const STEPS = [
  { key: "download", label: "Download audio" },
  { key: "transcribe", label: "Transcribe" },
  { key: "write", label: "Write to vault" },
  { key: "index", label: "Update indexes" },
] as const;

type StepStatus = "pending" | "active" | "done";

function getStepStatus(stepKey: string, events: ProgressEvent[]): StepStatus {
  const stepEvents = events.filter((e) => e.step === stepKey);
  if (stepEvents.some((e) => e.status === "completed")) return "done";
  if (stepEvents.some((e) => e.status === "started")) return "active";
  return "pending";
}

function StepIcon({ status }: { status: StepStatus }) {
  switch (status) {
    case "done":
      return (
        <div className="w-5 h-5 rounded-full bg-green/15 flex items-center justify-center">
          <Check className="w-3 h-3 text-green" />
        </div>
      );
    case "active":
      return <Loader2 className="w-5 h-5 text-amber animate-spin" />;
    case "pending":
      return <Circle className="w-5 h-5 text-text-muted/40" />;
  }
}

interface WaveformProps {
  active: boolean;
}

function Waveform({ active }: WaveformProps) {
  if (!active) return null;
  return (
    <div className="flex items-end gap-[2px] h-4 ml-auto">
      {[0, 1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="w-[2px] bg-amber/60 rounded-full waveform-bar origin-bottom"
          style={{
            height: "100%",
            animationDelay: `${i * 0.15}s`,
          }}
        />
      ))}
    </div>
  );
}

interface ProgressTrackerProps {
  events: ProgressEvent[];
  title?: string;
}

export default function ProgressTracker({ events, title }: ProgressTrackerProps) {
  const latestMessage = events.length > 0 ? events[events.length - 1].message : "";
  const isTranscribing = getStepStatus("transcribe", events) === "active";

  return (
    <div className="w-full max-w-2xl animate-slide-up">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <Waveform active={isTranscribing} />
        </div>
        <p
          className="text-xl font-semibold text-text tracking-tight"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Transcribing
        </p>
        {title && (
          <p className="text-sm text-text-secondary mt-1 truncate">{title}</p>
        )}
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {STEPS.map(({ key, label }) => {
          const status = getStepStatus(key, events);
          return (
            <div key={key} className="flex items-center gap-3">
              <StepIcon status={status} />
              <span
                className={`text-sm ${
                  status === "done"
                    ? "text-text"
                    : status === "active"
                    ? "text-text font-medium"
                    : "text-text-muted"
                }`}
              >
                {label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Latest status message */}
      {latestMessage && (
        <p className="mt-4 text-xs text-text-muted font-mono truncate">
          {latestMessage}
        </p>
      )}
    </div>
  );
}
