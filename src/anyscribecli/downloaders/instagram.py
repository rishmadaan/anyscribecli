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
from anyscribecli.core.deps import ensure_ytdlp_current, get_command


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
