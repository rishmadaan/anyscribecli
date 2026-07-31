"""Tests for the ``anyscribe migrate`` command (cli/migrate_cmd.py).

Real filesystem only: every case builds actual dirs/files under a throwaway
home and asserts what ends up on disk. Mocking is limited to ``shutil.which``
(the commands aren't installed in the test env).

The command calls ``maybe_migrate_app_home()`` directly, so the once-flag the
autouse ``_no_real_app_home_migration`` fixture sets doesn't gate it; the
``home`` fixture below still re-points the path constants so nothing escapes
the real home. See tests/test_migrate_app_home.py for the sibling fixture.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
from typer.main import get_command
from typer.testing import CliRunner

from anyscribe.cli import main as main_mod
from anyscribe.cli.main import app
from anyscribe.config import paths
from anyscribe.core import migrate as migrate_core

runner = CliRunner()

# Captured before any fixture patches it — the real legacy dir name without
# hardcoding the old package name here.
LEGACY_NAME = paths.LEGACY_APP_HOME.name


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Re-point every home-anchored path constant the command reads at a throwaway dir."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(paths, "APP_HOME", tmp_path / ".anyscribe")
    monkeypatch.setattr(paths, "LEGACY_APP_HOME", tmp_path / LEGACY_NAME)
    monkeypatch.setattr(paths, "CLAUDE_HOME", tmp_path / ".claude")
    monkeypatch.setattr(paths, "CLAUDE_SKILLS_DIR", tmp_path / ".claude" / "skills")
    monkeypatch.setattr(paths, "ASCLI_SKILL_TARGET", tmp_path / ".claude" / "skills" / "anyscribe")
    monkeypatch.setattr(migrate_core, "_app_home_migrated", False)
    # Commands aren't installed in the test env; a real which() would report all
    # three missing and add a noisy PATH warning. Pretend they're present so the
    # verification step is clean and deterministic.
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/local/bin/{name}")
    return tmp_path


def _seed_legacy(home: Path, keys: dict[str, str]) -> Path:
    """A realistic old ~/.anyscribecli: .env keys, non-default workspace, sessions, a download."""
    legacy = home / LEGACY_NAME
    (legacy / "sessions").mkdir(parents=True)
    (legacy / "sessions" / "s1.json").write_text('{"id": 1}\n')
    (legacy / "sessions" / "s2.json").write_text('{"id": 2}\n')
    (legacy / "downloads" / "audio").mkdir(parents=True)
    (legacy / "downloads" / "audio" / "clip.mp3").write_bytes(b"audio-bytes")
    (legacy / ".env").write_text("".join(f"{k}={v}\n" for k, v in keys.items()))
    (legacy / "config.yaml").write_text("provider: openai\nworkspace_path: /custom/vault\n")
    return legacy


def _snapshot(root: Path) -> dict:
    """Recursive (relpath -> (size, mtime_ns)) for files + a dir set. Byte-level fingerprint."""
    files: dict[str, tuple[int, int]] = {}
    dirs: set[str] = set()
    for p in root.rglob("*"):
        rel = str(p.relative_to(root))
        if p.is_dir():
            dirs.add(rel)
        else:
            st = p.stat()
            files[rel] = (st.st_size, st.st_mtime_ns)
    return {"files": files, "dirs": dirs}


def _parse_env(env_file: Path) -> dict[str, str]:
    out = {}
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


# --- 1. full migration ----------------------------------------------------


def test_full_migration_from_realistic_old_layout(home):
    keys = {"OPENAI_API_KEY": "sk-fakeAAA", "DEEPGRAM_API_KEY": "dg-fakeBBB", "IG_PASSWORD": "hunter2"}
    _seed_legacy(home, keys)

    result = runner.invoke(app, ["migrate"])
    assert result.exit_code == 0, result.output
    assert "nothing to do" not in result.output  # it did something

    new = home / ".anyscribe"
    assert new.is_dir()
    assert not (home / LEGACY_NAME).exists()  # whole dir moved

    assert _parse_env(new / ".env") == keys  # all 3 keys, identical values
    assert "workspace_path: /custom/vault" in (new / "config.yaml").read_text()
    assert (new / "sessions" / "s1.json").read_text() == '{"id": 1}\n'
    assert (new / "sessions" / "s2.json").exists()
    assert (new / "downloads" / "audio" / "clip.mp3").read_bytes() == b"audio-bytes"


# --- 2. second run is a no-op ---------------------------------------------


def test_second_run_is_a_noop(home):
    _seed_legacy(home, {"OPENAI_API_KEY": "sk-fake"})
    assert runner.invoke(app, ["migrate"]).exit_code == 0

    snap = _snapshot(home)
    result = runner.invoke(app, ["migrate"])

    assert result.exit_code == 0
    assert "nothing to do" in result.output
    assert _snapshot(home) == snap  # nothing changed on disk


# --- 3. --dry-run writes nothing ------------------------------------------


def test_dry_run_writes_nothing_but_describes_moves(home):
    _seed_legacy(home, {"OPENAI_API_KEY": "sk-fake"})
    # Make a real run have work in every step: Claude Code present (skill would
    # install) and an MCP entry that would be re-keyed.
    (home / ".claude").mkdir()
    (home / ".claude.json").write_text(json.dumps({"mcpServers": {"scribe": {"command": "scribe-mcp"}}}))

    snap = _snapshot(home)
    result = runner.invoke(app, ["migrate", "--dry-run"])

    assert result.exit_code == 0
    # Byte-identical: no config dir moved, no .bak, no skill files, no tmp.
    assert _snapshot(home) == snap
    assert not (home / ".claude.json.bak").exists()
    assert not (home / ".claude" / "skills" / "anyscribe").exists()
    assert (home / LEGACY_NAME).is_dir()  # legacy still in place

    # ...but the output still describes what it WOULD do.
    assert "~/.anyscribecli" in result.output
    assert "→" in result.output  # the → arrow
    assert "nothing written" in result.output


# --- 4. ~/.claude.json missing --------------------------------------------


def test_claude_json_missing_is_fine(home):
    _seed_legacy(home, {"OPENAI_API_KEY": "sk-fake"})
    assert not (home / ".claude.json").exists()

    result = runner.invoke(app, ["migrate", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["success"] is True
    assert data["data"]["mcp_entries_updated"] == 0


# --- 5. ~/.claude.json malformed ------------------------------------------


def test_claude_json_malformed_is_not_touched(home):
    _seed_legacy(home, {"OPENAI_API_KEY": "sk-fake"})
    garbage = "{ this is not json"
    (home / ".claude.json").write_text(garbage)

    result = runner.invoke(app, ["migrate"])
    assert result.exit_code == 0
    # Not overwritten or truncated.
    assert (home / ".claude.json").read_text() == garbage
    assert not (home / ".claude.json.bak").exists()
    assert not (home / ".claude.json.tmp").exists()
    assert "skipped" in result.output  # warned that it skipped


# --- 6. nested per-project mcpServers -------------------------------------


def test_nested_mcp_servers_all_rekeyed(home):
    _seed_legacy(home, {"OPENAI_API_KEY": "sk-fake"})
    claude_json = home / ".claude.json"
    claude_json.write_text(
        json.dumps(
            {
                "mcpServers": {"scribe": {"command": "scribe-mcp", "args": []}},
                "projects": {
                    "/some/path": {"mcpServers": {"scribe": {"command": "scribe-mcp"}}},
                    # Already migrated — must be left untouched (never clobber).
                    "/other": {
                        "mcpServers": {
                            "scribe": {"command": "scribe-mcp"},
                            "anyscribe": {"command": "anyscribe-mcp"},
                        }
                    },
                },
            }
        )
    )

    result = runner.invoke(app, ["migrate", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["data"]["mcp_entries_updated"] == 2  # top-level + /some/path

    written = json.loads(claude_json.read_text())  # still valid JSON
    top = written["mcpServers"]
    assert "scribe" not in top and top["anyscribe"]["command"] == "anyscribe-mcp"
    proj = written["projects"]["/some/path"]["mcpServers"]
    assert "scribe" not in proj and proj["anyscribe"]["command"] == "anyscribe-mcp"
    # The pre-migrated block is untouched: scribe left as-is, anyscribe unchanged.
    other = written["projects"]["/other"]["mcpServers"]
    assert other["scribe"] == {"command": "scribe-mcp"}
    assert other["anyscribe"] == {"command": "anyscribe-mcp"}

    assert (home / ".claude.json.bak").exists()


# --- 6b. ~/.claude.json mode is preserved across the temp-file swap --------


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file-mode bits")
def test_claude_json_mode_preserved_after_real_migrate(home):
    """A real migrate that rewrites an MCP entry must keep ~/.claude.json 0600.

    The file can hold MCP env API keys / oauth; the temp-file + os.replace swap
    would otherwise stamp it with the umask default (~644, world-readable).
    """
    _seed_legacy(home, {"OPENAI_API_KEY": "sk-fake"})
    claude_json = home / ".claude.json"
    claude_json.write_text(json.dumps({"mcpServers": {"scribe": {"command": "scribe-mcp"}}}))
    claude_json.chmod(0o600)

    result = runner.invoke(app, ["migrate"])
    assert result.exit_code == 0, result.output
    # The entry was actually rewritten (non-dry-run, real change)...
    written = json.loads(claude_json.read_text())
    assert written["mcpServers"]["anyscribe"]["command"] == "anyscribe-mcp"
    # ...and the destination kept its original 0600 mode.
    assert (claude_json.stat().st_mode & 0o777) == 0o600


# --- 7. cross-check: migrate.py's advice resolves to a real command -------


def test_migrate_py_error_command_is_a_registered_command():
    """The command migrate.py tells the user to run must actually exist, and
    main.py's dry-run/skill gate must key off that same command name.

    Not a tautology: the token is read out of core/migrate.py's error line
    (``run 'anyscribe migrate'``), NOT hardcoded here. Rename the command in
    main.py without fixing that message, or drift main.py's gate away from it,
    and this fails.
    """
    source = Path(migrate_core.__file__).read_text()
    m = re.search(r"run '([^']+)'", source)
    assert m, "no `run '<cmd>'` advice found in core/migrate.py"
    token = m.group(1).split()[-1]  # last word of "anyscribe migrate"

    registered = get_command(app).commands
    assert token in registered, f"{token!r} advised by migrate.py is not a registered command"

    # main.py gates _auto_update_skill()/_check_path_windows() off the migrate
    # command name so --dry-run writes nothing. Read that literal out of the
    # source (not hardcoded) and assert it matches — a rename of one side alone
    # silently regresses the "writes nothing" guarantee otherwise.
    main_source = Path(main_mod.__file__).read_text()
    gate = re.search(r'invoked_subcommand\s*!=\s*"([^"]+)"', main_source)
    assert gate, "no `invoked_subcommand != \"...\"` gate found in main.py"
    assert gate.group(1) == token, (
        f"main.py dry-run gate targets {gate.group(1)!r} but migrate.py advises {token!r}"
    )


# --- 8. --json output shape -----------------------------------------------


def test_json_output_shape_reports_key_count_not_values(home):
    keys = {"OPENAI_API_KEY": "sk-SECRETVALUEONE", "DG": "SECRETVALUETWO", "IG": "SECRETVALUETHREE"}
    _seed_legacy(home, keys)

    result = runner.invoke(app, ["migrate", "--json"])
    assert result.exit_code == 0

    data = json.loads(result.stdout)
    assert data["success"] is True and data["error"] is None
    d = data["data"]
    for field in (
        "dry_run",
        "app_home",
        "stale_skill_removed",
        "skill_installed",
        "mcp_entries_updated",
        "commands",
        "changed",
        "warnings",
    ):
        assert field in d, f"missing field {field}"
    assert d["app_home"]["files"] == 5  # 2 sessions + 1 audio + .env + config.yaml
    assert ".env (3 keys)" in d["app_home"]["entries"]  # count, not values

    # No secret value string may appear anywhere in the emitted output.
    for secret in keys.values():
        assert secret not in result.stdout


# --- 9. stale tray LaunchAgent (macOS) is repaired ------------------------

from anyscribe.core import service as service_mod  # noqa: E402


def _seed_stale_tray_plist(home: Path) -> Path:
    """A 0.13.x tray LaunchAgent whose ProgramArguments still call `anyscribecli`."""
    path = service_mod.plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '<?xml version="1.0"?>\n<plist><dict>'
        "<key>ProgramArguments</key><array>"
        "<string>/usr/bin/python</string><string>-m</string>"
        "<string>anyscribecli</string><string>tray</string>"
        "</array></dict></plist>\n"
    )
    return path


@pytest.fixture
def darwin(monkeypatch):
    """Run the macOS-only tray step everywhere; stub launchctl to a call recorder."""
    monkeypatch.setattr(sys, "platform", "darwin")
    calls: list[tuple] = []
    monkeypatch.setattr(service_mod, "_launchctl", lambda *a: calls.append(a))
    return calls


def test_stale_tray_plist_is_rewritten(home, darwin):
    path = _seed_stale_tray_plist(home)

    result = runner.invoke(app, ["migrate", "--json"])
    assert result.exit_code == 0, result.output

    content = path.read_text()
    assert "anyscribecli" not in content
    assert "<string>anyscribe</string>" in content  # current `-m anyscribe` invocation
    assert darwin  # launchctl invoked (unload + load), best-effort
    data = json.loads(result.stdout)
    assert data["data"]["tray_plist_repaired"] is True


def test_stale_tray_plist_dry_run_touches_nothing(home, darwin):
    path = _seed_stale_tray_plist(home)
    before = path.read_bytes()

    result = runner.invoke(app, ["migrate", "--dry-run"])
    assert result.exit_code == 0
    assert path.read_bytes() == before  # byte-identical
    assert darwin == []  # no launchctl call in dry-run
    assert "rewrite (stale" in result.output  # still reported (may wrap)


def test_no_tray_plist_is_clean_noop(home, darwin):
    result = runner.invoke(app, ["migrate", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["data"]["tray_plist_repaired"] is False
    assert darwin == []


def test_second_tray_run_is_idempotent(home, darwin):
    _seed_stale_tray_plist(home)
    assert runner.invoke(app, ["migrate"]).exit_code == 0
    darwin.clear()
    result = runner.invoke(app, ["migrate", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["data"]["tray_plist_repaired"] is False  # already anyscribe
    assert darwin == []
