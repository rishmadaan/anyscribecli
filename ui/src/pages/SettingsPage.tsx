import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import {
  getConfig,
  updateConfig,
  getProviders,
  testProvider,
  getHealth,
  updateKey,
} from "../api/client";
import type { Config, Provider } from "../api/types";
import LanguageInput from "../components/LanguageInput";
import { Check, AlertCircle, Loader2, ChevronUp, Key } from "lucide-react";

export default function SettingsPage() {
  const location = useLocation();
  const [config, setConfig] = useState<Config | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [health, setHealth] = useState<{
    ok: boolean;
    version: string;
    dependencies: Record<string, boolean>;
  } | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({});
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [expandedProvider, setExpandedProvider] = useState<string | null>(null);
  const [keyInput, setKeyInput] = useState("");
  const [savingKey, setSavingKey] = useState(false);
  const [keySaved, setKeySaved] = useState<string | null>(null);
  const [confirmOverwrite, setConfirmOverwrite] = useState(false);

  useEffect(() => {
    Promise.all([getConfig(), getProviders(), getHealth()]).then(([c, p, h]) => {
      setConfig(c);
      setProviders(p);
      setHealth(h);
    });
  }, []);

  // Deep-link from Transcribe page CTA: /settings#api-keys → scroll into view.
  useEffect(() => {
    if (location.hash !== "#api-keys" || !config) return;
    const el = document.getElementById("api-keys");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [location.hash, config]);

  const handleSave = async (updates: Partial<Config>) => {
    if (!config) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateConfig(updates);
      setConfig(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save setting");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (name: string) => {
    setTestingProvider(name);
    setError(null);
    try {
      const result = await testProvider(name);
      setTestResults((prev) => ({ ...prev, [name]: result }));
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to test ${name}`);
    } finally {
      setTestingProvider(null);
    }
  };

  if (!config) {
    return (
      <div className="px-8 py-10 max-w-3xl">
        <div className="h-8 w-32 bg-surface rounded animate-pulse mb-6" />
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-surface rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const selectedProvider = providers.find((p) => p.name === config.provider);
  const providerMissingKey = selectedProvider && !selectedProvider.has_key && config.provider !== "local";

  return (
    <div className="px-8 py-10 max-w-3xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h1
          className="text-2xl font-bold tracking-tight text-text"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Settings
        </h1>
        {saved && (
          <span className="flex items-center gap-1 text-xs text-green animate-fade-in">
            <Check className="w-3 h-3" />
            Saved
          </span>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="rounded-lg border border-red/30 bg-red/5 px-4 py-2 mb-6 flex items-center justify-between animate-slide-up">
          <p className="text-xs text-red font-mono">{error}</p>
          <button
            onClick={() => setError(null)}
            className="text-red/60 hover:text-red text-xs ml-4 cursor-pointer"
          >
            dismiss
          </button>
        </div>
      )}

      {/* Configure Defaults */}
      <section className="mb-10">
        <h2 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-4">
          Configure Defaults
        </h2>
        <div className="space-y-4">
          <SettingRow label="Default provider">
            <div className="flex items-center gap-2">
              <select
                value={config.provider}
                onChange={(e) => handleSave({ provider: e.target.value })}
                disabled={saving}
                className="bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40 w-48"
              >
                {providers.map((p) => (
                  <option key={p.name} value={p.name}>{p.name}</option>
                ))}
              </select>
              {providerMissingKey && (
                <span className="text-xs text-red flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  no key
                </span>
              )}
            </div>
          </SettingRow>

          <SettingRow label="Default language">
            <LanguageInput
              provider={config.provider}
              value={config.language}
              onChange={(v) => setConfig({ ...config, language: v })}
              onBlur={(v) => {
                if (v !== config.language) handleSave({ language: v });
              }}
              className="bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40 w-48"
            />
          </SettingRow>

          <SettingRow label="Output format">
            <div className="flex rounded-md border border-border overflow-hidden">
              {["clean", "timestamped", "diarized"].map((fmt) => (
                <button
                  key={fmt}
                  onClick={() => {
                    // Match CLI: selecting "diarized" auto-enables diarize.
                    // Selecting other formats does NOT force diarize off.
                    const updates: Partial<Config> = { output_format: fmt };
                    if (fmt === "diarized") {
                      updates.diarize = true;
                    }
                    handleSave(updates);
                  }}
                  className={`px-3 py-1.5 text-xs font-mono transition-colors cursor-pointer ${
                    config.output_format === fmt
                      ? "bg-amber/15 text-amber border-r border-border"
                      : "bg-surface-raised text-text-muted hover:text-text border-r border-border"
                  }`}
                >
                  {fmt === "diarized" ? "with-speaker-labels" : fmt}
                </button>
              ))}
            </div>
          </SettingRow>

          <SettingRow label="Keep media">
            <Toggle
              value={config.keep_media}
              onChange={(v) => handleSave({ keep_media: v })}
            />
          </SettingRow>
        </div>
      </section>

      {/* Providers */}
      <section className="mb-10" id="api-keys">
        <h2 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-4">
          Providers
        </h2>
        <div className="space-y-2">
          {providers.map((p) => {
            const testResult = testResults[p.name];
            const isExpanded = expandedProvider === p.name;
            const isLocal = p.name === "local";
            return (
              <div
                key={p.name}
                className="rounded-lg border border-border-subtle bg-surface overflow-hidden"
              >
                <div className="flex items-center gap-3 px-4 py-3">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      p.has_key ? "bg-green" : "bg-text-muted/40"
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-mono text-text">{p.name}</p>
                    <p className="text-xs text-text-muted truncate">{p.description}</p>
                  </div>
                  <button
                    onClick={() => handleTest(p.name)}
                    disabled={testingProvider === p.name}
                    className="
                      rounded-md border border-border px-2.5 py-1
                      text-xs text-text-muted hover:text-text
                      hover:bg-surface-raised transition-colors cursor-pointer
                      disabled:opacity-50
                    "
                  >
                    {testingProvider === p.name ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      "Test"
                    )}
                  </button>
                  {testResult && (
                    <span className={`text-xs ${testResult.success ? "text-green" : "text-red"}`}>
                      {testResult.success ? (
                        <Check className="w-3.5 h-3.5" />
                      ) : (
                        <AlertCircle className="w-3.5 h-3.5" />
                      )}
                    </span>
                  )}
                  {!isLocal && (
                    <button
                      onClick={() => {
                        if (isExpanded) {
                          setExpandedProvider(null);
                        } else {
                          setExpandedProvider(p.name);
                          setKeyInput("");
                          setKeySaved(null);
                          setConfirmOverwrite(false);
                        }
                      }}
                      className={`rounded-md px-1.5 py-1 transition-colors cursor-pointer ${
                        !p.has_key && !isExpanded
                          ? "text-amber hover:text-amber/80"
                          : "text-text-muted hover:text-text"
                      }`}
                      title={p.has_key ? "Update API key" : "Add API key"}
                    >
                      {isExpanded ? (
                        <ChevronUp className="w-3.5 h-3.5" />
                      ) : !p.has_key ? (
                        <span className="flex items-center gap-1 text-xs font-mono">
                          <Key className="w-3.5 h-3.5" />
                          add key
                        </span>
                      ) : (
                        <Key className="w-3.5 h-3.5" />
                      )}
                    </button>
                  )}
                </div>

                {/* Expandable API key input */}
                {isExpanded && (
                  <div className="px-4 pb-3 pt-0 border-t border-border-subtle">
                    <div className="flex items-center gap-2 mt-3">
                      <input
                        type="password"
                        value={keyInput}
                        onChange={(e) => {
                          setKeyInput(e.target.value);
                          setConfirmOverwrite(false);
                        }}
                        placeholder={p.has_key ? "Enter new key to replace existing" : "Paste API key"}
                        className="flex-1 bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40"
                        autoFocus
                      />
                      <button
                        onClick={async () => {
                          if (!keyInput.trim()) return;
                          if (p.has_key && !confirmOverwrite) {
                            setConfirmOverwrite(true);
                            return;
                          }
                          setSavingKey(true);
                          setConfirmOverwrite(false);
                          setError(null);
                          try {
                            await updateKey(p.name, keyInput.trim());
                            setKeySaved(p.name);
                            setKeyInput("");
                            const updated = await getProviders();
                            setProviders(updated);
                            setTimeout(() => setKeySaved(null), 2000);
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Failed to save key");
                          } finally {
                            setSavingKey(false);
                          }
                        }}
                        disabled={savingKey || !keyInput.trim()}
                        className="
                          rounded-md border border-border px-3 py-1.5
                          text-xs font-mono text-text-muted hover:text-text
                          hover:bg-surface-raised transition-colors cursor-pointer
                          disabled:opacity-50
                        "
                      >
                        {savingKey ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : keySaved === p.name ? (
                          <Check className="w-3 h-3 text-green" />
                        ) : confirmOverwrite ? (
                          "Replace?"
                        ) : (
                          "Save"
                        )}
                      </button>
                    </div>
                    {p.key_url && (
                      <p className="text-xs text-text-muted mt-2">
                        Get your key at{" "}
                        <a
                          href={p.key_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-amber hover:underline"
                        >
                          {p.key_url.replace(/^https?:\/\//, "")}
                        </a>
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* Workspace */}
      <section className="mb-10">
        <h2 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-4">
          Workspace
        </h2>
        <div className="rounded-lg border border-border-subtle bg-surface px-4 py-3">
          <p className="text-xs text-text-muted mb-1">Path</p>
          <p className="text-sm font-mono text-text">
            {config._resolved_workspace || config.workspace_path || "~/anyscribe"}
          </p>
        </div>
      </section>

      {/* System */}
      {health && (
        <section>
          <h2 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-4">
            System
          </h2>
          <div className="rounded-lg border border-border-subtle bg-surface px-4 py-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-muted">Version</span>
              <span className="text-xs font-mono text-text">v{health.version}</span>
            </div>
            {Object.entries(health.dependencies).map(([dep, ok]) => (
              <div key={dep} className="flex items-center justify-between">
                <span className="text-xs text-text-muted">{dep}</span>
                <span className={`text-xs ${ok ? "text-green" : "text-red"}`}>
                  {ok ? <Check className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────

function SettingRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-1">
      <label className="text-sm text-text-secondary">{label}</label>
      {children}
    </div>
  );
}

function Toggle({
  value,
  onChange,
}: {
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      onClick={() => onChange(!value)}
      className={`w-9 h-5 rounded-full transition-colors cursor-pointer ${
        value ? "bg-amber" : "bg-border"
      }`}
    >
      <div
        className={`w-3.5 h-3.5 rounded-full bg-white transition-transform mx-0.5 ${
          value ? "translate-x-4" : "translate-x-0"
        }`}
      />
    </button>
  );
}
