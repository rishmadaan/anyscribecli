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
