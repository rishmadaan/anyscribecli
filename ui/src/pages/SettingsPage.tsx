import { useEffect, useState } from "react";
import {
  getConfig,
  updateConfig,
  getProviders,
  testProvider,
  getHealth,
} from "../api/client";
import type { Config, Provider } from "../api/types";
import { Check, AlertCircle, Loader2 } from "lucide-react";

export default function SettingsPage() {
  const [config, setConfig] = useState<Config | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [health, setHealth] = useState<{
    ok: boolean;
    version: string;
    dependencies: Record<string, boolean>;
  } | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({});
  const [testingProvider, setTestingProvider] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getConfig(), getProviders(), getHealth()]).then(([c, p, h]) => {
      setConfig(c);
      setProviders(p);
      setHealth(h);
    });
  }, []);

  const handleSave = async (field: string, value: unknown) => {
    if (!config) return;
    setSaving(true);
    try {
      const updated = await updateConfig({ [field]: value } as Partial<Config>);
      setConfig(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (name: string) => {
    setTestingProvider(name);
    try {
      const result = await testProvider(name);
      setTestResults((prev) => ({ ...prev, [name]: result }));
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

  return (
    <div className="px-8 py-10 max-w-3xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
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

      {/* General */}
      <section className="mb-10">
        <h2 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-4">
          General
        </h2>
        <div className="space-y-4">
          <SettingRow label="Default provider">
            <select
              value={config.provider}
              onChange={(e) => handleSave("provider", e.target.value)}
              disabled={saving}
              className="bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40 w-48"
            >
              {providers.map((p) => (
                <option key={p.name} value={p.name}>{p.name}</option>
              ))}
            </select>
          </SettingRow>

          <SettingRow label="Default language">
            <input
              type="text"
              defaultValue={config.language}
              onBlur={(e) => handleSave("language", e.target.value)}
              className="bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40 w-48"
            />
          </SettingRow>

          <SettingRow label="Output format">
            <div className="flex rounded-md border border-border overflow-hidden">
              {["clean", "timestamped", "diarized"].map((fmt) => (
                <button
                  key={fmt}
                  onClick={() => handleSave("output_format", fmt)}
                  className={`px-3 py-1.5 text-xs font-mono transition-colors cursor-pointer ${
                    config.output_format === fmt
                      ? "bg-amber/15 text-amber border-r border-border"
                      : "bg-surface-raised text-text-muted hover:text-text border-r border-border"
                  }`}
                >
                  {fmt}
                </button>
              ))}
            </div>
          </SettingRow>

          <SettingRow label="Keep media">
            <Toggle
              value={config.keep_media}
              onChange={(v) => handleSave("keep_media", v)}
            />
          </SettingRow>

          <SettingRow label="Diarization">
            <Toggle
              value={config.diarize}
              onChange={(v) => handleSave("diarize", v)}
            />
          </SettingRow>
        </div>
      </section>

      {/* Providers */}
      <section className="mb-10">
        <h2 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-4">
          Providers
        </h2>
        <div className="space-y-2">
          {providers.map((p) => {
            const testResult = testResults[p.name];
            return (
              <div
                key={p.name}
                className="flex items-center gap-3 rounded-lg border border-border-subtle bg-surface px-4 py-3"
              >
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
