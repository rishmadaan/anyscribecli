import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getTranscripts, getWorkspaceInfo } from "../api/client";
import type { TranscriptMeta, WorkspaceInfo } from "../api/types";
import { FileText, Play, Camera, FileAudio, Search } from "lucide-react";
import type { LucideIcon } from "lucide-react";

const PLATFORM_ICON: Record<string, LucideIcon> = {
  youtube: Play,
  instagram: Camera,
  local: FileAudio,
};

const PLATFORM_COLOR: Record<string, string> = {
  youtube: "text-youtube",
  instagram: "text-instagram",
  local: "text-text-muted",
};

export default function HistoryPage() {
  const [transcripts, setTranscripts] = useState<TranscriptMeta[]>([]);
  const [workspace, setWorkspace] = useState<WorkspaceInfo | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getTranscripts(), getWorkspaceInfo()])
      .then(([t, w]) => {
        setTranscripts(t);
        setWorkspace(w);
      })
      .finally(() => setLoading(false));
  }, []);

  const filtered = transcripts.filter(
    (t) =>
      t.title.toLowerCase().includes(search.toLowerCase()) ||
      t.platform.toLowerCase().includes(search.toLowerCase())
  );

  // Group by date
  const grouped = filtered.reduce<Record<string, TranscriptMeta[]>>((acc, t) => {
    const date = t.date || "Unknown";
    if (!acc[date]) acc[date] = [];
    acc[date].push(t);
    return acc;
  }, {});

  return (
    <div className="px-8 py-10 max-w-4xl">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1
            className="text-2xl font-bold tracking-tight text-text"
            style={{ fontFamily: "var(--font-display)" }}
          >
            History
          </h1>
          {workspace && (
            <p className="text-xs text-text-muted font-mono mt-1">
              {workspace.file_count} transcripts · {workspace.total_words.toLocaleString()} words
            </p>
          )}
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search transcripts..."
          className="w-full bg-surface border border-border-subtle rounded-lg pl-9 pr-3 py-2 text-sm text-text placeholder:text-text-muted font-mono outline-none focus:border-amber/40"
        />
      </div>

      {/* Content */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 rounded-lg bg-surface animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16">
          <FileText className="w-8 h-8 text-text-muted mx-auto mb-3" />
          <p className="text-sm text-text-muted">
            {transcripts.length === 0
              ? "No transcriptions yet. Go transcribe something!"
              : "No results match your search."}
          </p>
        </div>
      ) : (
        <div className="space-y-8">
          {Object.entries(grouped).map(([date, items]) => (
            <div key={date}>
              <h3 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-3">
                {date}
              </h3>
              <div className="space-y-1.5">
                {items.map((t) => {
                  const Icon = PLATFORM_ICON[t.platform] || FileText;
                  const color = PLATFORM_COLOR[t.platform] || "text-text-muted";
                  return (
                    <Link
                      key={t.id}
                      to={`/history/${t.id}`}
                      className="
                        flex items-center gap-3 rounded-lg px-3 py-2.5
                        hover:bg-surface-raised transition-colors group
                      "
                    >
                      <Icon className={`w-4 h-4 ${color} shrink-0`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-text truncate group-hover:text-text">
                          {t.title}
                        </p>
                      </div>
                      <span className="text-xs text-text-muted font-mono shrink-0">
                        {t.duration}
                      </span>
                      <span className="text-xs text-text-muted font-mono shrink-0 w-16 text-right">
                        {t.word_count.toLocaleString()}w
                      </span>
                      <span className="text-xs text-text-muted font-mono shrink-0 w-16 text-right">
                        {t.provider}
                      </span>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
