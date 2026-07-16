# Ponytail Simplification Batch (v0.13.4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kill the two drift-prone duplications (provider→env-var map ×7, provider chunk-transcribe loop ×4) and sweep confirmed dead code, fixing two latent bugs (groq missing from preflight and MCP key checks) and one stale help text along the way.

**Architecture:** One canonical `PROVIDER_KEY_ENV` dict in `providers/__init__.py` that every consumer imports or derives from. One concrete `_transcribe_chunked()` method on the `TranscriptionProvider` base class holding the checkpoint-resume/overlap-dedup/timestamp-offset loop; each provider passes a `transcribe_chunk` closure. Checkpoint file format is unchanged — old on-disk checkpoints must still replay.

**Tech Stack:** Python ≥3.10, pytest, ruff. No new dependencies; one dependency removed (`websockets`).

## Global Constraints

- Package imports: always `from anyscribecli.x.y import z` — never from project root.
- After code changes run `pytest` (full suite) and `ruff check src/ && ruff format src/` before committing.
- Do not touch append-only history: `docs/building/journal/` old entries, `docs/superpowers/plans/` old plans.
- Checkpoint JSON format must not change (resume compatibility with checkpoints written by v0.13.3).
- No behavior changes to single-chunk (non-chunked) transcription paths. Two deliberate chunked-path behavior changes ARE in scope, both fixes: the original-file unlink guard (Task 2 — data loss) and sargam's chunk-local parse (Task 3 — fixes double-offset `end` fallback).
- Version bump is `0.13.4` (patch), done only in Task 6 via `./scripts/release.sh` — never edit version strings by hand mid-plan.
- Skill files (`src/anyscribecli/skill/`) and user docs (`docs/user/`) were grepped for `pull --yes`, `instagram.username`, `/api/version`, `get_languages`, `valid_model_sizes` — no live references exist (only append-only journal/plan history). Task 4 re-verifies with grep.

---

### Task 1: Canonical provider→env-var map

