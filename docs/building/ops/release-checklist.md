---
type: reference
tags: [release, checklist, versioning, pypi, distribution]
tldr: "Step-by-step checklist for every anyscribecli release — version bump through PyPI publish and post-release verification."
---

# Release Checklist

Follow this every time you release a new version of anyscribecli. Do not skip steps.

---

## Pre-Release

### 1. Make Sure Code Is Ready

```bash
# Run tests
pytest

# Lint
ruff check src/

# Format
ruff format src/

# Run the app — smoke test key commands
ascli --version
ascli doctor
```

Everything must pass. Do not release with failing tests or lint errors.

### 2. Check That All Docs Are Updated

Run through `docs/building/COMMIT_CHECKLIST.md`:

- [ ] README reflects current features and commands
- [ ] `docs/user/commands.md` covers any new/changed commands
- [ ] `docs/user/configuration.md` covers any new config options
- [ ] `docs/user/getting-started.md` is still accurate
- [ ] `docs/user/providers.md` reflects current providers
- [ ] `docs/building/` has a journal entry for significant changes
- [ ] `BACKLOG.md` is updated (move completed items, add new ones)

### 3. Decide the Version Number

SemVer rules for this project:

| Change Type | Bump | Example |
|-------------|------|---------|
| Bug fix, typo, small tweak | PATCH | 0.3.0 → 0.3.1 |
| New feature, new provider, new command (backwards compatible) | MINOR | 0.3.0 → 0.4.0 |
| Breaking change (config format, removed commands, renamed flags) | MAJOR | 0.x → 1.0.0 |

> While in `0.x` pre-stable, breaking changes are allowed between minor versions.

---

## Release

### 4. Bump Version in Two Files

Both must match. Update both at the same time.

**File 1:** `src/anyscribecli/__init__.py`
```python
__version__ = "X.Y.Z"
```

**File 2:** `pyproject.toml`
```toml
version = "X.Y.Z"
```

### 5. Commit and Tag

```bash
git add src/anyscribecli/__init__.py pyproject.toml
git commit -m "Bump version to X.Y.Z"
git tag vX.Y.Z
git push && git push --tags
```

### 6. Build Distribution Files

```bash
# Always clean first — stale builds cause subtle issues
rm -rf dist/

# Build
python -m build
```

This creates two files in `dist/`:
- `anyscribecli-X.Y.Z.tar.gz`
- `anyscribecli-X.Y.Z-py3-none-any.whl`

### 7. Verify the Build

```bash
# Check for packaging issues
twine check dist/*
```

Must say "PASSED" for both files. If it warns about the README, fix the markdown.

### 8. Upload to PyPI

```bash
twine upload dist/*
```

Uses credentials from `~/.pypirc`. If that file doesn't exist, twine will prompt for username (`__token__`) and password (your API token).

> **This is irreversible.** Once uploaded, this version number is permanently claimed. You cannot re-upload or overwrite it. If something is wrong, you must release a new PATCH version.

---

## Post-Release

### 9. Verify the Published Package

```bash
# Install in a clean environment to verify
python -m venv /tmp/ascli-test
source /tmp/ascli-test/bin/activate
pip install anyscribecli
ascli --version    # Should show new version
ascli doctor       # Should pass
deactivate
rm -rf /tmp/ascli-test
```

### 10. Create a GitHub Release (Optional but Recommended)

```bash
gh release create vX.Y.Z \
  --title "vX.Y.Z — Short Description" \
  --notes "## What's New

- Feature 1
- Feature 2
- Bug fix

## Install / Update

\`\`\`bash
pip install --upgrade anyscribecli
\`\`\`"
```

This gives users a changelog on GitHub and shows download counts per release.

### 11. Verify Update Path Works

```bash
# From an existing install, test that update works
ascli update --check    # Should detect new version
ascli update            # Should install it
ascli --version         # Should show new version
```

### 12. Write a Building Doc Journal Entry

For significant releases, create `docs/building/journal/YYYY-MM-DD-vXYZ-<slug>.md` describing what changed and why. Update `docs/building/_index.md`.

---

## Quick Reference (Copy-Paste Block)

For when you just need the commands:

```bash
# Pre-flight
pytest && ruff check src/

# Bump version in __init__.py AND pyproject.toml, then:
git add src/anyscribecli/__init__.py pyproject.toml
git commit -m "Bump version to X.Y.Z"
git tag vX.Y.Z
git push && git push --tags

# Build and publish
rm -rf dist/
python -m build
twine check dist/*
twine upload dist/*

# Verify
pip install --upgrade anyscribecli
ascli --version
```

---

## If Something Goes Wrong

| Scenario | What to Do |
|----------|-----------|
| Uploaded with a bug | Release a PATCH (X.Y.Z+1) immediately |
| Wrong version number | Can't undo — release the correct version as the next bump |
| Upload fails with 403 | API token expired — regenerate at pypi.org, update ~/.pypirc |
| Upload fails with 400 | Version already exists — you need a new version number |
| `ascli` command not found after install | Check `[project.scripts]` in pyproject.toml, rebuild |
| Tests pass locally but package broken | Test in a clean venv (step 9) before publishing |
