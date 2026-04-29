# Instagram → yt-dlp Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `instaloader` with `yt-dlp` for all Instagram reel/post downloads, eliminating the username+password storage requirement and the rate-limit-prone `test_login()` GraphQL probe.

**Architecture:** The new `InstagramDownloader` mirrors the existing `YouTubeDownloader` — yt-dlp via subprocess, JSON metadata extraction, single-step audio download with ffmpeg post-processing flags. Authentication, when needed, comes from the user's existing browser session via yt-dlp's `--cookies-from-browser` flag. No password is ever read or stored. The `instaloader` dependency is removed entirely. Existing users with `INSTAGRAM_PASSWORD` in `.env` see a one-time deprecation notice; the value is ignored, not deleted.

**Tech Stack:** Python 3.10+, yt-dlp (already a dependency, used via subprocess), httpx (already used elsewhere — not used here anymore), pytest, ruff. Frontend: React + TypeScript (one type-only change in `ui/src/api/types.ts`, no functional UI change required).

**Versioning:** Bumped to **0.8.3** (patch). The config-schema change is graceful — legacy `instagram.username` and `INSTAGRAM_PASSWORD` keys are silently discarded on load, so existing users see no errors and no manual migration is required.

---

## File Structure

**Modified:**
- `src/anyscribecli/downloaders/instagram.py` — full rewrite, ~80 LOC down from 175. Subprocess yt-dlp calls only. No `instaloader` import.
- `src/anyscribecli/config/settings.py` — `InstagramSettings`: drop `username`, add `browser: str = ""`. Update `from_dict` to silently discard legacy `username`/`password` keys. Drop `get_instagram_password` method.
- `src/anyscribecli/core/onboard_headless.py` — replace `instagram_username` and `instagram_password` parameters with `instagram_browser`. Stop writing `INSTAGRAM_PASSWORD` to `.env`.
- `src/anyscribecli/cli/onboard.py` — replace IG credential prompts with browser selector. Update `--instagram-*` typer flags. Update `_show_summary` IG line.
- `src/anyscribecli/web/routes/onboarding.py` — rename request fields `instagram_username`/`instagram_password` → `instagram_browser`. Pass through to headless backend.
- `ui/src/api/types.ts` — sync types to match backend schema change.
- `pyproject.toml` — remove `instaloader>=4.10`. Bump version to `0.8.3`.
- `src/anyscribecli/__init__.py` — bump `__version__` to `0.8.3`.
- `BACKLOG.md` — add 0.8.3 row.
- `src/anyscribecli/skill/SKILL.md` — update Instagram setup line.
- `src/anyscribecli/skill/references/commands.md` — update IG setup commands.
- `src/anyscribecli/skill/references/config.md` — update `instagram.*` section.
- `src/anyscribecli/skill/references/troubleshooting.md` — replace 401/login errors with cookie-related errors.
- `docs/user/getting-started.md` — IG setup steps.
- `docs/user/configuration.md` — `instagram.browser` field.
- `docs/user/providers.md` — IG section if present (verify in Task 12).
- `docs/building/_index.md` — new row pointing at the journal entry.

**Created:**
- `tests/test_instagram_downloader.py` — pattern matching, shortcode extraction, yt-dlp command shape (subprocess mocked).
- `tests/test_instagram_settings_migration.py` — old config (with `username`/`password` keys) still loads.
- `docs/building/journal/2026-04-29-instagram-yt-dlp-migration.md` — decision record.

**Deleted:**
- (None as files. `instaloader` removed via dep change, not file deletion.)

---

## Branching

- [ ] **Pre-Step: Create migration branch from main**

```bash
git checkout main && git pull --ff-only && git checkout -b instagram-yt-dlp-migration
```

Verify: `git status` shows clean working tree on the new branch. The currently-tracked modification to `src/anyscribecli/web/routes/transcribe.py` is unrelated — leave it untouched on `main`.

---

## Task 1: Capture current Instagram behavior we want to preserve in tests

The current downloader has two pieces of pure logic worth pinning before we rewrite: URL pattern matching (`can_handle`) and shortcode extraction. These shouldn't change across the migration — both `instaloader` and `yt-dlp` operate on the same shortcodes.

**Files:**
- Create: `tests/test_instagram_downloader.py`

- [ ] **Step 1: Write the pattern + shortcode tests**

```python
"""Tests for InstagramDownloader URL handling.

These tests pin behavior that must not regress across the instaloader→yt-dlp
migration: pattern matching and shortcode extraction. Network is never touched.
"""

from __future__ import annotations

import pytest

from anyscribecli.downloaders.instagram import InstagramDownloader


@pytest.fixture
def downloader() -> InstagramDownloader:
    return InstagramDownloader()


@pytest.mark.parametrize(
    "url",
    [
        "https://www.instagram.com/p/ABC123/",
        "https://instagram.com/p/ABC123",
        "https://www.instagram.com/reel/XYZ789/",
        "https://www.instagram.com/someuser/p/ABC123/",
        "https://www.instagram.com/someuser/reel/XYZ789/",
    ],
)
def test_can_handle_instagram_urls(downloader: InstagramDownloader, url: str) -> None:
    assert downloader.can_handle(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=abc",
        "https://twitter.com/user/status/123",
        "https://www.instagram.com/someuser/",  # profile, not a post/reel
        "not a url at all",
        "",
    ],
)
def test_rejects_non_instagram_post_urls(
    downloader: InstagramDownloader, url: str
) -> None:
    assert downloader.can_handle(url) is False


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.instagram.com/p/ABC123/", "ABC123"),
        ("https://www.instagram.com/p/ABC123", "ABC123"),
        ("https://www.instagram.com/reel/XYZ789/", "XYZ789"),
        ("https://www.instagram.com/reel/XYZ789?igsh=foo", "XYZ789"),
        ("https://www.instagram.com/someuser/p/ABC123/", "ABC123"),
        ("https://www.instagram.com/someuser/reel/XYZ789/", "XYZ789"),
    ],
)
def test_extract_shortcode(
    downloader: InstagramDownloader, url: str, expected: str
) -> None:
    assert downloader._extract_shortcode(url) == expected


def test_extract_shortcode_raises_on_bad_url(
    downloader: InstagramDownloader,
) -> None:
    with pytest.raises(ValueError, match="Could not extract shortcode"):
        downloader._extract_shortcode("https://example.com/foo")
```

