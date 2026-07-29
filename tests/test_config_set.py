"""Tests for the shared validated setter (core/config_set.py)."""

from __future__ import annotations

import os

import pytest

from anyscribecli.config.settings import load_config
from anyscribecli.core.config_set import set_value


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Point config.yaml and .env at tmp_path for every test in this module."""
    monkeypatch.setattr("anyscribecli.config.settings.CONFIG_FILE", tmp_path / "config.yaml")
    monkeypatch.setattr("anyscribecli.config.settings.ENV_FILE", tmp_path / ".env")
    saved = dict(os.environ)
    yield tmp_path
    # set_value writes API keys into the live env — restore it for other modules.
    os.environ.clear()
    os.environ.update(saved)


# ── API keys ──────────────────────────────────────────


def test_api_key_goes_to_env_file_and_process_env(isolated_config):
    out = set_value("openai_api_key", "sk-test")
    assert out.ok
    assert "OPENAI_API_KEY" in (isolated_config / ".env").read_text()
    assert os.environ["OPENAI_API_KEY"] == "sk-test"
    # config.yaml untouched — secrets never land there.
    assert not (isolated_config / "config.yaml").exists()


def test_api_key_accepts_dashes_and_case():
    assert set_value("Deepgram-API-Key", "dg").ok


# ── Enums ─────────────────────────────────────────────


def test_provider_write_pins_quality_custom():
    out = set_value("provider", "deepgram")
    assert out.ok
    assert "custom" in out.message
    s = load_config()
    assert (s.provider, s.quality) == ("deepgram", "custom")


def test_unknown_provider_rejected():
    out = set_value("provider", "nope")
    assert not out.ok
    assert "openai" in out.choices


@pytest.mark.parametrize(
    "key,value",
    [
        ("quality", "accuracy"),
        ("quality", "custom"),
        ("output_format", "diarized"),
        ("prompt_download", "ask"),
        ("local_file_media", "move"),
        ("local_model", "small"),
    ],
)
def test_enum_values_accepted(key, value):
    assert set_value(key, value).ok
    assert getattr(load_config(), key) == value


@pytest.mark.parametrize(
    "key", ["quality", "output_format", "prompt_download", "local_file_media", "local_model"]
)
def test_enum_rejects_garbage(key):
    out = set_value(key, "bogus")
    assert not out.ok and out.choices


def test_setting_quality_does_not_touch_provider():
    set_value("provider", "groq")
    assert set_value("quality", "cost").ok
    assert load_config().provider == "groq"  # apply_quality resolves tiers at run time


# ── Scalars ───────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected", [("true", True), ("YES", True), ("1", True), ("no", False)]
)
def test_boolean_coercion(raw, expected):
    assert set_value("keep_media", raw).ok
    assert load_config().keep_media is expected


def test_boolean_accepts_native_bool():
    assert set_value("diarize", True).ok
    assert load_config().diarize is True


def test_workspace_path_expanded():
    assert set_value("workspace_path", "~/notes").ok
    stored = load_config().workspace_path
    assert stored.startswith(os.path.expanduser("~")) and "~" not in stored


def test_language_is_free_text():
    assert set_value("language", "hi").ok
    assert load_config().language == "hi"


def test_nested_dot_key():
    assert set_value("instagram.browser", "firefox").ok
    assert load_config().instagram.browser == "firefox"


def test_unknown_key_lists_valid_keys():
    out = set_value("nope", "x")
    assert not out.ok
    assert "provider_models.<provider>" in out.choices
    assert "instagram.browser" in out.choices


def test_unknown_nested_key_rejected():
    assert not set_value("instagram.password", "x").ok


# ── Model pins ────────────────────────────────────────


def test_pin_valid_model():
    assert set_value("provider_models.openai", "whisper-1").ok
    assert load_config().provider_models == {"openai": "whisper-1"}


def test_pin_unknown_model_rejected_with_choices():
    out = set_value("provider_models.deepgram", "nova-9")
    assert not out.ok
    assert out.choices == ["nova-3", "nova-2"]


def test_pin_openrouter_accepts_any_slug():
    assert set_value("provider_models.openrouter", "vendor/whatever").ok


def test_pin_local_rejected_with_hint():
    out = set_value("provider_models.local", "base")
    assert not out.ok
    assert "local setup --model" in out.error


def test_pin_unknown_provider_rejected():
    assert not set_value("provider_models.bogus", "x").ok


def test_pin_accepts_user_added_openrouter_slug():
    set_value("extra_models.openrouter", "vendor/custom")
    assert set_value("provider_models.openrouter", "vendor/custom").ok


def test_pin_whole_dict_replacement():
    set_value("provider_models.openai", "whisper-1")
    out = set_value("provider_models", {"deepgram": "nova-2"})
    assert out.ok
    assert load_config().provider_models == {"deepgram": "nova-2"}


def test_pin_whole_dict_rejects_bad_entry():
    set_value("provider_models.openai", "whisper-1")
    assert not set_value("provider_models", {"deepgram": "nova-9"}).ok
    assert load_config().provider_models == {"openai": "whisper-1"}  # nothing persisted


# ── extra_models ──────────────────────────────────────


def test_extra_models_comma_separated_dedupes_and_strips():
    out = set_value("extra_models.openrouter", " a/b , c/d ,a/b, ")
    assert out.ok
    assert load_config().extra_models == {"openrouter": ["a/b", "c/d"]}


def test_extra_models_empty_value_clears():
    set_value("extra_models.openrouter", "a/b")
    assert set_value("extra_models.openrouter", "").ok
    assert load_config().extra_models == {}


def test_extra_models_rejects_non_openrouter():
    out = set_value("extra_models.openai", "some-model")
    assert not out.ok
    assert "openrouter" in out.error


def test_extra_models_whole_dict_replacement():
    out = set_value("extra_models", {"openrouter": ["a/b", "a/b"]})
    assert out.ok
    assert load_config().extra_models == {"openrouter": ["a/b"]}


def test_extra_models_bare_key_rejected():
    assert not set_value("extra_models", "a/b").ok
