"""Unit tests for the local-model vocabulary and cache helpers.

Live HF cache interactions (pull/delete of real model weights) are guarded by
the ``integration`` marker + ``ASCLI_RUN_INTEGRATION=1`` — ``pytest`` by
default exercises only the vocabulary and the "no huggingface_hub" fallbacks.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from anyscribecli.providers import local_models


def test_model_sizes_and_repos_aligned():
    assert set(local_models.MODEL_SIZES) == set(local_models.MODEL_REPOS.keys())
    assert set(local_models.MODEL_SIZES) == set(local_models.MODEL_SPECS.keys())


def test_recommended_model_is_a_valid_size():
    assert local_models.RECOMMENDED_MODEL in local_models.MODEL_SIZES


def test_validate_size_accepts_known():
    for size in local_models.MODEL_SIZES:
        local_models.validate_size(size)


def test_validate_size_rejects_unknown():
    with pytest.raises(ValueError):
        local_models.validate_size("huge")


def test_list_cached_models_returns_full_vocabulary_when_hub_missing():
    # _safe_import_hub returns None → helper must still give us 5 entries, all
    # marked uncached.
    with patch.object(local_models, "_safe_import_hub", return_value=None):
        entries = local_models.list_cached_models()
    sizes = [e["size"] for e in entries]
    assert sizes == local_models.MODEL_SIZES
    assert all(e["cached"] is False for e in entries)
    assert all(e["bytes"] == 0 for e in entries)


def test_is_cached_short_circuits_when_hub_missing():
    with patch.object(local_models, "_safe_import_hub", return_value=None):
        assert local_models.is_cached("base") is False


def test_any_model_cached_false_when_hub_missing():
    with patch.object(local_models, "_safe_import_hub", return_value=None):
        assert local_models.any_model_cached() is False


def test_delete_model_no_op_when_hub_missing():
    with patch.object(local_models, "_safe_import_hub", return_value=None):
        res = local_models.delete_model("base")
    assert res == {"status": "not_present", "size": "base", "bytes_freed": 0}


def test_pull_model_raises_without_faster_whisper():
    with patch.object(local_models, "faster_whisper_importable", return_value=False):
        with pytest.raises(RuntimeError, match="faster-whisper is not installed"):
            local_models.pull_model("base")


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("ASCLI_RUN_INTEGRATION") != "1",
    reason="opt-in network+disk test (set ASCLI_RUN_INTEGRATION=1)",
)
def test_pull_and_delete_tiny_model():
    # End-to-end: tiny is ~75MB, fastest to pull for CI-like coverage.
    if not local_models.faster_whisper_importable():
        pytest.skip("faster-whisper not installed in this env")
    try:
        result = local_models.pull_model("tiny")
        assert result["status"] in {"downloaded", "already_present"}
        assert local_models.is_cached("tiny")
    finally:
        rm = local_models.delete_model("tiny")
        assert rm["status"] in {"removed", "not_present"}
