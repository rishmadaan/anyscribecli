"""Tests for the shared provider/model resolver (core/resolve.py)."""

from __future__ import annotations

import pytest

from anyscribecli.config.settings import Settings
from anyscribecli.core.resolve import resolve_run

KEYS = (
    "OPENAI_API_KEY",
    "ELEVENLABS_API_KEY",
    "DEEPGRAM_API_KEY",
    "GROQ_API_KEY",
    "SARGAM_API_KEY",
    "OPENROUTER_API_KEY",
)


@pytest.fixture(autouse=True)
def _clear_keys(monkeypatch):
    for env in KEYS:
        monkeypatch.delenv(env, raising=False)


# ── provider precedence ─────────────────────────────────


def test_flag_beats_quality_and_diarize(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "x")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "x")
    plan = resolve_run(
        Settings(provider="openai", quality="accuracy"), cli_provider="sargam", diarize=True
    )
    assert (plan.provider, plan.via) == ("sargam", "flag")


def test_accuracy_tier_routes_to_elevenlabs(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "x")
    plan = resolve_run(Settings(provider="openai", quality="accuracy"))
    assert (plan.provider, plan.via) == ("elevenlabs", "quality: accuracy")


def test_cost_tier_routes_to_groq(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "x")
    plan = resolve_run(Settings(provider="openai", quality="cost"))
    assert plan.provider == "groq"


def test_free_tier_routes_to_local_without_a_key():
    plan = resolve_run(Settings(provider="openai", quality="free"))
    assert (plan.provider, plan.model) == ("local", None)


def test_keyless_tier_warns_and_falls_back():
    plan = resolve_run(Settings(provider="openai", quality="accuracy"))
    assert (plan.provider, plan.via) == ("openai", "config")
    assert plan.notes and "WARNING" in plan.notes[0]
    assert "ELEVENLABS_API_KEY" in plan.notes[0]
    assert "using openai instead" in plan.notes[0]


def test_custom_quality_respects_configured_provider(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "x")
    plan = resolve_run(Settings(provider="sargam", quality="custom"))
    assert (plan.provider, plan.via, plan.notes) == ("sargam", "config", [])


def test_diarize_routes_to_deepgram_when_key_present(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "x")
    plan = resolve_run(Settings(provider="openai", quality="custom"), diarize=True)
    assert (plan.provider, plan.via, plan.model) == ("deepgram", "diarize", "nova-3")
    assert "deepgram for diarization" in plan.notes[0]


def test_diarize_without_deepgram_key_keeps_provider():
    plan = resolve_run(Settings(provider="openai", quality="custom"), diarize=True)
    assert (plan.provider, plan.via) == ("openai", "config")
    assert plan.notes == ["diarization is handled by gpt-4o-transcribe-diarize"]


def test_diarize_suppresses_quality_tier(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "x")
    plan = resolve_run(Settings(provider="sargam", quality="cost"), diarize=True)
    assert (plan.provider, plan.via) == ("sargam", "config")


# ── model precedence ────────────────────────────────────


def test_model_defaults_to_first_catalog_entry():
    plan = resolve_run(Settings(provider="openai", quality="custom"))
    assert plan.model == "gpt-transcribe"


def test_pin_beats_catalog_default():
    s = Settings(provider="openai", quality="custom", provider_models={"openai": "whisper-1"})
    assert resolve_run(s).model == "whisper-1"


def test_cli_model_beats_pin():
    s = Settings(provider="openai", quality="custom", provider_models={"openai": "whisper-1"})
    assert resolve_run(s, cli_model="gpt-4o-transcribe").model == "gpt-4o-transcribe"


def test_pin_follows_the_resolved_provider(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "x")
    s = Settings(
        provider="openai",
        quality="cost",
        provider_models={"openai": "whisper-1", "groq": "whisper-large-v3"},
    )
    plan = resolve_run(s)
    assert (plan.provider, plan.model) == ("groq", "whisper-large-v3")


def test_unknown_cli_model_raises():
    with pytest.raises(ValueError, match="Unknown model 'nope' for provider 'openai'"):
        resolve_run(Settings(provider="openai", quality="custom"), cli_model="nope")


def test_extra_openrouter_slug_is_accepted():
    s = Settings(
        provider="openrouter",
        quality="custom",
        extra_models={"openrouter": ["some/new-model"]},
    )
    assert resolve_run(s, cli_model="some/new-model").model == "some/new-model"


# ── openai timestamp routing ────────────────────────────


def test_timestamped_output_switches_to_whisper1():
    s = Settings(provider="openai", quality="custom", output_format="timestamped")
    plan = resolve_run(s)
    assert plan.model == "whisper-1"
    assert plan.notes == ["switched to whisper-1 — gpt-transcribe can't produce timestamps"]


def test_clean_output_keeps_gpt_transcribe():
    s = Settings(provider="openai", quality="custom", output_format="clean")
    plan = resolve_run(s)
    assert (plan.model, plan.notes) == ("gpt-transcribe", [])


