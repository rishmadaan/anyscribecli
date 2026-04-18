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

  const placeholder = freeform ? "e.g. Spanish (free text)" : "auto";

  return (
    <>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur ? (e) => onBlur(e.target.value) : undefined}
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
