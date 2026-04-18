---
type: project-note
tags: [web-ui, ux, datalist, language-picker, diarize, labels]
tldr: Two follow-ups to the v0.7.4.7 language picker — v0.7.4.7.1 fixes the empty-popup bug (native datalists filter by current value, so "auto" pre-fill made the dropdown look broken; clearing on focus restores all options); v0.7.4.7.2 renames the diarize toggle to "Multi-speaker" and the "diarized" output to "with-speaker-labels" in the UI only (wire values unchanged).
---

# Language picker polish — v0.7.4.7.1 + v0.7.4.7.2

Two small UX fixes after [the language picker shipped in v0.7.4.7](2026-04-18-provider-language-lists.md).

## v0.7.4.7.1 — datalist popup empty when value is "auto"

**Symptom**: User reported the language dropdown showed nothing when clicked. Typing letters appended to the existing value (so typing `h` produced `autoh` instead of filtering to `h*` codes).

**Root cause**: Native HTML `<datalist>` filters its dropdown popup by the input's current value. With the field pre-filled with `"auto"` (the default config), the popup matched only entries containing "auto" — which is just the one `auto` entry, making the picker appear empty/broken.

**Fix** (`ui/src/components/LanguageInput.tsx`): the component now keeps a local `displayValue` state that's blanked on focus so the popup shows every option. On blur, if the user didn't pick or type anything, the previous value is restored. If they typed something, that's committed via `onChange`. The parent's `value` prop is only updated when there's a real change — the temporary blank doesn't leak.

This pattern (focus-clear + blur-restore for `<datalist>` inputs with non-empty defaults) is reusable. The native datalist popup behavior is non-obvious: with text in the input, it filters; with the input empty, it shows all options.

**Test** (Playwright):
- Click empty input → popup shows all 90 Deepgram codes
- Type `h` → input shows `h` (filters live, no `auto` prefix)
- Tab away with `h` typed → persists as `h`
- Tab away after just clicking → restores to `auto`

## v0.7.4.7.2 — UI labels in plain English

**Trigger**: User pointed out "diarize" / "diarized" are jargon — most users don't recognize the term.

**Change** (UI only, no API/CLI changes):

| Where | Before | After |
|---|---|---|
| Toggle label (`TranscribePage.tsx`) | `Diarize` | `Multi-speaker` |
| Format pill (`TranscribePage.tsx` + `SettingsPage.tsx`) | `diarized` | `with-speaker-labels` |
| Accordion summary suffix | `+ diarize` | `+ speakers` |

Wire values stay `"diarized"` / `diarize=true` — the API contract, CLI flag (`--diarize`), and saved config (`output_format: diarized`) are all unchanged. Only display labels are friendlier.

This is the right pattern when CLI/API and UI naming diverge: keep the developer-facing identifiers stable (CLI scripts and external tools depend on them), but use plain-English labels in the UI where users are. Document the mapping in user docs and README so users connecting the two surfaces aren't confused.

Row label width was bumped from `w-20` to `w-32` across the Options accordion to fit the longer "Multi-speaker" label without wrapping. Existing labels (Provider, Language, Format, Keep media) all still fit cleanly.

## Files touched

- `ui/src/components/LanguageInput.tsx` — focus-clear, blur-restore, local displayValue state
- `ui/src/pages/TranscribePage.tsx` — `formatLabel` helper for pill display, label rename, w-20 → w-32 across the accordion
- `ui/src/pages/SettingsPage.tsx` — pill display rename
- `README.md` — feature bullet expanded for the language picker; web UI label mapping callout
- `docs/user/configuration.md` — output_format table gets a "web UI label" note
- `docs/user/commands.md` — `scribe ui` section explains the label conventions
- `docs/user/providers.md` — diarization auto-routing section gets the same web UI label note

## Notes

- `--diarize` (CLI flag) and `diarize` (config key) are unchanged. Backwards compatible.
- The skill files (`src/anyscribecli/skill/`) are CLI-focused and weren't touched — they describe the developer-facing surface accurately as-is.
- A separate Foundry learning entry captures the focus-clear datalist pattern as a reusable insight: see `secondbrain/dev/journal/2026-04-18/datalist-popup-focus-clear-pattern.md`.
