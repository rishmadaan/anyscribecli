import { useState, useEffect } from "react";
import { useJob } from "../hooks/useJob";
import { getConfig } from "../api/client";
import type { Config } from "../api/types";
import URLInput from "../components/URLInput";
import ProgressTracker from "../components/ProgressTracker";
import ResultCard from "../components/ResultCard";
import { ChevronDown, ChevronUp } from "lucide-react";

export default function TranscribePage() {
  const { phase, events, result, error, submit, reset } = useJob();
  const [config, setConfig] = useState<Config | null>(null);
  const [showOptions, setShowOptions] = useState(false);

  // Override fields
  const [provider, setProvider] = useState("");
  const [language, setLanguage] = useState("");
  const [diarize, setDiarize] = useState(false);
  const [keepMedia, setKeepMedia] = useState(false);

  useEffect(() => {
    getConfig().then((c) => {
      setConfig(c);
      setProvider(c.provider);
      setLanguage(c.language);
      setDiarize(c.diarize);
      setKeepMedia(c.keep_media);
    });
  }, []);

  const handleSubmit = (url: string) => {
    submit({ url, provider, language, diarize, keep_media: keepMedia });
  };

  // Extract title from download step completion event
  const downloadedTitle = events
    .filter((e) => e.step === "download" && e.status === "completed")
    .map((e) => e.message.replace(/^(Downloaded|Ready): /, ""))[0];

  return (
    <div className="flex flex-col items-center justify-center min-h-full px-8 py-16">
      {phase === "idle" && (
        <div className="w-full max-w-2xl animate-fade-in">
          {/* Hero */}
          <h1
            className="text-3xl font-bold tracking-tight mb-2 text-text"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Transcribe
          </h1>
          <p className="text-text-secondary text-sm mb-8">
            Paste a YouTube, Instagram, or local file URL to transcribe.
          </p>

          <URLInput onSubmit={handleSubmit} />

          {/* Options accordion */}
          {config && (
            <div className="mt-6 w-full max-w-2xl">
              <button
                onClick={() => setShowOptions(!showOptions)}
                className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors cursor-pointer"
              >
                {showOptions ? (
                  <ChevronUp className="w-3.5 h-3.5" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" />
                )}
                <span className="font-mono">
                  {provider} · {language} · {diarize ? "diarize" : "no diarization"}
                </span>
              </button>

              {showOptions && (
                <div className="mt-3 rounded-lg border border-border-subtle bg-surface p-4 space-y-3 animate-slide-up">
                  <div className="flex items-center gap-4">
                    <label className="text-xs text-text-muted w-20">Provider</label>
                    <select
                      value={provider}
                      onChange={(e) => setProvider(e.target.value)}
                      className="flex-1 bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40"
                    >
                      {["openai", "deepgram", "elevenlabs", "sargam", "openrouter", "local"].map(
                        (p) => (
                          <option key={p} value={p}>{p}</option>
                        )
                      )}
                    </select>
                  </div>

                  <div className="flex items-center gap-4">
                    <label className="text-xs text-text-muted w-20">Language</label>
                    <input
                      type="text"
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      placeholder="auto"
                      className="flex-1 bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40"
                    />
                  </div>

                  <div className="flex items-center gap-4">
                    <label className="text-xs text-text-muted w-20">Diarize</label>
                    <button
                      onClick={() => setDiarize(!diarize)}
                      className={`w-9 h-5 rounded-full transition-colors cursor-pointer ${
                        diarize ? "bg-amber" : "bg-border"
                      }`}
                    >
                      <div
                        className={`w-3.5 h-3.5 rounded-full bg-white transition-transform mx-0.5 ${
                          diarize ? "translate-x-4" : "translate-x-0"
                        }`}
                      />
                    </button>
                  </div>

                  <div className="flex items-center gap-4">
                    <label className="text-xs text-text-muted w-20">Keep media</label>
                    <button
                      onClick={() => setKeepMedia(!keepMedia)}
                      className={`w-9 h-5 rounded-full transition-colors cursor-pointer ${
                        keepMedia ? "bg-amber" : "bg-border"
                      }`}
                    >
                      <div
                        className={`w-3.5 h-3.5 rounded-full bg-white transition-transform mx-0.5 ${
                          keepMedia ? "translate-x-4" : "translate-x-0"
                        }`}
                      />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {phase === "running" && (
        <ProgressTracker events={events} title={downloadedTitle} />
      )}

      {phase === "completed" && result && (
        <ResultCard result={result} onReset={reset} />
      )}

      {phase === "error" && (
        <div className="w-full max-w-2xl animate-slide-up">
          <div className="rounded-lg border border-red/30 bg-red/5 px-4 py-3 mb-4">
            <p className="text-sm text-red font-medium mb-1">Transcription failed</p>
            <p className="text-xs text-text-secondary font-mono">{error}</p>
          </div>
          <button
            onClick={reset}
            className="
              flex items-center justify-center gap-2
              rounded-lg border border-border hover:border-border/80
              bg-surface-raised hover:bg-surface-hover
              px-5 py-2.5 w-full text-sm text-text-secondary hover:text-text
              transition-colors cursor-pointer
            "
          >
            Try again
          </button>
        </div>
      )}
    </div>
  );
}
