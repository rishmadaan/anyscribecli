import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getTranscript } from "../api/client";
import type { TranscriptDetail } from "../api/types";
import { ArrowLeft, Copy, Check, ExternalLink } from "lucide-react";

export default function TranscriptView() {
  const { id } = useParams<{ id: string }>();
  const [transcript, setTranscript] = useState<TranscriptDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!id) return;
    getTranscript(id)
      .then(setTranscript)
      .finally(() => setLoading(false));
  }, [id]);

  const handleCopy = async () => {
    if (!transcript) return;
    await navigator.clipboard.writeText(transcript.body);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="px-8 py-10 max-w-4xl">
        <div className="h-8 w-48 bg-surface rounded animate-pulse mb-4" />
        <div className="h-64 bg-surface rounded animate-pulse" />
      </div>
    );
  }

  if (!transcript) {
    return (
      <div className="px-8 py-10 max-w-4xl">
        <p className="text-text-muted">Transcript not found.</p>
      </div>
    );
  }

  const fm = transcript.frontmatter;

  return (
    <div className="px-8 py-10 max-w-4xl">
      {/* Back */}
      <Link
        to="/history"
        className="inline-flex items-center gap-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors mb-6"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Back to history
      </Link>

      {/* Title */}
      <h1
        className="text-2xl font-bold tracking-tight text-text mb-2"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {String(fm.title || id)}
      </h1>

      {/* Metadata strip */}
      <div className="flex items-center gap-4 text-xs text-text-muted font-mono mb-6 flex-wrap">
        {fm.platform ? <span>{String(fm.platform)}</span> : null}
        {fm.duration ? <span>{String(fm.duration)}</span> : null}
        {fm.language ? <span>{String(fm.language)}</span> : null}
        {fm.word_count != null ? <span>{Number(fm.word_count).toLocaleString()} words</span> : null}
        {fm.provider ? <span>{String(fm.provider)}</span> : null}
        {fm.date_processed ? <span>{String(fm.date_processed)}</span> : null}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 mb-6">
        <button
          onClick={handleCopy}
          className="
            flex items-center gap-1.5 rounded-md border border-border
            bg-surface px-3 py-1.5 text-xs text-text-secondary
            hover:text-text hover:bg-surface-raised transition-colors cursor-pointer
          "
        >
          {copied ? <Check className="w-3 h-3 text-green" /> : <Copy className="w-3 h-3" />}
          {copied ? "Copied" : "Copy text"}
        </button>
        {fm.source ? (
          <a
            href={String(fm.source)}
            target="_blank"
            rel="noopener noreferrer"
            className="
              flex items-center gap-1.5 rounded-md border border-border
              bg-surface px-3 py-1.5 text-xs text-text-secondary
              hover:text-text hover:bg-surface-raised transition-colors
            "
          >
            <ExternalLink className="w-3 h-3" />
            Source
          </a>
        ) : null}
      </div>

      {/* Transcript body */}
      <div className="rounded-lg border border-border-subtle bg-surface p-6">
        <pre className="whitespace-pre-wrap text-sm text-text-secondary leading-relaxed font-mono">
          {transcript.body}
        </pre>
      </div>

      {/* File path */}
      <p className="mt-4 text-xs text-text-muted font-mono truncate">
        {transcript.file_path}
      </p>
    </div>
  );
}
