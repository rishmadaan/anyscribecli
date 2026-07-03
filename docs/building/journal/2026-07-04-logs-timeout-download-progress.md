---
type: feature
tags: [logs, cli, batch, timeout, web-ui, download-progress, testing, sargam, providers]
tldr: "v0.12.0. Three independent additions: scribe logs (read-only viewer over the existing daily/*.md logs + recovery dir — no new logging system), batch --timeout (ThreadPoolExecutor future per URL, with an abandoned-thread caveat since Python can't kill a running thread), and byte-level Web UI model-download progress (hf tqdm_class hook riding the existing status-poll fields, no WebSocket). Plus 41 provider unit tests that caught a real bug: sargam.py dropped speaker 0's label because an `or` chain treats integer 0 as falsy."
---

# `scribe logs`, `batch --timeout`, byte-level download progress, provider tests

**Date:** 2026-07-04
**Version:** 0.12.0
**Follows:** the [2026-07-03 audit fixes + lifecycle](2026-07-03-audit-fixes-and-lifecycle.md)

## `scribe logs` — a viewer, not a new log store

The ask was "let users see what they transcribed recently." The lazy option won:
`daily/YYYY-MM-DD.md` already records every run as a markdown table row. `cli/logs_cmd.py`
just reads those files newest-first and parses rows with a regex (`_ROW_RE`) instead of a
naive `split("|")` — the entry cell is a `[[path|title]]` wikilink that itself contains a
pipe, so a bare split breaks on it.

It also lists the **recovery directory** (`config/paths.py::RECOVERY_DIR`) — audio the
orchestrator already saves there when a transcription fails after download but before
writing the transcript (see `core/orchestrator.py`). `scribe logs` didn't add that
mechanism, it just surfaces what already existed with no way to see it.

No new logging framework, no cache file, no index. `--limit/-n` (default 20) and
`--json/-j`. Empty state: `No activity logged yet.`

## `batch --timeout` — a future with an abandoned-thread caveat

`--timeout SECONDS` (float, opt-in, default `None`) wraps each URL's `process()` call in a
`ThreadPoolExecutor(max_workers=1)` and calls `future.result(timeout=timeout)`. On
`TimeoutError`, the URL is marked failed with `"timed out after Ns"` and the batch
continues (or stops, if `--stop-on-error` is also set).

The honest caveat, documented inline in `cli/batch.py`: **Python can't kill a running
thread.** A timed-out worker keeps transcribing in the background even though the batch
loop has moved on and reported it failed — it's abandoned, not cancelled. Fine for a CLI
batch run where the process exits soon after anyway. If this ever needs to actually
free up API concurrency mid-run, the upgrade path is subprocess isolation
(`concurrent.futures.ProcessPoolExecutor`), which can be `.terminate()`d for real.

## Byte-level Web UI download progress — riding the existing poll

This closes the `0.9.x` BACKLOG row that had been queued to "stream progress via
WebSocket." That plan turned out to be more than the problem needed. `providers/local_models.py::pull_model()`
already calls `huggingface_hub.snapshot_download()`, which already drives tqdm progress
bars per file. `_progress_tqdm_class()` subclasses `huggingface_hub.utils.tqdm`, hooks
`__init__`/`update`/`close` to aggregate `(downloaded, total)` bytes across every live
byte-unit bar under a lock, and calls a `progress_cb(downloaded, total)` on each tick.

That callback plugs into the **existing** polling infrastructure — no WebSocket needed:
- `core/local_setup.py::run_setup()` emits a `download_progress` event through the same
  `on_progress` callback used for phase transitions.
- `web/routes/local.py` stores it as `state["progress"]` and returns it as
  `setup_progress` on `GET /api/local/status` (the endpoint `LocalSetupModal` already polls
  every 1.5s).
- `web/routes/models.py` does the same per queued download (`progress` dict keyed by
  model size), surfaced on `GET /api/models/local` for the Models table.

Frontend: `LocalSetupModal.tsx` swaps the spinner for a progress bar + "NN% · X MB / Y MB"
whenever `setup_progress.total > 0`; the Models table shows percent on downloading rows.
No new transport, no new endpoint — same poll, richer payload.

## Provider test suite — 41 tests, one real bug found

`tests/test_providers.py` now covers all six cloud providers (openai, deepgram,
elevenlabs, groq, openrouter, sargam): registry wiring, 401/429 → `ScribeAPIError`
classification, chunking behavior, diarize routing, and provider-specific response
parsing quirks.

**Bug found and fixed:** `sargam.py::_parse_response()` parsed diarized turns with
`speaker = turn.get("speaker") or turn.get("speaker_id")`. Integer `0` is falsy in Python,
so when Sarvam labeled the first speaker as `0`, the `or` fell through to
`speaker_id` (usually absent) and the label was dropped — speaker 0's turns came back
unlabeled. Fixed by testing `is None` explicitly instead of relying on truthiness:

```python
speaker = turn.get("speaker")
if speaker is None:
    speaker = turn.get("speaker_id")
```

`tests/test_providers.py::TestSargam::test_speaker_zero_label_kept` locks this in.

This is the same failure class the 2026-07-03 audit flagged: a real bug shipped silently
because nothing exercised the code path where speaker id is `0`, not because the fix was
hard. The suite went from 189 → 242 tests this release; the sargam fix is the direct
payoff of writing them.

## Files

- `cli/logs_cmd.py` (new), `cli/main.py` (register `logs`)
- `cli/batch.py` (`--timeout`, `_process_url` ThreadPoolExecutor wrapping)
- `providers/local_models.py` (`_progress_tqdm_class`, `pull_model(progress_cb=...)`)
- `core/local_setup.py` (`download_progress` event)
- `web/routes/local.py`, `web/routes/models.py` (`progress` / `setup_progress` fields)
- `ui/src/components/LocalSetupModal.tsx` (progress bar UI)
- `providers/sargam.py` (speaker-0 fix)
- `tests/test_logs_cli.py`, `tests/test_batch_timeout.py`, `tests/test_local_setup.py`,
  `tests/test_web_local.py`, `tests/test_providers.py` (new)
