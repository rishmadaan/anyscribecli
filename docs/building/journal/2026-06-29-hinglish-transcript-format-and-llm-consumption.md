---
type: reference
tags: [hinglish, transcription, llm, providers, deepgram, elevenlabs, sargam, tokenization]
tldr: "Bake-off + research on the best transcript format for Hinglish audio destined for LLMs. Verdict: store the verbatim transcript (not a translation) — translation is lossy and one-way; LLMs handle Hinglish well. Deepgram hi-Latn (romanized) is the sound default; ElevenLabs scribe_v2 (Devanagari) is marginally better for LLMs. Also records the Sarvam saaras:v2.5 + 28s-chunk fix (0.10.1)."
---

# Hinglish transcript format & LLM consumption

**Date:** 2026-06-29
**Follows:** [quality picker](2026-06-29-quality-picker.md) (this closes its "Hinglish bake-off" follow-up)

## Context

The operator's primary content is **primarily-English Hinglish** (Hindi-English
code-switching). Transcripts land in an Obsidian vault that is itself read,
summarized, and queried by LLMs (Claude via the scribe skill, etc.). Two
questions: (1) which provider/tier best handles their Hinglish, and (2) what
*format* should be stored for downstream LLM use — verbatim or translated?

## Bake-off (real 49s Hinglish clip, isolated runs)

| Engine | Words | Output style |
|--------|-------|--------------|
| **Deepgram `hi-Latn`** (`balanced` default's Hinglish path) | 142 | **Romanized** Hinglish — Hindi in Latin + English kept intact. Most complete + readable. |
| **ElevenLabs `scribe_v2`** (`accuracy` tier) | 141 | **Devanagari** Hindi + Latin English; tagged "[हँसने की आवाज़]". Highest fidelity. |
| OpenAI `whisper-1` | 84 | Devanagari, some garble on code-switched terms |
| **Sarvam `saaras:v2.5`** (28s chunks) | 134 | **English translation** (uses the `speech-to-text-translate` endpoint) |
| Deepgram auto (no language) | 72 | Dropped most Hindi — auto-detect insufficient for Hinglish |

The two leaders (Deepgram hi-Latn, ElevenLabs scribe_v2) are ~equally complete;
the difference is **script** (romanized vs Devanagari). Sarvam is a translator,
not a verbatim transcriber. The `hi-Latn` language flag is essential — Deepgram
auto-detect dropped half the Hindi.

## Sarvam fix discovered here (shipped 0.10.1)

- `saaras:v2` is **deprecated** (400). Bumped to `saaras:v2.5` (0.10.0).
- `saaras:v2.5` enforces the **30s REST limit as exclusive** — a 30.0s chunk is
  rejected. scribe chunked at exactly 30s → every chunk failed. Fixed by chunking
  at **28s** (`SARVAM_MAX_DURATION = 28`, `providers/sargam.py`). Shipped 0.10.1.
- Note: scribe's Sarvam uses `speech-to-text-translate`, so its output is an
  **English translation**, not verbatim. Longer-term it should adopt Sarvam's
  batch API (no 30s cap) — noted as future work.

## Research: what format do LLMs digest best?

Sourced survey (see Links). Headline: **LLMs digest Hinglish well; translation is
not the better path for storage.**

- **Comprehension is solid, the gap is small.** "Script Gap" (Dec 2025) tested
  Claude Sonnet 4.5 + GPT-4o directly: Hindi **84.8% native vs 81.6% romanized**
  (~3 pts). The degradation is "orthographic noise destabilizes hard
  *classification*", not a comprehension failure — so summarize/Q&A is fine.
  **Native script ≥ romanized** on current frontier models, never worse.
- **Code-switching adds difficulty** but frontier models are the most robust class.
- **Tokenization (counterintuitive):** English is always cheapest (~1 tok/word).
  On GPT-4o's `o200k` tokenizer, **Devanagari is now *cheaper* than romanized**
  (18 vs 24 tokens on the test sentence) — the old "Devanagari is expensive"
  wisdom is outdated for GPT-4o (still true on Llama/older tokenizers). For a
  personal vault, token cost is negligible either way. (Claude/Gemini tokenizers
  are not public — flagged uncertain.)
- **Fidelity:** translation loses names/idioms/voice, introduces errors, and is
  **one-way** — you cannot recover the original from a translation. Verbatim is
  the lossless source of truth; an LLM can translate/summarize it on demand.

## Verdict / decision

1. **Store the verbatim transcript, never a translation-only file.** Standard
   archival principle: keep the source of truth; treat translation/summary as
   derived, regenerable views. Sarvam's translate output is a derivative, not an
   archive.
2. **The current default — `balanced` → Deepgram `hi-Latn` (romanized verbatim) —
   is sound.** Lossless, LLM-digestible, human-skimmable in Latin. No change.
3. **Native-script (ElevenLabs `scribe_v2`, the `accuracy` tier) is marginally
   better for pure LLM use** (equal-or-better comprehension, canonical spelling,
   cheaper on GPT-4o) — but romanized wins on human skimmability. A preference
   call, not a correctness one.
4. **Best-of-both (future feature):** store verbatim + an optional, clearly
   labeled, regenerable LLM **summary/translation companion block** in the same
   note — never overwriting the verbatim. This is the "LLM post-processing pass"
   flagged as the top strategic gap in the [landscape audit](2026-06-27-transcription-landscape-and-config-audit.md).

## Links

- Script Gap (native vs roman, frontier LLMs) — https://arxiv.org/html/2512.10780v1
- LLMs Are Not (Yet) Code-Switchers (EMNLP 2023) — https://health-nlp.com/files/pubs/emnlp23c.pdf
- RomanSetu (romanization, token fertility) — https://arxiv.org/html/2401.14280v1
- OpenAI o200k Indic gains — https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/exploring-the-new-frontier-of-ai-openais-gpt-4-o-for-indic-languages/4142383
- Unlocking the Archives (retain raw transcript as ground truth) — https://arxiv.org/html/2411.03340v1
- CHILL SemEval-2025 (named-entity translation loss) — https://arxiv.org/pdf/2506.13070
