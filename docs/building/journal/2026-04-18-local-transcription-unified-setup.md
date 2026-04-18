---
type: feature
date: 2026-04-18
version: 0.8.0
tags: [local, faster-whisper, cli, web-ui, onboarding, agentic]
tldr: >
  Rebuilt local transcription as a first-class opt-in. Single unified setup
  routine (install faster-whisper + download Whisper model + persist default)
  driven from either `scribe local setup --model <size>`, a Web UI button, or
  an onboarding Y/n step. New `scribe local` and `scribe model` CLI groups are
  agentic-first (flag-driven, `--json` everywhere, explicit `--model`
  required). Fixed the green-dot lie and ship structured Test checks. This
  release also claims the 0.8.0 slot as the marker for the agentic-CLI /
  Web-UI-primary split.
---

# v0.8.0 — Local transcription: unified opt-in setup + model management

## Why this change

Local transcription was usable in theory (the `LocalProvider` worked, faster-whisper auto-downloaded models) but the UX had three gaps that made it broken in practice:

1. **The green dot lied.** `web/routes/config.py:73` hard-coded `has_key = (name == "local")` — it never checked whether faster-whisper was actually importable. Users saw "available", clicked Test, got an import error. Two pieces of UI telling opposite stories.
2. **No model management.** The model size was set only via the `ASCLI_LOCAL_MODEL` env var. Not persisted in config, not in onboarding, not in the Web UI. If you wanted `small` for a tricky interview, you had to `export` a shell variable. And there was no way to list, download, or delete cached weights.
3. **Setup was a scavenger hunt.** To get local working a user had to: know about the `[local]` pip extra, install it, guess/set the model size env var, then trigger a transcription that would blocking-download the model on first use. Four undocumented steps.

## What shipped

### CLI — two new command groups, agentic-first

- **`scribe local {setup, status, teardown}`** — provisioning lifecycle.
- **`scribe model {list, pull, rm, info}`** — day-to-day cache management.

Both groups follow the same agent-facing contract: flag-driven, no interactive prompts outside the setup confirmation, `--json` on every subcommand, structured exit codes, idempotent where it makes sense. `scribe local setup` in particular **requires `--model`** — the CLI refuses to pick a size silently, even in a TTY. The only place a size picker still runs is inside `scribe onboard` (TUI opt-in).

### Unified setup routine

`core/local_setup.py::run_setup(size)` is the single entry point used by all three surfaces (CLI, Web UI, onboarding). It:

1. Detects install method (`pipx`, `venv`, `system`) — checks `PIPX_HOME` and `sys.prefix != sys.base_prefix`.
2. Installs `faster-whisper` via the appropriate subprocess (`pipx inject anyscribecli faster-whisper>=1.0` or `python -m pip install ...`).
3. Downloads the chosen Whisper model via `huggingface_hub.snapshot_download`.
4. Persists `local_model` in `config.yaml`.

If the pip/pipx subprocess fails (PEP 668, permission errors, pipx not on PATH), we surface the exact command that ran and the captured stderr — never swallow silently. The pipx branch falls back to `python -m pip` if the `pipx` binary isn't on PATH.

### Web UI

`Settings → Providers → local` has two states:

- **Not set up**: shows a **Set up local transcription** button. No green dot, no Test button. Clicking opens a modal (`LocalSetupModal.tsx`) with a size picker (recommended size preselected + badged), triggers `POST /api/local/setup`, polls `GET /api/local/status`, shows phase-labeled progress.
- **Set up**: shows green dot + Test + an expand toggle. Expanded panel has a default-model dropdown, a 5-row models table with per-row download/delete, and a **Remove local transcription** button at the bottom.

The Test endpoint now returns structured sub-checks (`faster_whisper`, `ffmpeg`, `model_cached`) rendered as a small checklist inside the card.

### Onboarding

