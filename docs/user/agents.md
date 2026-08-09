---
title: Use anyscribe from your AI agent
summary: Connect anyscribe to Claude Code (skill) or any MCP host in about two minutes, and know exactly what your agent can drive.
read_when:
  - "You use Claude Code, Claude Desktop, Cursor, or another AI agent daily"
  - "You want to say 'transcribe this' instead of typing commands"
---

# Use anyscribe from your AI agent

You don't have to memorize flags. Hand a link to your agent and say "transcribe this" — it drives anyscribe for you.

> **`scribe` and `ascli` are shorter aliases for `anyscribe`** — every command on this page works typed as any of the three.

## Two ways in

**The Claude Code skill** teaches Claude how to *use the CLI*. Claude runs `anyscribe` commands in your terminal the way you would, so anything the command line can do, the skill can reach: transcribing, batches, provider setup, log reading, updates, local model management. It's the fuller path, and it only works in Claude Code.

**The MCP server** exposes a fixed set of ten tools over MCP — the Model Context Protocol, the standard way an AI app talks to an outside tool. It's narrower by design, but it works in any MCP host: Claude Desktop, Cursor, Claude Code, and anything else that speaks the protocol.

> **Not sure which?** If you live in Claude Code, install the skill. If you live in Claude Desktop or Cursor, use MCP. Installing both is fine — they don't conflict.

## Claude Code (skill)

```bash
pip install anyscribe
anyscribe install-skill
```

That copies the skill into `~/.claude/skills/anyscribe/`. Claude Code picks it up on the next session — no restart dance beyond opening a new one.

**You may already have it.** If Claude Code is installed on this machine, anyscribe installs the skill for you the first time you run *any* anyscribe command, and quietly refreshes it whenever the copy on disk falls behind the installed version. No prompt, nothing to opt into. Run `anyscribe install-skill` when you want to re-install or confirm it explicitly — say, after deleting the folder or debugging why Claude isn't picking it up.

Then either type `/anyscribe` to invoke it explicitly, or just ask in plain English — the skill activates on its own when your request is about transcription:

- "Transcribe this YouTube link and drop it in my vault: `https://youtube.com/watch?v=...`"
- "Transcribe these five URLs with the cheapest provider, and tell me which ones failed."
- "Switch me to Deepgram and re-run the last one with speaker labels."

> **New to skills?** A skill is a folder of instructions Claude reads when your request matches. Nothing runs in the background — the files just sit there until Claude needs them.

## MCP (Claude Desktop, Cursor, other hosts)

```bash
pip install "anyscribe[mcp]"
```

The server command, `anyscribe-mcp`, ships with the base package — it's already on your PATH. What the `[mcp]` extra adds is the MCP library the server needs in order to run, kept out of the base install so a plain `pip install anyscribe` stays light. Without the extra, the command exists but stops on a missing import; with it, `anyscribe-mcp` is the server your agent talks to.

> **Seeing `No module named 'mcp.server.fastmcp'`?** You're on an anyscribe
> release older than 0.16.3 with the newest MCP library. <!-- version-pin-ok --> The MCP project shipped
> a version 2 that renamed the piece anyscribe was importing, and older anyscribe
> releases didn't ask for a specific version — so a fresh install picked up the
> new one and the two no longer fit. Upgrading fixes it:
>
> ```bash
> pip install -U "anyscribe[mcp]"
> ```
>
> 0.16.3 and later pin the range explicitly, so this can't recur. <!-- version-pin-ok -->

**Claude Code:**

```bash
claude mcp add anyscribe -- anyscribe-mcp
```

**Claude Desktop** — add this to your `claude_desktop_config.json`:

```json
{ "mcpServers": { "anyscribe": { "command": "anyscribe-mcp" } } }
```

**Other hosts** (Cursor and friends) want the same two facts in whatever shape their config file takes: the command is `anyscribe-mcp`, and it needs no arguments.

> **Configure anyscribe first.** The MCP server uses the same `~/.anyscribe/config.yaml` and API keys as the CLI. Run `anyscribe onboard` once before wiring up MCP, or the tools will start by telling your agent there's no provider configured.

## What your agent can reach (skill vs MCP)

Both paths hit the same engine — the difference is how much of it is exposed.

| Capability | Skill (CLI) | MCP |
|------------|-------------|-----|
| Transcribe one URL or file | ✓ | ✓ `transcribe` |
| Transcribe many at once | ✓ | ✓ `batch_transcribe` |
| Download media without transcribing | ✓ | ✓ `download` |
| Browse what's in your vault | ✓ | ✓ `list_transcripts` |
| Delete a transcript | ✓ | ✓ `delete_transcript` |
| Read your settings | ✓ | ✓ `get_config` |
| Change a setting | ✓ | ✓ `set_config` |
| See available providers | ✓ | ✓ `list_providers` |
| Check an API key works | ✓ | ✓ `test_provider` |
| Health check | ✓ | ✓ `doctor` |
| Read run logs (`logs`) | ✓ | — |
| Update anyscribe (`update`) | ✓ | — |
| Run the setup wizard (`onboard`) | ✓ | — |
| Set up offline transcription (`local setup`) | ✓ | — |
| Manage Whisper models (`model list` / `pull` / `rm`) | ✓ | — |
| Menu-bar tray | ✗ | ✗ |

The tray is the one row where the agent runs out of road partway. Claude Code can *start* it (`anyscribe tray`) or set it to launch at login (`anyscribe install-service`), because those are ordinary commands. What no agent can do is use it: the tray's whole point is a menu-bar icon you click, and there's nothing to click on from a transcript. If you want anyscribe always running in the background, see [Getting Started → Keep it running](getting-started.md#keep-it-running).

> **Why the short list on MCP?** Every MCP tool is a permanent promise with a fixed shape. Ten cover the work; the rest are one-off maintenance jobs better done by a human at a terminal — or by Claude Code, which has the whole CLI anyway.

## Agent-friendly flags

Anything your agent needs to parse, it should ask for as JSON:

```bash
anyscribe "<url>" --json --quiet
```

Most commands that report results accept `--json`, and commands that would stop to ask "are you sure?" accept `--yes` (`-y`) to answer in advance — the pair that keeps an agent from hanging on a prompt it can't see. Full details, including the exact JSON shape, live in [Commands → For scripts and agents](commands.md#for-scripts-and-agents).
