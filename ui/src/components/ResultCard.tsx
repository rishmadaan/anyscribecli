import { Check, Copy, FileText, Plus } from "lucide-react";
import { useState } from "react";
import type { JobResult } from "../api/types";

interface ResultCardProps {
  result: JobResult;
  onReset: () => void;
}

export default function ResultCard({ result, onReset }: ResultCardProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(result.file_path);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const stats = [
    { label: "Duration", value: result.duration || "—" },
    { label: "Language", value: result.language },
    { label: "Words", value: result.word_count.toLocaleString() },
    { label: "Provider", value: result.provider },
  ];

  return (
    <div className="w-full max-w-2xl animate-slide-up">
      {/* Success header */}
      <div className="flex items-center gap-2 mb-4">
        <div className="w-6 h-6 rounded-full bg-green/15 flex items-center justify-center">
          <Check className="w-3.5 h-3.5 text-green" />
        </div>
        <span
          className="text-lg font-semibold text-text tracking-tight"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Done
        </span>
      </div>

      {/* Title */}
      <p className="text-sm text-text-secondary mb-5 truncate">
        {result.title}
      </p>

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {stats.map(({ label, value }) => (
          <div
            key={label}
            className="rounded-lg bg-surface border border-border-subtle px-3 py-2.5"
          >
            <div className="text-[11px] text-text-muted uppercase tracking-wider mb-1">
              {label}
            </div>
            <div className="text-sm font-mono text-text font-medium">
              {value}
            </div>
          </div>
        ))}
      </div>

      {/* File path */}
      <div className="flex items-center gap-2 rounded-lg bg-surface border border-border-subtle px-3 py-2.5 mb-5">
        <FileText className="w-3.5 h-3.5 text-text-muted shrink-0" />
        <code className="text-xs text-text-secondary truncate flex-1 font-mono">
          {result.file_path}
        </code>
        <button
          onClick={handleCopy}
          className="text-text-muted hover:text-text transition-colors shrink-0 cursor-pointer"
        >
          {copied ? (
            <Check className="w-3.5 h-3.5 text-green" />
          ) : (
            <Copy className="w-3.5 h-3.5" />
          )}
        </button>
      </div>

      {/* Actions */}
      <button
        onClick={onReset}
        className="
          flex items-center justify-center gap-2
          rounded-lg border border-border hover:border-border/80
          bg-surface-raised hover:bg-surface-hover
          px-5 py-2.5 w-full text-sm text-text-secondary hover:text-text
          transition-colors cursor-pointer
        "
      >
        <Plus className="w-4 h-4" />
        New transcription
      </button>
    </div>
  );
}
