import { useState, useEffect, useRef } from "react";
import { Link2, Play, Camera, FileAudio, Loader2 } from "lucide-react";
import type { LucideIcon } from "lucide-react";

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

interface URLInputProps {
  onSubmit: (url: string) => void;
  disabled?: boolean;
}

export default function URLInput({ onSubmit, disabled }: URLInputProps) {
  const [url, setUrl] = useState("");
  const [platform, setPlatform] = useState<Platform>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setPlatform(detectPlatform(url));
  }, [url]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim() && !disabled) {
      onSubmit(url.trim());
    }
  };

  const badge = platform ? PLATFORM_BADGE[platform] : null;

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl">
      <div
        className={`
          relative flex items-center gap-3 rounded-xl border
          bg-surface px-4 py-3 transition-all
          ${disabled
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
          disabled={disabled}
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
      </div>

      <button
        type="submit"
        disabled={!url.trim() || disabled}
        className="
          mt-4 w-full flex items-center justify-center gap-2
          rounded-lg bg-amber/90 hover:bg-amber px-5 py-2.5
          text-sm font-semibold text-bg
          transition-colors disabled:opacity-30 disabled:cursor-not-allowed
          cursor-pointer
        "
      >
        {disabled ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Processing...
          </>
        ) : (
          "Transcribe"
        )}
      </button>
    </form>
  );
}