- [ ] **Step 2: Run tests to verify they pass against current code**

Run: `pytest tests/test_instagram_downloader.py -v`
Expected: all 14+ test cases PASS. (We're pinning current behavior before changing implementation. If anything FAILs, the current regex/parsing has a bug — stop and investigate before continuing.)

- [ ] **Step 3: Commit**

```bash
git add tests/test_instagram_downloader.py
git commit -m "test: pin InstagramDownloader URL pattern + shortcode behavior

Pre-migration safety net. These tests must continue passing after the
yt-dlp rewrite — they cover pure logic (regex, parsing) that is
implementation-independent."
```

---

## Task 2: Rewrite InstagramDownloader using yt-dlp subprocess

This task swaps `instaloader` for `yt-dlp`. The shape mirrors `YouTubeDownloader`: `--dump-json` for metadata, then `--extract-audio` with ffmpeg post-processing flags for the audio file. Cookies are appended only when `instagram.browser` is configured.

**Files:**
- Modify: `src/anyscribecli/downloaders/instagram.py` (full rewrite)
- Modify: `tests/test_instagram_downloader.py` (add command-construction tests)

- [ ] **Step 1: Add failing tests for the new command construction**

Append the following to `tests/test_instagram_downloader.py`:

```python
from pathlib import Path
from unittest.mock import MagicMock, patch


@patch("anyscribecli.downloaders.instagram.load_config")
def test_build_ytdlp_args_no_browser_omits_cookies(
    mock_load_config: MagicMock, downloader: InstagramDownloader
) -> None:
    mock_settings = MagicMock()
    mock_settings.instagram.browser = ""
    mock_load_config.return_value = mock_settings

    args = downloader._build_ytdlp_cookie_args()

    assert args == []


@patch("anyscribecli.downloaders.instagram.load_config")
def test_build_ytdlp_args_with_browser_adds_cookies(
    mock_load_config: MagicMock, downloader: InstagramDownloader
) -> None:
    mock_settings = MagicMock()
    mock_settings.instagram.browser = "firefox"
    mock_load_config.return_value = mock_settings

    args = downloader._build_ytdlp_cookie_args()

    assert args == ["--cookies-from-browser", "firefox"]


@patch("anyscribecli.downloaders.instagram.subprocess.run")
@patch("anyscribecli.downloaders.instagram.load_config")
@patch("anyscribecli.downloaders.instagram.ensure_ytdlp_current")
def test_download_invokes_ytdlp_with_audio_flags(
    mock_ensure: MagicMock,
    mock_load_config: MagicMock,
    mock_run: MagicMock,
    downloader: InstagramDownloader,
    tmp_path: Path,
) -> None:
    """Sanity-check the shape of the yt-dlp invocation.

    Mocks subprocess so this test never touches the network. We only
    verify (a) metadata is fetched first via --dump-json, (b) audio
    download uses 16k mono 64k mp3 post-processor args matching Whisper
    optimization, (c) cookie args are passed through, and (d) the
    resulting mp3 is wrapped in a DownloadResult.
    """
    mock_settings = MagicMock()
    mock_settings.instagram.browser = "firefox"
    mock_load_config.return_value = mock_settings

    metadata = {
        "title": "Test Reel",
        "duration": 42.0,
        "uploader": "someuser",
        "description": "caption text",
    }
    import json as _json
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout=_json.dumps(metadata), stderr=""),
        MagicMock(returncode=0, stdout="", stderr=""),
    ]

    audio_file = tmp_path / "ABC123.mp3"
    audio_file.write_bytes(b"fake mp3 bytes")

    result = downloader.download(
        "https://www.instagram.com/reel/ABC123/", tmp_path
    )

    assert mock_run.call_count == 2
    meta_args = mock_run.call_args_list[0].args[0]
    dl_args = mock_run.call_args_list[1].args[0]

    assert "--dump-json" in meta_args
    assert "--cookies-from-browser" in meta_args
    assert "firefox" in meta_args

    assert "--extract-audio" in dl_args
    assert "--audio-format" in dl_args and "mp3" in dl_args
    assert any("16000" in a and "64k" in a for a in dl_args)
    assert "--cookies-from-browser" in dl_args

    assert result.platform == "instagram"
    assert result.title == "Test Reel"
    assert result.duration == 42.0
    assert result.channel == "someuser"
    assert result.description == "caption text"
    assert result.audio_path == audio_file
```

- [ ] **Step 2: Run new tests to verify they fail**

Run: `pytest tests/test_instagram_downloader.py -v`
Expected: the three new tests FAIL because `_build_ytdlp_cookie_args` doesn't exist and `download` still uses instaloader. Existing pattern/shortcode tests still PASS.

- [ ] **Step 3: Rewrite the downloader**

Replace the entire contents of `src/anyscribecli/downloaders/instagram.py` with:

```python
"""Instagram downloader using yt-dlp.

Replaces the previous instaloader-based implementation. yt-dlp:
  * Avoids authenticated GraphQL probing on every download (no test_login).
  * Reads cookies from the user's existing browser session — no password
    on disk.
  * Ships fixes within days when Instagram changes its extractor.

Public reels work without auth in many cases. For private reels (or when
Instagram throttles anonymous access), the user configures a browser via
``scribe config set instagram.browser firefox`` and yt-dlp pulls cookies
from that browser's profile via ``--cookies-from-browser``.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from anyscribecli.downloaders.base import AbstractDownloader, DownloadResult
from anyscribecli.config.settings import load_config


class InstagramDownloader(AbstractDownloader):
    """Download audio from Instagram reels/posts using yt-dlp."""

    PATTERNS = [
        r"instagram\.com(?:/[^/]+)?/p/",
        r"instagram\.com(?:/[^/]+)?/reel/",
    ]

    def can_handle(self, url: str) -> bool:
        return any(re.search(p, url) for p in self.PATTERNS)

    def _extract_shortcode(self, url: str) -> str:
        post_match = re.search(r"instagram\.com(?:/[^/]+)?/p/([^/?#&]+)", url)
        reel_match = re.search(r"instagram\.com(?:/[^/]+)?/reel/([^/?#&]+)", url)
        match = post_match or reel_match
        if not match:
            raise ValueError(f"Could not extract shortcode from Instagram URL: {url}")
        return match.group(1).split("/", 1)[0]

    def _build_ytdlp_cookie_args(self) -> list[str]:
        """Return ``--cookies-from-browser BROWSER`` if configured, else []."""
        settings = load_config()
        browser = (settings.instagram.browser or "").strip().lower()
        if not browser or browser == "none":
            return []
        return ["--cookies-from-browser", browser]

    def download(self, url: str, output_dir: Path) -> DownloadResult:
        from anyscribecli.core.deps import ensure_ytdlp_current, get_command

        ensure_ytdlp_current()
        ytdlp = get_command("yt-dlp")

        output_dir.mkdir(parents=True, exist_ok=True)
        shortcode = self._extract_shortcode(url)
        cookie_args = self._build_ytdlp_cookie_args()

        # Step 1: metadata
        meta_cmd = [*ytdlp, "--dump-json", "--no-download", *cookie_args, url]
        meta_result = subprocess.run(meta_cmd, capture_output=True, text=True, timeout=60)
        if meta_result.returncode != 0:
            raise RuntimeError(_friendly_error(meta_result.stderr))

        try:
            metadata = json.loads(meta_result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"yt-dlp returned invalid metadata: {e}")

        title = (metadata.get("title") or f"instagram-{shortcode}").strip()
        # Filename-safe title — keep only alphanumerics, spaces, dashes, underscores.
        safe_title = re.sub(r"[^\w\s-]", "", title)
        safe_title = re.sub(r"\s+", " ", safe_title).strip() or f"instagram-{shortcode}"

        duration = metadata.get("duration")
        channel = metadata.get("uploader") or metadata.get("uploader_id") or ""
        description = metadata.get("description") or ""

        # Step 2: download audio (16kHz mono 64kbps mp3 — Whisper-optimized)
        output_template = str(output_dir / f"{shortcode}.%(ext)s")
        dl_cmd = [
            *ytdlp,
            "--extract-audio",
            "--audio-format",
            "mp3",
            "--postprocessor-args",
            "ffmpeg:-ar 16000 -ac 1 -b:a 64k",
            "--output",
            output_template,
            "--no-playlist",
            "--no-overwrites",
            *cookie_args,
            url,
        ]
        dl_result = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=600)
        if dl_result.returncode != 0:
            raise RuntimeError(_friendly_error(dl_result.stderr))

        audio_path = output_dir / f"{shortcode}.mp3"
        if not audio_path.exists():
            # Fall back to glob in case yt-dlp picked a different shortcode form.
            mp3_files = sorted(output_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not mp3_files:
                raise RuntimeError("yt-dlp completed but no mp3 file was produced.")
            audio_path = mp3_files[0]

        return DownloadResult(
            audio_path=audio_path,
            title=safe_title,
            duration=duration,
            platform="instagram",
            original_url=url,
            channel=channel,
            description=description,
        )


def _friendly_error(stderr: str) -> str:
    """Translate common yt-dlp Instagram errors into actionable messages."""
    msg = (stderr or "").strip()
    lower = msg.lower()

    if "rate-limit reached" in lower or "login required" in lower or "login_required" in lower:
        return (
            "Instagram requires a login to fetch this reel.\n"
            "Configure cookies from your browser:\n"
            "  scribe config set instagram.browser firefox\n"
            "(supported: firefox, chrome, safari, brave, edge, chromium, vivaldi, opera)\n"
            "Then retry. If you're already configured, your browser session may have expired —\n"
            "open Instagram in that browser, log in, and try again."
        )
    if "private" in lower and "account" in lower:
        return (
            "This reel is from a private account.\n"
            "Configure cookies from a browser logged into an account that follows them:\n"
            "  scribe config set instagram.browser firefox"
        )
    if "video unavailable" in lower or "post not found" in lower or "not available" in lower:
        return (
            "This reel is not available — it may have been deleted, made private, or region-locked."
        )

    snippet = msg[:300] if msg else "yt-dlp failed with no error output"
    return f"Instagram download failed: {snippet}"
```

- [ ] **Step 4: Run all tests to verify**

Run: `pytest tests/test_instagram_downloader.py -v`
Expected: all tests PASS — pattern, shortcode, cookie-args, and download-shape.

- [ ] **Step 5: Run full suite to catch regressions**

Run: `pytest -x`
Expected: PASS. If anything fails, it's likely settings-related (next task) — note it but don't fix here.

- [ ] **Step 6: Commit**

```bash
git add src/anyscribecli/downloaders/instagram.py tests/test_instagram_downloader.py
git commit -m "feat(instagram): replace instaloader with yt-dlp subprocess

yt-dlp ships extractor fixes within days; instaloader is quarterly. yt-dlp
also supports --cookies-from-browser, eliminating the need to store an
Instagram password in .env. Same approach already used for YouTube.

The new error messages translate yt-dlp's 'rate-limit reached / login
required' cluster into actionable cookie-configuration steps."
```

---

## Task 3: Update settings — drop username/password, add browser

The `InstagramSettings` dataclass currently holds `username`. We replace it with `browser` (yt-dlp-supported browser name). `from_dict` must silently discard the legacy `username` key (and the historical `password` key it already drops) so existing config files load without error.

**Files:**
- Modify: `src/anyscribecli/config/settings.py`
- Create: `tests/test_instagram_settings_migration.py`

- [ ] **Step 1: Write failing migration tests**

Create `tests/test_instagram_settings_migration.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_instagram_settings_migration.py -v`
Expected: FAIL — `InstagramSettings` still has `username`, not `browser`.

- [ ] **Step 3: Update settings.py**

Edit `src/anyscribecli/config/settings.py`. Replace the `InstagramSettings` dataclass and the `Settings.from_dict` and `Settings.get_instagram_password` parts:

Find this block:

```python
@dataclass
class InstagramSettings:
    username: str = ""
    # password is NOT stored here — it lives in .env as INSTAGRAM_PASSWORD
```

Replace with:

```python
@dataclass
class InstagramSettings:
    """Instagram downloader configuration.

    ``browser`` is the name of a yt-dlp-supported browser (firefox, chrome,
    safari, brave, edge, chromium, vivaldi, opera) whose cookies will be
    used when downloading. Empty string = no cookies (anonymous fetch only,
    works for many public reels).

    Legacy fields ``username`` and ``password`` from pre-0.8.3 versions are
    silently discarded by ``Settings.from_dict``.
    """

    browser: str = ""
```

Find this block in `Settings.from_dict`:

```python
    @classmethod
    def from_dict(cls, data: dict) -> Settings:
        """Deserialize from a dict (loaded from YAML)."""
        ig_data = data.pop("instagram", {})
        # Drop password from config if it was there from old versions
        ig_data.pop("password", None)
        ig = InstagramSettings(**ig_data) if ig_data else InstagramSettings()
        return cls(instagram=ig, **data)
```

Replace with:

```python
    @classmethod
    def from_dict(cls, data: dict) -> Settings:
        """Deserialize from a dict (loaded from YAML)."""
        ig_data = data.pop("instagram", {}) or {}
        # Discard pre-0.8.3 fields. The yt-dlp migration removed username/password
        # — we read cookies from the user's browser instead.
        ig_data.pop("username", None)
        ig_data.pop("password", None)
        ig = InstagramSettings(**ig_data) if ig_data else InstagramSettings()
        return cls(instagram=ig, **data)
```

Find and **delete** this method (no replacement — yt-dlp does not need a password):

```python
    def get_instagram_password(self) -> str:
        """Get Instagram password from environment (stored in .env)."""
        return os.environ.get("INSTAGRAM_PASSWORD", "")
```

Then remove the now-unused `import os` if nothing else in the file uses it. Verify with `grep -n "^import os\|^from os" src/anyscribecli/config/settings.py` and `grep -n "os\." src/anyscribecli/config/settings.py` — if `os.` is referenced elsewhere, keep the import.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_instagram_settings_migration.py tests/test_instagram_downloader.py -v`
Expected: all PASS.

- [ ] **Step 5: Run full test suite**

Run: `pytest -x`
Expected: any failures should be from Tasks 4–7's call sites (`get_instagram_password`, `instagram_username`, `instagram_password` references). Note them — they'll be fixed in subsequent tasks. If the failure list contains anything *other* than those references, stop and investigate.

Quick scan for the call sites you'll need to fix next:

```bash
grep -rn "get_instagram_password\|instagram_username\|instagram_password\|INSTAGRAM_PASSWORD" src/ tests/
```

- [ ] **Step 6: Commit**

```bash
git add src/anyscribecli/config/settings.py tests/test_instagram_settings_migration.py
git commit -m "refactor(settings): drop instagram.username, add instagram.browser

Pre-0.8.3 configs with username/password keys still load — both are
silently discarded by Settings.from_dict. New field is browser, used
by the yt-dlp downloader to pull cookies via --cookies-from-browser."
```

---

## Task 4: Update headless onboarding — replace credentials with browser

`run_headless_onboard()` is the shared backend for the TUI wizard, the `--yes` flag, and the Web UI wizard. We swap its IG parameters in one place.

**Files:**
- Modify: `src/anyscribecli/core/onboard_headless.py`

- [ ] **Step 1: Update the function signature and body**

Edit `src/anyscribecli/core/onboard_headless.py`.

Find:

```python
    instagram_username: str | None = None,
    instagram_password: str | None = None,
```

Replace with:

```python
    instagram_browser: str | None = None,
```

Find:

```python
    if instagram_username is not None:
        settings.instagram.username = instagram_username
```

Replace with:

```python
    if instagram_browser is not None:
        settings.instagram.browser = instagram_browser
```

Find:

```python
    if instagram_password:
        env_keys["INSTAGRAM_PASSWORD"] = instagram_password
```

Delete this block entirely (no replacement — we no longer write `INSTAGRAM_PASSWORD`).

- [ ] **Step 2: Update the docstring if it mentions Instagram**

Search the function's docstring for "instagram" — if absent (likely is), skip. If present, update wording.

```bash
grep -n -i instagram src/anyscribecli/core/onboard_headless.py
```

- [ ] **Step 3: Run targeted tests**

Run: `pytest tests/test_onboard_headless.py -v`
Expected: any test that referenced `instagram_username` / `instagram_password` will now fail with TypeError. Update them to use `instagram_browser` (or drop the IG-specific assertion entirely if it was only smoke-coverage). If there are no IG-specific tests in that file, all tests should PASS.

```bash
grep -n -i instagram tests/test_onboard_headless.py
```

If matches found, edit each: replace `instagram_username="..."` with `instagram_browser="firefox"` and remove `instagram_password=...`. Replace assertions about `INSTAGRAM_PASSWORD` in `env_keys` with assertions that the password is **not** written.

- [ ] **Step 4: Commit**

```bash
git add src/anyscribecli/core/onboard_headless.py tests/test_onboard_headless.py
git commit -m "refactor(onboard): replace ig username/password with ig browser

The shared headless onboarding backend now takes a single instagram_browser
parameter instead of username+password. Browser name (firefox/chrome/etc)
flows into config; no secret is written to .env."
```

---

## Task 5: Update CLI `scribe onboard` flow

The interactive TUI wizard prompts for IG credentials. Replace those prompts with a browser selector. The non-interactive `--yes` flag's `--instagram-*` typer options also change.

**Files:**
- Modify: `src/anyscribecli/cli/onboard.py`

- [ ] **Step 1: Update the typer flag definitions**

Find this block (around lines 336–342):

```python
    instagram_username: Optional[str] = typer.Option(
        None, "--instagram-username", help="Instagram username (optional)."
    ),
    instagram_password: Optional[str] = typer.Option(
        None,
        "--instagram-password",
        help="Instagram password (optional, stored in .env).",
    ),
```

Replace with:

```python
    instagram_browser: Optional[str] = typer.Option(
        None,
        "--instagram-browser",
        help=(
            "Browser to read Instagram cookies from "
            "(firefox/chrome/safari/brave/edge/chromium/vivaldi/opera). "
            "Optional — only needed for private reels or when anonymous "
            "fetches are throttled."
        ),
    ),
```

- [ ] **Step 2: Update the parameter forwarding to `run_headless_onboard`**

There are two call sites — the headless `--yes` path (around line 103) and a separate path (around line 363). For each, find:

```python
            instagram_username=instagram_username,
            instagram_password=instagram_password,
```

Replace with:

```python
            instagram_browser=instagram_browser,
```

- [ ] **Step 3: Update the validation/echo block (around line 379)**

Find:

```python
        "--instagram-username": instagram_username,
        "--instagram-password": instagram_password,
```

Replace with:

```python
        "--instagram-browser": instagram_browser,
```

- [ ] **Step 4: Replace the interactive Instagram step in the TUI wizard**

Find the block starting around line 533 (search for "Step 6: Instagram"). Replace the entire block from the `# Step 6: Instagram credentials` comment through the closing of the `if change_ig:` block (ending around line 561) with:

```python
    # Step 6: Instagram cookies (browser selection)
    BROWSER_CHOICES = [
        "none (anonymous — works for many public reels)",
        "firefox",
        "chrome",
        "safari",
        "brave",
        "edge",
        "chromium",
        "vivaldi",
        "opera",
    ]
    BROWSER_VALUES = ["", "firefox", "chrome", "safari", "brave", "edge", "chromium", "vivaldi", "opera"]

    existing_browser = settings.instagram.browser
    change_ig = True
    if reconfiguring and existing_browser:
        console.print(f"\n  [bold]Instagram cookies:[/bold] {existing_browser}")
        change_ig = bconfirm("  Change Instagram cookie source?")
    else:
        console.print(
            Panel(
                "Instagram downloads use yt-dlp.\n"
                "Public reels often work without auth. For private reels or when\n"
                "anonymous fetches are throttled, scribe can read cookies from\n"
                "your browser — no password is ever stored.\n\n"
                "[dim]Pick 'none' to skip; you can always set this later with\n"
                "[/dim][cyan]scribe config set instagram.browser firefox[/cyan]",
                title="Instagram (Optional)",
                border_style="blue",
            )
        )
        change_ig = bconfirm("  Configure Instagram cookies now?")

    if change_ig:
        default_idx = BROWSER_VALUES.index(existing_browser) if existing_browser in BROWSER_VALUES else 0
        choice = bselect(
            BROWSER_CHOICES,
            cursor_index=default_idx,
            cursor="❯ ",
            cursor_style="cyan",
        )
        if choice is None:
            settings.instagram.browser = ""
        else:
            settings.instagram.browser = BROWSER_VALUES[BROWSER_CHOICES.index(choice)]
        if settings.instagram.browser:
            console.print(f"\n  [green]Selected:[/green] cookies from {settings.instagram.browser}\n")
        else:
            console.print("\n  [green]Selected:[/green] no cookies (anonymous)\n")
```

- [ ] **Step 5: Update the summary printer (around line 761)**

Find:

```python
        f"configured ({settings.instagram.username})"
        if settings.instagram.username
```

Replace with:

```python
        f"cookies from {settings.instagram.browser}"
        if settings.instagram.browser
```

If the surrounding context says "Instagram: configured (X)" — change the label too if needed for grammar. Read 5 lines of context around the line and adjust naturally.

- [ ] **Step 6: Add deprecation notice for legacy INSTAGRAM_PASSWORD**

Just before the wizard exits successfully (find the "[green]Onboarding complete" line or equivalent — search `grep -n "complete\|Done" src/anyscribecli/cli/onboard.py` for the right spot), add:

```python
    if os.environ.get("INSTAGRAM_PASSWORD"):
        console.print(
            "\n  [yellow]Note:[/yellow] An [bold]INSTAGRAM_PASSWORD[/bold] entry was found in your .env file.\n"
            "  scribe 0.8.3+ no longer uses it — Instagram downloads now go through yt-dlp\n"
            "  with browser cookies. You can safely remove that line from\n"
            f"  [dim]{ENV_FILE}[/dim] when convenient."
        )
```

The import for `ENV_FILE` may need adding — check `grep -n "ENV_FILE" src/anyscribecli/cli/onboard.py`. If not imported, add `from anyscribecli.config.paths import ENV_FILE` to the existing imports near the top.

- [ ] **Step 7: Run tests + smoke the CLI**

Run: `pytest tests/test_onboard_agent_cli.py -v`
Expected: any test that asserted on the old IG fields will fail. Update them: replace `--instagram-username` with `--instagram-browser`, drop `--instagram-password`.

Smoke test the help text:

```bash
python -m anyscribecli onboard --help
```

Expected: `--instagram-browser` listed, no `--instagram-username` or `--instagram-password`.

- [ ] **Step 8: Commit**

```bash
git add src/anyscribecli/cli/onboard.py tests/test_onboard_agent_cli.py
git commit -m "feat(onboard): swap IG credential prompts for browser selector

The TUI wizard now offers an arrow-key browser picker (firefox/chrome/
safari/brave/edge/chromium/vivaldi/opera/none). The --yes flag exposes
--instagram-browser; the old --instagram-username/--instagram-password
options are removed.

Existing INSTAGRAM_PASSWORD entries in .env trigger a one-line
deprecation notice on first re-onboard."
```

---

## Task 6: Update web onboarding API + frontend types

The Web UI's onboarding wizard does not collect Instagram fields (per the comment in `OnboardingWizard.tsx`), so there is no UI rendering change. We only update the API request schema and the TypeScript types so the contract stays in sync.

**Files:**
- Modify: `src/anyscribecli/web/routes/onboarding.py`
- Modify: `ui/src/api/types.ts`

- [ ] **Step 1: Update the FastAPI request model**

Edit `src/anyscribecli/web/routes/onboarding.py`.

Find:

```python
    instagram_username: Optional[str] = None
    instagram_password: Optional[str] = None
```

Replace with:

```python
    instagram_browser: Optional[str] = None
```

Find:

```python
            instagram_username=req.instagram_username,
            instagram_password=req.instagram_password,
```

Replace with:

```python
            instagram_browser=req.instagram_browser,
```

- [ ] **Step 2: Update the TypeScript types**

Edit `ui/src/api/types.ts`.

Find:

```typescript
  instagram: { username: string };
```

Replace with:

```typescript
  instagram: { browser: string };
```

Find:

```typescript
  instagram_username?: string;
  instagram_password?: string;
```

Replace with:

```typescript
  instagram_browser?: string;
```

- [ ] **Step 3: Verify nothing else in the frontend references the old fields**

```bash
grep -rn "instagram_username\|instagram_password\|instagram\.username" ui/src
```

Expected: no matches. If anything remains, update it (likely in `HistoryPage.tsx`, `TranscribePage.tsx`, or `URLInput.tsx`) — read the surrounding code and adapt. If a UI surfaces the IG username for display only, replace with the browser name or remove entirely.

- [ ] **Step 4: Build the frontend to verify TS compiles**

Run: `cd ui && npm run build && cd ..`
Expected: build succeeds. The output goes to `src/anyscribecli/web/static/` — yes, this commit should include the rebuilt static assets (the project commits the bundle).

- [ ] **Step 5: Run web onboarding tests**

Run: `pytest tests/test_web_onboarding.py -v`
Expected: any test that posted `instagram_username` / `instagram_password` to the API will fail. Update them to send `instagram_browser`.

- [ ] **Step 6: Commit**

```bash
git add src/anyscribecli/web/routes/onboarding.py ui/src/api/types.ts src/anyscribecli/web/static tests/test_web_onboarding.py
git commit -m "feat(web): rename IG onboarding fields to instagram_browser

API request schema and TS types follow the headless onboarding rename.
The OnboardingWizard component does not surface IG fields, so no UI
copy changes are needed. Static bundle rebuilt."
```

---

## Task 7: Remove instaloader dependency + bump version

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/anyscribecli/__init__.py`
- Modify: `BACKLOG.md`

- [ ] **Step 1: Remove instaloader from dependencies**

Edit `pyproject.toml`. In the `[project]` `dependencies = [...]` list, find:

```
    "instaloader>=4.10",
```

Delete this line entirely.

- [ ] **Step 2: Bump version in pyproject.toml**

Find:

```
version = "0.8.2"
```

Replace with:

```
version = "0.8.3"
```

- [ ] **Step 3: Bump version in __init__.py**

Edit `src/anyscribecli/__init__.py`. Find `__version__ = "0.8.2"` and change to `"0.8.3"`.

```bash
grep -n "__version__" src/anyscribecli/__init__.py
```

- [ ] **Step 4: Update BACKLOG.md**

Read the current BACKLOG.md to understand the format:

```bash
head -80 BACKLOG.md
```

Add a row/section for `0.8.3` matching the existing style. The headline should be:

```
0.8.3 — Instagram migrates to yt-dlp; instaloader removed
```

Bullets should mention:
- Replace instaloader with yt-dlp via subprocess
- Drop INSTAGRAM_PASSWORD requirement; use --cookies-from-browser
- Config schema: instagram.username + INSTAGRAM_PASSWORD → instagram.browser (legacy keys silently discarded)

- [ ] **Step 5: Verify install works**

Run: `pip install -e .` from the repo root.
Expected: succeeds without instaloader being pulled. `pip show instaloader` will still show it installed locally (we don't uninstall) — that's fine, fresh installs won't pull it.

- [ ] **Step 6: Run full test suite**

Run: `pytest`
Expected: ALL tests PASS.

Run: `ruff check src/`
Expected: clean. If `ruff` flags an unused import (likely `instaloader` somewhere we missed, or `os` in settings.py), fix it.

Run: `ruff format src/ --check`
Expected: clean. If not, run `ruff format src/` and stage the formatting changes.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/anyscribecli/__init__.py BACKLOG.md
git commit -m "chore: bump to 0.8.3; remove instaloader dependency

Instagram downloads now use yt-dlp (already a dependency for YouTube).
instaloader is no longer needed."
```

---

## Task 8: Update Claude Code skill files

The skill is the primary user-facing surface (per CLAUDE.md). Stale skill = broken product. Touch all four files.

**Files:**
- Modify: `src/anyscribecli/skill/SKILL.md`
- Modify: `src/anyscribecli/skill/references/commands.md`
- Modify: `src/anyscribecli/skill/references/config.md`
- Modify: `src/anyscribecli/skill/references/troubleshooting.md`

- [ ] **Step 1: Read each skill file and locate IG sections**

```bash
grep -n -i "instagram\|INSTAGRAM" src/anyscribecli/skill/SKILL.md src/anyscribecli/skill/references/*.md
```

- [ ] **Step 2: SKILL.md — update Instagram command snippet and any decision-tree mention**

In `src/anyscribecli/skill/SKILL.md`, find any line referencing `scribe config set instagram.username` or instructions to set `INSTAGRAM_PASSWORD`. Replace the setup snippet with:

```
For Instagram reels — public reels usually work with no setup.
For private reels or rate-limited cases, configure cookies from a browser:
  scribe config set instagram.browser firefox
(supported: firefox, chrome, safari, brave, edge, chromium, vivaldi, opera)
```

If there's a "safety rules" or "do not" section that mentions storing passwords, remove the IG-password-specific bullet.

- [ ] **Step 3: commands.md — update the `scribe onboard` flag table and IG examples**

In `src/anyscribecli/skill/references/commands.md`:

Find any table row or example with `--instagram-username` or `--instagram-password`. Replace with `--instagram-browser BROWSER` (one row), and update the description column to: "Browser to read IG cookies from. Optional — only needed for private reels."

If there's a standalone "Instagram setup" example, replace it with:

```bash
# Configure browser for IG cookies (only if needed)
scribe config set instagram.browser firefox
```

- [ ] **Step 4: config.md — rewrite the `instagram.*` settings section**

In `src/anyscribecli/skill/references/config.md`, find the section describing `instagram.username` and the related `.env` key `INSTAGRAM_PASSWORD`. Replace with:

```markdown
### `instagram.browser`

Browser to read Instagram cookies from. yt-dlp uses this when downloading reels.
Empty string means anonymous (no cookies). Many public reels work without
cookies; private reels and rate-limited fetches need this set.

Supported values: `firefox`, `chrome`, `safari`, `brave`, `edge`, `chromium`,
`vivaldi`, `opera`, or empty.

Example:

```bash
scribe config set instagram.browser firefox
```

> **Pre-0.8.3 users:** the older `instagram.username` field and the
> `INSTAGRAM_PASSWORD` entry in `.env` are no longer used. They're silently
> ignored on load and can be removed when convenient.
```

- [ ] **Step 5: troubleshooting.md — replace IG 401/login errors**

In `src/anyscribecli/skill/references/troubleshooting.md`, find any entry referencing instaloader-style errors ("Please wait a few minutes", `test_login`, "401 Unauthorized" for IG, "BadCredentialsException", "TwoFactorAuthRequired"). Replace the IG section with:

```markdown
### Instagram: "rate-limit reached" or "login required"

The reel is gated behind login. Configure cookies from a browser logged into
Instagram:

```bash
scribe config set instagram.browser firefox
```

Then retry. If you've already configured a browser and still see this:
1. Open Instagram in that browser and confirm you're logged in.
2. Visit the reel URL in that same browser to confirm you can view it.
3. If it loads in the browser but not via scribe, your cookie store may be
   locked by the running browser — quit the browser and retry.

### Instagram: "private account"

The reel is from a private account. Cookies from a browser logged into an
account that follows the poster will work; cookies from a different account
won't.

### Instagram: "video unavailable" / "post not found"

The reel was deleted, made private, or is region-locked. There's no
client-side fix.
```

- [ ] **Step 6: Commit**

```bash
git add src/anyscribecli/skill/
git commit -m "docs(skill): update IG sections for yt-dlp + browser cookies

SKILL.md, commands.md, config.md, troubleshooting.md all rewritten to
describe the new instagram.browser config field, drop references to
INSTAGRAM_PASSWORD, and replace the 401/test_login error entry with the
yt-dlp 'rate-limit reached / login required' cluster."
```

---

## Task 9: Update user-facing docs

**Files:**
- Modify: `docs/user/getting-started.md`
- Modify: `docs/user/configuration.md`
- Modify: `docs/user/providers.md`

- [ ] **Step 1: Locate IG references in user docs**

```bash
grep -n -i "instagram\|INSTAGRAM" docs/user/*.md
```

For each file with matches, follow the same content updates as the skill files (Task 8) — but with the "semi-technical audience who may be new to CLI tools" tone called out in CLAUDE.md.

- [ ] **Step 2: getting-started.md — IG setup section**

Find any "Instagram setup" or "credentials" section. Replace with a copy-paste-ready snippet:

```markdown
## Instagram (optional)

Public reels usually work out of the box. If you hit rate-limiting, or want
to transcribe reels from accounts you follow, scribe can read your existing
browser session — no password needed:

```bash
scribe config set instagram.browser firefox
```

Supported browsers: `firefox`, `chrome`, `safari`, `brave`, `edge`, `chromium`,
`vivaldi`, `opera`.

> **Tip:** Firefox tends to work most reliably on macOS. Chrome's cookie
> encryption can make extraction flakier.

> **Note for upgraders:** If you onboarded with scribe < 0.8.3, you may have
> an `INSTAGRAM_PASSWORD` in your `~/.anyscribecli/.env`. It's no longer used
> and can be removed.
```

- [ ] **Step 3: configuration.md — `instagram.browser` field reference**

Find the `instagram.*` section. Replace with the same content shape as in `skill/references/config.md` (Task 8 Step 4), tone-adjusted for the broader user-doc audience (define "cookies", "browser session" if first use).

- [ ] **Step 4: providers.md — verify IG is mentioned correctly**

```bash
grep -n -i instagram docs/user/providers.md
```

If IG is listed as a "downloader" rather than a transcription provider (likely a confusion in the doc), check what's actually said — only update if it references the old credentials/auth flow. Don't restructure the doc beyond that.

- [ ] **Step 5: Commit**

```bash
git add docs/user/
git commit -m "docs(user): update Instagram instructions for 0.8.3 yt-dlp flow

getting-started, configuration, providers — all rewritten to describe
instagram.browser config and the cookie-based flow. Pre-0.8.3 upgrade
notes added."
```

---

## Task 10: Write the building journal entry

**Files:**
- Create: `docs/building/journal/2026-04-29-instagram-yt-dlp-migration.md`
- Modify: `docs/building/_index.md`

- [ ] **Step 1: Confirm the journal frontmatter format used in the repo**

```bash
head -15 docs/building/journal/$(ls docs/building/journal | tail -1)
```

Use the same shape (type, tags, tldr).

- [ ] **Step 2: Write the journal entry**

Create `docs/building/journal/2026-04-29-instagram-yt-dlp-migration.md` with:

```markdown
---
type: decision
tags: [instagram, downloader, yt-dlp, instaloader, migration]
tldr: Replaced instaloader with yt-dlp for Instagram. No more password on disk; rate-limit-prone test_login() probe gone.
---

# Instagram → yt-dlp migration (0.8.3)

## Problem

`instaloader` calls authenticated GraphQL endpoints (`test_login()`,
`Post.from_shortcode`) on every download. Instagram's anti-automation
heuristic flags this pattern, especially under burst usage from
`scribe ui`. Users hit `401 Unauthorized — "Please wait a few minutes
before you try again"` even with valid sessions.

The library also forced users to put `INSTAGRAM_PASSWORD` in `.env`,
which was poor hygiene for a privacy-first local app. The Dropzone
"Instagram Downloader" bundle uses the same library with the same
flow — it works only because of light, manual, drag-by-drag usage; not
because the library is robust.

## Decision

Drop `instaloader`. Use `yt-dlp` as the sole Instagram downloader,
called via subprocess (matching the existing `YouTubeDownloader`
pattern). For private/throttled cases, read cookies from the user's
browser via `--cookies-from-browser`. No password ever stored.

## Why yt-dlp

- Nightly extractor fixes (instaloader is quarterly).
- Already a project dependency for YouTube — no new tool.
- Browser-cookie auth uses real session, doesn't trigger heuristics.
- Higher quality ceiling (1080p vs instaloader's 720p).
- Public reels often work with no auth at all.

## Alternatives considered

- **gallery-dl**: image-oriented; its own ecosystem routes reels to
  yt-dlp anyway.
- **instagrapi**: documented account-ban risk; requires user/pass.
- **Playwright/Selenium**: heavy install footprint; reinventing yt-dlp.

## Migration

- Config schema: `instagram.username` (config.yaml) + `INSTAGRAM_PASSWORD`
  (.env) → `instagram.browser` (config.yaml). Old keys silently discarded
  on load; users see a deprecation notice during re-onboard.
- TUI / `--yes` / Web UI: shared `run_headless_onboard()` rewritten;
  `instagram_username` + `instagram_password` parameters → `instagram_browser`.
- Skill + user docs rewritten end-to-end.

## Source URLs (verified 2026-04-29)

- yt-dlp issue tracker: https://github.com/yt-dlp/yt-dlp/issues/7165 (canonical IG login issue)
- instaloader rate-limit reports: issues #2426, #2501, #2511, #2532, #2568, #2682
- instaloader ban warning: #2555
```

- [ ] **Step 3: Update `docs/building/_index.md`**

Read the index to see the format:

```bash
head -20 docs/building/_index.md
```

Add a new row (newest first) pointing at the journal entry. Match the existing column format exactly — date, slug/title, type, summary.

- [ ] **Step 4: Commit**

```bash
git add docs/building/journal/2026-04-29-instagram-yt-dlp-migration.md docs/building/_index.md
git commit -m "docs(building): journal entry for IG yt-dlp migration

Decision record explaining why instaloader was dropped, why yt-dlp
won the comparison, what alternatives were considered, and how the
config schema migrates."
```

---

## Task 11: Manual smoke test

Automated tests can't verify that yt-dlp actually downloads a reel — that requires hitting Instagram. Do this once, end-to-end, before merging.

**No file changes.**

- [ ] **Step 1: Smoke test the anonymous path**

Pick a public reel (any creator's recent post). Run:

```bash
python -m anyscribecli transcribe "https://www.instagram.com/reel/<SHORTCODE>/" --json
```

Expected: a JSON result with `audio_path`, `title`, `duration`. The mp3 should land in `~/.anyscribecli/downloads/audio/`. Markdown should land in the workspace.

- [ ] **Step 2: Smoke test the cookies path**

```bash
scribe config set instagram.browser firefox
```

(Substitute your actual browser if not Firefox. If yt-dlp errors on cookie extraction, check that the browser is fully closed — some browsers lock the cookie SQLite while running.)

Run the same `transcribe` command on the same reel. Expected: same successful result, but the yt-dlp log should mention reading cookies from the browser profile.

- [ ] **Step 3: Smoke test error translation**

Try a known-deleted or private reel from an account you don't follow. Expected: a clean error message matching one of the `_friendly_error` branches (e.g., "This reel requires login..." or "This reel is not available...").

- [ ] **Step 4: Smoke test the Web UI**

```bash
scribe ui
```

Open `http://127.0.0.1:8457`, paste an Instagram reel URL, run a transcription. Expected: success, same as CLI.

- [ ] **Step 5: Smoke test onboarding**

```bash
scribe onboard --force
```

Expected: the IG step now shows the browser arrow-key picker, not username/password prompts. If you have `INSTAGRAM_PASSWORD` in your `.env`, the deprecation notice prints at the end.

- [ ] **Step 6: If anything fails in steps 1–5**

Stop. Do not merge. Diagnose the failure, add a regression test if applicable, fix, repeat the smoke test.

---

## Task 12: Final sweep + PR

- [ ] **Step 1: Run the full verification chain**

```bash
pytest && ruff check src/ && ruff format src/ --check
```

Expected: all pass.

- [ ] **Step 2: Verify no instaloader references remain**

```bash
grep -rn -i "instaloader\|INSTAGRAM_PASSWORD" src/ tests/ docs/ ui/src/ pyproject.toml
```

Expected: only matches are intentional — the deprecation notice in `cli/onboard.py` (mentions `INSTAGRAM_PASSWORD` to tell users to remove it), the legacy-key-discard logic in `settings.py` and its test, and the journal entry. **No imports, no calls, no documentation telling users to set IG_PASSWORD.**

- [ ] **Step 3: Verify version bump is consistent**

```bash
grep -n "0.8.3\|0.8.2" src/anyscribecli/__init__.py pyproject.toml
```

Expected: both files show `0.8.3`. No stale `0.8.2` mentions anywhere code-side.

- [ ] **Step 4: Push and open the PR**

```bash
git push -u origin instagram-yt-dlp-migration
gh pr create --title "Instagram: migrate from instaloader to yt-dlp (0.8.3)" --body "$(cat <<'EOF'
## Summary
- Replace `instaloader` with `yt-dlp` for all Instagram reel/post downloads
- Drop `INSTAGRAM_PASSWORD` requirement; use `--cookies-from-browser` instead
- Config schema: `instagram.username` + `INSTAGRAM_PASSWORD` → `instagram.browser`
- Bump to 0.8.3 (config schema break)

## Why
`instaloader` probes authenticated GraphQL on every download — Instagram's
anti-automation flags the pattern under regular usage and returns
`401 Unauthorized — "Please wait a few minutes before you try again"`.
`yt-dlp` ships extractor fixes daily, supports cookies from the browser
(no password on disk), and is already a project dependency for YouTube.

See `docs/building/journal/2026-04-29-instagram-yt-dlp-migration.md`
for the full decision record.

## Migration for existing users
- Pre-0.8.3 config files load fine — `instagram.username` and `INSTAGRAM_PASSWORD`
  are silently discarded.
- A one-time deprecation notice prints during `scribe onboard` if
  `INSTAGRAM_PASSWORD` is still in `.env`.
- New config: `scribe config set instagram.browser firefox` (only needed for
  private reels or throttled cases).

## Test plan
- [x] Pattern + shortcode tests (no network)
- [x] Settings migration tests (legacy keys discarded)
- [x] yt-dlp command-construction tests (subprocess mocked)
- [x] Web onboarding API tests
- [x] CLI agent tests
- [ ] Manual smoke: public reel via CLI (anonymous)
- [ ] Manual smoke: public reel via CLI (with browser cookies)
- [ ] Manual smoke: deleted/private reel error translation
- [ ] Manual smoke: Web UI transcribe an IG reel
- [ ] Manual smoke: `scribe onboard --force` shows browser picker

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 5: Wait for CI green, then merge**

Don't merge before checking the manual smoke-test boxes in the PR description.

---

## Done criteria

- `pytest` green; `ruff check src/` clean; `ruff format src/ --check` clean.
- `grep -rn instaloader src/` empty.
- A public Instagram reel transcribes end-to-end via CLI and Web UI.
- `scribe onboard --force` shows the browser picker, not username/password prompts.
- `pyproject.toml` and `__init__.py` both report `0.8.3`.
- Journal entry exists and is linked from `_index.md`.
- All four skill files updated.
- All three user docs updated.
