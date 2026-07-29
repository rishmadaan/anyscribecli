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
from pathlib import Path

import pytest
from typer.main import get_command
from typer.testing import CliRunner

from anyscribe.config import paths
from anyscribe.core import migrate as migrate_core
from anyscribe.cli.main import app

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


# --- 7. cross-check: migrate.py's advice resolves to a real command -------


def test_migrate_py_error_command_is_a_registered_command():
    """The command migrate.py tells the user to run must actually exist.

    Not a tautology: the token is read out of core/migrate.py's error line
    (``run 'anyscribe migrate'``), NOT hardcoded here. Rename the command in
    main.py without fixing that message, or vice-versa, and this fails.
    """
    source = Path(migrate_core.__file__).read_text()
    m = re.search(r"run '([^']+)'", source)
    assert m, "no `run '<cmd>'` advice found in core/migrate.py"
    token = m.group(1).split()[-1]  # last word of "anyscribe migrate"

    registered = get_command(app).commands
    assert token in registered, f"{token!r} advised by migrate.py is not a registered command"


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
