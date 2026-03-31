"""Allow running as `python -m anyscribecli`.

This is the recommended way to run ascli on Windows when the Python
Scripts directory is not on PATH:

    python -m anyscribecli onboard
    python -m anyscribecli transcribe "https://..."
"""

from anyscribecli.cli.main import app

app()
