"""Tests for Instagram settings migration.

Existing users have config.yaml files with `instagram.username` (and
historically `instagram.password`). After dropping these fields in the
yt-dlp migration, those configs must still load without error.
"""

from __future__ import annotations

from anyscribecli.config.settings import InstagramSettings, Settings


def test_legacy_username_field_is_discarded() -> None:
    data = {
        "provider": "openai",
        "instagram": {"username": "olduser"},
    }
    s = Settings.from_dict(data)
    assert isinstance(s.instagram, InstagramSettings)
    assert s.instagram.browser == ""
    # username field should not exist on the new dataclass
    assert not hasattr(s.instagram, "username")


def test_legacy_password_field_is_discarded() -> None:
    data = {
        "provider": "openai",
        "instagram": {"password": "should-not-be-stored"},
    }
    s = Settings.from_dict(data)
    assert s.instagram.browser == ""


def test_legacy_username_and_password_both_discarded() -> None:
    data = {
        "provider": "openai",
        "instagram": {"username": "olduser", "password": "ignored"},
    }
    s = Settings.from_dict(data)
    assert s.instagram.browser == ""


def test_new_browser_field_loads() -> None:
    data = {
        "provider": "openai",
        "instagram": {"browser": "firefox"},
    }
    s = Settings.from_dict(data)
    assert s.instagram.browser == "firefox"


def test_default_browser_is_empty() -> None:
    s = Settings()
    assert s.instagram.browser == ""


def test_to_dict_roundtrip_preserves_browser() -> None:
    s = Settings()
    s.instagram.browser = "chrome"
    d = s.to_dict()
    assert d["instagram"] == {"browser": "chrome"}
    s2 = Settings.from_dict(d)
    assert s2.instagram.browser == "chrome"
