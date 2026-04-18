/** Setup banner — shown on all pages when ffmpeg or provider keys are missing. */

import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Check, Circle, Copy, X, Terminal } from "lucide-react";
import { getHealth, getKeysStatus } from "../api/client";

const POLL_INTERVAL_MS = 30_000;

function detectPlatform(): "macos" | "windows" | "linux" {
  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes("mac")) return "macos";
  if (ua.includes("win")) return "windows";
  return "linux";
}

const FFMPEG_COMMANDS: Record<string, { cmd: string; note?: string }> = {
  macos: { cmd: "brew install ffmpeg" },
  windows: { cmd: "winget install Gyan.FFmpeg" },
  linux: { cmd: "sudo apt install ffmpeg", note: "or your distro's package manager" },
};

export default function SetupBanner() {
  const [loading, setLoading] = useState(true);
  const [dismissed, setDismissed] = useState(false);
  const [ffmpegOk, setFfmpegOk] = useState(true);
  const [hasAnyKey, setHasAnyKey] = useState(true);
  const [copied, setCopied] = useState(false);

  const checkSetup = useCallback(async () => {
    try {
      const [health, keys] = await Promise.all([getHealth(), getKeysStatus()]);
      setFfmpegOk(health.dependencies.ffmpeg && health.dependencies.ffprobe);
      setHasAnyKey(Object.values(keys).some(Boolean));
    } catch {
      // Backend not reachable — don't show banner
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkSetup();
  }, [checkSetup]);

  // Poll while banner is visible
  useEffect(() => {
    if (loading || dismissed || (ffmpegOk && hasAnyKey)) return;
    const id = setInterval(checkSetup, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [loading, dismissed, ffmpegOk, hasAnyKey, checkSetup]);

  // Don't render if setup is complete, loading, or dismissed
  if (loading || dismissed || (ffmpegOk && hasAnyKey)) return null;

  const platform = detectPlatform();
  const ffmpegInfo = FFMPEG_COMMANDS[platform];

  const handleCopy = () => {
    navigator.clipboard.writeText(ffmpegInfo.cmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mx-6 mt-6 rounded-lg border border-amber/30 bg-amber/5 px-5 py-4 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber" />
          <span className="text-sm font-medium text-text">
            Setup needed to start transcribing
          </span>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-text-muted hover:text-text transition-colors cursor-pointer p-0.5"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {/* Step 1: ffmpeg */}
        <div className="flex items-start gap-2.5">
          {ffmpegOk ? (
            <Check className="w-4 h-4 text-green mt-0.5 shrink-0" />
          ) : (
            <Circle className="w-4 h-4 text-amber mt-0.5 shrink-0" />
          )}
          <div className="flex-1 min-w-0">
            <p className={`text-sm ${ffmpegOk ? "text-text-muted line-through" : "text-text"}`}>
              Install ffmpeg
            </p>
            {!ffmpegOk && (
              <div className="mt-1.5 flex items-center gap-2">
                <div className="flex items-center gap-1.5 bg-surface-raised border border-border rounded-md px-2.5 py-1">
                  <Terminal className="w-3 h-3 text-text-muted" />
                  <code className="text-xs font-mono text-text">{ffmpegInfo.cmd}</code>
                </div>
                <button
                  onClick={handleCopy}
                  className="text-text-muted hover:text-text transition-colors cursor-pointer p-1"
                  title="Copy command"
                >
                  {copied ? (
                    <Check className="w-3 h-3 text-green" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )}
                </button>
                {ffmpegInfo.note && (
                  <span className="text-xs text-text-muted">{ffmpegInfo.note}</span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Step 2: Provider key */}
        <div className="flex items-start gap-2.5">
          {hasAnyKey ? (
            <Check className="w-4 h-4 text-green mt-0.5 shrink-0" />
          ) : (
            <Circle className="w-4 h-4 text-amber mt-0.5 shrink-0" />
          )}
          <div>
            <p className={`text-sm ${hasAnyKey ? "text-text-muted line-through" : "text-text"}`}>
              Set up a transcription provider
            </p>
            {!hasAnyKey && (
              <p className="text-xs text-text-muted mt-1">
                Go to{" "}
                <Link to="/settings" className="text-amber hover:underline">
                  Settings → Providers
                </Link>{" "}
                and add an API key
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
