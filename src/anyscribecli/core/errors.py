"""Structured error types and retry logic for transcription providers."""

from __future__ import annotations

import logging
import random
import time
from functools import wraps
from typing import Callable, TypeVar

import httpx

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable)


# ── Error hierarchy ─────────────────────────────────────


class ScribeAPIError(RuntimeError):
    """Base for all provider API errors with structured metadata."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 0,
        provider: str = "",
        retryable: bool = False,
        user_message: str = "",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider
        self.retryable = retryable
        self.user_message = user_message or message


class AuthenticationError(ScribeAPIError):
    """401/403 — invalid or missing API key."""

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(message, retryable=False, **kwargs)


class RateLimitError(ScribeAPIError):
    """429 — rate limited by provider."""

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(message, retryable=True, **kwargs)


class ServerError(ScribeAPIError):
    """500/502/503 — transient server error."""

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(message, retryable=True, **kwargs)


class TranscriptionTimeoutError(ScribeAPIError):
    """Request timed out."""

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(message, retryable=True, **kwargs)


# ── Classification ──────────────────────────────────────

# Provider-specific URLs where users can manage API keys
_KEY_URLS: dict[str, str] = {
    "openai": "https://platform.openai.com/api-keys",
    "deepgram": "https://console.deepgram.com/",
    "elevenlabs": "https://elevenlabs.io/app/settings/api-keys",
    "sargam": "https://dashboard.sarvam.ai",
    "openrouter": "https://openrouter.ai/keys",
}


def classify_api_error(status_code: int, body: str, provider: str) -> ScribeAPIError:
    """Map an HTTP status + response body to the correct ScribeAPIError subclass."""
    kwargs = {"status_code": status_code, "provider": provider}
    short_body = body[:200] if body else ""

    if status_code in (401, 403):
        key_url = _KEY_URLS.get(provider, "")
        url_hint = f"\n  Get a key: {key_url}" if key_url else ""
        return AuthenticationError(
            f"{provider} API auth error ({status_code}): {short_body}",
            user_message=(
                f"Invalid or missing API key for {provider}.\n"
                f"  Fix: scribe config set {provider}_api_key YOUR_KEY{url_hint}\n"
                f"  Or:  scribe onboard --force"
            ),
            **kwargs,
        )

    if status_code == 429:
        return RateLimitError(
            f"{provider} rate limited (429): {short_body}",
            user_message=(
                f"Rate limited by {provider}. Wait a moment and retry,\n"
                f"or switch providers: scribe config set provider <other>"
            ),
            **kwargs,
        )

    if status_code >= 500:
        return ServerError(
            f"{provider} server error ({status_code}): {short_body}",
            user_message=(
                f"Transient {provider} server error ({status_code}). "
                "This usually resolves on its own — retry in a few seconds."
            ),
            **kwargs,
        )

    # 4xx client errors (not auth or rate limit) — not retryable
    return ScribeAPIError(
        f"{provider} API error ({status_code}): {short_body}",
        user_message=f"{provider} rejected the request ({status_code}): {short_body}",
        **kwargs,
    )


# ── Retry decorator ─────────────────────────────────────


def with_retry(
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
) -> Callable[[F], F]:
    """Exponential backoff retry for provider API calls.

    Retries on: RateLimitError, ServerError, TranscriptionTimeoutError,
    httpx.ConnectError, httpx.TimeoutException.
    Does NOT retry on AuthenticationError or other client errors.
    """

    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except AuthenticationError:
                    raise  # Never retry auth errors
                except (RateLimitError, ServerError, TranscriptionTimeoutError) as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        delay = min(
                            base_delay * (2**attempt) + random.uniform(0, 1),
                            max_delay,
                        )
                        logger.warning(
                            "Retry %d/%d for %s after %s (%.1fs delay)",
                            attempt + 1,
                            max_retries,
                            getattr(fn, "__qualname__", getattr(fn, "__name__", "unknown")),
                            type(exc).__name__,
                            delay,
                        )
                        time.sleep(delay)
                    else:
                        raise
                except (httpx.ConnectError, httpx.TimeoutException) as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        delay = min(
                            base_delay * (2**attempt) + random.uniform(0, 1),
                            max_delay,
                        )
                        logger.warning(
                            "Retry %d/%d for %s after network error: %s (%.1fs delay)",
                            attempt + 1,
                            max_retries,
                            getattr(fn, "__qualname__", getattr(fn, "__name__", "unknown")),
                            exc,
                            delay,
                        )
                        time.sleep(delay)
                    else:
                        raise TranscriptionTimeoutError(
                            f"Request failed after {max_retries} retries: {exc}",
                            provider=kwargs.get("provider", ""),
                            user_message=(
                                f"Network error after {max_retries} retries. "
                                "Check your internet connection."
                            ),
                        ) from exc
            raise last_exc  # type: ignore[misc]  # unreachable but satisfies mypy

        return wrapper  # type: ignore[return-value]

    return decorator
