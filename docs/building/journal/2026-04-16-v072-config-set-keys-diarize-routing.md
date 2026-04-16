---
type: project-note
tags: [config, api-keys, deepgram, diarization, auto-routing]
tldr: "`scribe config set` handles API keys (routes to .env). `--diarize` auto-switches to Deepgram when configured. Fixes OpenAI 25MB diarize limit for large files."
---

# v0.7.2 — API Key Config + Diarize Auto-Routing

## What Changed

### 1. `scribe config set` handles API keys

`cli/config_cmd.py` — added `_API_KEY_MAP` dict that maps lowercase key names (`deepgram_api_key`, `openai_api_key`, etc.) to their env var equivalents (`DEEPGRAM_API_KEY`, etc.). The `config_set` command checks this map before the existing config.yaml logic. If matched, calls `save_env()` and returns early.

```bash
scribe config set deepgram_api_key YOUR_KEY  # stored in .env, not config.yaml
```

### 2. `--diarize` auto-routes to Deepgram

`cli/transcribe.py` and `cli/batch.py` — when `diarize=True` and no explicit `--provider` was passed, checks `os.environ.get("DEEPGRAM_API_KEY")`. If set, switches `settings.provider` to `"deepgram"` and prints a dim info line.

### Why

A 3-hour Voice Memo (87MB m4a, 82MB as mp3) failed with OpenAI's `gpt-4o-transcribe-diarize` — the endpoint has a 25MB upload limit. The diarize path in `providers/openai.py` sends the raw file directly without chunking. Chunking for diarization is hard because speaker IDs need cross-chunk consistency.

Deepgram handles large files natively with consistent speaker labels. Auto-routing makes the common case (meetings, interviews) work without users needing to remember `-p deepgram`.

### Files changed

- `src/anyscribecli/cli/config_cmd.py` — API key routing in config set
- `src/anyscribecli/cli/transcribe.py` — diarize auto-routing + `import os`
- `src/anyscribecli/cli/batch.py` — same diarize auto-routing + `import os`
- 13 documentation files updated
