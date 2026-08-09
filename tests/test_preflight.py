"""Tests for pre-flight validation."""

from unittest.mock import patch

import pytest

from anyscribe.config.settings import Settings
from anyscribe.core.preflight import preflight_check


class TestPreflightCheck:
    @patch("anyscribe.core.preflight.shutil.which", return_value=None)
    def test_missing_ffmpeg(self, mock_which):
        with pytest.raises(RuntimeError, match="ffmpeg not found"):
            preflight_check(Settings(), "https://youtube.com/watch?v=x")

    @patch(
        "anyscribe.core.preflight.shutil.which",
        side_effect=lambda x: "/usr/bin/ffmpeg" if x == "ffmpeg" else None,
    )
    def test_missing_ffprobe(self, mock_which):
        with pytest.raises(RuntimeError, match="ffprobe not found"):
            preflight_check(Settings(), "https://youtube.com/watch?v=x")

    @patch("anyscribe.core.preflight.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch.dict("os.environ", {}, clear=True)
    def test_missing_api_key(self, mock_which):
        settings = Settings(provider="openai")
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY not set"):
            preflight_check(settings, "https://youtube.com/watch?v=x")

    @patch("anyscribe.core.preflight.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch.dict("os.environ", {}, clear=True)
    def test_missing_api_key_for_hand_edited_provider_alias(self, mock_which):
        # A hand-edited `provider: sarvam` used to sail through the key check
        # (PROVIDER_KEY_ENV.get on the raw name returns None => "needs no key"),
        # so the run only died on a 401 after downloading and converting.
        settings = Settings(provider="sarvam")
        with pytest.raises(RuntimeError, match="SARGAM_API_KEY not set"):
            preflight_check(settings, "https://youtube.com/watch?v=x")

    @patch("anyscribe.core.preflight.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch.dict("os.environ", {}, clear=True)
    def test_api_key_fix_hint_names_the_canonical_provider(self, mock_which):
        # The hint is a command the user pastes — it must say sargam_api_key,
        # which is the only spelling `config set` accepts for a key name.
        with pytest.raises(RuntimeError, match=r"config set sargam_api_key"):
            preflight_check(Settings(provider="sarvam"), "https://youtube.com/watch?v=x")

    @patch("anyscribe.core.preflight.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch.dict("os.environ", {}, clear=True)
    def test_missing_groq_api_key(self, mock_which):
        # Regression: groq had drifted out of preflight's provider->env map,
        # so a missing GROQ_API_KEY passed preflight and failed mid-run.
        settings = Settings(provider="groq")
        with pytest.raises(RuntimeError, match="GROQ_API_KEY not set"):
            preflight_check(settings, "https://youtube.com/watch?v=x")

    @patch("anyscribe.core.preflight.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    def test_unsupported_local_format(self, mock_which, tmp_path):
        bad_file = tmp_path / "file.xyz"
        bad_file.write_bytes(b"\x00")
        with pytest.raises(RuntimeError, match="Unsupported format"):
            preflight_check(Settings(), str(bad_file))

    @patch("anyscribe.core.preflight.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    def test_missing_local_file(self, mock_which):
        with pytest.raises(RuntimeError, match="File not found"):
            preflight_check(Settings(), "/nonexistent/file.mp3")

    @patch("anyscribe.core.preflight.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"})
    @patch("anyscribe.core.preflight.shutil.disk_usage")
    def test_low_disk_space(self, mock_disk, mock_which):
        mock_disk.return_value = type("Usage", (), {"free": 100 * 1024 * 1024})()  # 100MB
        with pytest.raises(RuntimeError, match="Low disk space"):
            preflight_check(Settings(), "https://youtube.com/watch?v=x")

    @patch("anyscribe.core.preflight.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch.dict("os.environ", {}, clear=True)
    def test_local_provider_no_key_needed(self, mock_which):
        settings = Settings(provider="local")
        # Should not raise — local provider doesn't need an API key
        preflight_check(settings, "https://youtube.com/watch?v=x")
