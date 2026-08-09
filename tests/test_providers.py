"""Unit tests for the six cloud transcription providers.

All HTTP is stubbed at the httpx.post boundary — no network, no real keys.
"""

from __future__ import annotations

import base64
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from anyscribe.core.errors import AuthenticationError, RateLimitError
from anyscribe.providers import (
    PROVIDER_REGISTRY,
    get_models,
    get_provider,
    normalize_provider_name,
)
from anyscribe.providers.base import TranscriptionProvider, TranscriptResult
from anyscribe.providers.deepgram import DeepgramProvider
from anyscribe.providers.elevenlabs import ElevenLabsProvider
from anyscribe.providers.groq import GroqProvider
from anyscribe.providers.openai import OpenAIProvider
from anyscribe.providers.openrouter import OpenRouterProvider
from anyscribe.providers.sargam import SargamProvider

CLOUD_PROVIDERS = ["openai", "deepgram", "elevenlabs", "groq", "openrouter", "sargam"]


# ── shared plumbing ─────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    """Fake keys, no retry sleeps, checkpoints in tmp, deterministic duration."""
    for name in CLOUD_PROVIDERS:
        monkeypatch.setenv(f"{name.upper()}_API_KEY", f"key-{name}")
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.setattr("anyscribe.core.errors.time.sleep", lambda s: None)
    monkeypatch.setattr("anyscribe.core.checkpoint.CHECKPOINT_DIR", tmp_path / "ckpt")
    # Small fake file + 10s duration → needs_chunking() is False everywhere by default
    monkeypatch.setattr("anyscribe.core.audio.get_audio_duration", lambda p: 10.0)


@pytest.fixture
def audio(tmp_path):
    p = tmp_path / "clip.mp3"
    p.write_bytes(b"fake-mp3-bytes")
    return p


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text="boom"):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text

    def json(self):
        return self._json


def stub_post(monkeypatch, *responses):
    """Replace httpx.post; returns list of captured calls. Last response repeats."""
    calls: list[dict] = []
    queue = list(responses)

    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return queue.pop(0) if len(queue) > 1 else queue[0]

    monkeypatch.setattr(httpx, "post", fake_post)
    return calls


# ── registry ────────────────────────────────────────────


