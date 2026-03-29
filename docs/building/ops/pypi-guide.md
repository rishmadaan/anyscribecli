---
type: reference
tags: [pypi, distribution, publishing, first-time-setup]
tldr: "Complete guide to how PyPI works, first-time setup, TestPyPI, API tokens, and how to publish anyscribecli."
---

# PyPI Publishing Guide

## How PyPI Works

PyPI (Python Package Index) is the App Store for Python packages. When someone runs `pip install anyscribecli`, pip goes to pypi.org, finds the package, downloads it, and installs it.

The flow:

```
Your code → Build (creates .tar.gz + .whl) → Upload to PyPI → Users install with pip
```

### What Gets Built

When you build, two files are created in `dist/`:

- `anyscribecli-X.Y.Z.tar.gz` — source distribution (raw code)
- `anyscribecli-X.Y.Z-py3-none-any.whl` — wheel (pre-built, installs faster)

Both get uploaded. pip prefers the wheel.

### What PyPI Reads

PyPI pulls your project page from `pyproject.toml`:
- `name`, `version`, `description` → shown on the project page
- `readme = "README.md"` → rendered as the long description
- `project.urls` → links sidebar on the project page
- `project.scripts` → the `ascli` CLI entry point

All of this is already configured in your `pyproject.toml`.

---

## First-Time Setup (Do This Once)

### 1. Install Build Tools

```bash
pip install build twine
```

- `build` — creates the distribution files
- `twine` — uploads them to PyPI

### 2. Create a TestPyPI Account

Go to **test.pypi.org** and create an account. This is a sandbox — same system as real PyPI, but nothing there is "real." Use this for dry runs.

1. Go to test.pypi.org → Register
2. Verify email
3. Go to Account Settings → API Tokens → Add API Token
4. Scope: "Entire account" (first upload, project doesn't exist yet)
5. Save the token — you only see it once

### 3. Create a Real PyPI API Token

Go to **pypi.org** → Account Settings → API Tokens → Add API Token.

- First upload: scope to "Entire account" (project doesn't exist yet)
- After first upload: delete this token, create a new one scoped to `anyscribecli` only

### 4. Save Tokens in ~/.pypirc

Create `~/.pypirc` so you don't type tokens every time:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR-REAL-TOKEN-HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR-TEST-TOKEN-HERE
```

> **Security:** This file contains secrets. Make sure it's not in any git repo. Check with `ls -la ~/.pypirc` — it should be `-rw-------` (owner-only). Fix with `chmod 600 ~/.pypirc` if needed.

---

## TestPyPI Dry Run (Do This Before First Real Publish)

```bash
# 1. Clean and build
rm -rf dist/
python -m build

# 2. Upload to TestPyPI
twine upload --repository testpypi dist/*

# 3. Install from TestPyPI to verify
pip install --index-url https://test.pypi.org/simple/ anyscribecli

# 4. Test it works
ascli --version
```

If something is wrong (bad description, missing metadata), fix it and bump the version — you cannot re-upload the same version number, even on TestPyPI.

---

## Publishing for Real

See [release-checklist.md](release-checklist.md) for the full step-by-step process you follow every release.

The core commands:

```bash
rm -rf dist/
python -m build
twine upload dist/*
```

---

## Key Rules

### Versions Are Immutable

Once you upload `0.3.0`, it's permanent. You cannot overwrite it, delete it, or re-upload it. If you find a bug, you must bump to `0.3.1`. This is why TestPyPI exists — test there first.

### Name Is Claimed on First Upload

The name `anyscribecli` gets reserved to your account on first upload. Nobody else can use it after that.

### README Rendering

PyPI renders your README.md as the project description. If it looks broken, check:
- No relative image links (PyPI can't resolve them — use full GitHub raw URLs)
- Standard markdown only (no GitHub-specific extensions)
- Preview locally: `twine check dist/*` catches some rendering issues

---

## After Publishing

### Your Project Page

`https://pypi.org/project/anyscribecli/`

Shows: description, version history, install command, metadata, links.

### Download Stats

`https://pypistats.org/packages/anyscribecli`

Shows: daily/weekly/monthly downloads, broken down by Python version, OS, and package version. Updates daily with ~1 day lag. No code changes needed — this is automatic for all PyPI packages.

### Update install.sh

After the first real publish, update `install.sh` to use PyPI as primary:

```bash
pip install anyscribecli           # instead of git+https://github.com/...
```

The GitHub fallback can stay as a backup.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `twine upload` fails with 403 | Token expired or wrong scope | Regenerate token, update ~/.pypirc |
| `twine upload` fails with 400 | Version already exists on PyPI | Bump version, rebuild, re-upload |
| Package installs but `ascli` not found | Entry point misconfigured | Check `[project.scripts]` in pyproject.toml |
| README looks broken on PyPI | Unsupported markdown or relative links | Run `twine check dist/*`, fix markdown |
| `pip install` gets old version | pip cache | `pip install --no-cache-dir anyscribecli` |