def test_explicit_model_is_never_auto_switched():
    s = Settings(provider="openai", quality="custom", output_format="timestamped")
    plan = resolve_run(s, cli_model="gpt-4o-transcribe")
    assert (plan.model, plan.notes) == ("gpt-4o-transcribe", [])


def test_segment_capable_model_is_left_alone():
    s = Settings(
        provider="openai",
        quality="custom",
        output_format="timestamped",
        provider_models={"openai": "whisper-1"},
    )
    plan = resolve_run(s)
    assert (plan.model, plan.notes) == ("whisper-1", [])


def test_non_openai_provider_is_not_rerouted(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "x")
    s = Settings(provider="deepgram", quality="custom", output_format="timestamped")
    assert resolve_run(s).model == "nova-3"


# ── informational notes ─────────────────────────────────


def test_hi_latn_on_deepgram_is_noted():
    s = Settings(provider="deepgram", quality="custom", language="hi-Latn")
    assert resolve_run(s).notes == ["hi-Latn is transcribed by deepgram's nova model"]


def test_hi_latn_on_another_provider_is_silent():
    s = Settings(provider="openai", quality="custom", language="hi-Latn")
    assert resolve_run(s).notes == []


# ── CLI wiring ──────────────────────────────────────────


def test_cli_prints_the_plan_and_passes_the_model(tmp_path, monkeypatch):
    import json

    from typer.testing import CliRunner

    import anyscribecli.core.orchestrator as orchestrator
    from anyscribecli.cli.main import app

    seen: dict = {}

    def fake_process(url, settings, quiet=False, force=False, model=None):
        seen["model"] = model
        seen["provider"] = settings.provider
        return orchestrator.ProcessResult(
            file_path=tmp_path / "out.md",
            title="T",
            platform="youtube",
            duration="1:00",
            language="en",
            word_count=2,
            provider=settings.provider,
        )

    monkeypatch.setattr(orchestrator, "process", fake_process)
    result = CliRunner().invoke(
        app,
        [
            "transcribe",
            "https://youtube.com/watch?v=x",
            "--json",
            "-p",
            "openai",
            "-m",
            "whisper-1",
        ],
    )

    assert result.exit_code == 0, result.output
    assert seen == {"model": "whisper-1", "provider": "openai"}
    # CliRunner folds stderr into .output, so slice from the JSON body.
    payload = json.loads(result.output[result.output.index("{") :])
    assert payload["data"]["model"] == "whisper-1"
    assert "→ openai · whisper-1 (flag)" in result.stderr


def test_cli_rejects_an_unknown_model(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    import anyscribecli.core.orchestrator as orchestrator
    from anyscribecli.cli.main import app

    def fail(*a, **kw):  # pragma: no cover — must never run
        raise AssertionError("process() should not be reached")

    monkeypatch.setattr(orchestrator, "process", fail)
    result = CliRunner().invoke(
        app, ["transcribe", "https://youtube.com/watch?v=x", "-p", "openai", "-m", "nope"]
    )

    assert result.exit_code == 1
    assert "Unknown model 'nope'" in result.stderr


def test_config_level_diarize_folds_into_resolution(monkeypatch):
    # Persisted diarize: true must resolve like --diarize (audit finding).
    from anyscribecli.config.settings import Settings
    from anyscribecli.core.resolve import resolve_run

    monkeypatch.setenv("DEEPGRAM_API_KEY", "k")
    s = Settings(provider="openai", quality="custom", diarize=True, output_format="diarized")
    plan = resolve_run(s)
    assert plan.provider == "deepgram"
    assert any("diarization" in n for n in plan.notes)
    # And no false whisper-1 note when diarize drives the run
    assert not any("whisper-1" in n for n in plan.notes)


def test_diarize_without_deepgram_key_notes_skipped_tier(monkeypatch):
    from anyscribecli.config.settings import Settings
    from anyscribecli.core.resolve import resolve_run

    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "k")
    s = Settings(provider="openai", quality="cost")
    plan = resolve_run(s, diarize=True)
    assert plan.provider == "openai"
    assert any("tier skipped" in n for n in plan.notes)


def test_unknown_provider_rejected_at_resolve():
    import pytest as _pytest

    from anyscribecli.config.settings import Settings
    from anyscribecli.core.resolve import resolve_run

    with _pytest.raises(ValueError, match="Unknown provider"):
        resolve_run(Settings(), cli_provider="nope")


def test_diarize_keyless_balanced_tier_keeps_actionable_warning(monkeypatch):
    # balanced -> deepgram, which CAN diarize — the note must say the key is
    # missing, not that the tier "can't diarize" (re-verify finding D2).
    from anyscribecli.config.settings import Settings
    from anyscribecli.core.resolve import resolve_run

    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    plan = resolve_run(Settings(provider="openai", quality="balanced"), diarize=True)
    assert plan.provider == "openai"
    assert any("WARNING" in n and "DEEPGRAM_API_KEY" in n for n in plan.notes)
    assert not any("can't diarize" in n for n in plan.notes)