The map "provider name → API-key env var" is hand-copied in 7 places. Two copies have drifted (missing `groq`): `core/preflight.py` (preflight silently can't check groq keys) and `mcp/server.py` `test_provider` (reports groq key as set even when missing). Create one canonical dict and derive everything else.

**Files:**
- Modify: `src/anyscribecli/providers/__init__.py` (add dict after `PROVIDER_REGISTRY`, ~line 19)
- Modify: `src/anyscribecli/core/quality.py:25-37`
- Modify: `src/anyscribecli/core/onboard_headless.py:38-50`
- Modify: `src/anyscribecli/core/preflight.py:16-24,60`
- Modify: `src/anyscribecli/web/routes/config.py:43-51`
- Modify: `src/anyscribecli/web/routes/onboarding.py:67` (live consumer of `onboard_headless.PROVIDER_KEY_ENV` — iterates `.items()`)
- Modify: `src/anyscribecli/cli/config_cmd.py:20-27,236-243`
- Modify: `src/anyscribecli/mcp/server.py:470-476`
- Test: `tests/test_providers.py` (add to `TestRegistry`), `tests/test_preflight.py` (add groq case)

**Interfaces:**
- Produces: `anyscribecli.providers.PROVIDER_KEY_ENV: dict[str, str | None]` — keys are exactly the 7 registry provider names; value is the env-var name, or `None` for `local`. Later tasks and all consumers rely on this exact name and location.

- [ ] **Step 1: Write the failing sync test**

Add to `TestRegistry` in `tests/test_providers.py`:

```python
    def test_key_env_map_covers_registry_exactly(self):
        from anyscribecli.providers import PROVIDER_KEY_ENV

        assert set(PROVIDER_KEY_ENV) == set(PROVIDER_REGISTRY)
        assert PROVIDER_KEY_ENV["local"] is None
        assert all(v for k, v in PROVIDER_KEY_ENV.items() if k != "local")
```

Add to `TestPreflightCheck` in `tests/test_preflight.py`, directly below `test_missing_api_key` (same decorator pattern):

```python
    @patch("anyscribecli.core.preflight.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch.dict("os.environ", {}, clear=True)
    def test_missing_groq_api_key(self, mock_which):
        # Regression: groq had drifted out of preflight's provider->env map,
        # so a missing GROQ_API_KEY passed preflight and failed mid-run.
        settings = Settings(provider="groq")
        with pytest.raises(RuntimeError, match="GROQ_API_KEY not set"):
            preflight_check(settings, "https://youtube.com/watch?v=x")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_providers.py::TestRegistry::test_key_env_map_covers_registry_exactly tests/test_preflight.py -v`
Expected: FAIL — `ImportError: cannot import name 'PROVIDER_KEY_ENV'`, and the groq preflight test fails because preflight's map has no `groq` entry (no RuntimeError raised).

- [ ] **Step 3: Add the canonical dict**

In `src/anyscribecli/providers/__init__.py`, after `PROVIDER_REGISTRY`:

```python
# Canonical provider -> env var holding its API key (None = no key needed).
# Single source of truth — every other map (web, cli, mcp, preflight,
# onboarding, quality) imports or derives from this. Was hand-copied in
# 7 places and drifted twice (groq went missing from preflight + mcp).
PROVIDER_KEY_ENV: dict[str, str | None] = {
    "openai": "OPENAI_API_KEY",
    "deepgram": "DEEPGRAM_API_KEY",
    "elevenlabs": "ELEVENLABS_API_KEY",
    "sargam": "SARGAM_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "groq": "GROQ_API_KEY",
    "local": None,
}
```

- [ ] **Step 4: Migrate the six consumers**

`src/anyscribecli/core/quality.py` — delete the `_PROVIDER_KEY_ENV` dict (lines 27-37 incl. its two comment lines) and add the import; `_has_key` body changes name only:

```python
from anyscribecli.providers import PROVIDER_KEY_ENV


def _has_key(provider: str) -> bool:
    """True if the provider needs no key, or its key is set in the environment."""
    env = PROVIDER_KEY_ENV.get(provider)
    return env is None or bool(os.environ.get(env))
```

`src/anyscribecli/core/onboard_headless.py` — delete the local `PROVIDER_KEY_ENV` dict and its "Kept in sync with" comment (lines 38-48); replace with import + derived sets. `API_PROVIDERS`/`ALL_PROVIDERS` keep their exact current values (external importers: `web/routes/onboarding.py`, `cli/onboard.py`):

```python
from anyscribecli.providers import PROVIDER_KEY_ENV

API_PROVIDERS = {name for name, env in PROVIDER_KEY_ENV.items() if env}
ALL_PROVIDERS = API_PROVIDERS | {"local"}
```

Usages at lines ~127/204/207 (`PROVIDER_KEY_ENV[provider]`, `.get(name)`) need no edit — all are reached only for API providers, and `local: None` behaves like a missing key for `.get()` + falsy checks.

**`src/anyscribecli/web/routes/onboarding.py`** — imports `PROVIDER_KEY_ENV` from `onboard_headless` (line 26) and iterates it at line 67. With the canonical map, `"local": None` would hit `os.environ.get(None)` → `TypeError` → `GET /api/onboarding/status` 500s, and `tests/test_web_onboarding.py:33` pins `provider_keys` to exactly the 6 API providers. Filter the comprehension:

```python
    provider_keys = {
        name: bool(os.environ.get(env_var))
        for name, env_var in PROVIDER_KEY_ENV.items()
        if env_var
    }
```

`src/anyscribecli/core/preflight.py` — delete `_PROVIDER_ENV_VARS` (lines 16-24) and import the canonical map; line 60 becomes:

```python
from anyscribecli.providers import PROVIDER_KEY_ENV
```

```python
    env_var = PROVIDER_KEY_ENV.get(settings.provider)
```

(`local` maps to `None` → the existing `if env_var and ...` guard skips it, same as the old missing-key behavior. groq is now checked — that's the bug fix.)

`src/anyscribecli/web/routes/config.py` — replace the `PROVIDER_KEY_MAP` literal (lines 43-51) with a derived dict so all six existing usages (including the `.items()` iteration at line 265) stay untouched:

```python
from anyscribecli.providers import PROVIDER_KEY_ENV

# Maps provider name -> env var for its API key (API providers only)
PROVIDER_KEY_MAP: dict[str, str] = {k: v for k, v in PROVIDER_KEY_ENV.items() if v}
```

`src/anyscribecli/cli/config_cmd.py` — replace the `_API_KEY_MAP` literal (lines 20-27) with a derivation, and delete the inline `key_map` in `providers_test` (lines 236-243):

```python
from anyscribecli.providers import PROVIDER_KEY_ENV

# "openai_api_key" -> "OPENAI_API_KEY", for `scribe config set <x>_api_key`
_API_KEY_MAP = {f"{name}_api_key": env for name, env in PROVIDER_KEY_ENV.items() if env}
```

and in `providers_test`:

```python
    env_var = PROVIDER_KEY_ENV.get(provider_name)
```

`src/anyscribecli/mcp/server.py` — delete the inline `key_map` (lines 470-476, the one missing groq); use the canonical map (add the import at the top of the file with the other `anyscribecli` imports):

```python
from anyscribecli.providers import PROVIDER_KEY_ENV
```

```python
    env_var = PROVIDER_KEY_ENV.get(provider_name)
```

- [ ] **Step 5: Verify no stragglers**

Run: `grep -rn "OPENAI_API_KEY" src/anyscribecli/ --include="*.py" | grep -v "providers/__init__.py" | grep '"OPENAI_API_KEY"'`
Expected: hits inside provider implementation files reading their own key (e.g. `openai.py`'s `os.environ.get`), and `cli/onboard.py:164-194`, whose interactive-wizard provider-metadata dicts carry `"env_var"` fields alongside display names/descriptions — that is presentation metadata, not an eighth key map; leave it (deriving it would couple wizard copy to the canonical dict for no gain). Anything else mapping provider names to env vars: migrate it the same way before proceeding.

- [ ] **Step 6: Run the full suite**

Run: `pytest && ruff check src/ && ruff format src/`
Expected: all PASS, including the two new tests and `tests/test_web_onboarding.py` (its `provider_keys` assertion sees the same 6 API providers thanks to the Step 4 filter).

- [ ] **Step 7: Commit**

```bash
git add -A src/ tests/
git commit -m "refactor: single canonical PROVIDER_KEY_ENV map

Was hand-copied in 7 places; two copies had drifted (groq missing from
preflight and MCP test_provider — both silently skipped groq key checks).
One dict in providers/__init__.py, everything else imports or derives."
```

---

### Task 2: Shared `_transcribe_chunked()` — openai, deepgram, elevenlabs

The checkpoint-resume / overlap-dedup / timestamp-offset loop is copy-pasted near-verbatim in openai.py:114-182, deepgram.py:95-163, elevenlabs.py:69-134 (groq inherits openai's). Hoist it onto the base class. Sargam migrates separately in Task 3 (its `_parse_response` signature changes).

**Files:**
- Modify: `src/anyscribecli/providers/base.py` (add method to `TranscriptionProvider`)
- Modify: `src/anyscribecli/providers/openai.py` (`transcribe`, ~lines 114-182)
- Modify: `src/anyscribecli/providers/deepgram.py` (`transcribe`, ~lines 95-163)
- Modify: `src/anyscribecli/providers/elevenlabs.py` (`transcribe`, ~lines 69-134)
- Test: `tests/test_providers.py` (existing chunk tests are the harness; add one resume test)

**Interfaces:**
- Produces: `TranscriptionProvider._transcribe_chunked(audio_path: Path, chunks: list[tuple[Path, float]], language: str, transcribe_chunk: Callable[[Path], TranscriptResult]) -> TranscriptResult`. `transcribe_chunk` returns a **chunk-local** result (timestamps starting at 0, any segment ids); the loop applies offsets and renumbers ids globally. Chunk files are unlinked as processed; `audio_path` itself is never unlinked (Task 3's sargam relies on this guard).
- Consumes: `ChunkCheckpoint` from `anyscribecli.core.checkpoint`, `deduplicate_overlap` from `anyscribecli.core.audio` (both imported lazily inside the method, matching current provider style).

- [ ] **Step 1: Write the failing resume test**

The existing `test_chunked_transcription_stitches_and_offsets` (openai) and `test_multi_chunk_transcripts_stitched` (sargam) pin the stitch/offset behavior. The resume-from-checkpoint path has no direct test — add one to `TestOpenAI` in `tests/test_providers.py`. Read `test_chunked_transcription_stitches_and_offsets` (line ~169) first and reuse its exact monkeypatching approach for forcing `needs_chunking` true and stubbing `chunk_audio`; the new test differs only in pre-seeding the checkpoint:

```python
    def test_chunked_resume_skips_completed_chunks(self, audio, tmp_path, monkeypatch):
        """A checkpoint written by a previous (v0.13.3) run replays without re-posting."""
        from anyscribecli.core.checkpoint import ChunkCheckpoint

        # Two fake chunks at offsets 0 and 1080s (mirror the existing chunk test's setup)
        chunk1 = tmp_path / "c1.mp3"
        chunk2 = tmp_path / "c2.mp3"
        chunk1.write_bytes(b"x")
        chunk2.write_bytes(b"y")
        monkeypatch.setattr(
            "anyscribecli.providers.openai.needs_chunking", lambda p: True
        )
        monkeypatch.setattr(
            "anyscribecli.providers.openai.chunk_audio",
            lambda p: [(chunk1, 0.0), (chunk2, 1080.0)],
        )

        # Pre-seed chunk 0 as completed, exactly as the old loop saved it:
        # globally-offset segments, chunk-local text/duration.
        ckpt = ChunkCheckpoint.load_or_create(audio, "openai", "auto", 2)
        ckpt.mark_completed(
            0,
            {
                "text": "part one",
                "language": "en",
                "duration": 1080.0,
                "segments": [
                    {"id": 0, "start": 0.0, "end": 5.0, "text": "part one", "speaker": None}
                ],
            },
        )
        ckpt.save()

        resp = {
            "text": "part two",
            "language": "en",
            "duration": 30.0,
            "segments": [{"start": 0.0, "end": 5.0, "text": "part two"}],
        }
        calls = stub_post(monkeypatch, FakeResponse(json_data=resp))
        result = OpenAIProvider().transcribe(audio)

        assert len(calls) == 1  # chunk 0 replayed from checkpoint, not re-posted
        assert result.text == "part one part two"
        assert [s.id for s in result.segments] == [0, 1]
        assert result.segments[1].start == 1080.0  # offset applied to live chunk
```

API verified against `core/checkpoint.py`: `load_or_create(audio_path, provider, language, total_chunks)`, `mark_completed(index, dict)` (segments stored as plain dicts), `save()`. The autouse `_isolate` fixture already redirects `CHECKPOINT_DIR` to tmp, so the seeded checkpoint is picked up by the provider under test.

- [ ] **Step 2: Run new test to verify it passes against the OLD code**

Run: `pytest tests/test_providers.py -k resume -v`
Expected: PASS. This test pins current behavior *before* the refactor — that's the point. (If it fails, the test's checkpoint seeding doesn't match `checkpoint.py`'s real API; fix the test, not the code.)

- [ ] **Step 3: Add `_transcribe_chunked` to the base class**

In `src/anyscribecli/providers/base.py`, add imports and the concrete method on `TranscriptionProvider`:

```python
from typing import Callable
```

```python
    def _transcribe_chunked(
        self,
        audio_path: Path,
        chunks: list[tuple[Path, float]],
        language: str,
        transcribe_chunk: Callable[[Path], TranscriptResult],
    ) -> TranscriptResult:
        """Shared chunk loop: checkpoint resume, overlap dedup, timestamp offsets.

        ``transcribe_chunk`` maps one chunk file to a chunk-local
        TranscriptResult (timestamps from 0; ids arbitrary — renumbered here).
        Chunk files are deleted as processed; ``audio_path`` itself never is.
        Checkpoint payload format matches pre-0.13.4 checkpoints exactly.
        """
        from anyscribecli.core.audio import deduplicate_overlap
        from anyscribecli.core.checkpoint import ChunkCheckpoint

        ckpt = ChunkCheckpoint.load_or_create(audio_path, self.name, language, len(chunks))
        all_text_parts: list[str] = []
        all_segments: list[TranscriptSegment] = []
        detected_language = ""
        total_duration = 0.0
        segment_id = 0

        for i, (chunk_path, offset) in enumerate(chunks):
            if ckpt.is_completed(i):
                saved = ckpt.get(i)
                all_text_parts.append(saved["text"])
                if not detected_language:
                    detected_language = saved.get("language", "")
                for seg_data in saved.get("segments", []):
                    all_segments.append(TranscriptSegment(**seg_data))
                    segment_id = max(segment_id, seg_data.get("id", 0) + 1)
                if saved.get("duration"):
                    total_duration = max(total_duration, offset + saved["duration"])
                if chunk_path != audio_path:
                    chunk_path.unlink(missing_ok=True)
                continue
            try:
                result = transcribe_chunk(chunk_path)
                text = (
                    deduplicate_overlap(all_text_parts[-1], result.text)
                    if all_text_parts
                    else result.text
                )
                all_text_parts.append(text)
                if not detected_language:
                    detected_language = result.language
                for seg in result.segments:
                    seg.id = segment_id
                    seg.start += offset
                    seg.end += offset
                    segment_id += 1
                    all_segments.append(seg)
                if result.duration:
                    total_duration = max(total_duration, offset + result.duration)
                ckpt.mark_completed(
                    i,
                    {
                        "text": result.text,
                        "language": result.language,
                        "duration": result.duration,
                        "segments": result.segments,
                    },
                )
                ckpt.save()
            finally:
                if chunk_path != audio_path:
                    chunk_path.unlink(missing_ok=True)

        ckpt.cleanup()
        full_text = " ".join(all_text_parts)
        return TranscriptResult(
            text=full_text,
            language=detected_language,
            duration=total_duration or None,
            segments=all_segments,
        )
```

Notes locked in by the current code, do not "improve": segments are mutated (offset/renumbered) **before** `mark_completed`, so saved checkpoints hold globally-offset segments — identical to what all four providers save today; `word_count` is intentionally omitted (`TranscriptResult.__post_init__` computes it).

**The `chunk_path != audio_path` guard is a deliberate bug fix, not a no-op.** Today, `needs_chunking` triggers on size >25MB *or* duration >30min (`core/audio.py:26`), but `chunk_audio` returns `[(audio_path, 0.0)]` — the original file — when duration ≤18min (`core/audio.py:67-69`). So a >25MB but short file enters the current loop with the original as its only "chunk", and the unconditional `finally: chunk_path.unlink(...)` **deletes the user's source audio** (openai.py:173, deepgram.py:153, elevenlabs.py:124). The guard closes that. It is also load-bearing for sargam in Task 3, whose `_chunk_for_sarvam` returns the original the same way.

- [ ] **Step 3b: Write the data-loss regression test**

Add to `TestOpenAI` in `tests/test_providers.py`:

```python
    def test_large_short_file_is_not_deleted(self, audio, monkeypatch):
        """>25MB but ≤18min: chunk_audio hands back the original file as the
        sole chunk — the old loop's unconditional unlink deleted it."""
        monkeypatch.setattr(
            "anyscribecli.providers.openai.needs_chunking", lambda p: True
        )
        monkeypatch.setattr(
            "anyscribecli.providers.openai.chunk_audio", lambda p: [(p, 0.0)]
        )
        resp = {"text": "hello", "language": "en", "duration": 30.0, "segments": []}
        stub_post(monkeypatch, FakeResponse(json_data=resp))
        result = OpenAIProvider().transcribe(audio)
        assert result.text == "hello"
        assert audio.exists()  # original source file must survive
```

Expected before the refactor: FAILS (`audio.exists()` is False — the bug). Expected after Step 4: PASSES.

- [ ] **Step 4: Replace the three copy-pasted loops**

`src/anyscribecli/providers/openai.py` — in `transcribe`, everything from `# Chunk large files (>25MB) — pattern from AnyScribe web app` down through the final `return TranscriptResult(...)` (lines ~114-182) becomes:

```python
        return self._transcribe_chunked(
            audio_path,
            chunk_audio(audio_path),
            language,
            lambda p: self._parse_response(self._transcribe_single(p, language, api_key)),
        )
```

Remove the now-unused `from anyscribecli.core.checkpoint import ChunkCheckpoint` local import and, if `deduplicate_overlap` has no remaining uses in the file, drop it from the `core.audio` import line (keep `chunk_audio`, `needs_chunking`).

`src/anyscribecli/providers/deepgram.py` — same replacement for lines ~95-163; the closure carries `diarize`:

```python
        return self._transcribe_chunked(
            audio_path,
            chunk_audio(audio_path),
            language,
            lambda p: self._parse_response(
                self._transcribe_single(p, language, api_key, diarize=diarize),
                diarize=diarize,
            ),
        )
```

`src/anyscribecli/providers/elevenlabs.py` — same replacement for lines ~69-134:

```python
        return self._transcribe_chunked(
            audio_path,
            chunk_audio(audio_path),
            language,
            lambda p: self._parse_response(self._transcribe_single(p, language, api_key)),
        )
```

The `if not needs_chunking(...)` early returns and (for openai) the diarize-rejects-large-files guard above these lines stay exactly as they are.

- [ ] **Step 5: Run the full suite**

Run: `pytest && ruff check src/ && ruff format src/`
Expected: all PASS — in particular `test_chunked_transcription_stitches_and_offsets`, the new resume test, and every groq test (groq inherits `OpenAIProvider.transcribe`, so it gets the shared loop for free).

- [ ] **Step 6: Commit**

```bash
git add -A src/ tests/
git commit -m "refactor(providers): hoist chunk loop into base._transcribe_chunked

The checkpoint-resume/overlap-dedup/timestamp-offset loop was copy-pasted
in openai, deepgram, elevenlabs (groq via inheritance). One template on the
base class; checkpoint format unchanged, old checkpoints still replay.

Also fixes a data-loss bug: a >25MB but <=18min file enters the loop with
the ORIGINAL file as its only chunk (chunk_audio returns [(audio_path, 0.0)]),
and the old unconditional unlink deleted the user's source audio. The shared
loop never unlinks audio_path. Adds resume + data-loss regression tests."
```

---

### Task 3: Migrate sargam to the shared loop

Sargam's copy differs in three ways, all absorbed by the shared loop: its chunks come from `_chunk_for_sarvam` (which can return the *original* file as the single chunk — the loop's `chunk_path != audio_path` guard protects it); it tracks no duration (`result.duration` is `None` → total stays `0.0` → returned as `None`, same as today); and its `_parse_response` currently applies `offset`/`start_id` itself — that responsibility moves to the loop, so the parse signature simplifies.

**Files:**
- Modify: `src/anyscribecli/providers/sargam.py` (`transcribe` ~lines 124-190, `_parse_response` ~lines 190-225)
- Test: `tests/test_providers.py` (`TestSargam`, update `test_diarized_turns_parsed_with_offset`)

**Interfaces:**
- Consumes: `self._transcribe_chunked(...)` from Task 2 — including its guarantee of never unlinking `audio_path`.
- Produces: `SargamProvider._parse_response(data: dict) -> TranscriptResult` (offset/start_id params removed; segments come back chunk-local, ids from `enumerate`).

- [ ] **Step 1: Update the direct-call parse test to the new contract**

In `tests/test_providers.py`, replace `test_diarized_turns_parsed_with_offset` with:

```python
    def test_diarized_turns_parsed_chunk_local(self):
        # Offsets/ids are applied by the shared chunk loop, not the parser.
        data = {
            "transcript": "hello there",
            "language_code": "hi-IN",
            "diarized_transcript": [
                {"speaker": "SPEAKER_0", "text": " hello ", "start": 0.0, "end": 1.0},
                {"speaker": "SPEAKER_1", "text": "there", "start": 1.0, "end": 2.0},
            ],
        }
        result = SargamProvider()._parse_response(data)
        first, second = result.segments
        assert (first.id, first.start, first.end) == (0, 0.0, 1.0)
        assert first.text == "hello"
        assert first.speaker == "SPEAKER_0"
        assert (second.id, second.speaker) == (1, "SPEAKER_1")
```

`test_speaker_zero_label_kept` already calls `_parse_response(data)` with no offset args — it needs no change and pins the speaker-0 regression.

- [ ] **Step 2: Run sargam tests to verify the updated one fails**

Run: `pytest tests/test_providers.py::TestSargam -v`
Expected: `test_diarized_turns_parsed_chunk_local` FAILS (old signature still accepts offset but the semantics assertion on ids/starts passes trivially — if it passes, proceed anyway; the red step here is weak because the old default args are 0/0. The real gate is Step 4's full-suite run.)

- [ ] **Step 3: Rewrite sargam's transcribe and parse**

`transcribe` (everything from `from anyscribecli.core.checkpoint import ChunkCheckpoint` through the final `return TranscriptResult(...)`) becomes:

```python
    def transcribe(
        self, audio_path: Path, language: str = "auto", diarize: bool = False
    ) -> TranscriptResult:
        api_key = self._get_api_key()
        return self._transcribe_chunked(
            audio_path,
            self._chunk_for_sarvam(audio_path),
            language,
            lambda p: self._parse_response(
                self._transcribe_single(p, language, api_key, diarize=diarize)
            ),
        )
```

`_parse_response` drops `offset`/`start_id`:

```python
    def _parse_response(self, data: dict) -> TranscriptResult:
        """Parse Sarvam response into a chunk-local TranscriptResult."""
        transcript = data.get("transcript", "")
        language = data.get("language_code", "unknown")

        segments: list[TranscriptSegment] = []
        turns = data.get("turns") or data.get("diarized_transcript") or []
        for i, turn in enumerate(turns):
            speaker = turn.get("speaker")
            if speaker is None:
                speaker = turn.get("speaker_id")
            text = turn.get("text") or turn.get("transcript", "")
            start = turn.get("start", 0.0)
            end = turn.get("end", start)
            if text.strip():
                segments.append(
                    TranscriptSegment(
                        id=i,
                        start=start,
                        end=end,
                        text=text.strip(),
                        speaker=str(speaker) if speaker is not None else None,
                    )
                )

        return TranscriptResult(
            text=transcript,
            language=language,
            duration=None,
            segments=segments,
        )
```

Remove sargam's now-unused imports if any (`ChunkCheckpoint` local import, `deduplicate_overlap` if unused elsewhere in the file).

Behavior notes locked by existing tests: single-chunk files still route through the loop with `[(audio_path, 0.0)]` and the original is never deleted (`test_happy_path_single_chunk`); multi-chunk stitching order and chunk-file cleanup unchanged (`test_multi_chunk_transcripts_stitched`).

Deliberate deltas vs the old sargam loop (all improvements, journal them in Task 5): the old parse's `end = turn.get("end", start) + offset` double-offset the fallback (`start` already included offset) — chunk-local parsing fixes that; checkpoint-replay id counting moves from `+= 1` per segment to `max(id+1)` (identical for the normal contiguous case, and immune to id gaps from empty-text turns); output segment ids are now always contiguous.

- [ ] **Step 4: Run the full suite**

Run: `pytest && ruff check src/ && ruff format src/`
Expected: all PASS, including all six `TestSargam` tests.

- [ ] **Step 5: Commit**

```bash
git add -A src/ tests/
git commit -m "refactor(sargam): use shared _transcribe_chunked

Parse is now chunk-local (offset/renumbering moved to the shared loop).
Original-file chunks are protected by the loop's audio_path guard."
```

---

### Task 4: Dead-code sweep + stale help text + drop websockets dep

Every deletion below was verified zero-caller by grep across `src/`, `ui/src/`, `tests/`, `docs/user/`, and `src/anyscribecli/skill/` (2026-07-16) — with one exception the fresh-eyes review caught: **the skill docs DO reference `model pull --yes`** in two places, and per project CLAUDE.md the skill is the primary usage path, so those must change in the same commit. The `instagram.username` help text is a real bug (key removed from settings in v0.8.3, documented example errors) and lives in the MCP `set_config` docstring too, not just the CLI.

Line-number caveat: Task 1 already edited `config_cmd.py` (deleted lines 236-243, shrank 20-27), so ranges below for that file are pre-Task-1 numbers — locate by content.

**Files:**
- Modify: `src/anyscribecli/providers/languages.py:367-372`
- Modify: `src/anyscribecli/web/routes/models.py:51-56`
- Modify: `src/anyscribecli/core/local_setup.py:342-344`
- Modify: `src/anyscribecli/providers/local.py:22-24,73-74`
- Modify: `src/anyscribecli/web/routes/system.py`
- Modify: `src/anyscribecli/cli/models_cmd.py:105-111`
- Modify: `src/anyscribecli/cli/config_cmd.py:66-74,86`
- Modify: `src/anyscribecli/mcp/server.py:385`
- Modify: `src/anyscribecli/skill/references/commands.md:424`
- Modify: `src/anyscribecli/skill/references/providers.md:153`
- Modify: `pyproject.toml:44`
- Test: `tests/test_web.py:174-179` (delete `test_version`)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: nothing later tasks rely on.

- [ ] **Step 1: Apply the deletions**

1. `providers/languages.py` — delete the whole `get_languages` function (lines 367-372). `PROVIDER_LANGUAGES` and everything above stays.
2. `web/routes/models.py` — delete `_queue_position` (lines 51-56, def through `return -1`).
3. `core/local_setup.py` — delete `valid_model_sizes` (the 3-line function at line 342).
4. `providers/local.py` — delete lines 22-24 (`# Exported for back-compat...`, `LOCAL_MODELS = MODEL_SIZES`, `DEFAULT_MODEL = RECOMMENDED_MODEL`); at lines 73-74 replace both `LOCAL_MODELS` references with `MODEL_SIZES`:

```python
        if model_size not in MODEL_SIZES:
            raise ValueError(f"Unknown model '{model_size}'. Available: {', '.join(MODEL_SIZES)}")
```

5. `web/routes/system.py` — delete the `/version` endpoint (the `@router.get("/version")` decorator and 2-line function), delete the now-unused `from anyscribecli import __version__` import, and change the module docstring to `"""System endpoints — shutdown."""`.
6. `tests/test_web.py` — delete the `test_version` method (lines ~175-179). Keep `test_shutdown`.
7. `cli/models_cmd.py` — in `model_pull`, delete the `yes` parameter line and the `_ = yes  # accepted for API symmetry with rm` line:

```python
@models_app.command("pull")
def model_pull(
    size: str = typer.Argument(..., help="Model size to download."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """[bold]Download[/bold] a Whisper model to the local cache. Idempotent."""
```

8. `cli/config_cmd.py` — fix the stale example in `config_set` (three spots):

```python
    key: str = typer.Argument(
        ..., help="Setting key (e.g., 'provider', 'language', 'instagram.browser')."
    ),
```

in the docstring:

```python
    Use dot-notation for nested keys: `scribe config set instagram.browser firefox`
```

and the comment at ~line 86: `# Handle dot-notation (e.g., instagram.username)` → `# Handle dot-notation (e.g., instagram.browser)`.

9. `mcp/server.py:385` — same stale example in the `set_config` tool docstring (agent-facing):

```python
    Use dot-notation for nested keys (e.g., "instagram.browser").
```

10. Skill docs — remove the now-invalid `--yes` from `model pull` (typer rejects unknown options, so agents following the skill would get exit 2):
    - `src/anyscribecli/skill/references/commands.md:424`: `scribe model pull <size> --yes --json` → `scribe model pull <size> --json`
    - `src/anyscribecli/skill/references/providers.md:153`: `` `scribe model pull <size> --yes --json` `` → `` `scribe model pull <size> --json` ``

11. `pyproject.toml` — delete the `"websockets>=12.0",` line from `dependencies`. (`uvicorn[standard]` already bundles websocket support; nothing in `src/` imports `websockets` directly — verified.)

- [ ] **Step 2: Verify nothing referenced the deleted names**

Run: `grep -rn "get_languages\|valid_model_sizes\|_queue_position\|LOCAL_MODELS\|DEFAULT_MODEL\|api/version\|instagram.username\|pull.*--yes\|import websockets" src/ tests/ ui/src/ docs/user/ --include="*.py" --include="*.ts" --include="*.tsx" --include="*.md" | grep -v __pycache__`
Expected remaining hits, all legitimate — leave them: `openrouter.py`'s own class attribute `DEFAULT_MODEL` (a different, live constant); `src/anyscribecli/skill/references/config.md:65` (historical note about the v0.8.3 migration *away from* `instagram.username` — accurate as written); `tests/test_instagram_settings_migration.py` (tests that the legacy key is discarded). Anything else: fix before proceeding.

- [ ] **Step 3: Reinstall and run the full suite**

Run: `pip install -e . && pytest && ruff check src/ && ruff format src/`
Expected: install succeeds without `websockets` pinned (uvicorn's extra still provides it — `python -c "import uvicorn, websockets"` still works); all tests PASS including `test_web.py`'s WebSocket tests (`useJob` flow), which prove the dep removal is safe.

- [ ] **Step 4: Commit**

```bash
git add -A src/ tests/ pyproject.toml
git commit -m "chore: dead-code sweep + fix stale config-set examples

Delete zero-caller code: get_languages, _queue_position, valid_model_sizes,
local.py back-compat aliases, GET /api/version, model pull --yes (no-op).
Sync skill docs (commands.md, providers.md) to the pull flag removal.
Fix config set help (CLI + MCP docstring) still advertising
instagram.username (removed in 0.8.3).
Drop websockets dep — uvicorn[standard] already bundles it."
```

---

### Task 5: Building-docs journal entry

Per the repo's documentation ethic: a batch of refactors + three latent-bug fixes gets a journal entry. No user docs change (no user-visible behavior changed except removing a documented no-op flag, and no `docs/user/` file referenced it — verified in Task 4 Step 2). Skill docs were already synced in Task 4's commit (the `pull --yes` references), keeping skill changes in the same commit as the CLI change per project CLAUDE.md.

**Files:**
- Create: `docs/building/journal/2026-07-16-ponytail-simplification-batch.md`
- Modify: `docs/building/_index.md` (new row, newest first)

**Interfaces:** none.

- [ ] **Step 1: Write the journal entry**

Create `docs/building/journal/2026-07-16-ponytail-simplification-batch.md`. Match the frontmatter shape of the most recent entry in `docs/building/journal/` (read one first), then:

```markdown
---
type: refactor
tags: [providers, config, dead-code, ponytail]
tldr: Ponytail audit batch — canonical PROVIDER_KEY_ENV map (fixes groq drift in preflight+MCP), shared _transcribe_chunked on the provider base class (fixes original-file deletion for >25MB short files), dead-code sweep, websockets dep dropped.
---

# Ponytail simplification batch (v0.13.4)

A repo-wide over-engineering audit (2026-07-16) found the provider→env-var
map hand-copied in 7 places — two copies had already drifted (groq missing
from `core/preflight.py` and the MCP `test_provider` key check, so groq key
problems were silently unreported). It also found the chunk-transcribe loop
(checkpoint resume, overlap dedup, timestamp offsets) copy-pasted across
openai/deepgram/elevenlabs/sargam.

## What changed

1. **Canonical map** — `providers/__init__.py::PROVIDER_KEY_ENV` is now the
   single source of truth; web `PROVIDER_KEY_MAP`, cli `_API_KEY_MAP`,
   onboarding `API_PROVIDERS`/`ALL_PROVIDERS`, quality, preflight, and MCP
   all derive from it. A registry-sync test pins it
   (`test_key_env_map_covers_registry_exactly`).
2. **Shared chunk loop** — `TranscriptionProvider._transcribe_chunked()`
   holds the loop once; providers pass a `transcribe_chunk` closure returning
   chunk-local results. Checkpoint format unchanged — pre-0.13.4 checkpoints
   replay (regression test: `test_chunked_resume_skips_completed_chunks`).
   Sargam's `_parse_response` lost its `offset`/`start_id` params — the loop
   owns offsetting now. Two bugs died in the move: (a) **data loss** — a
   >25MB but ≤18min file entered the old loop with the *original* file as
   its only chunk (`chunk_audio` returns `[(audio_path, 0.0)]` for ≤18min)
   and the unconditional unlink deleted the user's source audio; the shared
   loop never unlinks `audio_path` (regression test:
   `test_large_short_file_is_not_deleted`); (b) sargam's old parse
   double-offset the `end` fallback when the API omitted it
   (`turn.get("end", start) + offset` where `start` already carried the
   offset).
3. **Dead-code sweep** — deleted zero-caller `get_languages`,
   `_queue_position`, `valid_model_sizes`, `local.py` back-compat aliases,
   `GET /api/version`, and the no-op `model pull --yes`. Fixed `config set`
   help still advertising `instagram.username` (removed in 0.8.3). Dropped
   the `websockets` dependency (`uvicorn[standard]` bundles it).

## Deliberately NOT done (audit findings judged not worth the churn)

Deleting `model reinstall` (shipped UX), collapsing the four ScribeAPIError
subclasses (readable type names), and ~10 micro-shrinks of <15 lines each.
Rationale: only duplication that drifts and dead code carry real cost.
```

- [ ] **Step 2: Add the index row**

In `docs/building/_index.md`, add a new row at the top of the table (match existing row format exactly — read the current top row first):

```markdown
| 2026-07-16 | refactor | [[journal/2026-07-16-ponytail-simplification-batch.md\|v0.13.4 ponytail simplification batch]] | Canonical PROVIDER_KEY_ENV map (fixes groq drift in preflight+MCP key checks); shared `_transcribe_chunked` on the provider base class; dead-code sweep; `websockets` dep dropped. |
```

- [ ] **Step 3: Commit**

```bash
git add docs/building/
git commit -m "docs: journal entry for ponytail simplification batch"
```

---

### Task 6: Release v0.13.4 — STOP, confirm with Rish first

`./scripts/release.sh` bumps both version files, commits, tags, and pushes — which triggers the PyPI publish. That is outward-facing: **do not run it without Rish's explicit go-ahead in this session.**

**Files:**
- Modify (via script): `src/anyscribecli/__init__.py`, `pyproject.toml`
- Modify: `BACKLOG.md` (version table row + release section, matching the format of the 0.13.3 entry — read it first)

**Interfaces:** none.

- [ ] **Step 1: Update BACKLOG.md**

Add a `0.13.4` row/section describing the batch (canonical key map + groq preflight/MCP fix, shared chunk loop, dead-code sweep, websockets dep dropped), and mark it released. Match the 0.13.3 entry's format exactly.

```bash
git add BACKLOG.md
git commit -m "docs: BACKLOG entry for 0.13.4"
```

- [ ] **Step 2: Confirm with Rish, then release**

Ask: "Batch is green locally — ship 0.13.4 to PyPI?" On yes:

Run: `./scripts/release.sh 0.13.4 "canonical provider key map (fixes groq preflight/MCP drift), shared provider chunk loop, dead-code sweep, drop websockets dep"`
Expected: both version files bumped and matching, tag `v0.13.4` pushed, PyPI workflow triggered.

- [ ] **Step 3: Post-release verification**

Run: `grep -rn "0\.13\.3" README.md docs/user/ src/anyscribecli/skill/ 2>/dev/null`
Expected: no hardcoded old-version strings needing a bump (historical references in append-only journals are fine). Confirm the GitHub Actions publish run goes green.
