"""Tests for audio overlap deduplication."""

from anyscribecli.core.audio import deduplicate_overlap


class TestDeduplicateOverlap:
    def test_exact_overlap(self):
        prev = "the cat sat on the mat"
        curr = "on the mat and ate fish"
        result = deduplicate_overlap(prev, curr)
        assert result == "and ate fish"

    def test_no_overlap(self):
        prev = "hello world"
        curr = "goodbye moon"
        result = deduplicate_overlap(prev, curr)
        assert result == "goodbye moon"

    def test_empty_prev(self):
        result = deduplicate_overlap("", "hello world")
        assert result == "hello world"

    def test_empty_curr(self):
        result = deduplicate_overlap("hello world", "")
        assert result == ""

    def test_full_overlap(self):
        text = "the quick brown fox"
        result = deduplicate_overlap(text, text)
        assert result == ""

    def test_short_text(self):
        # Too short to dedup (< 3 words)
        result = deduplicate_overlap("hi", "hi there")
        assert result == "hi there"

    def test_longer_overlap(self):
        prev = "one two three four five six seven eight"
        curr = "five six seven eight nine ten"
        result = deduplicate_overlap(prev, curr)
        assert result == "nine ten"
