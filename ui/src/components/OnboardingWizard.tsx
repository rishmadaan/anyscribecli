/** First-run onboarding wizard for the Web UI.
 *
 * Full-screen modal that walks the user through the minimum required to start
 * transcribing: pick a provider, hand over a key (or set up local), point at
 * a workspace, done. Advanced preferences (language default, output format,
 * Instagram, etc.) are NOT in the wizard — they default to sane values and
 * users tweak them in Settings later.
 *
 * The wizard writes to the backend exactly once, at the final Done step,
 * calling ``POST /api/onboarding/save`` which fans out to config + keys. The
 * one exception is offline opt-in: if the user says yes to local, that step
 * kicks off ``POST /api/local/setup`` inline and polls until the download
 * finishes — because that work can take minutes and shouldn't block the final
 * Done click.
 *
 * Trigger: App.tsx mounts this whenever ``GET /api/onboarding/status`` reports
 * ``completed: false`` AND localStorage flag ``scribe_onboarding_dismissed``
 * isn't set. Settings has a button to re-open it manually.
 */

import { useEffect, useRef, useState } from "react";
import { Check, Loader2, AlertCircle, ChevronRight, ChevronLeft, Sparkles, X } from "lucide-react";
import Modal from "./Modal";
import {
  getOnboardingStatus,
  saveOnboarding,
  testProvider,
  setupLocal,
  getLocalStatus,
  getSetupLog,
} from "../api/client";
import type { LocalModelEntry, LocalStatusResponse } from "../api/types";

// Keep these in lock-step with backend ``onboard_headless.PROVIDER_KEY_ENV``.
const API_PROVIDERS = [
  { name: "openai", label: "OpenAI Whisper", description: "General purpose, multilingual, segment timestamps", env: "OPENAI_API_KEY", url: "https://platform.openai.com/api-keys" },
  { name: "deepgram", label: "Deepgram", description: "Fast, accurate, native diarization + Hindi Latin", env: "DEEPGRAM_API_KEY", url: "https://console.deepgram.com/" },
  { name: "elevenlabs", label: "ElevenLabs Scribe", description: "High accuracy, 99 languages, word-level timestamps", env: "ELEVENLABS_API_KEY", url: "https://elevenlabs.io/app/settings/api-keys" },
  { name: "sargam", label: "Sarvam AI", description: "Optimized for Indic languages", env: "SARGAM_API_KEY", url: "https://dashboard.sarvam.ai" },
  { name: "openrouter", label: "OpenRouter", description: "Access various models via unified API", env: "OPENROUTER_API_KEY", url: "https://openrouter.ai/keys" },
];

type Step =
  | "welcome"
  | "provider"
  | "api_key"
  | "offline_opt_in"
  | "workspace"
  | "done";

type FormState = {
  provider: string | null;
  apiKey: string;
  workspace: string;
  enableLocal: boolean;
  localModel: string | null;
};

interface Props {
  onClose: () => void;
}

