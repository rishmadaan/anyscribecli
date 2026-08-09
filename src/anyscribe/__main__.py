"""Allow running as `python -m anyscribe`.

This is the recommended way to run anyscribe on Windows when the Python
Scripts directory is not on PATH:

    python -m anyscribe onboard
    python -m anyscribe "https://..."
"""

from anyscribe.cli.main import app

app()
