---
type: troubleshooting
tags: [web-ui, uploads, local-files]
tldr: "Web UI uploads now keep the original filename in an isolated temp subdirectory so transcript slugs come from the user's file name instead of a UUID."
---

# Web Upload Filename Preservation

The Web UI upload endpoint used to save uploaded local files as a short UUID
plus the original extension. That avoided collisions, but it also meant the
local-file downloader saw a title like `3f2a8b9c` and the vault writer produced
transcripts named after upload UUIDs instead of the user's actual file.

The fix keeps collision avoidance at the directory level: every upload gets a
short UUID subdirectory under the temp uploads directory, while the file inside
that directory keeps its original filename. The filename is lightly sanitized by
dropping directory components, null bytes, leading dots, and surrounding
whitespace.

This preserves the downstream invariant that `LocalFileDownloader` derives the
title from `Path.stem`, so an uploaded file named `My Recording.mp3` naturally
becomes a transcript slug like `my-recording`.
