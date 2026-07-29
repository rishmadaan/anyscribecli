import { useId, useState } from "react";
import type { Provider } from "../api/types";

interface ModelInputProps {
  provider?: Provider;
  value: string;
  onChange: (v: string) => void;
  className?: string;
  disabled?: boolean;
}

const INPUT_CLS =
  "flex-1 bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40";

/** Default model for a provider: the pinned one, else the provider's first. */
export function defaultModelFor(
  provider: Provider | undefined,
  pinned: Record<string, string> | undefined
): string {
  if (!provider) return "";
  return (pinned ?? {})[provider.name] ?? provider.models?.[0] ?? "";
}

/** True when the provider offers a real choice worth rendering a control for. */
export function hasModelChoice(provider: Provider | undefined): boolean {
  return !!provider && (provider.freeform_model || (provider.models?.length ?? 0) > 1);
}

/**
 * Model picker for one provider. Renders nothing unless there's a choice:
 * a <select> for fixed lists, a datalist-backed text input for openrouter
 * (any slug is valid). Local has its own model cards elsewhere.
 */
export default function ModelInput({
  provider,
  value,
  onChange,
  className,
  disabled,
}: ModelInputProps) {
  const listId = useId();
  // Datalists filter their popup by the input's current value, so a prefilled
  // slug hides every other suggestion. Blank the visible value while focused.
  const [focused, setFocused] = useState(false);
  const [draft, setDraft] = useState("");

  if (!hasModelChoice(provider) || !provider) return null;
  const cls = className ?? INPUT_CLS;

  if (!provider.freeform_model) {
    return (
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={cls}
      >
        {provider.models.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
    );
  }

  return (
    <>
      <input
        type="text"
        value={focused ? draft : value}
        onChange={(e) => setDraft(e.target.value)}
        onFocus={() => {
          setFocused(true);
          setDraft("");
        }}
        onBlur={(e) => {
          setFocused(false);
          setDraft("");
          const typed = e.target.value.trim();
          // Commit once on blur; empty field = user cleared it, keep old value.
          if (typed && typed !== value) onChange(typed);
        }}
        placeholder={value || provider.models[0] || "model slug"}
        list={listId}
        disabled={disabled}
        className={cls}
      />
      <datalist id={listId}>
        {provider.models.map((m) => (
          <option key={m} value={m} />
        ))}
      </datalist>
    </>
  );
}
