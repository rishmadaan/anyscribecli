"""Tests for Settings (de)serialization."""

from __future__ import annotations

import os
from unittest.mock import patch

from anyscribecli.config.settings import (
    Settings,
    delete_env,
    env_file_keys,
    forget_env_var,
    save_env,
)


def test_from_dict_tolerates_unknown_keys():
    # A config written by a different version may carry keys this version
    # doesn't know (top-level and inside instagram). It must load, not crash.
    data = {
        "provider": "deepgram",
        "quality": "cost",
        "future_top_level_key": "ignored",
        "instagram": {"browser": "chrome", "username": "legacy-pre-0.8.3"},
    }
    s = Settings.from_dict(data)
    assert s.provider == "deepgram"
    assert s.quality == "cost"
    assert s.instagram.browser == "chrome"  # known key kept; unknown 'username' dropped


def test_quality_defaults_to_balanced():
    assert Settings().quality == "balanced"


def test_delete_env_removes_only_named_keys(tmp_path):
    env_file = tmp_path / ".env"
    with patch("anyscribecli.config.settings.ENV_FILE", env_file):
        save_env({"OPENAI_API_KEY": "sk-a", "DEEPGRAM_API_KEY": "dg-b"})
        delete_env(["OPENAI_API_KEY"])
        remaining = env_file.read_text()
    assert "OPENAI_API_KEY" not in remaining
    assert "DEEPGRAM_API_KEY=dg-b" in remaining


def test_delete_env_missing_file_is_noop(tmp_path):
    env_file = tmp_path / ".env"  # never created
    with patch("anyscribecli.config.settings.ENV_FILE", env_file):
        delete_env(["OPENAI_API_KEY"])  # must not raise
    assert not env_file.exists()


def test_delete_env_handles_export_prefixed_keys(tmp_path):
    # A hand-edited .env may use valid dotenv `export KEY=...` syntax. Deletion
    # must still match the key, or the removal silently no-ops and python-dotenv
    # reloads it. (Codex review finding, 2026-07-14.)
    env_file = tmp_path / ".env"
    env_file.write_text("export OPENAI_API_KEY=sk-a\nDEEPGRAM_API_KEY=dg-b\n")
    with patch("anyscribecli.config.settings.ENV_FILE", env_file):
        delete_env(["OPENAI_API_KEY"])
        remaining = env_file.read_text()
    assert "OPENAI_API_KEY" not in remaining
    assert "DEEPGRAM_API_KEY=dg-b" in remaining


