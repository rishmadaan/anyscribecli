# Building Docs — Recent Entries

| Date | Type | Entry | TL;DR |
|------|------|-------|-------|
| 2026-03-31 | project-note | [[journal/2026-03-31-v053-ytdlp-auto-update.md\|v0.5.3 yt-dlp Auto-Update]] | Auto-detect and update stale yt-dlp (>60 days old) before any download. Prevents 403 errors from YouTube streaming format changes. |
| 2026-03-30 | project-note | [[journal/2026-03-30-v050-052-workspace-pypi-flatten.md\|v0.5.0–v0.5.2 Workspace, PyPI, Flatten]] | Configurable workspace path, PyPI automation via GitHub Actions, media→downloads rename, flattened workspace structure (removed date folders). Three migrations, one release script. |
| 2026-03-30 | plan | [[plans/flatten-workspace-structure.md\|Flatten Workspace Structure]] | Remove YYYY-MM-DD date folders — flatten to sources/&lt;platform&gt;/&lt;slug&gt;.md. Auto-migrate existing files on first run. (Done in v0.5.2) |
| 2026-03-30 | project-note | [[journal/2026-03-30-v041-claude-code-skill.md\|v0.4.1 Claude Code Skill]] | Built a Claude Code skill that teaches Claude how to use ascli for end users. Bundled in package, distributed via install-skill command and onboard integration. |
| 2026-03-30 | feature | [[journal/2026-03-30-local-file-transcription.md\|Local File Transcription]] | Added local file transcription — mp3, mp4, m4a, wav, opus, ogg, flac, webm, aac, wma files. New LocalFileDownloader, updated CLI and vault writer. |
| 2026-03-30 | project-note | [[journal/2026-03-30-v032-onboard-reconfig-ux.md\|v0.3.2 Onboard Reconfig UX]] | onboard --force shows current settings, asks before overwriting. Instagram error message fix. |
| 2026-03-29 | reference | [[ops/pypi-guide.md\|PyPI Publishing Guide]] | How PyPI works, first-time setup, TestPyPI, API tokens, troubleshooting. |
| 2026-03-29 | reference | [[ops/release-checklist.md\|Release Checklist]] | Step-by-step for every release — version bump through PyPI publish and verification. |
| 2026-03-29 | reference | [[ops/whats-automated.md\|What's Automated vs Manual]] | Self-update system, doctor checks, and what remains manual (versioning, publishing, docs). |
| 2026-03-29 | project-note | [[journal/2026-03-29-v031-documentation-accuracy-audit.md\|v0.3.1 Documentation Accuracy Audit]] | Full doc audit — 16 issues fixed across README, user docs, building docs. Fake terminal output, wrong paths, missing flags. |
| 2026-03-27 | project-note | [[journal/2026-03-27-v030-download-media-ux.md\|v0.3.0 Download, Media, UX]] | Download command, media outside vault, arrow-key selectors, URL validation, Instagram password to .env |
| 2026-03-26 | project-note | [[journal/2026-03-26-v020-full-feature-build.md\|v0.2.0 Full Feature Build]] | Built all features — Instagram, 4 new providers, batch, config commands, full onboarding |
| 2026-03-26 | decision | [[journal/2026-03-26-initial-architecture.md\|Initial Architecture]] | Initial architecture for anyscribecli MVP — layered pipeline with pluggable providers and downloaders |
