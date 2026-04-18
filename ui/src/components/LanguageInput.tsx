import { useEffect, useId, useState } from "react";
import { getProviderLanguages } from "../api/client";
import type { LanguageOption } from "../api/types";

interface LanguageInputProps {
  provider: string;
  value: string;
  onChange: (v: string) => void;
  onBlur?: (v: string) => void;
  className?: string;
}

const AUTO_OPTION: LanguageOption = { code: "auto", name: "Auto-detect" };

const INPUT_CLS =
  "flex-1 bg-surface-raised border border-border rounded-md px-2.5 py-1.5 text-sm text-text font-mono outline-none focus:border-amber/40";

export default function LanguageInput({ provider, value, onChange, onBlur, className }: LanguageInputProps) {
  const listId = useId();
  const [languages, setLanguages] = useState<LanguageOption[]>([AUTO_OPTION]);
  const [freeform, setFreeform] = useState(false);
  // Local display value: temporarily blanked on focus so the <datalist>
  // popup shows ALL options instead of filtering by the current value
  // (native datalists filter the popup by whatever's already in the input).
  const [displayValue, setDisplayValue] = useState(value);

  useEffect(() => {
    setDisplayValue(value);
  }, [value]);

  useEffect(() => {
    if (!provider) return;
    let cancelled = false;
    getProviderLanguages(provider)
      .then((res) => {
        if (cancelled) return;
        setFreeform(res.freeform);
        setLanguages(res.freeform ? [AUTO_OPTION] : [AUTO_OPTION, ...res.languages]);
      })
      .catch(() => {
        if (cancelled) return;
        setFreeform(false);
        setLanguages([AUTO_OPTION]);
      });
    return () => {
      cancelled = true;
    };
  }, [provider]);

  const placeholder = freeform ? "e.g. Spanish (free text)" : value || "auto";

  const handleFocus = () => {
    // Datalists filter their popup by the input's current value. With "auto"
    // pre-filled, the popup would show only the "auto" entry. Clearing the
    // visible value on focus lets the popup show every supported language.
    if (!freeform) setDisplayValue("");
  };

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    const typed = e.target.value;
    // If the user cleared the field and didn't pick or type anything, restore
    // the previous value rather than committing an empty string.
    const finalValue = typed.trim() === "" ? value : typed;
    if (finalValue !== value) onChange(finalValue);
    setDisplayValue(finalValue);
    if (onBlur) onBlur(finalValue);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDisplayValue(e.target.value);
    onChange(e.target.value);
  };

  return (
    <>
      <input
        type="text"
        value={displayValue}
        onChange={handleChange}
        onFocus={handleFocus}
        onBlur={handleBlur}
        placeholder={placeholder}
        list={freeform ? undefined : listId}
        className={className ?? INPUT_CLS}
      />
      {!freeform && (
        <datalist id={listId}>
          {languages.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.name}
            </option>
          ))}
        </datalist>
      )}
    </>
  );
}
