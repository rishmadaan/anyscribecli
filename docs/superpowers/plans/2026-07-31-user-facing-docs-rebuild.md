# User-Facing Docs Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn anyscribe's docs into a product-grade, accurate, three-door docs site for AI-tool power users, and ship the small product fixes the docs depend on.

**Architecture:** `docs/user/*.md` stays the single source of truth; `scripts/build-docs.py` renders it to committed HTML under `landing/docs/` (Vercel serves it statically — `vercel.json` is NOT touched). Product fixes land first so docs never describe broken behavior. CI gains a docs job: render-diff gate + version-drift gate + MCP-table gate.

**Tech Stack:** Python 3.10+ (typer CLI, FastAPI web), React+TS+Vite (`ui/`), bash/PowerShell installers, `markdown` (pip) for rendering, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-07-31-user-facing-docs-design.md` — read it before starting any task.

## Global Constraints

- Current version is **0.16.0** (`pyproject.toml:7`, `src/anyscribe/__init__.py:3`). Do not bump until the final task.
- **Never print an exact version in doc prose.** Historical mentions that must stay get a `<!-- version-pin-ok -->` marker on the same line.
- **Skill files are first-class** (project CLAUDE.md): any behavior change updates `src/anyscribe/skill/` in the same commit.
- docs/user standards (project CLAUDE.md): YAML frontmatter (`title`, `summary`, `read_when`), lead with the command, copy-paste-ready examples, `>` blockquotes for asides.
- The CLI command in user-facing copy is `scribe` (aliases `anyscribe`, `ascli` exist; don't introduce them in new prose).
- Audience: **AI-tool power users** — terminal-tolerant if guided; no need to explain what a terminal is, but every command must be copy-paste-complete.
- Gates for every task: `ruff check src tests && pytest` for Python; `cd ui && npm run lint && npm run build` for frontend changes.
- Commit after every task; commit messages end with `Co-Authored-By:` per session convention.

## File Structure (created/modified across the plan)

| Path | Role |
|---|---|
| `install.sh`, `install.ps1` | installer fixes (Tasks 1–2) |
| `src/anyscribe/web/routes/config.py`, `routes/system.py` | keys/status + autostart routes (Tasks 3, 5) |
| `ui/src/components/{OnboardingWizard,Layout,SetupBanner}.tsx`, `ui/src/api/client.ts`, `ui/src/pages/SettingsPage.tsx` | UI fixes (Tasks 4–5) |
| `landing/index.html` | accuracy + link wiring only, no style changes (Tasks 6, 13) |
| `docs/user/agents.md` (new), `getting-started.md`, `commands.md`, `configuration.md`, `providers.md` | the three doors (Tasks 7–10) |
| `README.md` | short pitch (Task 11) |
| `scripts/build-docs.py`, `scripts/check-docs.py` (new), `.github/workflows/ci.yml`, `landing/docs/*.html` (generated, committed) | docs pipeline (Task 12) |
| `tests/test_install_sh.py`, `tests/test_autostart_route.py`, `tests/test_keys_status.py` (new) | checks |

---

### Task 1: install.sh — fix the three fresh-Mac crashes, tray extra, honest prompts

**Files:**
- Modify: `install.sh`
- Test: `tests/test_install_sh.py` (new)

**Interfaces:**
- Produces: `install.sh` with a `$PY` variable (resolved Python ≥3.10) used for every pip call; `resolve_python()` helper. Task 8's docs describe this installer's behavior — keep messages exactly as written here.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_install_sh.py
"""Static guards for install.sh — the bugs these catch shipped once already."""
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "install.sh"
SRC = SCRIPT.read_text()


def test_bash_syntax_ok():
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash not available")
    subprocess.run([bash, "-n", str(SCRIPT)], check=True)


def test_brew_activated_in_current_shell_after_install():
    # Fresh Homebrew installs are not on PATH in the running script;
    # without this eval the very next brew call dies on Apple Silicon.
    assert 'eval "$(/opt/homebrew/bin/brew shellenv)"' in SRC


def test_no_bare_pip3_installs():
    # Modern macOS blocks the stock pip3 (externally-managed). Every install
    # must go through the resolved "$PY" -m pip.
    assert "pip3 install" not in SRC


def test_tray_extra_is_installed_on_pip_path():
    assert 'anyscribe[tray]' in SRC


def test_homebrew_prompt_warns_about_password_and_time():
    assert "password" in SRC and "10-20 minutes" in SRC
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_install_sh.py -v`
Expected: FAIL on `test_brew_activated…`, `test_no_bare_pip3_installs`, `test_tray_extra…`, `test_homebrew_prompt…` (syntax test passes).

- [ ] **Step 3: Apply the fixes**

3a. In `install_brew_if_needed()` (line ~117), before and after the Homebrew install:

```bash
        if [[ "$answer" =~ ^[Yy] ]]; then
            info "Installing Homebrew..."
            warn "Homebrew will ask for your Mac password and can take 10-20 minutes — this is normal."
            if [[ "$DRY_RUN" == true ]]; then
                echo "    [dry-run] Would install Homebrew"
            else
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                # Fresh installs are not on PATH in this shell yet — activate now.
                if [[ -x /opt/homebrew/bin/brew ]]; then
                    eval "$(/opt/homebrew/bin/brew shellenv)"
                elif [[ -x /usr/local/bin/brew ]]; then
                    eval "$(/usr/local/bin/brew shellenv)"
                fi
            fi
```

3b. Add a Python resolver after the `command_exists` helper (line ~45), and a global near the defaults:

```bash
PY="python3"

# Find a Python >= 3.10, preferring version-suffixed binaries (a brew
# python@3.12 install provides python3.12; the bare python3 may still be
# the old system one).
resolve_python() {
    local cand
    for cand in python3.12 python3.11 python3.10 python3; do
        if command_exists "$cand" && "$cand" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
            PY="$cand"
            return 0
        fi
    done
    return 1
}
```

3c. Rewrite `check_python()` to use it (replaces lines ~194-221):

```bash
check_python() {
    info "Checking Python..."
    if resolve_python; then
        ok "Python $("$PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")') ($PY)"
        return 0
    fi
    warn "Python 3.10+ not found"
    read -rp "    Install Python? [Y/n] " answer </dev/tty
    answer="${answer:-Y}"
    if [[ "$answer" =~ ^[Yy] ]]; then
        install_package "Python" "python@3.12" "python3" ""
        resolve_python || die "Python installed but no python3.10+ found on PATH. Open a new terminal and re-run the installer."
    else
        die "Python 3.10+ is required. Install from https://python.org and try again."
    fi
}
```

3d. In `install_package()` (pip fallback, lines ~178-187), replace `pip3` with `"$PY" -m pip`:

```bash
    if [[ -n "$pip_pkg" ]]; then
        info "Installing $name via pip..."
        if [[ "$DRY_RUN" == true ]]; then
            echo "    [dry-run] $PY -m pip install $pip_pkg"
        else
            "$PY" -m pip install "$pip_pkg"
        fi
        return
    fi
```

3e. In `install_scribe()` (lines ~262-298): default `pip_cmd="anyscribe[tray]"`; the git path stays `pip_cmd="git+${REPO_URL}"` with a comment `# git installs skip the [tray] extra — extras syntax differs for git URLs (spec §3)`. Replace both pip calls and branch the pipx bootstrap on OS:

```bash
        local pip_output
        if pip_output=$("$PY" -m pip install "$pip_cmd" 2>&1); then
            : # Success
        elif echo "$pip_output" | grep -qi "externally-managed"; then
            warn "System Python is externally managed. Using pipx instead..."
            if ! command_exists pipx; then
                info "Installing pipx..."
                if [[ "$OS" == "macos" ]]; then
                    brew install pipx
                else
                    case "$LINUX_PKG" in
                        apt)    sudo apt install -y pipx ;;
                        dnf)    sudo dnf install -y pipx ;;
                        pacman) sudo pacman -S --noconfirm python-pipx ;;
                        *)      "$PY" -m pip install --user pipx ;;
                    esac
                fi
            fi
            pipx install "$pip_cmd"
```

Also update the dry-run echo (line ~273) to `echo "    [dry-run] $PY -m pip install $pip_cmd"`, and the header comment (line 15) to mention the tray.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_install_sh.py -v` — Expected: all PASS.
Also run: `bash install.sh --dry-run` locally — expect it to reach the final box with `[dry-run]` lines and no errors.

- [ ] **Step 5: Commit**

```bash
git add install.sh tests/test_install_sh.py
git commit -m "fix(install): survive fresh Apple Silicon — brew shellenv, resolved \$PY pip, pipx via brew; add [tray] extra"
```

---

### Task 2: install.ps1 — tray-extra parity

**Files:**
- Modify: `install.ps1:158`

The spec's read-through of install.ps1 found the three macOS bug classes already handled (Refresh-Path after installs, `$script:PythonCmd -m pip` throughout, working failure fallback). Only change needed:

- [ ] **Step 1: Edit line 158**

```powershell
    & $script:PythonCmd -m pip install --quiet "anyscribe[tray]"
```

(was `& $script:PythonCmd -m pip install --quiet anyscribe`). Update the header comment (line 11) to `#   4. Installs anyscribe (with menu-bar tray) via pip`.

- [ ] **Step 2: Verify** — `pwsh -NoProfile -Command "[scriptblock]::Create((Get-Content -Raw install.ps1)) | Out-Null"` if pwsh is installed; otherwise visual diff only (note it in the commit body).

- [ ] **Step 3: Commit**

```bash
git add install.ps1
git commit -m "fix(install): windows installer includes [tray] extra"
```

---

### Task 3: keys/status counts local — kills the forever "Setup needed" banner

**Files:**
- Modify: `src/anyscribe/web/routes/config.py:312-315`
- Test: `tests/test_keys_status.py` (new)

**Interfaces:**
- Produces: `GET /api/keys/status` response gains a `"local": bool` entry (true when faster-whisper is importable). Sole consumer is `ui/src/components/SetupBanner.tsx:34` (`Object.values(keys).some(Boolean)`) — no frontend change needed; verified: `PUT /keys` uses `PROVIDER_KEY_MAP` directly and is unaffected.

- [ ] **Step 1: Write the failing test** (follow the TestClient fixture pattern in `tests/test_config_dashboard.py`):

```python
# tests/test_keys_status.py
"""local needs no API key — a local-only setup must not look 'unconfigured'."""


def test_keys_status_includes_local_when_ready(client, monkeypatch):
    monkeypatch.setattr(
        "anyscribe.web.routes.config.faster_whisper_importable", lambda: True
    )
    data = client.get("/api/keys/status").json()
    assert data["local"] is True


def test_keys_status_local_false_when_not_installed(client, monkeypatch):
    monkeypatch.setattr(
        "anyscribe.web.routes.config.faster_whisper_importable", lambda: False
    )
    data = client.get("/api/keys/status").json()
    assert data["local"] is False
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/test_keys_status.py -v` → FAIL (KeyError / AttributeError).

- [ ] **Step 3: Implement** — in `keys_status()`:

```python
@router.get("/keys/status")
async def keys_status() -> dict:
    load_env()
    status = {name: bool(os.environ.get(env_var)) for name, env_var in PROVIDER_KEY_MAP.items()}
    # local needs no key — count it as configured when faster-whisper is installed
    status["local"] = faster_whisper_importable()
    return status
```

Import `faster_whisper_importable` from `anyscribe.providers.local_models` at the top of the file if not already imported (the file already uses `is_cached` from there — extend that import).

- [ ] **Step 4: Verify** — `pytest tests/test_keys_status.py -v` → PASS; `pytest` full suite green.

- [ ] **Step 5: Commit**

```bash
git add src/anyscribe/web/routes/config.py tests/test_keys_status.py
git commit -m "fix(web): keys/status counts local as configured — stops permanent setup banner for local-only users"
```

---

### Task 4: Groq in the wizard + post-Shutdown "way back in"

**Files:**
- Modify: `ui/src/components/OnboardingWizard.tsx:35-41`, `ui/src/components/Layout.tsx:29-39`

- [ ] **Step 1: Add the Groq card** to `API_PROVIDERS` (after deepgram, mirroring `src/anyscribe/cli/onboard.py:197-202`):

```ts
  { name: "groq", label: "Groq", description: "Cheapest + fastest cloud Whisper (large-v3-turbo)", env: "GROQ_API_KEY", url: "https://console.groq.com/keys" },
```

- [ ] **Step 2: Post-Shutdown copy** — in the `if (stopped)` block of `Layout.tsx`, after the "You can close this tab." line:

```tsx
          <p className="text-sm text-text-muted">You can close this tab.</p>
          <p className="text-xs text-text-muted mt-3">
            To reopen later, run <code className="font-mono">scribe ui</code> in your
            terminal — or click the anyscribe menu-bar icon, if installed.
          </p>
```

- [ ] **Step 3: Verify** — `cd ui && npm run lint && npm run build` → clean. Manual smoke: `scribe ui`, open wizard via Settings → re-run onboarding, confirm Groq card renders with a working key link; click Shutdown → confirm the new copy shows.

- [ ] **Step 4: Commit**

```bash
git add ui/src/components/OnboardingWizard.tsx ui/src/components/Layout.tsx
git commit -m "feat(ui): groq provider card in wizard; post-shutdown screen names the way back in"
```

---

### Task 5: "Open at login" toggle (macOS only, hidden elsewhere)

**Files:**
- Modify: `src/anyscribe/web/routes/system.py`, `ui/src/api/client.ts`, `ui/src/pages/SettingsPage.tsx`
- Test: `tests/test_autostart_route.py` (new)

**Interfaces:**
- Produces: `GET /api/autostart` → `{"supported": bool, "enabled": bool}`; `PUT /api/autostart` body `{"enabled": bool}` → same shape, 400 off-macOS. Client exports `getAutostart()`, `setAutostart(enabled)`. Reuses `install_service()`/`uninstall_service()`/`plist_path()` from `src/anyscribe/core/service.py` unchanged.

- [ ] **Step 1: Write the failing tests** (same client fixture as Task 3; `service._launchctl` is designed for monkeypatching — see `src/anyscribe/core/service.py:53`):

```python
# tests/test_autostart_route.py
"""Autostart route — macOS-only launchd toggle, honest 400 elsewhere."""
import anyscribe.web.routes.system as system_routes
from anyscribe.core import service


def test_autostart_status_reports_supported(client, monkeypatch, tmp_path):
    monkeypatch.setattr(system_routes.sys, "platform", "darwin")
    monkeypatch.setattr(service, "launch_agents_dir", lambda: tmp_path)
    data = client.get("/api/autostart").json()
    assert data == {"supported": True, "enabled": False}


def test_autostart_enable_writes_plist(client, monkeypatch, tmp_path):
    monkeypatch.setattr(system_routes.sys, "platform", "darwin")
    monkeypatch.setattr(service, "launch_agents_dir", lambda: tmp_path)
    monkeypatch.setattr(service, "_launchctl", lambda *a: None)
    data = client.put("/api/autostart", json={"enabled": True}).json()
    assert data["enabled"] is True
    assert (tmp_path / "com.anyscribe.tray.plist").exists()
    # and off again
    data = client.put("/api/autostart", json={"enabled": False}).json()
    assert data["enabled"] is False
    assert not (tmp_path / "com.anyscribe.tray.plist").exists()


def test_autostart_rejected_off_macos(client, monkeypatch):
    monkeypatch.setattr(system_routes.sys, "platform", "linux")
    assert client.put("/api/autostart", json={"enabled": True}).status_code == 400
    assert client.get("/api/autostart").json() == {"supported": False, "enabled": False}
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/test_autostart_route.py -v` → FAIL (404s).

- [ ] **Step 3: Implement the routes** in `src/anyscribe/web/routes/system.py`:

```python
"""System endpoints — shutdown, autostart."""

from __future__ import annotations

import sys

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from anyscribe.core import service

router = APIRouter(prefix="/api", tags=["system"])


class AutostartRequest(BaseModel):
    enabled: bool


def _autostart_state() -> dict:
    supported = sys.platform == "darwin"
    return {
        "supported": supported,
        "enabled": supported and service.plist_path().exists(),
    }


@router.get("/autostart")
async def autostart_status() -> dict:
    return _autostart_state()


@router.put("/autostart")
async def set_autostart(req: AutostartRequest) -> dict:
    if sys.platform != "darwin":
        raise HTTPException(status_code=400, detail="Autostart is only supported on macOS")
    if req.enabled:
        service.install_service()
    else:
        service.uninstall_service()
    return _autostart_state()
```

(keep the existing `shutdown` route unchanged below it).

- [ ] **Step 4: Run tests** — `pytest tests/test_autostart_route.py -v` → PASS.

- [ ] **Step 5: Client + Settings UI.** In `ui/src/api/client.ts`:

```ts
// ── System ───────────────────────────────────────────

export type AutostartState = { supported: boolean; enabled: boolean };

export const getAutostart = () => fetchJSON<AutostartState>("/autostart");

export const setAutostart = (enabled: boolean) =>
  fetchJSON<AutostartState>("/autostart", {
    method: "PUT",
    body: JSON.stringify({ enabled }),
  });
```

In `SettingsPage.tsx`, add state + effect in the main component and render a row using the existing `SettingRow`/`Toggle` helpers (defined at `SettingsPage.tsx:1355-1391`), placed in the same section as the re-run-onboarding button (~line 286). Render **nothing** when `!autostart.supported`:

```tsx
const [autostart, setAutostartState] = useState<AutostartState | null>(null);

useEffect(() => {
  getAutostart().then(setAutostartState).catch(() => setAutostartState(null));
}, []);

const handleAutostart = async (v: boolean) => {
  const next = await setAutostart(v);
  setAutostartState(next);
};

{autostart?.supported && (
  <SettingRow label="Open at login (menu-bar app)">
    <Toggle value={autostart.enabled} onChange={(v) => void handleAutostart(v)} />
  </SettingRow>
)}
```

Add a one-line hint under the row: `Starts the anyscribe menu-bar icon when you log in.`

- [ ] **Step 6: Verify** — `cd ui && npm run lint && npm run build`; `pytest`; manual smoke on this Mac: toggle on → `ls ~/Library/LaunchAgents/com.anyscribe.tray.plist` exists; toggle off → gone.

- [ ] **Step 7: Commit**

```bash
git add src/anyscribe/web/routes/system.py tests/test_autostart_route.py ui/src/api/client.ts ui/src/pages/SettingsPage.tsx
git commit -m "feat: open-at-login toggle in Settings (macOS), wired to existing launchd service"
```

---

### Task 6: Accuracy pass — landing, docs/user, skill references

**Files:**
- Modify: `landing/index.html`, `docs/user/getting-started.md`, `docs/user/commands.md`, `docs/user/configuration.md`, `src/anyscribe/skill/references/config.md`, `src/anyscribe/skill/references/commands.md`

Exact edits (README is handled wholesale in Task 11 — do not touch it here):

- [ ] **Step 1: Versions out of prose.**
  - `landing/index.html:1419`: `<span><b>anyscribe</b> &nbsp;·&nbsp; MIT open source</span>` (delete `v0.13.1 ·`)
  - `landing/index.html:2051`: `<span>MIT &nbsp;·&nbsp; no tracking · no analytics · no cookies</span>`
  - `docs/user/getting-started.md:85`: remove the version from the sentence (rephrase to "the latest version").
  - `docs/user/commands.md:1117` and `src/anyscribe/skill/references/commands.md:662`: replace the literal `v0.13.0`-style string with version-free phrasing ("your installed version — check `scribe --version`").
  - `src/anyscribe/skill/references/troubleshooting.md:267` mentions 0.13.1/0.13.2 **legitimately** (historical bug note) — append `<!-- version-pin-ok -->` to each such line instead of editing.
- [ ] **Step 2: ffmpeg claim.** `landing/index.html:1944` — replace "checks your system, installs missing pieces (`yt-dlp`, `ffmpeg`), and walks you through picking an engine" with "checks your system and walks you through picking an engine — the install command itself already brought in `yt-dlp` and `ffmpeg`" (keep the surrounding `<code>` styling for `scribe ui`).
- [ ] **Step 3: Parity claims.** Replace both:
  - `docs/user/getting-started.md:19`
  - `src/anyscribe/skill/references/config.md:41`
  with: "Every *setting* can be changed from either the CLI or the Web UI. A few maintenance commands are CLI-only: `batch`, `logs`, `doctor`, `update`, and `tray`."
- [ ] **Step 4: Quit→Shutdown.** `docs/user/getting-started.md:103` only — the sidebar button is labelled **Shutdown** (`ui/src/components/Layout.tsx:104`). The tray menu's "Quit" mentions in `commands.md:916,937` and `skill/references/troubleshooting.md:273,285` are correct — leave them.
- [ ] **Step 5: configuration.md hygiene.** Swap the warning to *before* the `rm -rf` reset command (lines ~498-502); explain `ASCLI_` env prefix in one parenthetical at line ~314 ("legacy prefix, still honored"); at line ~391 offer "any text editor" with `nano` as the example rather than assuming it; gloss "BCP-47" at line ~233 in one parenthetical ("language codes like `en` or `hi-Latn`").
- [ ] **Step 6: Verify with greps** (all must return nothing):

```bash
grep -rn "installs missing pieces" landing/
grep -rn "nothing is terminal-only" src/anyscribe/skill/ docs/
grep -rn "never need to hop" docs/
grep -rEn "v?0\.(8|13)\.[0-9]" docs/user/ landing/ src/anyscribe/skill/ | grep -v "version-pin-ok"
```

- [ ] **Step 7: Commit**

```bash
git add landing/index.html docs/user/ src/anyscribe/skill/references/
git commit -m "docs: accuracy pass — versions out of prose, ffmpeg claim, scoped parity claims, shutdown label"
```

---

### Task 7: Door 1 — `docs/user/agents.md` (new)

**Files:**
- Create: `docs/user/agents.md`
- Modify: `src/anyscribe/skill/SKILL.md` (cross-link only)

**Interfaces:**
- Produces: the page Task 12's MCP-table gate parses — the MCP tool list MUST appear as backtick-quoted names in a table under a heading containing "MCP".

Write the page with this exact structure and facts (prose is the implementer's, facts are not):

- [ ] **Step 1: Write `docs/user/agents.md`**

Frontmatter:

```yaml
---
title: Use anyscribe from your AI agent
summary: Connect anyscribe to Claude Code (skill) or any MCP host in about two minutes, and know exactly what your agent can drive.
read_when:
  - "You use Claude Code, Claude Desktop, Cursor, or another AI agent daily"
  - "You want to say 'transcribe this' instead of typing commands"
---
```

Sections, in order:
1. **Two ways in** — the Claude Code **skill** (agent drives the CLI: can reach everything) vs the **MCP server** (fixed ten-tool surface for Claude Desktop, Cursor, any MCP host). One short paragraph each.
2. **Claude Code (skill)** — verified commands: `pip install anyscribe` then `scribe install-skill`; or `scribe onboard` auto-detects Claude Code and offers it. After install: `/anyscribe` or just ask ("transcribe this YouTube link"). Three example asks as a bullet list.
3. **MCP (Claude Desktop, Cursor, other hosts)** — `pip install "anyscribe[mcp]"`; server binary is `anyscribe-mcp`. Claude Code registration: `claude mcp add anyscribe -- anyscribe-mcp`. Claude Desktop JSON snippet:

```json
{ "mcpServers": { "anyscribe": { "command": "anyscribe-mcp" } } }
```

4. **What your agent can reach** — table with columns `Capability | Skill (CLI) | MCP`. MCP tools (from `src/anyscribe/mcp/server.py` decorators — verify before writing): `transcribe`, `batch_transcribe`, `download`, `list_transcripts`, `delete_transcript`, `get_config`, `set_config`, `list_providers`, `test_provider`, `doctor`. CLI-only rows (Skill ✓ / MCP —): `logs`, `update`, `onboard`, `local setup`, model management (`model list/pull/rm`). Final row: menu-bar `tray` — no agent path (✗/✗), link to getting-started's keep-it-running section.
5. **Agent-friendly flags** — brief: every command takes `--json` and `--yes`; link to commands.md's "For scripts and agents" section (created in Task 9).

- [ ] **Step 2: Cross-link.** In `src/anyscribe/skill/SKILL.md`, add one line near the top pointing human readers to `docs/user/agents.md`.

- [ ] **Step 3: Verify** — every command in the page copy-pastes correctly against `scribe --help` / `scribe install-skill --help` output; MCP tool names match `grep -A1 "@mcp.tool" src/anyscribe/mcp/server.py | grep "def "`.

- [ ] **Step 4: Commit**

```bash
git add docs/user/agents.md src/anyscribe/skill/SKILL.md
git commit -m "docs: agents.md — Door 1 guide (skill vs MCP, honest capability map)"
```

---

### Task 8: Door 2 — restructure `docs/user/getting-started.md`

**Files:**
- Modify: `docs/user/getting-started.md`

- [ ] **Step 1: Restructure** to this outline (keep frontmatter, update `summary`; keep any still-true prose — this is a reorder + additions, not a from-scratch rewrite):
  1. **What you need** (short): the one-line installer brings Python, ffmpeg, yt-dlp; plus *either* the free local engine *or* an API key from one provider (link providers.md).
  2. **Step 1 — Install**: the curl one-liner (macOS/Linux) and PowerShell one-liner (Windows) FIRST, `pip install "anyscribe[tray]"` as the alternative. The current manual Homebrew/Python walkthrough (lines ~41-89) moves wholesale to an **Appendix: manual install** at the bottom.
  3. **Step 2 — First run**: `scribe ui` → wizard walkthrough (existing content, updated for the Groq card from Task 4).
  4. **Step 3 — First transcript** (existing content).
  5. **Keep it running** (NEW section — this is the spec's biggest content gap): the tray (`scribe tray`, installed by default now), **Open at login** via Settings toggle (macOS) or `scribe install-service`, and "closed the tab / hit Shutdown / rebooted? → run `scribe ui` again — your library and settings are untouched."
  6. **Where next**: agents.md (Door 1), commands.md, providers.md.
- [ ] **Step 2: Verify** — walk the doc top-to-bottom on this machine, executing every command block in order; each must work as written. Confirm the promoted tray blockquote from old line ~221 is folded into section 5, not duplicated.
- [ ] **Step 3: Commit**

```bash
git add docs/user/getting-started.md
git commit -m "docs: getting-started — installer first, keep-it-running chapter, manual path to appendix"
```

---

### Task 9: Door 3 — `docs/user/commands.md` restructure

**Files:**
- Modify: `docs/user/commands.md`

- [ ] **Step 1:** Move the "Agentic-first CLI" block (lines ~13-21: `--json`, TTY detection, exit codes) to a new `## For scripts and agents` section at the bottom of the file; leave a one-line pointer at the top.
- [ ] **Step 2:** Add a `Where in the Web UI?` column to the command overview table (lines ~23-61). Mapping: `transcribe`/`download` → "Transcribe page"; config commands → "Settings"; history/list/delete → "History"; `ui` → "—"; `batch`, `logs`, `doctor`, `update`, `tray`, `onboard`, `local`, `model` → "— (CLI only)" except `onboard` → "Settings → re-run wizard" and `local setup` → "Settings → Local provider card". Verify each mapping against the actual UI pages before writing.
- [ ] **Step 3: Create `docs/user/troubleshooting.md`** (spec §1 supporting page). Not new prose from scratch: consolidate the existing troubleshooting-by-error-text material (the sections at the bottom of `commands.md` ~line 618+ and the user-relevant parts of `src/anyscribe/skill/references/troubleshooting.md`) into one page with standard frontmatter, organized by literal error text the user sees. `commands.md` keeps a one-line pointer where the section was. The skill's copy stays (agents need it bundled) — the CI version gate keeps both honest.
- [ ] **Step 4:** Verify — every command in the overview table exists in `scribe --help` output; no drift.
- [ ] **Step 5: Commit**

```bash
git add docs/user/commands.md docs/user/troubleshooting.md
git commit -m "docs: commands — web-UI column, agent material to its own section; troubleshooting page"
```

---

### Task 10: `docs/user/providers.md` — cost-to-start table

**Files:**
- Modify: `docs/user/providers.md`

- [ ] **Step 1:** Add a table directly under the intro, before any per-provider detail: columns `Provider | Free to start? | Card needed? | Rough cost`. Rows for all seven providers. Facts come ONLY from what's already documented in this repo (existing providers.md pricing around line ~126, onboarding descriptions) — where the repo documents nothing (e.g. a provider's free-tier terms), write "see [provider's pricing page](url)" using the URLs from `src/anyscribe/web/routes/config.py:55-62`. Do not invent free-tier claims. Known anchors: `local` = $0, no account; Deepgram = $200 signup credit.
- [ ] **Step 2:** Lead the "which should I pick" guidance with the quality tiers (accuracy/balanced/cost/free) so the table is a reference, not a decision burden.
- [ ] **Step 3:** Verify — all seven providers from `src/anyscribe/providers/__init__.py` PROVIDER_REGISTRY appear; every URL resolves.
- [ ] **Step 4: Commit**

```bash
git add docs/user/providers.md
git commit -m "docs: providers — honest cost-to-start table, tiers-first guidance"
```

---

### Task 11: README rewrite — short pitch

**Files:**
- Modify: `README.md`

- [ ] **Step 1:** Rewrite to ≤130 lines with this structure:
  1. Name + one-line tagline + the three-surfaces trio (keep current lines 3-9 flavor, tightened).
  2. **Privacy block** — keep current lines 13-21 verbatim (spec: best copy in the repo).
  3. **What you need** — compact prerequisites (moved ABOVE install; replaces the table at old line 206).
  4. **Install** — the two one-liners + pip alternative; then `scribe ui`.
  5. Screenshot (`landing/assets/scribe-ui.png` reference as today).
  6. **Docs** — links to the site pages (`https://<landing-domain>/docs/agents`, `/docs/getting-started`, `/docs/commands`, `/docs/providers`, `/docs/configuration` — use the real deployed domain, check `vercel` project or ask; GitHub-relative links as a fallback ONLY if the domain is unclear at implementation time, flagged in the PR).
  7. **Upgrading from anyscribecli** — the migration note from old lines 68-72, moved here at the bottom.
  8. License.
- [ ] **Step 2:** Verify — no exact version strings; every retained command tested; `grep -n "0\.[0-9]*\.[0-9]" README.md` returns nothing unmarked.
- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README as short pitch — prerequisites first, docs links, migration note to bottom"
```

---

### Task 12: Docs pipeline — `build-docs.py`, `check-docs.py`, CI job

**Files:**
- Create: `scripts/build-docs.py`, `scripts/check-docs.py`, `landing/docs/*.html` (generated)
- Modify: `.github/workflows/ci.yml`, `pyproject.toml` (dev extra)

**Interfaces:**
- Produces: `python scripts/build-docs.py` renders every `docs/user/*.md` → `landing/docs/<stem>.html` + `landing/docs/index.html`; idempotent (same input → byte-identical output — no timestamps). `python scripts/check-docs.py` exits non-zero on version drift or MCP-table drift. Task 13 links to `/docs/<stem>` URLs (Vercel `cleanUrls` serves `.html` without extension).

- [ ] **Step 1:** Add `markdown>=3.5` to the `dev` extra in `pyproject.toml`.

- [ ] **Step 2: Write `scripts/build-docs.py`** — single file, this shape (implementer fills the HTML template with styling *sampled from `landing/index.html`'s existing CSS variables* — dark bg, mono accents; keep it under ~80 lines of CSS; no JS):

```python
#!/usr/bin/env python3
"""Render docs/user/*.md to committed HTML under landing/docs/.

Idempotent: no timestamps, no randomness. CI re-runs this and fails on diff.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "user"
OUT = ROOT / "landing" / "docs"

# Door order — drives index.html ordering and nav
PAGES = ["agents", "getting-started", "commands", "providers", "configuration", "troubleshooting"]

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
MD_LINK = re.compile(r"\]\((?!https?://|#|/)([\w-]+)\.md(#[\w-]*)?\)")

TEMPLATE = """<!doctype html>... (title, minimal dark styling matching landing
CSS vars, a small header linking back to / and across PAGES, {body}) ..."""


def render(stem: str) -> str:
    text = (SRC / f"{stem}.md").read_text()
    meta = {}
    m = FRONTMATTER.match(text)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith((" ", "-")):
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip().strip('"')
        text = text[m.end():]
    text = MD_LINK.sub(r"](/docs/\1\2)", text)  # sibling .md links → clean URLs
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "toc"])
    return TEMPLATE.format(title=meta.get("title", stem), body=body)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for stem in PAGES:
        (OUT / f"{stem}.html").write_text(render(stem))
    # index: one card per page from each file's frontmatter title+summary
    ...
    print(f"rendered {len(PAGES)} pages + index → {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

The `...` for index generation and the TEMPLATE body are the implementer's to complete — everything else (regexes, idempotency rule, PAGES order, link rewriting) is fixed as written. Internal-link validation: after rendering, scan output for `href="/docs/<x>"` where `<x>` not in PAGES → exit 1.

- [ ] **Step 3: Write `scripts/check-docs.py`:**

```python
#!/usr/bin/env python3
"""Docs honesty gates: version drift + MCP table drift. Exit non-zero on either."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def real_version() -> str:
    m = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M)
    assert m, "version not found in pyproject.toml"
    return m.group(1)

def check_versions() -> list[str]:
    """Any vX.Y.Z in user-facing prose must equal the real version or be
    marked <!-- version-pin-ok --> on the same line."""
    version = real_version()
    offenders = []
    targets = ["docs/user", "landing", "README.md", "src/anyscribe/skill"]
    pat = re.compile(r"v?\d+\.\d+\.\d+")
    for target in targets:
        base = ROOT / target
        files = [base] if base.is_file() else [
            p for p in base.rglob("*") if p.suffix in {".md", ".html"}
        ]
        for f in files:
            for i, line in enumerate(f.read_text().splitlines(), 1):
                if "version-pin-ok" in line:
                    continue
                for hit in pat.findall(line):
                    if hit.lstrip("v") != version:
                        offenders.append(f"{f.relative_to(ROOT)}:{i}: {hit}")
    return offenders

def check_mcp_table() -> list[str]:
    """Every @mcp.tool in server.py must appear backticked in agents.md."""
    server = (ROOT / "src/anyscribe/mcp/server.py").read_text()
    actual = set(re.findall(r"@mcp\.tool\(\)\s*\ndef (\w+)", server))
    agents = (ROOT / "docs/user/agents.md").read_text()
    documented = set(re.findall(r"`([a-z_]+)`", agents))
    missing = actual - documented
    return [f"agents.md missing MCP tool: `{t}`" for t in sorted(missing)]

def main() -> int:
    problems = check_versions() + check_mcp_table()
    for p in problems:
        print(p, file=sys.stderr)
    return 1 if problems else 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the gates NOW and watch them fail meaningfully at least once** (the spec's own rule: a gate that has never failed has shown nothing). Temporarily add `v0.1.0` to a doc line, run `python scripts/check-docs.py`, see it flagged, revert. Temporarily rename one MCP tool in agents.md, see it flagged, revert.

- [ ] **Step 5: Render + commit output.** `python scripts/build-docs.py`, open `landing/docs/index.html` locally (e.g. `python -m http.server -d landing`) and click through all pages + cross-links.

- [ ] **Step 6: CI job** — append to `.github/workflows/ci.yml`:

```yaml
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install renderer
        run: python -m pip install "markdown>=3.5"
      - name: Render docs
        run: python scripts/build-docs.py
      - name: Committed HTML matches sources
        run: git diff --exit-code landing/docs
      - name: Version + capability drift gates
        run: python scripts/check-docs.py
```

- [ ] **Step 7: Commit**

```bash
git add scripts/build-docs.py scripts/check-docs.py landing/docs/ .github/workflows/ci.yml pyproject.toml
git commit -m "feat(docs): commit-time docs renderer + honesty gates (version drift, MCP table) in CI"
```

---

### Task 13: Landing wiring — nav + footer to the new docs

**Files:**
- Modify: `landing/index.html`

- [ ] **Step 1:** Footer links (lines ~2025-2036): replace the four `github.com/.../blob/main/docs/user/*.md` hrefs with `/docs/getting-started`, `/docs/commands`, `/docs/providers`, `/docs/configuration`; add `/docs/agents` under the "AI agents" item (keep the `#agent` anchor link too). BACKLOG changelog link stays on GitHub.
- [ ] **Step 2:** Nav: find the header nav list (search `class="links"` markup, near the `nav.links` CSS at line ~147) and add `<li><a href="/docs/">Docs</a></li>`.
- [ ] **Step 3:** Verify — `python -m http.server -d landing` and click every changed link; `grep -c "blob/main/docs" landing/index.html` returns 0.
- [ ] **Step 4: Commit**

```bash
git add landing/index.html
git commit -m "docs: landing links point at the docs site, not GitHub file views"
```

---

### Task 14: Close-out — journal, version bump, fresh-Mac verification

**Files:**
- Create: `docs/building/journal/2026-07-31-user-facing-docs-rebuild.md`
- Modify: `docs/building/_index.md`, `BACKLOG.md`

- [ ] **Step 1: Journal entry** per project convention (frontmatter: type, tags, tldr): what shipped (three doors, pipeline, product fixes), the Opus-review corrections (MCP capability split; commit-time render), and the deliberate exclusions (§4 of the spec). Add the `_index.md` row (newest first).
- [ ] **Step 2: Fresh-environment install verification** (spec §6 — required before release):
  - Linux leg (automatable): `docker run --rm -it -v "$PWD/install.sh":/install.sh ubuntu:24.04 bash` → `apt update && apt install -y curl python3 python3-pip && bash /install.sh` answering prompts; expect clean finish and `scribe --version`.
  - macOS leg: run `bash install.sh` on a clean macOS VM (UTM) or a spare Mac **without** Homebrew. **This needs Rishabh's hardware — flag it, do not fake it.** Minimum fallback if no VM: `env PATH=/usr/bin:/bin HOME="$HOME" bash install.sh --dry-run` interactively, confirming the Homebrew branch and warnings fire.
  - Record actual output (pass or fail, verbatim tail) in the journal entry.
- [ ] **Step 3: Version bump — GATED.** This is a patch by project convention (`0.16.1`). `./scripts/release.sh` pushes a tag that **publishes to PyPI** — get Rishabh's explicit go-ahead before running it. Before the bump, run the Version Tag Checklist from CLAUDE.md (BACKLOG.md table, skill files, `grep` for stale strings — `scripts/check-docs.py` now does most of this).
- [ ] **Step 4: Final full gate** — `ruff check src tests && pytest && (cd ui && npm run lint && npm run build) && python scripts/build-docs.py && git diff --exit-code landing/docs && python scripts/check-docs.py`.
- [ ] **Step 5: Commit**

```bash
git add docs/building/ BACKLOG.md
git commit -m "docs: journal + close-out for user-facing docs rebuild"
```
