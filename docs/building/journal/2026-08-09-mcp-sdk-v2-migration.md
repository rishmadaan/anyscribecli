---
type: fix
tags: [mcp, dependencies, ci, testing, protocol]
tldr: "The `[mcp]` extra asked for `mcp>=1.0` with no ceiling, so pip resolved onto the SDK v2 major released 2026-07-28 — which deleted `mcp.server.fastmcp` outright and broke every fresh `pip install \"anyscribe[mcp]\"` on import. Fixed by migrating to `MCPServer` (protocol revision 2026-07-28) and pinning `mcp>=2,<3`; the functional migration was two lines because v2 kept decorators, sync handlers, docstring schemas and stdio `run()` unchanged. The real finding is why nobody saw it: CI installed `.[dev]` and never `.[mcp]`, so `tests/test_mcp_providers.py` importorskipped away on every run since the server shipped in v0.6.0 — the MCP layer had never been tested in CI at all."
---

# MCP SDK v2 migration + the unbounded-dependency break

**Date:** 2026-08-09 · Ships in v0.16.3

## What happened

Anthropic published MCP specification revision `2026-07-28` on 2026-07-28. The
Python SDK shipped `2.0.0` the same day, alongside a final `1.29.0`.

Our extra declared:

```toml
mcp = ["mcp>=1.0"]
```

No upper bound. From release day onward, a fresh `pip install "anyscribe[mcp]"`
resolved to `2.0.0` — and v2 removed `mcp.server.fastmcp` with no compatibility
shim. `server.py:19` imported exactly that. So `anyscribe-mcp` died on startup:

```
ModuleNotFoundError: No module named 'mcp.server.fastmcp'
```

Existing machines were unaffected — they already had a 1.x wheel on disk and pip
had no reason to touch it. The break was invisible to anyone already running it
and total for anyone installing fresh. That asymmetry is why it went twelve days
unnoticed.

## Why CI didn't catch it — the actual root cause

`.github/workflows/ci.yml` installed `-e ".[dev]"`. The `mcp` extra was never
installed. `tests/test_mcp_providers.py` opens with:

```python
pytest.importorskip("mcp", reason="mcp extra not installed (...)")
```

So the entire MCP test module **skipped on every CI run since the server shipped
in v0.6.0**. Not failed — skipped, which reads green. The dependency bound was
the proximate cause; the missing extra in CI is why a whole layer could rot
without a signal.

Fixed by installing `.[dev,mcp]`. Verified the guard actually bites rather than
assuming it: with the extra present and the old import in place, pytest reports
a hard collection error, not a skip.

```
E   ModuleNotFoundError: No module named 'mcp.server.fastmcp'
ERROR test_oldapi.py
!!!!!! Interrupted: 1 error during collection !!!!!!
```

## The migration itself

Two lines. v2's rework is real but lands almost entirely outside what this
server uses — checked against a scratch venv running `mcp==2.0.0`, not against
the docs:

| Concern | v2 status |
|---|---|
| `FastMCP` class | renamed `MCPServer`, in `mcp.server.mcpserver` (also re-exported from `mcp.server`) |
| `@mcp.tool()` / `@mcp.resource(uri)` | unchanged signatures |
| Sync (non-`async`) handlers | still supported; now run on worker threads via `anyio.to_thread.run_sync()` |
| Docstring-derived schemas, JSON returns | unchanged |
| `mcp.run(transport="stdio")` | unchanged (only HTTP transports moved `host`/`port` to `run()`) |
| `requires-python` | `>=3.10` — matches our existing floor, no bump needed |

All ten tools are plain sync functions returning JSON strings and none touch
`Context`, so the removal of `get_context()` doesn't reach us.

Also set while in the file:

- Server identity `scribe` → `anyscribe`. This is the display name hosts show in
  their server list; it was the last pre-rename identity left in the codebase.
- Added `version=__version__`. Without it `server_info.version` was empty, so a
  host showed a nameless version and "which anyscribe is this?" needed a
  `doctor()` call to answer.
- The three `scribe://` resource URIs are **left alone on purpose**. They are
  addresses, not display names — anything that resolved one would break. Noted
  in the module docstring so the asymmetry doesn't read as an oversight.

## Test added

`test_server_registers_every_tool_and_resource` asserts the registered surface
is exactly 10 tools and 3 resources. The import alone catches a moved class; it
cannot catch decorators that still import but silently stop registering, which
would ship an MCP server advertising nothing. This closes that gap.

## Verification

Against the real installed console script over stdio, driven by a v2 client —
not a unit-test stub:

```
negotiated protocol : 2026-07-28
server_info         : anyscribe 0.16.3
tools               : 10 [batch_transcribe, delete_transcript, doctor, download,
                          get_config, list_providers, list_transcripts,
                          set_config, test_provider, transcribe]
resources           : ['scribe://config', 'scribe://providers', 'scribe://workspace']
call_tool round-trip: ['deepgram', 'elevenlabs', 'groq', 'local', 'openai',
                       'openrouter', 'sargam']
```

Full suite: 482 passed, 1 skipped. `ruff check src tests scripts` clean.

## The rule this leaves behind

Two, both now recorded in `architecture.md`:

1. **Optional extras get an upper bound on the major.** An unbounded `>=` on a
   dependency whose import path we hard-code is a scheduled outage on the
   maintainer's release day, not ours. Majors get migrated deliberately, never
   resolved into.
2. **If a test module can `importorskip` itself out of existence, CI must
   install whatever makes it run.** A skipped test is indistinguishable from a
   passing one at a glance, which is the same failure shape as the 2026-07-31
   marker bug: green over a hole.

## Residual risk

SDK v2 is twelve days old. If it misbehaves in the field the fallback is small
and known: revert the two lines and ship `mcp>=1.28,<2` as 0.16.4 — the v1
maintenance line still receives security patches, and the deprecated
handshake-based revisions have a twelve-month runway per the spec's feature
lifecycle policy.
