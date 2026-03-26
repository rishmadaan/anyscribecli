"""Instagram downloader using instaloader.

Mirrors the Dropzone Instagram Downloader bundle pattern:
session caching, login with test_login fallback, shortcode extraction.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from anyscribecli.downloaders.base import AbstractDownloader, DownloadResult
from anyscribecli.config.paths import SESSIONS_DIR
from anyscribecli.config.settings import load_config


class InstagramDownloader(AbstractDownloader):
    """Download video/audio from Instagram using instaloader + yt-dlp for audio extraction."""

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

    def _get_instaloader(self):
        """Create and authenticate an Instaloader instance.

        Mirrors Dropzone bundle: load session → test_login → fresh login if invalid → save.
        """
        try:
            import instaloader
        except ImportError:
            raise RuntimeError(
                "instaloader is required for Instagram downloads.\n"
                "Install it with: pip install instaloader\n"
                "Or: pip install anyscribecli[instagram]"
            )

        L = instaloader.Instaloader()
        settings = load_config()
        username = settings.instagram.username
        password = settings.instagram.password

        if not username or not password:
            raise RuntimeError(
                "Instagram credentials not configured.\n"
                "Run: ascli config set instagram.username YOUR_USERNAME\n"
                "Run: ascli config set instagram.password YOUR_PASSWORD\n"
                "Or re-run: ascli onboard --force"
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
        except Exception as e:
            raise RuntimeError(
                f"Instagram login failed: {e}\n"
                "Check your credentials in ~/.anyscribecli/config.yaml\n"
                "Note: Instagram may temporarily block logins from new locations."
            )

        return L

    def download(self, url: str, output_dir: Path) -> DownloadResult:
        try:
            import instaloader
        except ImportError:
            raise RuntimeError(
                "instaloader is required for Instagram downloads.\n"
                "Install it with: pip install instaloader\n"
                "Or: pip install anyscribecli[instagram]"
            )

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

        duration = post.video_duration if post.is_video else None

        if not post.is_video:
            raise RuntimeError(
                "This Instagram post is an image, not a video. "
                "ascli can only transcribe video/audio content."
            )

        # Download video using instaloader
        video_dir = output_dir / f"ig_{shortcode}"
        video_dir.mkdir(exist_ok=True)
        L.download_post(post, target=str(video_dir))

        # Find the downloaded video file
        video_files = list(video_dir.glob("*.mp4"))
        if not video_files:
            raise RuntimeError("Instagram download completed but no video file found.")

        video_path = video_files[0]

        # Extract audio optimized for Whisper using ffmpeg
        audio_path = output_dir / f"{shortcode}.mp3"
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-ar", "16000",
            "-ac", "1",
            "-b:a", "64k",
            "-f", "mp3",
            str(audio_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"Audio extraction failed: {result.stderr.strip()[:200]}")

        # Clean up video files
        for f in video_dir.iterdir():
            f.unlink()
        video_dir.rmdir()

        return DownloadResult(
            audio_path=audio_path,
            title=title,
            duration=duration,
            platform="instagram",
            original_url=url,
            channel=post.owner_username or "",
            description=post.caption or "",
        )
