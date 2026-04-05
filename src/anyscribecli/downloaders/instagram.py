"""Instagram downloader using instaloader.

Mirrors the Dropzone Instagram Downloader bundle pattern:
session caching, login with test_login fallback, shortcode extraction.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import httpx
import instaloader

from anyscribecli.downloaders.base import AbstractDownloader, DownloadResult
from anyscribecli.config.paths import SESSIONS_DIR
from anyscribecli.config.settings import load_config


class InstagramDownloader(AbstractDownloader):
    """Download video/audio from Instagram using instaloader for auth + direct video download."""

    PATTERNS = [
        r"instagram\.com(?:/[^/]+)?/p/",
        r"instagram\.com(?:/[^/]+)?/reel/",
    ]

    def can_handle(self, url: str) -> bool:
        return any(re.search(p, url) for p in self.PATTERNS)

    def _extract_shortcode(self, url: str) -> str:
        """Extract the post/reel shortcode from an Instagram URL."""
        post_match = re.search(r"instagram\.com(?:/[^/]+)?/p/([^/?#&]+)", url)
        reel_match = re.search(r"instagram\.com(?:/[^/]+)?/reel/([^/?#&]+)", url)

        match = post_match or reel_match
        if not match:
            raise ValueError(f"Could not extract shortcode from Instagram URL: {url}")

        return match.group(1).split("/", 1)[0]

    def _get_instaloader(self) -> instaloader.Instaloader:
        """Create and authenticate an Instaloader instance.

        Mirrors Dropzone bundle: load session → test_login → fresh login if invalid → save.
        """
        L = instaloader.Instaloader(
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
        )
        settings = load_config()
        username = settings.instagram.username
        password = settings.get_instagram_password()

        if not username or not password:
            raise RuntimeError(
                "Instagram credentials not configured.\n"
                "Run: scribe config set instagram.username YOUR_USERNAME\n"
                "Add INSTAGRAM_PASSWORD=YOUR_PASSWORD to ~/.anyscribecli/.env\n"
                "Or re-run: scribe onboard --force"
            )

        session_file = SESSIONS_DIR / "instagram_session"
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

        # Load existing session if available
        if session_file.exists():
            try:
                L.load_session_from_file(username, filename=str(session_file))
                if L.test_login() is not None:
                    return L  # Session still valid
            except Exception:
                pass  # Session invalid, will re-login

        # Fresh login
        try:
            L.login(username, password)
            L.save_session_to_file(str(session_file))
        except instaloader.exceptions.BadCredentialsException:
            raise RuntimeError(
                "Instagram login failed: incorrect username or password.\n"
                "Check your credentials: scribe config show\n"
                "Update them: scribe config set instagram.username YOUR_USERNAME"
            )
        except instaloader.exceptions.TwoFactorAuthRequiredException:
            raise RuntimeError(
                "Instagram requires two-factor authentication.\n"
                "Use an account without 2FA, or generate an app-specific password."
            )
        except Exception as e:
            raise RuntimeError(
                f"Instagram login failed: {e}\n"
                "This can happen when:\n"
                "  - Credentials are wrong\n"
                "  - Instagram temporarily blocked the login (try again later)\n"
                "  - The account has 2FA enabled\n"
                "Tip: Use a secondary/dummy account for scribe."
            )

        return L

    def download(self, url: str, output_dir: Path) -> DownloadResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        shortcode = self._extract_shortcode(url)

        L = self._get_instaloader()
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        title = post.caption[:80].strip() if post.caption else f"instagram-{shortcode}"
        # Clean title for filename
        title = re.sub(r"[^\w\s-]", "", title)
        title = re.sub(r"\s+", " ", title).strip()
        if not title:
            title = f"instagram-{shortcode}"

        if not post.is_video:
            raise RuntimeError(
                "This Instagram post is an image, not a video.\n"
                "scribe can only transcribe video/audio content."
            )

        duration = post.video_duration

        # Download video directly via URL (faster than download_post)
        video_url = post.video_url
        if not video_url:
            raise RuntimeError(
                "Could not get video URL from Instagram.\n"
                "The post may be private, or Instagram may be rate-limiting.\n"
                "Try again in a few minutes, or check your credentials."
            )

        video_path = output_dir / f"{shortcode}.mp4"
        response = httpx.get(video_url, follow_redirects=True, timeout=120.0)
        if response.status_code != 200:
            raise RuntimeError(f"Failed to download video: HTTP {response.status_code}")
        video_path.write_bytes(response.content)

        # Extract audio optimized for Whisper using ffmpeg
        audio_path = output_dir / f"{shortcode}.mp3"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-b:a",
            "64k",
            "-f",
            "mp3",
            str(audio_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"Audio extraction failed: {result.stderr.strip()[:200]}")

        # Clean up video file
        video_path.unlink(missing_ok=True)

        return DownloadResult(
            audio_path=audio_path,
            title=title,
            duration=duration,
            platform="instagram",
            original_url=url,
            channel=post.owner_username or "",
            description=post.caption or "",
        )