def test_env_file_keys_normalizes_export_and_skips_noise(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("export OPENAI_API_KEY=sk-a\nDEEPGRAM_API_KEY=dg-b\n# note\n\n")
    with patch("anyscribecli.config.settings.ENV_FILE", env_file):
        assert env_file_keys() == {"OPENAI_API_KEY", "DEEPGRAM_API_KEY"}


def test_env_file_keys_empty_when_absent(tmp_path):
    with patch("anyscribecli.config.settings.ENV_FILE", tmp_path / ".env"):
        assert env_file_keys() == set()


def test_delete_preserves_comments_multiline_and_handles_export_tab(tmp_path):
    # Codex re-review (2026-07-14): env parsing must match the full dotenv
    # grammar load_env() accepts. Deleting one key must preserve comments and
    # unrelated multiline values, and `export\tKEY` (tab, not space) must be
    # both visible to env_file_keys and deletable.
    env_file = tmp_path / ".env"
    env_file.write_text(
        '# my secrets\nOTHER="line1\nline2"\nexport\tDEEPGRAM_API_KEY=dg\nOPENAI_API_KEY=sk-plain\n'
    )
    with patch("anyscribecli.config.settings.ENV_FILE", env_file):
        assert env_file_keys() == {"OTHER", "DEEPGRAM_API_KEY", "OPENAI_API_KEY"}
        delete_env(["OPENAI_API_KEY"])
        after = env_file.read_text()
        assert "# my secrets" in after  # comment preserved
        assert 'OTHER="line1\nline2"' in after  # multiline value intact
        assert "OPENAI_API_KEY" not in after
        delete_env(["DEEPGRAM_API_KEY"])  # export-tab key is deletable
        assert env_file_keys() == {"OTHER"}


def test_save_env_keeps_plain_format_and_preserves_others(tmp_path):
    env_file = tmp_path / ".env"
    with patch("anyscribecli.config.settings.ENV_FILE", env_file):
        save_env({"OPENAI_API_KEY": "sk-a"})
        save_env({"DEEPGRAM_API_KEY": "dg-b"})  # must not clobber the first
        text = env_file.read_text()
    assert "OPENAI_API_KEY=sk-a" in text  # unquoted, plain KEY=value
    assert "DEEPGRAM_API_KEY=dg-b" in text


def test_save_env_creates_owner_only_secret_file(tmp_path):
    # Codex review (P1, 2026-07-14): the .env holds API keys and must never be
    # world-readable — regression guard against the 0644 `touch()` default.
    import stat

    env_file = tmp_path / ".env"
    with patch("anyscribecli.config.settings.ENV_FILE", env_file):
        save_env({"OPENAI_API_KEY": "sk-secret"})
    mode = stat.S_IMODE(env_file.stat().st_mode)
    assert mode == 0o600, f"expected 0600, got {mode:o}"


def test_save_env_tightens_preexisting_world_readable_file(tmp_path):
    import stat

    env_file = tmp_path / ".env"
    env_file.write_text("DEEPGRAM_API_KEY=dg\n")
    env_file.chmod(0o644)  # simulate a loosely-created file
    with patch("anyscribecli.config.settings.ENV_FILE", env_file):
        save_env({"OPENAI_API_KEY": "sk-a"})
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600


def test_forget_env_var_restores_value_inherited_from_shell():
    # Codex re-review (2026-07-14): deleting a saved key that is ALSO exported by
    # the parent shell must not disable the shell-provided credential.
    with (
        patch.dict("anyscribecli.config.settings._PRISTINE_ENV", {"XY_KEY": "from-shell"}),
        patch.dict(os.environ, {"XY_KEY": "from-env"}),
    ):
        forget_env_var("XY_KEY")
        assert os.environ["XY_KEY"] == "from-shell"  # inherited value retained


def test_forget_env_var_drops_key_not_inherited():
    with patch.dict("anyscribecli.config.settings._PRISTINE_ENV", {}, clear=True):
        with patch.dict(os.environ, {"XY_KEY": "session-only"}):
            forget_env_var("XY_KEY")
            assert "XY_KEY" not in os.environ


def test_provider_models_null_yaml_coerced_to_empty_dict():
    # A hand-edited bare `provider_models:` line parses to None — must not
    # crash `.get()` lookups in the orchestrator.
    from anyscribecli.config.settings import Settings

    for bad in (None, "hello", 7, ["x"]):
        s = Settings.from_dict({"provider_models": bad})
        assert s.provider_models == {}
    s = Settings.from_dict({"provider_models": {"openai": "gpt-transcribe"}})
    assert s.provider_models == {"openai": "gpt-transcribe"}


def test_extra_models_coerced_to_dict_of_lists():
    from anyscribecli.config.settings import Settings

    assert Settings().extra_models == {}
    for bad in (None, "hello", 7, ["x"]):
        assert Settings.from_dict({"extra_models": bad}).extra_models == {}
    # Non-list values are dropped; list entries are stringified.
    s = Settings.from_dict({"extra_models": {"openrouter": ["a/b", 7], "openai": "nope"}})
    assert s.extra_models == {"openrouter": ["a/b", "7"]}


def test_sargam_v25_pin_migrated_away(tmp_path):
    from anyscribecli.core.migrate import maybe_migrate_sargam_model

    cfg = tmp_path / "config.yaml"
    with patch("anyscribecli.config.settings.CONFIG_FILE", cfg):
        s = Settings(provider_models={"sargam": "saaras:v2.5", "openai": "whisper-1"})
        assert maybe_migrate_sargam_model(s) is True
        # Pin dropped (v3 is the default), unrelated pins untouched, config saved.
        assert s.provider_models == {"openai": "whisper-1"}
        assert "saaras" not in cfg.read_text()
        # Second run is a no-op and must not rewrite the file.
        assert maybe_migrate_sargam_model(s) is False
        assert maybe_migrate_sargam_model(Settings()) is False


def test_extra_models_round_trips_through_yaml(tmp_path):
    import yaml
    from anyscribecli.config.settings import Settings

    s = Settings(extra_models={"openrouter": ["vendor/x"]})
    assert Settings.from_dict(yaml.safe_load(yaml.dump(s.to_dict()))).extra_models == {
        "openrouter": ["vendor/x"]
    }
