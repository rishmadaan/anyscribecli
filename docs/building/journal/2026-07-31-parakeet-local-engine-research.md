---
type: plan
tags: [local, providers, parakeet, research]
tldr: "Research + integration plan for NVIDIA Parakeet as a second local engine. Verdict: integrate parakeet-tdt-0.6b-v3 via onnx-asr as new entries in the existing local model vocabulary (no new provider); skip the April-2026 parakeet-unified-en-0.6b (NeMo-only, streaming-focused). Not implemented yet — awaiting green light."
---

# NVIDIA Parakeet as a local engine — research & integration plan

**Status: plan only, nothing implemented.** Researched 2026-07-31.

## The model landscape (fetched 2026-07-31)

- **`nvidia/parakeet-tdt-0.6b-v3`** (Aug 2025, CC-BY-4.0) — 600M-param FastConformer-TDT.
  25 European languages with auto language detection, built-in punctuation +
  capitalization, word/segment timestamps. ~6.34% avg WER on the Open ASR
  leaderboard English track (whisper-large-v3 is ~7.4%) at vastly higher
  throughput. **No Hindi / Indic languages** — Whisper stays the local
  multilingual answer; Sarvam stays the Indic answer.
- **`nvidia/parakeet-unified-en-0.6b`** (Apr 2026 — the "just launched" one) —
  English-only, unifies offline + 160ms streaming in one model. **NeMo-only**
  today (torch + nemo_toolkit, GBs of deps, GPU-oriented). anyscribe does
  offline batch, so streaming buys nothing. Skip; revisit when an ONNX/MLX
  conversion appears.

## Runtimes evaluated (no NeMo)

| Runtime | Platforms | Deps | Timestamps | Verdict |
|---|---|---|---|---|
| `onnx-asr` (MIT) | mac/linux/win, x86+ARM CPU | numpy + onnxruntime only | token-level + VAD segments | **Chosen** — one engine, works everywhere |
| `parakeet-mlx` (Apache-2.0) | Apple Silicon only | MLX stack | sentence + word | Faster on Mac (~60x realtime on M3) but single-platform; possible later darwin-arm64 upgrade path |
| NeMo | GPU/Linux-oriented | torch + nemo (GBs) | yes | Rejected — dependency weight absurd for a CLI tool |

`onnx-asr` details: `pip install onnx-asr[cpu,hub]`, Python 3.10–3.14,
`load_model("nemo-parakeet-tdt-0.6b-v3")` pulls
`istupakov/parakeet-tdt-0.6b-v3-onnx` from HF (so `scan_cache_dir`-based
model management keeps working). Max ~20–30s per utterance → built-in VAD
handles long audio; VAD segments map onto `TranscriptSegment`.

## Integration shape (the lazy path)

**Not a new provider.** Parakeet becomes new entries in the existing local
model vocabulary; the `local` provider dispatches on model name.

1. `providers/local_models.py` — add `parakeet-v3` to `MODEL_SIZES`,
   `MODEL_REPOS` (→ `istupakov/parakeet-tdt-0.6b-v3-onnx`), `MODEL_SPECS`;
   add an engine lookup (name → `faster-whisper` | `onnx-asr`).
2. `providers/local.py` — `transcribe()` branches: parakeet models load via
   `onnx_asr.load_model(...)` with VAD, map segments → `TranscriptSegment`;
   whisper path untouched. Ignore `language` param (v3 auto-detects) with a
   warning for non-covered languages.
3. `core/local_setup.py` — make the pip-install spec engine-aware
   (`FASTER_WHISPER_SPEC` → per-engine spec table); `check_status` /
   teardown cover both packages.
4. CLI (`local_cmd.py`, `models_cmd.py`) and Web UI mostly inherit for free —
   they iterate `MODEL_SIZES` / the API. Verify help text + spec copy.
5. Docs: user `providers.md`/`configuration.md`/`commands.md`, skill files
   (SKILL.md + references), building docs, this entry updated to `feature`.
6. Patch version bump per the "bounded addition → patch" policy.

Estimated ~200–250 LOC of real change + docs.

## Open questions at implementation time

- Verify quantized (int8) file size in `istupakov/parakeet-tdt-0.6b-v3-onnx`
  and whether onnx-asr picks int8 by default on CPU (fills `MODEL_SPECS`).
- Whether `RECOMMENDED_MODEL` should eventually become parakeet for
  English-dominant users (keep `base` until tested on real transcripts).
- Segment granularity from VAD chunks vs whisper's natural segments — check
  transcript readability before shipping.
