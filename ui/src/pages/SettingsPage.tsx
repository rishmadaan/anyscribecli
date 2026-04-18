import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import {
  getConfig,
  updateConfig,
  getProviders,
  testProvider,
  getHealth,
  updateKey,
  getLocalStatus,
  pullLocalModel,
  deleteLocalModel,
  reinstallLocalModel,
  teardownLocal,
} from "../api/client";
import type {
  Config,
  Provider,
  ProviderTestResult,
  LocalStatusResponse,
} from "../api/types";
import LanguageInput from "../components/LanguageInput";
import LocalSetupModal from "../components/LocalSetupModal";
import {
  Check,
  AlertCircle,
  Loader2,
  ChevronUp,
  ChevronDown,
  Key,
  Sparkles,
  Download,
  Trash2,
  RefreshCw,
  PlayCircle,
} from "lucide-react";

const MB = 1024 * 1024;

export default function SettingsPage() {
  const location = useLocation();
  const [config, setConfig] = useState<Config | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [health, setHealth] = useState<{
    ok: boolean;
    version: string;
    dependencies: Record<string, boolean>;
  } | null>(null);
  const [localStatus, setLocalStatus] = useState<LocalStatusResponse | null>(
    null
  );
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<
    Record<string, ProviderTestResult>
  >({});
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [expandedProvider, setExpandedProvider] = useState<string | null>(null);
  const [keyInput, setKeyInput] = useState("");
  const [savingKey, setSavingKey] = useState(false);
  const [keySaved, setKeySaved] = useState<string | null>(null);
  const [confirmOverwrite, setConfirmOverwrite] = useState(false);
  const [showSetupModal, setShowSetupModal] = useState(false);
  const [pullingSize, setPullingSize] = useState<string | null>(null);
  const [deletingSize, setDeletingSize] = useState<string | null>(null);
  const [reinstallingSize, setReinstallingSize] = useState<string | null>(null);
  const [confirmTeardown, setConfirmTeardown] = useState(false);
  const [tearingDown, setTearingDown] = useState(false);

  const refreshAll = async () => {
    const [c, p, h, l] = await Promise.all([
      getConfig(),
      getProviders(),
      getHealth(),
      getLocalStatus(),
    ]);
    setConfig(c);
    setProviders(p);
    setHealth(h);
    setLocalStatus(l);
  };

  useEffect(() => {
    refreshAll();
  }, []);

  // Deep-link from Transcribe page CTA.
  useEffect(() => {
    if (location.hash !== "#api-keys" || !config) return;
    const el = document.getElementById("api-keys");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [location.hash, config]);

  // Poll local status while any long-running local operation is in flight.
  // Now includes queued downloads (not just the running one).
  useEffect(() => {
    const anyQueueActivity = (localStatus?.models || []).some(
      (m) => m.downloading || m.queued
    );
    if (
      !pullingSize &&
      !deletingSize &&
      !reinstallingSize &&
      !localStatus?.setup_running &&
      !anyQueueActivity
    )
      return;
    const id = setInterval(async () => {
      try {
        const [l, p] = await Promise.all([getLocalStatus(), getProviders()]);
        setLocalStatus(l);
        setProviders(p);
        if (pullingSize) {
          const entry = l.models.find((m) => m.size === pullingSize);
          if (entry?.cached) setPullingSize(null);
        }
      } catch {
        // transient
      }
    }, 1500);
    return () => clearInterval(id);
  }, [
    pullingSize,
    deletingSize,
    reinstallingSize,
    localStatus?.setup_running,
    localStatus?.models,
  ]);

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

  const handlePull = async (size: string) => {
    setPullingSize(size);
    setError(null);
    try {
      await pullLocalModel(size);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to download ${size}`);
      setPullingSize(null);
    }
  };

  const handleDelete = async (size: string) => {
    setDeletingSize(size);
    setError(null);
    try {
      await deleteLocalModel(size);
      const l = await getLocalStatus();
      setLocalStatus(l);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to delete ${size}`);
    } finally {
      setDeletingSize(null);
    }
  };

  const handleReinstall = async (size: string) => {
    setReinstallingSize(size);
    setError(null);
    try {
      await reinstallLocalModel(size);
      const l = await getLocalStatus();
      setLocalStatus(l);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to reinstall ${size}`);
    } finally {
      setReinstallingSize(null);
    }
  };

  const handleTeardown = async () => {
    setTearingDown(true);
    setError(null);
    try {
      await teardownLocal();
      await refreshAll();
      setConfirmTeardown(false);
      setExpandedProvider(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove local");
    } finally {
      setTearingDown(false);
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
  const providerMissingKey = selectedProvider && !selectedProvider.has_key;

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
        <div className="flex items-center gap-3">
          {saved && (
            <span className="flex items-center gap-1 text-xs text-green animate-fade-in">
              <Check className="w-3 h-3" />
              Saved
            </span>
          )}
          <button
            onClick={() => {
              const w = window as unknown as { openOnboarding?: () => void };
              w.openOnboarding?.();
            }}
            className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer"
            title="Re-run the onboarding wizard"
          >
            <PlayCircle className="w-3 h-3" />
            Run setup wizard
          </button>
        </div>
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
                  <option key={p.name} value={p.name}>
                    {p.name}
                  </option>
                ))}
              </select>
              {providerMissingKey && (
                <span className="text-xs text-red flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  {config.provider === "local" ? "not set up" : "no key"}
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
                    const updates: Partial<Config> = { output_format: fmt };
                    if (fmt === "diarized") updates.diarize = true;
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

            if (isLocal) {
              return (
                <LocalProviderCard
                  key={p.name}
                  provider={p}
                  status={localStatus}
                  isExpanded={isExpanded}
                  testResult={testResult}
                  testing={testingProvider === p.name}
                  pullingSize={pullingSize}
                  deletingSize={deletingSize}
                  reinstallingSize={reinstallingSize}
                  config={config}
                  onToggleExpand={() =>
                    setExpandedProvider(isExpanded ? null : p.name)
                  }
                  onTest={() => handleTest(p.name)}
                  onOpenSetup={() => setShowSetupModal(true)}
                  onPull={handlePull}
                  onDelete={handleDelete}
                  onReinstall={handleReinstall}
                  onDefaultChange={(size) =>
                    handleSave({ local_model: size })
                  }
                  confirmTeardown={confirmTeardown}
                  onTeardownRequest={() => setConfirmTeardown(true)}
                  onTeardownConfirm={handleTeardown}
                  onTeardownCancel={() => setConfirmTeardown(false)}
                  tearingDown={tearingDown}
                />
              );
            }

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
                    <p className="text-xs text-text-muted truncate">
                      {p.description}
                    </p>
                  </div>
                  <button
                    onClick={() => handleTest(p.name)}
                    disabled={testingProvider === p.name}
                    className="rounded-md border border-border px-2.5 py-1 text-xs text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50"
                  >
                    {testingProvider === p.name ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      "Test"
                    )}
                  </button>
                  {testResult && (
                    <span
                      className={`text-xs ${
                        testResult.success ? "text-green" : "text-red"
                      }`}
                    >
                      {testResult.success ? (
                        <Check className="w-3.5 h-3.5" />
                      ) : (
                        <AlertCircle className="w-3.5 h-3.5" />
                      )}
                    </span>
                  )}
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
                </div>

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
                        placeholder={
                          p.has_key
                            ? "Enter new key to replace existing"
                            : "Paste API key"
                        }
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
                            setError(
                              err instanceof Error
                                ? err.message
                                : "Failed to save key"
                            );
                          } finally {
                            setSavingKey(false);
                          }
                        }}
                        disabled={savingKey || !keyInput.trim()}
                        className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50"
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
                  {ok ? (
                    <Check className="w-3 h-3" />
                  ) : (
                    <AlertCircle className="w-3 h-3" />
                  )}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {showSetupModal && (
        <LocalSetupModal
          onClose={() => setShowSetupModal(false)}
          onDone={async () => {
            setShowSetupModal(false);
            await refreshAll();
          }}
        />
      )}
    </div>
  );
}

// ── Local provider card ─────────────────────────────

function LocalProviderCard({
  provider,
  status,
  isExpanded,
  testResult,
  testing,
  pullingSize,
  deletingSize,
  reinstallingSize,
  config,
  onToggleExpand,
  onTest,
  onOpenSetup,
  onPull,
  onDelete,
  onReinstall,
  onDefaultChange,
  confirmTeardown,
  onTeardownRequest,
  onTeardownConfirm,
  onTeardownCancel,
  tearingDown,
}: {
  provider: Provider;
  status: LocalStatusResponse | null;
  isExpanded: boolean;
  testResult?: ProviderTestResult;
  testing: boolean;
  pullingSize: string | null;
  deletingSize: string | null;
  reinstallingSize: string | null;
  config: Config;
  onToggleExpand: () => void;
  onTest: () => void;
  onOpenSetup: () => void;
  onPull: (size: string) => void;
  onDelete: (size: string) => void;
  onReinstall: (size: string) => void;
  onDefaultChange: (size: string) => void;
  confirmTeardown: boolean;
  onTeardownRequest: () => void;
  onTeardownConfirm: () => void;
  onTeardownCancel: () => void;
  tearingDown: boolean;
}) {
  const setUp = provider.set_up;

  return (
    <div className="rounded-lg border border-border-subtle bg-surface overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-3">
        {setUp ? (
          <div className="w-2 h-2 rounded-full bg-green" />
        ) : (
          <Sparkles className="w-3.5 h-3.5 text-amber" />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-mono text-text">{provider.name}</p>
          <p className="text-xs text-text-muted truncate">
            {provider.description}
          </p>
        </div>
        {/* Always show Diagnose — runs the same structured test; pre-setup
            it surfaces which piece is missing without requiring setup. */}
        <button
          onClick={onTest}
          disabled={testing}
          className="rounded-md border border-border px-2.5 py-1 text-xs text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50"
          title={setUp ? "Run diagnostics" : "Diagnose missing dependencies"}
        >
          {testing ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : setUp ? (
            "Test"
          ) : (
            "Diagnose"
          )}
        </button>
        {testResult && (
          <span
            className={`text-xs ${
              testResult.success ? "text-green" : "text-red"
            }`}
            title={testResult.message}
          >
            {testResult.success ? (
              <Check className="w-3.5 h-3.5" />
            ) : (
              <AlertCircle className="w-3.5 h-3.5" />
            )}
          </span>
        )}
        {!setUp ? (
          <button
            onClick={onOpenSetup}
            className="rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-mono hover:bg-amber/80 transition-colors cursor-pointer"
          >
            Set up local transcription
          </button>
        ) : (
          <button
            onClick={onToggleExpand}
            className="rounded-md px-1.5 py-1 text-text-muted hover:text-text transition-colors cursor-pointer"
            title={isExpanded ? "Hide models" : "Manage models"}
          >
            {isExpanded ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>
        )}
      </div>

      {/* Structured test-result sub-checks — rendered whether or not local is
          set up; pre-setup it surfaces which piece is missing. */}
      {testResult?.checks && (
        <div className="px-4 pb-3 pt-0 border-t border-border-subtle">
          <div className="mt-3 space-y-1">
            {(
              [
                ["faster-whisper", testResult.checks.faster_whisper],
                ["ffmpeg", testResult.checks.ffmpeg],
                [
                  `model: ${testResult.checks.model_cached.size ?? ""}`,
                  testResult.checks.model_cached,
                ],
              ] as const
            ).map(([label, c]) => (
              <div
                key={label}
                className="flex items-center gap-2 text-xs font-mono"
              >
                {c.ok ? (
                  <Check className="w-3 h-3 text-green shrink-0" />
                ) : (
                  <AlertCircle className="w-3 h-3 text-red shrink-0" />
                )}
                <span className="text-text-muted">{label}</span>
                <span className={c.ok ? "text-text" : "text-red"}>
                  {c.message}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Expanded: default-model picker, models table, teardown. */}
      {isExpanded && setUp && status && (
        <div className="px-4 pb-4 pt-0 border-t border-border-subtle">
          {/* Default-model picker: pill strip with download-in-place for
              uncached sizes. Cached pills act like radio buttons; uncached
              ones trigger onPull and update the dropdown state automatically
              once the queue completes. */}
          <div className="mt-3 mb-4">
            <div className="flex items-center gap-2 flex-wrap">
              <label className="text-xs font-mono text-text-muted">
                Default model
              </label>
              <div className="flex items-center gap-1 flex-wrap">
                {status.models.map((m) => {
                  const selected = config.local_model === m.size;
                  const isPulling = pullingSize === m.size;
                  const isDownloading = !!m.downloading || isPulling;
                  const isQueued = !!m.queued;
                  if (m.cached) {
                    return (
                      <button
                        key={m.size}
                        onClick={() => onDefaultChange(m.size)}
                        aria-pressed={selected}
                        className={`rounded-md px-2.5 py-1 text-xs font-mono border transition-colors cursor-pointer ${
                          selected
                            ? "border-amber bg-amber/15 text-amber"
                            : "border-border text-text-muted hover:text-text hover:bg-surface-raised"
                        }`}
                        title={`Use ${m.size} as the default model`}
                      >
                        {m.size}
                      </button>
                    );
                  }
                  return (
                    <button
                      key={m.size}
                      onClick={() => onPull(m.size)}
                      disabled={isDownloading || isQueued}
                      className="rounded-md px-2 py-1 text-xs font-mono border border-border-subtle border-dashed text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                      title={
                        isDownloading
                          ? "Downloading…"
                          : isQueued
                          ? "Queued"
                          : `Download ${m.size} (~${m.spec.download_mb} MB) to enable as default`
                      }
                    >
                      {isDownloading ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : isQueued ? null : (
                        <Download className="w-3 h-3" />
                      )}
                      <span>
                        {m.size}
                        {isQueued && " (queued)"}
                      </span>
                    </button>
                  );
                })}
              </div>
              <span className="ml-auto text-xs text-text-muted font-mono">
                {Math.round(status.total_disk_bytes / MB)} MB on disk
              </span>
            </div>
          </div>

          <div className="rounded-md border border-border-subtle bg-surface-raised overflow-hidden">
            {status.models.map((m, i) => {
              const isPulling = pullingSize === m.size;
              const isDeleting = deletingSize === m.size;
              const isReinstalling = reinstallingSize === m.size;
              const isDownloading = !!m.downloading || isPulling;
              const isQueued = !!m.queued;
              return (
                <div
                  key={m.size}
                  className={`flex items-center gap-3 px-3 py-2 ${
                    i > 0 ? "border-t border-border-subtle" : ""
                  }`}
                >
                  <span className="text-xs font-mono text-text w-20">
                    {m.size}
                  </span>
                  <span className="text-[10px] font-mono text-text-muted w-20">
                    {m.cached ? `${Math.round(m.bytes / MB)} MB` : "—"}
                  </span>
                  <span className="text-[10px] text-text-muted flex-1 truncate">
                    {m.spec.quality}
                    {isQueued && (
                      <span className="ml-2 text-[9px] font-mono text-amber bg-amber/10 border border-amber/30 rounded px-1 py-0.5">
                        queued #{m.queue_position ?? "?"}
                      </span>
                    )}
                  </span>
                  {m.cached ? (
                    <>
                      <button
                        onClick={() => onReinstall(m.size)}
                        disabled={isReinstalling || isDownloading}
                        className="rounded-md border border-border px-2 py-1 text-[11px] font-mono text-text-muted hover:text-text hover:bg-surface transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
                        title="Delete and re-download (for corrupted weights)"
                      >
                        {isReinstalling ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <RefreshCw className="w-3 h-3" />
                        )}
                      </button>
                      <button
                        onClick={() => onDelete(m.size)}
                        disabled={
                          isDeleting ||
                          isReinstalling ||
                          (config.local_model === m.size &&
                            status.models.filter((x) => x.cached).length === 1)
                        }
                        className="rounded-md border border-border px-2 py-1 text-[11px] font-mono text-text-muted hover:text-red hover:border-red/30 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
                        title={
                          config.local_model === m.size &&
                          status.models.filter((x) => x.cached).length === 1
                            ? "can't delete the only cached model while it's the default"
                            : "Delete from cache"
                        }
                      >
                        {isDeleting ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Trash2 className="w-3 h-3" />
                        )}
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => onPull(m.size)}
                      disabled={isDownloading || isQueued}
                      className="rounded-md border border-border px-2 py-1 text-[11px] font-mono text-text-muted hover:text-text hover:bg-surface transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
                    >
                      {isDownloading ? (
                        <>
                          <Loader2 className="w-3 h-3 animate-spin" />
                          downloading
                        </>
                      ) : isQueued ? (
                        <>queued</>
                      ) : (
                        <>
                          <Download className="w-3 h-3" />
                          ~{m.spec.download_mb} MB
                        </>
                      )}
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          <div className="mt-4 flex items-center justify-end gap-2">
            {!confirmTeardown ? (
              <button
                onClick={onTeardownRequest}
                className="text-xs text-text-muted hover:text-red transition-colors cursor-pointer font-mono"
              >
                Remove local transcription
              </button>
            ) : (
              <>
                <span className="text-xs text-text-muted font-mono">
                  Uninstall faster-whisper and delete all models?
                </span>
                <button
                  onClick={onTeardownCancel}
                  className="rounded-md border border-border px-2 py-1 text-xs font-mono text-text-muted hover:text-text transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={onTeardownConfirm}
                  disabled={tearingDown}
                  className="rounded-md border border-red/30 bg-red/5 px-2 py-1 text-xs font-mono text-red hover:bg-red/10 transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1"
                >
                  {tearingDown ? (
                    <>
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Removing…
                    </>
                  ) : (
                    "Confirm remove"
                  )}
                </button>
              </>
            )}
          </div>
        </div>
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