class TestRegistry:
    def test_all_seven_providers_resolve(self):
        assert sorted(PROVIDER_REGISTRY) == sorted(CLOUD_PROVIDERS + ["local"])
        for name in PROVIDER_REGISTRY:
            provider = get_provider(name)
            assert isinstance(provider, TranscriptionProvider)
            assert provider.name == name

    def test_unknown_provider_rejected(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("nope")

    def test_key_env_map_covers_registry_exactly(self):
        from anyscribe.providers import PROVIDER_KEY_ENV

        assert set(PROVIDER_KEY_ENV) == set(PROVIDER_REGISTRY)
        assert PROVIDER_KEY_ENV["local"] is None
        assert all(v for k, v in PROVIDER_KEY_ENV.items() if k != "local")


# ── error classification (shared raise-path in every provider) ──


class TestErrorClassification:
    @pytest.mark.parametrize("name", CLOUD_PROVIDERS)
    def test_401_raises_auth_error_no_retry(self, name, audio, monkeypatch):
        calls = stub_post(monkeypatch, FakeResponse(401, text="unauthorized"))
        with pytest.raises(AuthenticationError) as exc_info:
            get_provider(name).transcribe(audio)
        assert not exc_info.value.retryable
        assert "API key" in exc_info.value.user_message
        assert len(calls) == 1  # auth errors are never retried

    @pytest.mark.parametrize("name", CLOUD_PROVIDERS)
    def test_429_retries_then_raises_rate_limit(self, name, audio, monkeypatch):
        calls = stub_post(monkeypatch, FakeResponse(429, text="slow down"))
        with pytest.raises(RateLimitError) as exc_info:
            get_provider(name).transcribe(audio)
        assert exc_info.value.retryable
        assert "Rate limited" in exc_info.value.user_message
        assert len(calls) == 4  # 1 attempt + 3 retries (with_retry default)


# ── openai ──────────────────────────────────────────────

WHISPER_RESPONSE = {
    "text": "hello world from whisper",
    "language": "english",
    "duration": 4.2,
    "segments": [
        {"id": 0, "start": 0.0, "end": 2.0, "text": " hello world "},
        {"id": 1, "start": 2.0, "end": 4.2, "text": "from whisper"},
    ],
}


class TestOpenAI:
    def test_happy_path_maps_verbose_json(self, audio, monkeypatch):
        calls = stub_post(monkeypatch, FakeResponse(json_data=WHISPER_RESPONSE))
        result = get_provider("openai", "whisper-1").transcribe(audio, language="en")
        assert isinstance(result, TranscriptResult)
        assert result.text == "hello world from whisper"
        assert result.language == "english"
        assert result.duration == 4.2
        assert [s.text for s in result.segments] == ["hello world", "from whisper"]
        assert result.word_count == 4
        (call,) = calls
        assert call["url"] == OpenAIProvider.API_URL
        assert call["headers"]["Authorization"] == "Bearer key-openai"
        assert call["data"]["model"] == "whisper-1"
        assert call["data"]["response_format"] == "verbose_json"
        assert call["data"]["language"] == "en"

    def test_auto_language_omits_param(self, audio, monkeypatch):
        calls = stub_post(monkeypatch, FakeResponse(json_data=WHISPER_RESPONSE))
        OpenAIProvider().transcribe(audio)  # language="auto"
        assert "language" not in calls[0]["data"]

    def test_missing_key_is_actionable(self, audio, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY")
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            OpenAIProvider().transcribe(audio)

    def test_diarize_routes_to_diarize_model(self, audio, monkeypatch):
        # Real TranscriptionDiarized shape: no language field, string segment
        # ids, a type marker — NOT the whisper-1 verbose_json shape.
        resp = {
            "text": "hi",
            "duration": 1.0,
            "task": "transcribe",
            "segments": [
                {
                    "id": "seg_0",
                    "type": "transcript.text.segment",
                    "start": 0.0,
                    "end": 1.0,
                    "text": "hi",
                    "speaker": "A",
                }
            ],
        }
        calls = stub_post(monkeypatch, FakeResponse(json_data=resp))
        result = OpenAIProvider().transcribe(audio, language="hi", diarize=True)
        assert calls[0]["data"]["model"] == "gpt-4o-transcribe-diarize"
        # Spec: diarized_json is the only format that carries speaker labels,
        # and chunking_strategy is required for >30s inputs.
        assert calls[0]["data"]["response_format"] == "diarized_json"
        assert calls[0]["data"]["chunking_strategy"] == "auto"
        assert result.segments[0].speaker == "A"
        # No language in the response — the requested language is echoed back.
        assert result.language == "hi"

    def test_diarize_rejects_large_files(self, audio, monkeypatch):
        monkeypatch.setattr("anyscribe.providers.openai.needs_chunking", lambda p: True)
        with pytest.raises(RuntimeError, match="25MB"):
            OpenAIProvider().transcribe(audio, diarize=True)

    def test_chunked_transcription_stitches_and_offsets(self, audio, tmp_path, monkeypatch):
        c1, c2 = tmp_path / "c1.mp3", tmp_path / "c2.mp3"
        c1.write_bytes(b"1")
        c2.write_bytes(b"2")
        monkeypatch.setattr("anyscribe.providers.openai.needs_chunking", lambda p: True)
        monkeypatch.setattr(
            "anyscribe.providers.openai.chunk_audio", lambda p: [(c1, 0.0), (c2, 1080.0)]
        )
        r1 = {
            "text": "part one",
            "language": "english",
            "duration": 1085.0,
            "segments": [{"id": 0, "start": 0.0, "end": 5.0, "text": "part one"}],
        }
        r2 = {
            "text": "part two",
            "language": "english",
            "duration": 100.0,
            "segments": [{"id": 0, "start": 0.0, "end": 5.0, "text": "part two"}],
        }
        calls = stub_post(monkeypatch, FakeResponse(json_data=r1), FakeResponse(json_data=r2))
        result = OpenAIProvider().transcribe(audio)
        assert len(calls) == 2
        assert result.text == "part one part two"
        assert result.language == "english"
        assert [s.start for s in result.segments] == [0.0, 1080.0]  # offsets applied
        assert [s.id for s in result.segments] == [0, 1]  # ids renumbered
        assert result.duration == 1180.0  # offset + chunk duration
        assert not c1.exists() and not c2.exists()  # chunk files cleaned up

    def test_chunked_resume_skips_completed_chunks(self, audio, tmp_path, monkeypatch):
        """A checkpoint written by a previous (v0.13.3) run replays without re-posting."""
        from anyscribe.core.checkpoint import ChunkCheckpoint

        # Two fake chunks at offsets 0 and 1080s (mirror the existing chunk test's setup)
        chunk1 = tmp_path / "c1.mp3"
        chunk2 = tmp_path / "c2.mp3"
        chunk1.write_bytes(b"x")
        chunk2.write_bytes(b"y")
        monkeypatch.setattr("anyscribe.providers.openai.needs_chunking", lambda p: True)
        monkeypatch.setattr(
            "anyscribe.providers.openai.chunk_audio",
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

    def test_large_short_file_is_not_deleted(self, audio, monkeypatch):
        """>25MB but ≤18min: chunk_audio hands back the original file as the
        sole chunk — the old loop's unconditional unlink deleted it."""
        monkeypatch.setattr("anyscribe.providers.openai.needs_chunking", lambda p: True)
        monkeypatch.setattr("anyscribe.providers.openai.chunk_audio", lambda p: [(p, 0.0)])
        resp = {"text": "hello", "language": "en", "duration": 30.0, "segments": []}
        stub_post(monkeypatch, FakeResponse(json_data=resp))
        result = OpenAIProvider().transcribe(audio)
        assert result.text == "hello"
        assert audio.exists()  # original source file must survive


# ── deepgram ────────────────────────────────────────────


def dg_response(words, transcript, detected="en"):
    return {
        "results": {
            "channels": [
                {
                    "alternatives": [
                        {
                            "transcript": transcript,
                            "words": words,
                            "detected_language": detected,
                        }
                    ]
                }
            ]
        }
    }


class TestDeepgram:
    def test_happy_path(self, audio, monkeypatch):
        words = [
            {"word": "hello", "punctuated_word": "Hello,", "start": 0.0, "end": 0.5},
            {"word": "world", "punctuated_word": "world.", "start": 0.5, "end": 1.0},
        ]
        calls = stub_post(monkeypatch, FakeResponse(json_data=dg_response(words, "Hello, world.")))
        result = DeepgramProvider().transcribe(audio, language="en")
        assert result.text == "Hello, world."
        assert result.language == "en"
        assert result.duration == 1.0  # last word's end
        assert result.segments[0].text == "Hello, world."  # punctuated words
        (call,) = calls
        assert call["params"]["model"] == "nova-3"
        assert call["params"]["language"] == "en"
        assert call["headers"]["Authorization"] == "Token key-deepgram"
        assert call["content"] == audio.read_bytes()

    def test_hi_latn_routes_to_legacy_nova(self):
        provider = DeepgramProvider()
        assert provider._build_params("hi-Latn", False)["model"] == "nova"
        assert provider._build_params("hi", False)["model"] == "nova-3"
        # auto omits language; diarize adds flag
        params = provider._build_params("auto", True)
        assert "language" not in params
        assert params["diarize"] == "true"

    def test_diarize_groups_words_by_speaker(self, audio, monkeypatch):
        words = [
            {"word": "hi", "punctuated_word": "Hi", "start": 0.0, "end": 0.4, "speaker": 0},
            {"word": "there", "punctuated_word": "there.", "start": 0.4, "end": 0.8, "speaker": 0},
            {"word": "hello", "punctuated_word": "Hello.", "start": 1.0, "end": 1.5, "speaker": 1},
        ]
        calls = stub_post(
            monkeypatch, FakeResponse(json_data=dg_response(words, "Hi there. Hello."))
        )
        result = DeepgramProvider().transcribe(audio, diarize=True)
        assert calls[0]["params"]["diarize"] == "true"
        assert len(result.segments) == 2
        first, second = result.segments
        assert (first.speaker, first.text, first.start, first.end) == (
            "Speaker 0",
            "Hi there.",
            0.0,
            0.8,
        )
        assert (second.speaker, second.text) == ("Speaker 1", "Hello.")

    def test_empty_channels_returns_empty_result(self, audio, monkeypatch):
        stub_post(monkeypatch, FakeResponse(json_data={"results": {"channels": []}}))
        result = DeepgramProvider().transcribe(audio)
        assert result.text == ""
        assert result.segments == []


# ── elevenlabs ──────────────────────────────────────────


class TestElevenLabs:
    def test_happy_path_sends_scribe_v2(self, audio, monkeypatch):
        resp = {
            "text": "namaste world",
            "language_code": "hi",
            "words": [
                {"text": "namaste", "start": 0.0, "end": 0.6},
                {"text": "world", "start": 0.6, "end": 1.2},
            ],
        }
        calls = stub_post(monkeypatch, FakeResponse(json_data=resp))
        result = ElevenLabsProvider().transcribe(audio, language="hi")
        assert result.text == "namaste world"
        assert result.language == "hi"
        assert result.duration == 1.2
        assert result.segments[0].text == "namaste world"
        (call,) = calls
        assert call["url"] == ElevenLabsProvider.API_URL
        assert call["data"]["model_id"] == "scribe_v2"
        assert call["data"]["language_code"] == "hi"
        assert call["headers"]["xi-api-key"] == "key-elevenlabs"

    def test_auto_language_omits_code(self, audio, monkeypatch):
        calls = stub_post(monkeypatch, FakeResponse(json_data={"text": "x", "language_code": "en"}))
        ElevenLabsProvider().transcribe(audio)
        assert "language_code" not in calls[0]["data"]

    def test_no_words_means_no_segments_or_duration(self, audio, monkeypatch):
        stub_post(monkeypatch, FakeResponse(json_data={"text": "bare", "language_code": "en"}))
        result = ElevenLabsProvider().transcribe(audio)
        assert result.text == "bare"
        assert result.segments == []
        assert result.duration is None


# ── groq (OpenAI-compatible subclass — test the wiring, not the logic) ──


class TestGroq:
    def test_inherits_openai_provider(self):
        provider = GroqProvider()
        assert isinstance(provider, OpenAIProvider)
        assert provider.name == "groq"
        assert provider.API_URL == "https://api.groq.com/openai/v1/audio/transcriptions"
        assert provider.MODEL == "whisper-large-v3-turbo"

    def test_request_uses_groq_url_model_and_key(self, audio, monkeypatch):
        resp = {"text": "hi", "language": "english", "duration": 1.0, "segments": []}
        calls = stub_post(monkeypatch, FakeResponse(json_data=resp))
        result = GroqProvider().transcribe(audio)
        assert result.text == "hi"
        (call,) = calls
        assert call["url"] == GroqProvider.API_URL
        assert call["data"]["model"] == "whisper-large-v3-turbo"
        assert call["headers"]["Authorization"] == "Bearer key-groq"

    def test_missing_groq_key(self, audio, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY")
        with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
            GroqProvider().transcribe(audio)

    def test_diarize_unsupported(self, audio):
        with pytest.raises(RuntimeError, match="no diarization"):
            GroqProvider().transcribe(audio, diarize=True)


# ── openrouter (audio-via-chat) ─────────────────────────

CHAT_RESPONSE = {"choices": [{"message": {"content": "the transcript"}}]}


class TestOpenRouter:
    def test_audio_via_chat_request_shape(self, audio, monkeypatch):
        calls = stub_post(monkeypatch, FakeResponse(json_data=CHAT_RESPONSE))
        result = OpenRouterProvider().transcribe(audio)
        assert result.text == "the transcript"
        assert result.language == "unknown"  # auto → unknown
        assert result.segments == []  # chat transcription has no timestamps
        (call,) = calls
        assert call["url"] == OpenRouterProvider.API_URL
        assert call["headers"]["Authorization"] == "Bearer key-openrouter"
        body = call["json"]
        assert body["model"] == "openai/gpt-audio-mini"
        message = body["messages"][0]
        assert message["role"] == "user"
        text_part, audio_part = message["content"]
        assert "Transcribe this audio" in text_part["text"]
        expected_b64 = base64.b64encode(audio.read_bytes()).decode()
        assert audio_part["input_audio"] == {"data": expected_b64, "format": "mp3"}

    def test_language_becomes_prose_instruction(self, audio, monkeypatch):
        calls = stub_post(monkeypatch, FakeResponse(json_data=CHAT_RESPONSE))
        result = OpenRouterProvider().transcribe(audio, language="hi")
        assert "The audio is in hi." in calls[0]["json"]["messages"][0]["content"][0]["text"]
        assert result.language == "hi"

    def test_model_env_var_is_ignored(self, audio, monkeypatch):
        # OPENROUTER_MODEL support was removed — the model picker
        # (provider_models / extra_models) is the only way to change it.
        monkeypatch.setenv("OPENROUTER_MODEL", "google/gemini-flash")
        calls = stub_post(monkeypatch, FakeResponse(json_data=CHAT_RESPONSE))
        OpenRouterProvider().transcribe(audio)
        assert calls[0]["json"]["model"] == OpenRouterProvider.DEFAULT_MODEL


# ── sargam (Sarvam) ─────────────────────────────────────


def fake_ffmpeg(commands: list):
    """Fake subprocess.run that records the command and creates the output file."""

    def run(cmd, **kwargs):
        commands.append(cmd)
        Path(cmd[-1]).write_bytes(b"chunk-bytes")
        return SimpleNamespace(returncode=0, stderr="")

    return run


class TestSargam:
    def test_happy_path_single_chunk(self, audio, monkeypatch):
        resp = {"transcript": "ek do teen", "language_code": "hi-IN"}
        calls = stub_post(monkeypatch, FakeResponse(json_data=resp))
        result = SargamProvider().transcribe(audio, language="hi-IN")
        assert result.text == "ek do teen"
        assert result.language == "hi-IN"
        assert result.word_count == 3
        (call,) = calls
        assert call["url"] == SargamProvider.API_URL
        assert call["data"]["model"] == "saaras:v3"
        assert call["data"]["mode"] == "translate"
        assert call["data"]["language_code"] == "hi-IN"
        assert call["headers"]["api-subscription-key"] == "key-sargam"
        assert audio.exists()  # original file is never deleted

    def test_28s_clip_not_chunked(self, audio, monkeypatch):
        monkeypatch.setattr("anyscribe.core.audio.get_audio_duration", lambda p: 28.0)
        assert SargamProvider()._chunk_for_sarvam(audio) == [(audio, 0.0)]

    def test_30s_clip_chunked_into_28s_pieces(self, audio, monkeypatch):
        # Sarvam's 30s limit is EXCLUSIVE — exactly-30s clips are rejected upstream,
        # so a 30.0s file must be split into <=28s chunks.
        monkeypatch.setattr("anyscribe.core.audio.get_audio_duration", lambda p: 30.0)
        commands: list = []
        monkeypatch.setattr("anyscribe.providers.sargam.subprocess.run", fake_ffmpeg(commands))
        chunks = SargamProvider()._chunk_for_sarvam(audio)
        assert [offset for _, offset in chunks] == [0.0, 28.0]
        for cmd in commands:
            assert cmd[cmd.index("-t") + 1] == "28"
        for path, _ in chunks:
            path.unlink()

    def test_multi_chunk_transcripts_stitched(self, audio, monkeypatch):
        monkeypatch.setattr("anyscribe.core.audio.get_audio_duration", lambda p: 60.0)
        commands: list = []
        monkeypatch.setattr("anyscribe.providers.sargam.subprocess.run", fake_ffmpeg(commands))
        calls = stub_post(
            monkeypatch,
            FakeResponse(json_data={"transcript": "one", "language_code": "hi-IN"}),
            FakeResponse(json_data={"transcript": "two", "language_code": "hi-IN"}),
            FakeResponse(json_data={"transcript": "three", "language_code": "hi-IN"}),
        )
        result = SargamProvider().transcribe(audio)
        assert len(calls) == 3  # 60s / 28s → chunks at 0, 28, 56
        assert result.text == "one two three"
        assert result.language == "hi-IN"
        assert audio.exists()
        assert not list(audio.parent.glob("*_sarvam*.mp3"))  # chunk files cleaned up

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

    def test_speaker_zero_label_kept(self):
        # Integer speaker id 0 is falsy — a bare `or` chain used to drop the
        # first speaker's label. Guard with `is not None` semantics.
        data = {
            "transcript": "hi",
            "language_code": "hi-IN",
            "turns": [{"speaker": 0, "text": "hi", "start": 0.0, "end": 1.0}],
        }
        result = SargamProvider()._parse_response(data)
        assert result.segments[0].speaker == "0"


# ── model picker ─────────────────────────────────────────


class TestModelPicker:
    def test_get_provider_pins_model(self):
        assert get_provider("openai", "gpt-transcribe").model == "gpt-transcribe"

    def test_get_provider_rejects_unknown_model(self):
        with pytest.raises(ValueError, match="Unknown model"):
            get_provider("openai", "not-a-model")

    def test_openrouter_accepts_any_slug(self):
        assert get_provider("openrouter", "vendor/custom").model == "vendor/custom"

    def test_gpt_transcribe_uses_plain_json(self, audio, monkeypatch):
        # No verbose_json on gpt-transcribe: json format, no granularities,
        # and the detected language comes from the new "languages" list.
        resp = {"text": "hello there", "languages": [{"code": "en"}]}
        calls = stub_post(monkeypatch, FakeResponse(json_data=resp))
        provider = get_provider("openai", "gpt-transcribe")
        result = provider.transcribe(audio)
        (call,) = calls
        assert call["data"]["model"] == "gpt-transcribe"
        assert call["data"]["response_format"] == "json"
        assert "timestamp_granularities[]" not in call["data"]
        assert result.text == "hello there"
        assert result.language == "en"
        assert result.segments == []

    def test_whisper1_pin_keeps_verbose_json(self, audio, monkeypatch):
        resp = {"text": "hi", "language": "en", "duration": 1.0, "segments": []}
        calls = stub_post(monkeypatch, FakeResponse(json_data=resp))
        get_provider("openai", "whisper-1").transcribe(audio)
        (call,) = calls
        assert call["data"]["model"] == "whisper-1"
        assert call["data"]["response_format"] == "verbose_json"

    def test_unpinned_openai_uses_gpt_transcribe(self, audio, monkeypatch):
        # Catalog default and the provider's own default must agree.
        calls = stub_post(monkeypatch, FakeResponse(json_data={"text": "hi"}))
        OpenAIProvider().transcribe(audio)
        assert calls[0]["data"]["model"] == get_models("openai")[0] == "gpt-transcribe"

    def test_sargam_v25_pin_rejected(self):
        # saaras:v2.5 and its /speech-to-text-translate endpoint are retired.
        with pytest.raises(ValueError, match="Unknown model"):
            get_provider("sargam", "saaras:v2.5")

    def test_openrouter_model_pin_used(self, audio, monkeypatch):
        monkeypatch.setenv("OPENROUTER_MODEL", "env/model")
        calls = stub_post(monkeypatch, FakeResponse(json_data=CHAT_RESPONSE))
        provider = get_provider("openrouter", "google/gemini-2.5-flash-lite")
        provider.transcribe(audio)
        (call,) = calls
        assert call["json"]["model"] == "google/gemini-2.5-flash-lite"

    def test_get_models_merges_extras(self):
        assert get_models("openai")[0] == "gpt-transcribe"
        assert get_models("openrouter", {"openrouter": ["vendor/x"]})[-1] == "vendor/x"
        # No extras for this provider, unknown provider, dupes: all safe.
        assert get_models("deepgram", {"openrouter": ["vendor/x"]}) == ["nova-3", "nova-2"]
        assert get_models("nope") == []
        assert (
            get_models("openrouter", {"openrouter": ["vendor/x", "vendor/x"]}).count("vendor/x")
            == 1
        )
        assert get_models("openai", {"openai": ["whisper-1"]}) == get_models("openai")

    def test_local_pin_rejected(self):
        # local's model choice lives in settings.local_model, not the picker —
        # a -m pin must fail loudly instead of being silently ignored.
        with pytest.raises(ValueError, match="does not support model selection"):
            get_provider("local", "large-v3")

    def test_sargam_never_sends_undocumented_diarization_field(self, audio, monkeypatch):
        resp = {"transcript": "ek", "language_code": "hi-IN"}
        calls = stub_post(monkeypatch, FakeResponse(json_data=resp))
        SargamProvider().transcribe(audio, diarize=True)
        (call,) = calls
        assert "with_diarization" not in call["data"]


# ── spelling alias ──────────────────────────────────────


class TestProviderNameAlias:
    """The vendor is "Sarvam AI"; our registry key is `sargam`. Typing the
    real spelling must land on the same provider, on every surface."""

    def test_normalize_maps_sarvam_to_sargam(self):
        assert normalize_provider_name("sarvam") == "sargam"

    def test_normalize_leaves_canonical_names_alone(self):
        for name in PROVIDER_REGISTRY:
            assert normalize_provider_name(name) == name

    def test_get_provider_accepts_the_alias(self):
        assert isinstance(get_provider("sarvam"), SargamProvider)

    def test_unknown_provider_error_lists_canonical_names_only(self):
        with pytest.raises(ValueError) as e:
            get_provider("nope")
        assert "sargam" in str(e.value)
        assert "sarvam" not in str(e.value)
