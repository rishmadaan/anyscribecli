"""Tests for error classification and retry logic."""

from unittest.mock import MagicMock, patch

import pytest

from anyscribecli.core.errors import (
    AuthenticationError,
    RateLimitError,
    ScribeAPIError,
    ServerError,
    classify_api_error,
    with_retry,
)


class TestClassifyAPIError:
    def test_401_returns_auth_error(self):
        err = classify_api_error(401, "Unauthorized", "openai")
        assert isinstance(err, AuthenticationError)
        assert err.status_code == 401
        assert err.provider == "openai"
        assert not err.retryable
        assert "scribe config set" in err.user_message

    def test_403_returns_auth_error(self):
        err = classify_api_error(403, "Forbidden", "deepgram")
        assert isinstance(err, AuthenticationError)
        assert not err.retryable

    def test_429_returns_rate_limit(self):
        err = classify_api_error(429, "Too many requests", "elevenlabs")
        assert isinstance(err, RateLimitError)
        assert err.retryable
        assert "Rate limited" in err.user_message

    def test_500_returns_server_error(self):
        err = classify_api_error(500, "Internal server error", "openai")
        assert isinstance(err, ServerError)
        assert err.retryable

    def test_503_returns_server_error(self):
        err = classify_api_error(503, "Service unavailable", "sargam")
        assert isinstance(err, ServerError)
        assert err.retryable

    def test_400_returns_base_error(self):
        err = classify_api_error(400, "Bad request", "openai")
        assert isinstance(err, ScribeAPIError)
        assert not isinstance(err, AuthenticationError)
        assert not err.retryable

    def test_long_body_truncated(self):
        body = "x" * 500
        err = classify_api_error(400, body, "openai")
        assert len(str(err)) < 500


class TestWithRetry:
    def test_success_on_first_try(self):
        fn = MagicMock(return_value="ok")
        decorated = with_retry(max_retries=3)(fn)
        assert decorated() == "ok"
        assert fn.call_count == 1

    @patch("anyscribecli.core.errors.time.sleep")
    def test_retries_on_server_error(self, mock_sleep):
        fn = MagicMock(side_effect=[
            ServerError("fail", status_code=500, provider="openai"),
            ServerError("fail again", status_code=500, provider="openai"),
            "ok",
        ])
        decorated = with_retry(max_retries=3, base_delay=0.01)(fn)
        assert decorated() == "ok"
        assert fn.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("anyscribecli.core.errors.time.sleep")
    def test_no_retry_on_auth_error(self, mock_sleep):
        fn = MagicMock(side_effect=AuthenticationError(
            "bad key", status_code=401, provider="openai"
        ))
        decorated = with_retry(max_retries=3)(fn)
        with pytest.raises(AuthenticationError):
            decorated()
        assert fn.call_count == 1
        mock_sleep.assert_not_called()

    @patch("anyscribecli.core.errors.time.sleep")
    def test_exhausts_retries(self, mock_sleep):
        fn = MagicMock(side_effect=RateLimitError(
            "limited", status_code=429, provider="openai"
        ))
        decorated = with_retry(max_retries=2, base_delay=0.01)(fn)
        with pytest.raises(RateLimitError):
            decorated()
        assert fn.call_count == 3  # 1 initial + 2 retries
