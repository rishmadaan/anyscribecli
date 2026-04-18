import { useState, useEffect, useRef } from "react";
import { Link2, Play, Camera, FileAudio, Loader2, FolderOpen } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { uploadFile } from "../api/client";

type Platform = "youtube" | "instagram" | "local" | null;

function detectPlatform(url: string): Platform {
  if (!url) return null;
  if (/youtube\.com|youtu\.be/i.test(url)) return "youtube";
  if (/instagram\.com/i.test(url)) return "instagram";
  if (/^[/~]|^[A-Za-z]:\\/.test(url)) return "local";
  return null;
}

const PLATFORM_BADGE: Record<string, { label: string; color: string; icon: LucideIcon }> = {
  youtube: { label: "YouTube", color: "text-youtube", icon: Play },
  instagram: { label: "Instagram", color: "text-instagram", icon: Camera },
  local: { label: "Local file", color: "text-text-muted", icon: FileAudio },
};

const ACCEPTED_FORMATS = ".mp3,.mp4,.m4a,.wav,.opus,.ogg,.flac,.webm,.aac,.wma";

interface URLInputProps {
  onSubmit: (url: string) => void;
  disabled?: boolean;
}

export default function URLInput({ onSubmit, disabled }: URLInputProps) {
  const [url, setUrl] = useState("");
  const [platform, setPlatform] = useState<Platform>(null);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setPlatform(detectPlatform(url));
  }, [url]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim() && !disabled && !uploading) {
      onSubmit(url.trim());
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const { path } = await uploadFile(file);
      // Submit directly with the server-side path
      onSubmit(path);
    } catch (err) {
      setUrl(`Error: ${err instanceof Error ? err.message : "Upload failed"}`);
    } finally {
      setUploading(false);
      // Reset file input so the same file can be selected again
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const badge = platform ? PLATFORM_BADGE[platform] : null;
  const isDisabled = disabled || uploading;

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl">
      <div
        className={`
          relative flex items-center gap-3 rounded-xl border
          bg-surface px-4 py-3 transition-all
          ${isDisabled
            ? "border-border opacity-60"
            : "border-border-subtle focus-within:border-amber/40 focus-within:shadow-[0_0_0_3px_rgba(240,160,80,0.08)]"
          }
        `}
      >
        <Link2 className="w-4 h-4 text-text-muted shrink-0" />

        <input
          ref={inputRef}
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste a URL or file path..."
          disabled={isDisabled}
          className="
            flex-1 bg-transparent text-text placeholder:text-text-muted
            text-sm outline-none font-mono
          "
        />

        {badge && (
          <span
            className={`flex items-center gap-1.5 text-xs font-medium ${badge.color} shrink-0`}
          >
            <badge.icon className="w-3.5 h-3.5" />
            {badge.label}
          </span>
        )}

        {/* Browse local file */}
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={isDisabled}
          className="
            text-text-muted hover:text-text transition-colors cursor-pointer
            disabled:opacity-50 disabled:cursor-not-allowed shrink-0
            p-0.5 rounded hover:bg-surface-hover
          "
          title="Browse local file"
        >
          {uploading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <FolderOpen className="w-4 h-4" />
          )}
        </button>

        <input
          ref={fileRef}
          type="file"
          accept={ACCEPTED_FORMATS}
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>

      <button
        type="submit"
        disabled={!url.trim() || isDisabled}
        className="
          mt-4 w-full flex items-center justify-center gap-2
          rounded-lg bg-amber/90 hover:bg-amber px-5 py-2.5
          text-sm font-semibold text-bg
          transition-colors disabled:opacity-30 disabled:cursor-not-allowed
          cursor-pointer
        "
      >
        {isDisabled ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            {uploading ? "Uploading..." : "Processing..."}
          </>
        ) : (
          "Transcribe"
        )}
      </button>
    </form>
  );
}
