import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useJob } from "../hooks/useJob";
import { getConfig, getProviders } from "../api/client";
import type { Config, Provider } from "../api/types";
import URLInput from "../components/URLInput";
import ProgressTracker from "../components/ProgressTracker";
import ResultCard from "../components/ResultCard";
import LanguageInput from "../components/LanguageInput";
import ModelInput from "../components/ModelInput";
import { defaultModelFor, hasModelChoice } from "../api/models";
import { ChevronDown, ChevronUp } from "lucide-react";

// User-facing label for the diarize/diarized output format. The wire value
// stays "diarized" so the API contract doesn't change.
const formatLabel = (fmt: string) => (fmt === "diarized" ? "with-speaker-labels" : fmt);

export default function TranscribePage() {
  const { phase, events, result, error, submit, cancel, reset } = useJob();
  const [config, setConfig] = useState<Config | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [showOptions, setShowOptions] = useState(false);
  const [lastUrl, setLastUrl] = useState(""); // retained for retry / re-transcribe

  // Override fields
  const [quality, setQuality] = useState("balanced");
  const [provider, setProvider] = useState(""); // "" = auto (resolved from quality)
  const [model, setModel] = useState(""); // per-run model override; only when provider is explicit
  const [language, setLanguage] = useState("");
  const [diarize, setDiarize] = useState(false);
  const [keepMedia, setKeepMedia] = useState(false);
  const [outputFormat, setOutputFormat] = useState("clean");

  useEffect(() => {
    Promise.all([getConfig(), getProviders()]).then(([c, p]) => {
      setConfig(c);
      setProviders(p);
      setQuality(c.quality || "balanced");
      setProvider(""); // default to auto — quality drives the provider
      setLanguage(c.language);
      setDiarize(c.diarize);
      setKeepMedia(c.keep_media);
      setOutputFormat(c.output_format);
    });
  }, []);

  // undefined while provider is "" (auto) → no model control, no model sent.
  const selectedProvider = providers.find((p) => p.name === provider);

  const handleSubmit = (url: string, force = false) => {
    setLastUrl(url);
    // Send quality; only send provider when the user explicitly overrode "auto".
    submit({
      url,
      quality,
      provider: provider || undefined,
      // Model only travels with an explicit provider — on auto it's ambiguous.
      model: provider && model ? model : undefined,
      language,
      diarize,
      keep_media: keepMedia,
      output_format: outputFormat,
      force,
    });
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
                  {quality}{provider ? ` · ${provider}` : ""}{provider && model ? ` · ${model}` : ""} · {language} · {formatLabel(outputFormat)}{diarize && outputFormat !== "diarized" ? " + speakers" : ""}
                </span>
              </button>

              {showOptions && (
                <div className="mt-3 rounded-lg border border-border-subtle bg-surface p-4 space-y-3 animate-slide-up">
                  <div className="flex items-center gap-4">
                    <label className="text-xs text-text-muted w-32 shrink-0">Quality</label>
                    <div className="flex rounded-md border border-border overflow-hidden">
                      {["accuracy", "balanced", "cost", "free"].map((q) => (
                        <button
                          key={q}
                          onClick={() => setQuality(q)}
                          className={`px-3 py-1.5 text-xs font-mono transition-colors cursor-pointer ${
                            quality === q
                              ? "bg-amber/15 text-amber border-r border-border"
                              : "bg-surface-raised text-text-muted hover:text-text border-r border-border"
                          }`}
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <label className="text-xs text-text-muted w-32 shrink-0">Provider</label>
                    <select
                      value={provider}
                      onChange={(e) => {
                        const name = e.target.value;
                        setProvider(name);
                        setModel(
                          defaultModelFor(
                            providers.find((p) => p.name === name),
                            config.provider_models
                          )
                        );
                      }}
                      className="flex-1 bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40"
                    >
                      <option value="">auto · from quality</option>
                      {providers.map((p) => (
                        <option key={p.name} value={p.name} disabled={!p.has_key}>
                          {p.name}{p.has_key ? "" : " · needs key"}
                        </option>
                      ))}
                    </select>
                  </div>

                  {hasModelChoice(selectedProvider) && (
                    <div className="flex items-center gap-4">
                      <label className="text-xs text-text-muted w-32 shrink-0">Model</label>
                      <ModelInput
                        provider={selectedProvider}
                        value={model}
                        onChange={setModel}
                      />
                    </div>
                  )}

                  {(() => {
                    const missing = providers.filter((p) => !p.has_key).length;
                    if (missing === 0) return null;
                    return (
                      <div className="flex items-center gap-4">
                        <span className="w-32 shrink-0" />
                        <p className="text-xs text-text-muted">
                          {missing} {missing === 1 ? "provider needs" : "providers need"} a key —{" "}
                          <Link to="/settings#api-keys" className="text-amber hover:underline">
                            Settings
                          </Link>
                        </p>
                      </div>
                    );
                  })()}

                  <div className="flex items-center gap-4">
                    <label className="text-xs text-text-muted w-32 shrink-0">Language</label>
                    <LanguageInput
                      provider={provider}
                      value={language}
                      onChange={setLanguage}
                    />
                  </div>

                  <div className="flex items-center gap-4">
                    <label className="text-xs text-text-muted w-32 shrink-0">Format</label>
                    <div className="flex rounded-md border border-border overflow-hidden">
                      {["clean", "timestamped", "diarized"].map((fmt) => (
                        <button
                          key={fmt}
                          onClick={() => {
                            setOutputFormat(fmt);
                            if (fmt === "diarized") setDiarize(true);
                          }}
                          className={`px-3 py-1.5 text-xs font-mono transition-colors cursor-pointer ${
                            outputFormat === fmt
                              ? "bg-amber/15 text-amber border-r border-border"
                              : "bg-surface-raised text-text-muted hover:text-text border-r border-border"
                          }`}
                        >
                          {formatLabel(fmt)}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <label className="text-xs text-text-muted w-32 shrink-0">Multi-speaker</label>
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
                    <label className="text-xs text-text-muted w-32 shrink-0">Keep media</label>
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
        <div className="w-full max-w-2xl flex flex-col items-center">
          <ProgressTracker events={events} title={downloadedTitle} />
          <button
            onClick={cancel}
            className="
              mt-6 self-start
              flex items-center justify-center gap-2
              rounded-lg border border-border hover:border-red/40
              bg-surface-raised hover:bg-red/5
              px-4 py-2 text-sm text-text-secondary hover:text-red
              transition-colors cursor-pointer
            "
          >
            Stop
          </button>
        </div>
      )}

      {phase === "completed" && result && result.cached && (
        <div className="w-full max-w-2xl animate-slide-up">
          <div className="rounded-lg border border-amber/30 bg-amber/5 px-4 py-3 mb-4">
            <p className="text-sm text-amber font-medium mb-1">Already transcribed</p>
            <p className="text-xs text-text-secondary mb-2">
              This source is already in your vault.
            </p>
            <Link
              to={`/history/${result.file_path.split("/").pop()?.replace(/\.md$/, "")}`}
              className="text-xs text-amber hover:underline font-mono break-all"
            >
              {result.file_path}
            </Link>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => handleSubmit(lastUrl, true)}
              className="
                flex-1 flex items-center justify-center gap-2
                rounded-lg bg-amber/90 hover:bg-amber px-5 py-2.5
                text-sm font-semibold text-bg transition-colors cursor-pointer
              "
            >
              Re-transcribe
            </button>
            <button
              onClick={reset}
              className="
                flex items-center justify-center gap-2
                rounded-lg border border-border hover:border-border/80
                bg-surface-raised hover:bg-surface-hover
                px-5 py-2.5 text-sm text-text-secondary hover:text-text
                transition-colors cursor-pointer
              "
            >
              Done
            </button>
          </div>
        </div>
      )}

      {phase === "completed" && result && !result.cached && (
        <ResultCard result={result} onReset={reset} />
      )}

      {phase === "cancelled" && (
        <div className="w-full max-w-2xl animate-slide-up">
          <div className="rounded-lg border border-border bg-surface px-4 py-3 mb-4">
            <p className="text-sm text-text font-medium mb-1">Transcription cancelled</p>
            <p className="text-xs text-text-secondary">You stopped this job.</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => handleSubmit(lastUrl)}
              className="
                flex-1 flex items-center justify-center gap-2
                rounded-lg bg-amber/90 hover:bg-amber px-5 py-2.5
                text-sm font-semibold text-bg transition-colors cursor-pointer
              "
            >
              Try again
            </button>
            <button
              onClick={reset}
              className="
                flex items-center justify-center gap-2
                rounded-lg border border-border hover:border-border/80
                bg-surface-raised hover:bg-surface-hover
                px-5 py-2.5 text-sm text-text-secondary hover:text-text
                transition-colors cursor-pointer
              "
            >
              New
            </button>
          </div>
        </div>
      )}

      {phase === "error" && (
        <div className="w-full max-w-2xl animate-slide-up">
          <div className="rounded-lg border border-red/30 bg-red/5 px-4 py-3 mb-4">
            <p className="text-sm text-red font-medium mb-1">Transcription failed</p>
            <p className="text-xs text-text-secondary font-mono">{error}</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => lastUrl && handleSubmit(lastUrl)}
              className="
                flex-1 flex items-center justify-center gap-2
                rounded-lg bg-amber/90 hover:bg-amber px-5 py-2.5
                text-sm font-semibold text-bg transition-colors cursor-pointer
              "
            >
              Try again
            </button>
            <button
              onClick={reset}
              className="
                flex items-center justify-center gap-2
                rounded-lg border border-border hover:border-border/80
                bg-surface-raised hover:bg-surface-hover
                px-5 py-2.5 text-sm text-text-secondary hover:text-text
                transition-colors cursor-pointer
              "
            >
              New
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