export default function OnboardingWizard({ onClose }: Props) {
  const [step, setStep] = useState<Step>("welcome");
  const [form, setForm] = useState<FormState>({
    provider: null,
    apiKey: "",
    workspace: "",
    enableLocal: false,
    localModel: null,
  });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [defaultWorkspace, setDefaultWorkspace] = useState("");

  // Preload the default workspace so StepWorkspace can show it as a hint.
  useEffect(() => {
    getOnboardingStatus()
      .then(() => {
        // The status endpoint doesn't return the default path directly; we
        // derive it from /api/config which always returns _resolved_workspace.
        return fetch("/api/config")
          .then((r) => r.json())
          .then((c) => setDefaultWorkspace(c._resolved_workspace || ""));
      })
      .catch(() => {
        // non-critical
      });
  }, []);

  // Dismissing (Skip for now) sets the localStorage flag so we don't pop the
  // wizard again next page load.
  const dismiss = (persist: boolean) => {
    if (persist) {
      try {
        localStorage.setItem("scribe_onboarding_dismissed", "1");
      } catch {
        // private mode / storage disabled — not fatal
      }
    }
    onClose();
  };

  const branchFromProvider = (provider: string) => {
    setForm((f) => ({ ...f, provider }));
    if (provider === "local") {
      // Local path: jump straight into model setup (no API key step). The
      // offline_opt_in step handles the size picker + setup trigger.
      setForm((f) => ({ ...f, enableLocal: true }));
      setStep("offline_opt_in");
    } else {
      setStep("api_key");
    }
  };

  const finish = async () => {
    if (!form.provider) return;
    setSaving(true);
    setSaveError(null);
    try {
      await saveOnboarding({
        provider: form.provider,
        api_key: form.provider !== "local" ? form.apiKey || undefined : undefined,
        workspace: form.workspace || undefined,
        local_model:
          form.provider === "local"
            ? form.localModel || undefined
            : undefined,
      });
      dismiss(true);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Failed to save onboarding");
    } finally {
      setSaving(false);
    }
  };

  const stepIndex = STEPS.indexOf(step);
  const totalSteps = STEPS.length - 1; // welcome doesn't count

  return (
    <Modal
      onClose={() => dismiss(false)}
      disableClose={saving}
      ariaLabelledBy="onboarding-title"
      size="xl"
    >
      {/* Header: title + progress + skip */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2
            id="onboarding-title"
            className="text-lg font-bold text-text"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {stepTitle(step)}
          </h2>
          {step !== "welcome" && step !== "done" && (
            <p className="text-[10px] font-mono text-text-muted mt-0.5">
              Step {stepIndex} of {totalSteps}
            </p>
          )}
        </div>
        {step !== "done" && !saving && (
          <button
            onClick={() => dismiss(true)}
            className="flex items-center gap-1 text-xs font-mono text-text-muted hover:text-text transition-colors cursor-pointer"
            aria-label="Skip onboarding"
          >
            Skip for now
            <X className="w-3 h-3" />
          </button>
        )}
      </div>

      {/* Error banner at wizard level (save failures land here) */}
      {saveError && (
        <div className="rounded-md border border-red/30 bg-red/5 px-3 py-2 mb-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red mt-0.5 shrink-0" />
            <p className="text-xs text-red font-mono break-words">{saveError}</p>
          </div>
        </div>
      )}

      {/* Step body */}
      {step === "welcome" && (
        <StepWelcome onNext={() => setStep("provider")} />
      )}
      {step === "provider" && (
        <StepProvider onPick={branchFromProvider} />
      )}
      {step === "api_key" && form.provider && form.provider !== "local" && (
        <StepApiKey
          providerName={form.provider}
          value={form.apiKey}
          onChange={(v) => setForm((f) => ({ ...f, apiKey: v }))}
          onBack={() => setStep("provider")}
          onNext={() => setStep("offline_opt_in")}
        />
      )}
      {step === "offline_opt_in" && (
        <StepOfflineOptIn
          // Local-as-primary provider: treat as "required". API-as-primary:
          // optional toggle.
          required={form.provider === "local"}
          selected={form.localModel}
          enabled={form.enableLocal}
          onSetEnabled={(e) => setForm((f) => ({ ...f, enableLocal: e }))}
          onSelectSize={(s) => setForm((f) => ({ ...f, localModel: s }))}
          onBack={() =>
            setStep(form.provider === "local" ? "provider" : "api_key")
          }
          onNext={() => setStep("workspace")}
        />
      )}
      {step === "workspace" && (
        <StepWorkspace
          defaultPath={defaultWorkspace}
          value={form.workspace}
          onChange={(v) => setForm((f) => ({ ...f, workspace: v }))}
          onBack={() => setStep("offline_opt_in")}
          onNext={() => setStep("done")}
        />
      )}
      {step === "done" && (
        <StepDone
          form={form}
          saving={saving}
          onBack={() => setStep("workspace")}
          onFinish={finish}
        />
      )}
    </Modal>
  );
}

const STEPS: Step[] = ["welcome", "provider", "api_key", "offline_opt_in", "workspace", "done"];

function stepTitle(step: Step): string {
  switch (step) {
    case "welcome":
      return "Welcome to scribe";
    case "provider":
      return "Pick a transcription provider";
    case "api_key":
      return "Add your API key";
    case "offline_opt_in":
      return "Offline transcription";
    case "workspace":
      return "Workspace location";
    case "done":
      return "All set";
  }
}

// ── Step components ───────────────────────────────────────────────

function StepWelcome({ onNext }: { onNext: () => void }) {
  return (
    <>
      <p className="text-sm text-text-muted mb-6">
        scribe turns videos and audio into clean markdown transcripts in your
        Obsidian vault. Let's get you set up in a minute.
      </p>
      <div className="rounded-lg border border-border-subtle bg-surface-raised px-4 py-3 mb-6">
        <p className="text-xs text-text-muted">
          You can skip this any time and configure things later in Settings.
        </p>
      </div>
      <div className="flex justify-end">
        <button
          onClick={onNext}
          className="rounded-md bg-amber text-surface px-4 py-2 text-sm font-mono hover:bg-amber/80 transition-colors cursor-pointer flex items-center gap-2"
        >
          Let's go
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </>
  );
}

function StepProvider({ onPick }: { onPick: (provider: string) => void }) {
  return (
    <>
      <p className="text-sm text-text-muted mb-4">
        Pick the service that transcribes your audio. You can change this
        later or add more providers in Settings.
      </p>
      <div className="space-y-2 mb-6">
        {API_PROVIDERS.map((p) => (
          <button
            key={p.name}
            onClick={() => onPick(p.name)}
            className="w-full text-left rounded-lg border border-border-subtle bg-surface hover:border-amber/40 hover:bg-amber/5 px-4 py-3 transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-mono text-text font-bold">{p.name}</span>
              <span className="text-xs text-text-muted">· {p.label}</span>
            </div>
            <p className="text-xs text-text-muted">{p.description}</p>
          </button>
        ))}
        <button
          onClick={() => onPick("local")}
          className="w-full text-left rounded-lg border border-border-subtle bg-surface hover:border-amber/40 hover:bg-amber/5 px-4 py-3 transition-colors cursor-pointer"
        >
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="w-3.5 h-3.5 text-amber" />
            <span className="text-sm font-mono text-text font-bold">local</span>
            <span className="text-xs text-text-muted">· Offline, free, runs on your machine</span>
          </div>
          <p className="text-xs text-text-muted">
            No API key, no internet. Installs faster-whisper + a Whisper model
            on your device (~145 MB for the recommended size).
          </p>
        </button>
      </div>
    </>
  );
}

function StepApiKey({
  providerName,
  value,
  onChange,
  onBack,
  onNext,
}: {
  providerName: string;
  value: string;
  onChange: (v: string) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const provider = API_PROVIDERS.find((p) => p.name === providerName);

  const handleTest = async () => {
    if (!value) return;
    setTesting(true);
    setTestResult(null);
    try {
      // Test endpoint reads from env — since we haven't saved yet, this only
      // works if the env var was already set. We still expose the button for
      // post-save verification; for wizard-phase the best we can do is check
      // shape of the key.
      const result = await testProvider(providerName);
      setTestResult(result);
    } catch (e) {
      setTestResult({
        success: false,
        message: e instanceof Error ? e.message : "Test failed",
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <>
      <p className="text-sm text-text-muted mb-4">
        Paste your {provider?.label || providerName} API key. It's stored
        locally in <code className="text-xs font-mono text-text">~/.anyscribecli/.env</code> and
        never shared.
      </p>
      <div className="mb-4">
        <input
          type="password"
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            setTestResult(null);
          }}
          placeholder="Paste key here"
          autoFocus
          className="w-full bg-surface-raised border border-border rounded-md px-3 py-2 text-sm text-text font-mono outline-none focus:border-amber/40"
        />
        {provider?.url && (
          <p className="text-[10px] font-mono text-text-muted mt-2">
            Need a key?{" "}
            <a
              href={provider.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-amber hover:underline"
            >
              {provider.url.replace(/^https?:\/\//, "")}
            </a>
          </p>
        )}
      </div>

      {testResult && (
        <div
          className={`rounded-md px-3 py-2 mb-4 border ${
            testResult.success
              ? "border-green/30 bg-green/5"
              : "border-red/30 bg-red/5"
          }`}
        >
          <div className="flex items-center gap-2">
            {testResult.success ? (
              <Check className="w-3.5 h-3.5 text-green" />
            ) : (
              <AlertCircle className="w-3.5 h-3.5 text-red" />
            )}
            <p
              className={`text-xs font-mono ${
                testResult.success ? "text-green" : "text-red"
              }`}
            >
              {testResult.message}
            </p>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer flex items-center gap-1"
        >
          <ChevronLeft className="w-3 h-3" />
          Back
        </button>
        <div className="flex items-center gap-2">
          <button
            onClick={handleTest}
            disabled={!value || testing}
            className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50"
          >
            {testing ? <Loader2 className="w-3 h-3 animate-spin" /> : "Test key"}
          </button>
          <button
            onClick={onNext}
            disabled={!value}
            className="rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-mono hover:bg-amber/80 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
          >
            Next
            <ChevronRight className="w-3 h-3" />
          </button>
        </div>
      </div>
    </>
  );
}

function StepOfflineOptIn({
  required,
  enabled,
  selected,
  onSetEnabled,
  onSelectSize,
  onBack,
  onNext,
}: {
  required: boolean;
  enabled: boolean;
  selected: string | null;
  onSetEnabled: (v: boolean) => void;
  onSelectSize: (s: string) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const [status, setStatus] = useState<LocalStatusResponse | null>(null);
  const [settingUp, setSettingUp] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [logOpen, setLogOpen] = useState(false);
  const logCursorRef = useRef(0);

  useEffect(() => {
    getLocalStatus().then((s) => {
      setStatus(s);
      if (!selected) onSelectSize(s.recommended_model);
    });
  }, []);

  // Poll during setup.
  useEffect(() => {
    if (!settingUp) return;
    const id = setInterval(async () => {
      try {
        const [s, log] = await Promise.all([
          getLocalStatus(),
          getSetupLog(logCursorRef.current),
        ]);
        setStatus(s);
        if (log.lines.length > 0) {
          setLogLines((prev) => [...prev, ...log.lines]);
          logCursorRef.current = log.total;
        }
        if (!s.setup_running) {
          clearInterval(id);
          setSettingUp(false);
          if (s.setup_error) {
            setSetupError(s.setup_error);
            setLogOpen(true);
          } else if (s.set_up) {
            onNext();
          }
        }
      } catch {
        // transient
      }
    }, 1500);
    return () => clearInterval(id);
  }, [settingUp, onNext]);

  const handleStartSetup = async () => {
    if (!selected) return;
    setSettingUp(true);
    setSetupError(null);
    setLogLines([]);
    logCursorRef.current = 0;
    try {
      await setupLocal(selected);
      const s = await getLocalStatus();
      setStatus(s);
    } catch (e) {
      setSetupError(e instanceof Error ? e.message : "Failed to start setup");
      setSettingUp(false);
    }
  };

  const recommended = status?.recommended_model || "base";
  const models = status?.models || [];

  return (
    <>
      {!required && (
        <div className="mb-4">
          <p className="text-sm text-text-muted mb-3">
            You can also run transcription offline (on your machine, no API
            needed). Larger models are more accurate but use more disk and
            memory.
          </p>
          <div className="flex items-center gap-2 rounded-lg border border-border-subtle bg-surface px-3 py-2">
            <input
              type="checkbox"
              id="enable-local"
              checked={enabled}
              onChange={(e) => onSetEnabled(e.target.checked)}
              className="cursor-pointer"
            />
            <label
              htmlFor="enable-local"
              className="text-sm text-text cursor-pointer"
            >
              Also enable offline / local transcription
            </label>
          </div>
        </div>
      )}

      {required && (
        <p className="text-sm text-text-muted mb-4">
          Pick a Whisper model size. Larger means more accurate but slower and
          bigger on disk.
        </p>
      )}

      {(enabled || required) && (
        <ModelSizeList
          models={models}
          recommended={recommended}
          selected={selected}
          onSelect={onSelectSize}
          disabled={settingUp}
        />
      )}

      {setupError && (
        <div className="rounded-md border border-red/30 bg-red/5 px-3 py-2 mb-3 mt-3">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red mt-0.5 shrink-0" />
            <p className="text-xs text-red font-mono break-words">
              {setupError.length > 500 ? setupError.slice(0, 500) + "…" : setupError}
            </p>
          </div>
        </div>
      )}

      {(settingUp || logLines.length > 0) && (enabled || required) && (
        <div className="my-4">
          <div className="rounded-md border border-border-subtle bg-surface-raised px-3 py-2">
            <div className="flex items-center gap-2">
              {settingUp && <Loader2 className="w-4 h-4 animate-spin text-amber" />}
              <p className="text-xs text-text font-mono">
                {settingUp
                  ? "Installing faster-whisper and downloading the model…"
                  : "Install log"}
              </p>
            </div>
          </div>
          <button
            onClick={() => setLogOpen(!logOpen)}
            className="mt-2 text-[10px] font-mono text-text-muted hover:text-text cursor-pointer"
          >
            {logOpen ? "hide" : "show"} install log ({logLines.length} lines)
          </button>
          {logOpen && (
            <pre className="mt-1 max-h-48 overflow-auto rounded-md border border-border-subtle bg-black/20 p-2 text-[10px] font-mono text-text-muted whitespace-pre-wrap break-all">
              {logLines.length > 0 ? logLines.join("\n") : "(no output yet)"}
            </pre>
          )}
        </div>
      )}

      <div className="flex items-center justify-between mt-5">
        <button
          onClick={onBack}
          disabled={settingUp}
          className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1"
        >
          <ChevronLeft className="w-3 h-3" />
          Back
        </button>
        <div className="flex items-center gap-2">
          {(enabled || required) && (
            <button
              onClick={handleStartSetup}
              disabled={!selected || settingUp}
              className="rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-mono hover:bg-amber/80 transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1"
            >
              {settingUp ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Setting up…
                </>
              ) : status?.set_up ? (
                "Installed — continue"
              ) : (
                "Install now"
              )}
            </button>
          )}
          {!required && !enabled && (
            <button
              onClick={onNext}
              className="rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-mono hover:bg-amber/80 transition-colors cursor-pointer flex items-center gap-1"
            >
              Skip, next
              <ChevronRight className="w-3 h-3" />
            </button>
          )}
          {(enabled || required) && status?.set_up && (
            <button
              onClick={onNext}
              className="rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-mono hover:bg-amber/80 transition-colors cursor-pointer flex items-center gap-1"
            >
              Next
              <ChevronRight className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
    </>
  );
}

function ModelSizeList({
  models,
  recommended,
  selected,
  onSelect,
  disabled,
}: {
  models: LocalModelEntry[];
  recommended: string;
  selected: string | null;
  onSelect: (s: string) => void;
  disabled: boolean;
}) {
  if (models.length === 0) {
    return (
      <div className="text-xs text-text-muted font-mono py-4">
        Loading model sizes…
      </div>
    );
  }

  return (
    <div className="space-y-2 mb-3">
      {models.map((m) => {
        const isRecommended = m.size === recommended;
        const isSelected = selected === m.size;
        return (
          <button
            key={m.size}
            disabled={disabled}
            onClick={() => onSelect(m.size)}
            className={`w-full text-left rounded-lg border px-3 py-2 transition-colors cursor-pointer ${
              isSelected
                ? "border-amber bg-amber/5"
                : "border-border-subtle bg-surface hover:border-border"
            } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-mono text-text font-bold">
                {m.size}
              </span>
              {isRecommended && (
                <span className="text-[10px] font-mono text-amber bg-amber/10 border border-amber/30 rounded px-1.5 py-0.5">
                  recommended
                </span>
              )}
              {m.cached && (
                <span className="text-[10px] font-mono text-green bg-green/10 border border-green/30 rounded px-1.5 py-0.5">
                  cached
                </span>
              )}
              <span className="ml-auto text-xs text-text-muted font-mono">
                ~{m.spec.download_mb} MB
              </span>
            </div>
            <p className="text-xs text-text-muted mt-1">
              {m.spec.quality} · {m.spec.relative_speed}
            </p>
          </button>
        );
      })}
    </div>
  );
}

function StepWorkspace({
  defaultPath,
  value,
  onChange,
  onBack,
  onNext,
}: {
  defaultPath: string;
  value: string;
  onChange: (v: string) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <>
      <p className="text-sm text-text-muted mb-4">
        scribe writes transcripts into an Obsidian-compatible vault. Default
        is fine for most users.
      </p>
      <div className="mb-4">
        <label className="block text-xs font-mono text-text-muted mb-1">
          Workspace path
        </label>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={defaultPath || "~/anyscribe"}
          className="w-full bg-surface-raised border border-border rounded-md px-3 py-2 text-sm text-text font-mono outline-none focus:border-amber/40"
        />
        <p className="text-[10px] font-mono text-text-muted mt-1">
          Leave blank to use the default ({defaultPath || "~/anyscribe"}).
        </p>
      </div>
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer flex items-center gap-1"
        >
          <ChevronLeft className="w-3 h-3" />
          Back
        </button>
        <button
          onClick={onNext}
          className="rounded-md bg-amber text-surface px-3 py-1.5 text-xs font-mono hover:bg-amber/80 transition-colors cursor-pointer flex items-center gap-1"
        >
          Next
          <ChevronRight className="w-3 h-3" />
        </button>
      </div>
    </>
  );
}

function StepDone({
  form,
  saving,
  onBack,
  onFinish,
}: {
  form: FormState;
  saving: boolean;
  onBack: () => void;
  onFinish: () => void;
}) {
  return (
    <>
      <p className="text-sm text-text-muted mb-4">
        One click and we'll save everything. You can change any of this in
        Settings later.
      </p>
      <div className="rounded-lg border border-border-subtle bg-surface-raised p-4 mb-5 space-y-2">
        <SummaryRow label="Provider" value={form.provider || "—"} />
        {form.provider && form.provider !== "local" && form.apiKey && (
          <SummaryRow label="API key" value="••••" />
        )}
        {form.provider === "local" && form.localModel && (
          <SummaryRow label="Local model" value={form.localModel} />
        )}
        <SummaryRow
          label="Workspace"
          value={form.workspace || "(default)"}
        />
        {form.provider !== "local" && form.enableLocal && form.localModel && (
          <SummaryRow
            label="Offline model"
            value={form.localModel}
          />
        )}
      </div>
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          disabled={saving}
          className="rounded-md border border-border px-3 py-1.5 text-xs font-mono text-text-muted hover:text-text hover:bg-surface-raised transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1"
        >
          <ChevronLeft className="w-3 h-3" />
          Back
        </button>
        <button
          onClick={onFinish}
          disabled={saving}
          className="rounded-md bg-amber text-surface px-4 py-2 text-sm font-mono hover:bg-amber/80 transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-2"
        >
          {saving ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Saving…
            </>
          ) : (
            <>
              <Check className="w-3.5 h-3.5" />
              Finish &amp; start transcribing
            </>
          )}
        </button>
      </div>
    </>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs font-mono text-text-muted">{label}</span>
      <span className="text-xs font-mono text-text">{value}</span>
    </div>
  );
}
