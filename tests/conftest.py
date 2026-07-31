"""Suite-wide isolation: never touch the developer's real ~/.anyscribe.

Every path constant in anyscribe.config.paths binds from Path.home() at
IMPORT time, so redirecting HOME must happen here, at conftest import — pytest
imports conftest before any test module, i.e. before anyscribe is imported.
Anything later (fixtures, monkeypatch.setenv) is too late: the real paths are
already baked into module-level constants.

This exists because three onboarding tests once wrote through to the real
~/.anyscribe — replacing the developer's OPENAI_API_KEY with "sk-test" and
rewriting config.yaml — while the suite stayed green (2026-07-29 audit).
"""

from __future__ import annotations

import os
import sys
import tempfile

assert not any(m.startswith("anyscribe") for m in sys.modules), (
    "anyscribe was imported before tests/conftest.py could isolate HOME — "
    "real user config would be at risk. Import it only inside tests/fixtures."
)

_ISOLATED_HOME = tempfile.mkdtemp(prefix="ascli-test-home-")
os.environ["HOME"] = _ISOLATED_HOME  # macOS / Linux
os.environ["USERPROFILE"] = _ISOLATED_HOME  # Windows