After the primary provider is picked, a new optional step asks *"Also enable offline/local transcription?"* (default No). If Yes, a beaupy size picker with `base` pre-highlighted runs, then `run_setup()` inline with phase output. Clean separation: local is a secondary-opt-in, not baked into the primary-provider flow.

### Settings dataclass

Added `local_model: str = "base"` to `Settings`. `from_dict` tolerates missing keys, so old `config.yaml` files keep working.

## Architecture decisions

### Opt-in, not bundled

Core `pip install anyscribecli` stays lean — **no** `faster-whisper` in main dependencies. The `[local]` extra stays in `pyproject.toml` as an escape hatch for CI/Docker/power users. Primary UX is `scribe local setup`, which invokes pip/pipx via subprocess on demand. Rationale: most users will be fine with an API provider; the 200+ MB of ctranslate2/onnxruntime dependencies shouldn't be a baseline tax.

### Explicit model choice, no silent defaults

`scribe local setup` without `--model` exits 2 with a hint listing `base` as recommended. This keeps agents honest — they must pass `--model` explicitly, and the skill docs tell them to default to `base` unless the user asks otherwise. The cost of one extra round trip is tiny; the clarity of audit trails (logs show exactly what the agent chose) is worth it.

### Two command groups, not one

`scribe local` manages the lifecycle (install/uninstall faster-whisper itself). `scribe model` manages the cache (download/delete individual model weights). Tried merging them; the single-namespace version (`scribe model setup`) was semantically awkward ("setup" isn't about models, it's about the whole provider). Split gives cleaner `--help` output and clearer mental model.

### Marker release

Claimed `0.8.0` — the previously-reserved "Cache/Dedup/Quality" slot in BACKLOG moves to `0.9.0`. Rationale: this release is the first one that materially shifts the product's shape (CLI becomes agent-first, Web UI becomes human-first), so it deserves a minor bump as the narrative anchor rather than disappearing into a `0.7.x` patch.

## Critical files

- `src/anyscribecli/providers/local_models.py` — vocabulary (`MODEL_SIZES`, `RECOMMENDED_MODEL`, `MODEL_REPOS`, `MODEL_SPECS`), HF cache wrappers (`list_cached_models`, `pull_model`, `delete_model`).
- `src/anyscribecli/core/local_setup.py` — provisioning engine: install-method detection, `install_faster_whisper`, `run_setup`, `run_teardown`, `check_status`, `local_ready`.
- `src/anyscribecli/cli/local_cmd.py`, `src/anyscribecli/cli/models_cmd.py` — the two new Typer groups.
- `src/anyscribecli/web/routes/local.py`, `src/anyscribecli/web/routes/models.py` — new FastAPI routers.
- `src/anyscribecli/web/routes/config.py` — `has_key` for local now reflects `local_ready()`; Test endpoint returns structured `checks`.
- `ui/src/pages/SettingsPage.tsx` — two-state local card with `LocalProviderCard` component inline.
- `ui/src/components/LocalSetupModal.tsx` — size-picker modal with polling progress.

## Backlog seeded

- **TUI removal sweep** — strip beaupy / interactive prompts from CLI commands outside `onboard`; rework `onboard.py` to support a flag-driven path (`scribe onboard --provider X --api-key ... --yes`).
- **Byte-level download progress in Web UI** — replace the current spinner + "downloading…" with true progress bars streamed via WebSocket.
- **GPU diagnostics** — `scribe local status` could report detected compute device (CPU vs CUDA vs Metal).

## What was NOT done

- Did not bundle `faster-whisper` into core deps (kept lean install).
- Did not pool `WhisperModel` instances across transcriptions (still reloaded on each call; acceptable for v1, worth revisiting if batch jobs become a priority).
- Did not implement diarization for local (faster-whisper doesn't support it natively; requires pyannote wiring — separate project).
- Did not flip `settings.provider` to `local` after setup. Setup prepares local; switching default providers stays with the user.
