---
type: feature
tags: [web-ui, providers, languages, ux]
tldr: Per-provider language picker on the Transcribe page. Static lists in `providers/languages.py` exposed via `/api/providers/{name}/languages`, rendered as a native HTML `<datalist>`. Provider dropdown also now disables unconfigured options and surfaces a "needs key → Settings" CTA.
---

# Per-provider language picker + provider key clarity

## What changed

Two coupled web UI improvements shipped together since they touch the same
component (Transcribe page → Options accordion):

1. **Provider dropdown signals key status.** Configured providers are
   selectable as before. Unconfigured ones render with `· needs key`
   suffix and `<option disabled>` so they appear but can't be picked.
   Below the dropdown, a one-line CTA: `"N providers need a key — Settings"`
   that deep-links to `/settings#api-keys` and scrolls the Providers
   section into view.
2. **Language is a per-provider dropdown.** Replaces the free-text input.
   New `<LanguageInput>` component wraps a native HTML `<datalist>` —
   suggestions drop down, but the user can also type any code. When the
   selected provider changes, the list refetches. OpenRouter is
   special-cased as `freeform: true` (no canonical list — it accepts a
   prose language instruction in the prompt).

The same `<LanguageInput>` is reused on the Settings page for the default
language, so picking a default language is just as easy as picking one for
a single transcription.

## Why now

The Transcribe page is the most-used screen. Two recurring UX issues:

- Users picked a provider whose key wasn't set, then watched it fail at
  submit time. The `has_key` field was already returned by `/api/providers`
  — we just weren't using it.
- Each provider accepts different language codes (ISO 639-1, BCP-47,
  Sarvam's Indic codes, Deepgram's `hi-Latn` for Hinglish). Users had to
  know which format to type. A dropdown removes that lookup.

## Architecture

- **Static lists, not live fetching.** Half the providers don't expose a
  list endpoint, so consistency wins via static lists in
  `src/anyscribecli/providers/languages.py`. The module docstring lists
  every source URL plus rules for editing.
- **`<datalist>` over a custom combobox.** Native HTML, zero JS for
  keyboard handling. Browser styling is consistent enough across modern
  Chromium/Firefox/Safari that we don't need a custom widget.
- **Code-not-translated.** Each entry uses the EXACT code the provider's
  API expects. We never translate between formats — that path leads to
  bugs. Deepgram entries for legacy-Nova-only languages (currently only
  `hi-Latn`) carry an internal `"model": "nova"` tag; the router in
  `deepgram.py:47` reads this and the UI never shows it.
- **No `supported_languages()` classmethod on providers.** Considered, but
  it would just delegate to a dict lookup keyed by name — pure ceremony.
  The endpoint reads `PROVIDER_LANGUAGES` directly. Less indirection,
  same result.

## Source URLs (verified 2026-04-18)

| Provider     | URL                                                              | Count |
|--------------|------------------------------------------------------------------|-------|
| OpenAI       | https://github.com/openai/whisper/blob/main/whisper/tokenizer.py | 99    |
| Local        | (same as OpenAI — faster-whisper wraps Whisper)                  | 99    |
| Deepgram     | https://developers.deepgram.com/docs/models-languages-overview   | 89    |
| ElevenLabs   | https://elevenlabs.io/speech-to-text (Scribe v1)                 | 92    |
| Sarvam       | https://docs.sarvam.ai/api-reference-docs/speech-to-text         | 23    |
| OpenRouter   | (none — freeform prose instruction)                              | —     |

The Deepgram list merges Nova-3's set with one explicit Nova-2 fallback
(`hi-Latn` for romanized Hindi). The merge happens in data, not at runtime
— each entry knows which model to route to.

## Files touched

**Backend (new + edited):**
- `src/anyscribecli/providers/languages.py` (new)
- `src/anyscribecli/web/routes/config.py` — `GET /api/providers/{name}/languages`
- `src/anyscribecli/web/models.py` — `LanguageOption`, `ProviderLanguagesResponse`

**Frontend:**
- `ui/src/components/LanguageInput.tsx` (new)
- `ui/src/api/types.ts` — new TS interfaces
- `ui/src/api/client.ts` — `getProviderLanguages`
- `ui/src/pages/TranscribePage.tsx` — disabled options, Settings CTA, swap to `<LanguageInput>`
- `ui/src/pages/SettingsPage.tsx` — `id="api-keys"` anchor, scroll-to-hash effect, swap to `<LanguageInput>`

**Docs:**
- `CLAUDE.md` — new section "Updating Provider Language Lists" (the maintenance instructions for future-Claude/me when upstream lists change)
- `docs/building/providers.md` — note on language API
- `docs/building/_index.md` — index entry

## Maintenance

When a provider adds/removes a language upstream, follow the steps in
`CLAUDE.md → "Updating Provider Language Lists"`. Tag the Deepgram entry's
`model` field if the language only works on the legacy Nova model. Always
re-fetch the source URL before editing — don't trust the existing list as
a baseline if it's been more than a few months.
