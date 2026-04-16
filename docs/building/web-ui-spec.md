# Scribe Web UI — Frontend Specification

> **Status:** Proposed  
> **Date:** 2026-04-16  
> **Author:** Rish Madaan  

## Overview

A single-page web application that serves as the GUI for scribe — replacing the terminal experience with a fast, modern, native-feeling interface. The backend is a Python FastAPI server that wraps the existing CLI orchestrator. This document specifies the **frontend only**.

The app runs locally at `http://localhost:6227`. No auth, no cloud, no accounts. It is a personal productivity tool.

---

## Architecture Decision

**Choice: Local web UI served by the Python process (`scribe ui`)**

Evaluated alternatives:

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Local web UI** | Direct Python code reuse, zero packaging, cross-platform, fastest to build | Needs server start, no system tray | **Phase 1** |
| **Tauri wrapper** | Native window, system tray, lightweight (~10MB) | Bridge to Python, Rust complexity | Phase 2 |
| **Electron** | Cross-platform, deep OS integration | 150MB+ runtime, two runtimes (Node + Python) | Skip |
| **Native Swift** | Best macOS experience, menubar/share sheet | macOS-only, rewrite or bridge all Python logic | Phase 3 (maybe) |

**Progression path:**
1. **Phase 1 (now):** `scribe ui` → Starlette + React SPA → browser tab
2. **Phase 2 (later):** Tauri shell around the same web UI → native window + tray
3. **Phase 3 (maybe):** Swift menubar app for macOS power users

The web UI built in phase 1 is reused in phases 2 and 3. No throwaway work.

---

## Design Philosophy

**Reference aesthetic:** Linear, Raycast, Arc Browser, Vercel Dashboard.

Dark mode first (with light mode toggle). The UI should feel like a native desktop app that happens to run in a browser — not a "web app."

**Principles:**
- **Speed of access is everything.** Paste URL → transcribe must take under 2 seconds from page load. No wizard, no modal, no confirmation — just paste and go.
- **Information density over whitespace.** Show history, current status, and settings at a glance. Don't hide information behind tabs unless necessary.
- **Subtle motion.** Micro-animations for state transitions (processing → complete), but never block interaction with animation. Progress indicators should feel alive, not static spinners.
- **Monospace accents.** Monospace font (JetBrains Mono / Berkeley Mono / Geist Mono) for data values (durations, word counts, file paths). Proportional sans-serif (Inter / Geist Sans) for headings and body text.

---

## Tech Stack

- **Framework:** React 19 + TypeScript (Vite)
- **Styling:** Tailwind CSS v4 + shadcn/ui components
- **State:** Zustand (lightweight, no boilerplate)
- **Icons:** Lucide React
- **Animations:** Framer Motion (subtle transitions only)
- **WebSocket:** Native WebSocket API
- **Build output:** Static files served by the Python backend from `/static`

---

## Layout

Single page with a persistent sidebar (collapsible on narrow viewports).

```
┌─────────────────────────────────────────────────────┐
│  ⌘  Scribe                          [⚙] [🌙/☀️]   │  ← Top bar
├──────────┬──────────────────────────────────────────┤
│          │                                          │
│ History  │          Main Content Area               │
│          │                                          │
│ ──────── │  (Transcribe / Batch / Settings view)    │
│ Today    │                                          │
│  · vid1  │                                          │
│  · vid2  │                                          │
│ Yesterday│                                          │
│  · vid3  │                                          │
│          │                                          │
│          │                                          │
├──────────┴──────────────────────────────────────────┤
│  Status bar: provider · language · workspace path   │  ← Persistent footer
└─────────────────────────────────────────────────────┘
```

---

## Screens

### 1. Transcribe View (default, primary)

Where users spend 90% of their time. Must be the first thing they see.

**Input state:**

```
┌─────────────────────────────────────────────────┐
│                                                 │
│   ┌─────────────────────────────────────────┐   │
│   │  🔗  Paste a URL or drop a file...      │   │  ← Large input field
│   │      [📋 Paste]  [📁 Browse]            │   │     clipboard + file picker
│   └─────────────────────────────────────────┘   │
│                                                 │
│   ┌─ Options (collapsed by default) ───────┐   │
│   │  Provider: [openai ▾]                   │   │  ← Inline dropdowns
│   │  Language: [auto ▾]                     │   │
│   │  ☐ Speaker diarization                  │   │
│   │  ☐ Keep media files                     │   │
│   └─────────────────────────────────────────┘   │
│                                                 │
│   [ ▶  Transcribe ]                             │  ← Primary action button
│                                                 │
└─────────────────────────────────────────────────┘
```

**Behaviors:**
- Auto-detect URL type on paste: show badge — "YouTube" (red), "Instagram" (pink), "Local file" (gray)
- Options section is a disclosure accordion — collapsed by default, showing one-line summary: `openai · auto · no diarization`
- Hitting Transcribe transforms the input area into the progress view in-place (no navigation)

**Progress state:**

```
┌─────────────────────────────────────────────────┐
│                                                 │
│   Transcribing                                  │
│   "How to Build a Second Brain — Ali Abdaal"    │  ← Title from download
│   youtube.com                                   │
│                                                 │
│   ━━━━━━━━━━━━━━━━━━━━━━━━━━░░░░░░░  68%       │  ← Smooth progress bar
│                                                 │
│   ✓ Downloaded audio          0:42              │  ← Step checklist
│   ✓ Transcribing with openai  2:18              │
│   ◉ Writing to vault...                         │  ← Pulsing dot
│   ○ Updating indexes                            │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Completion state:**

```
┌─────────────────────────────────────────────────┐
│                                                 │
│   ✓ Done                                        │
│   "How to Build a Second Brain — Ali Abdaal"    │
│                                                 │
│   Duration    Language    Words     Provider     │
│   45:12       en          8,432     openai       │  ← Stat cards
│                                                 │
│   📄 ~/anyscribe/how-to-build-a-second-brain.md │  ← Clickable path
│                                                 │
│   [ Open in Obsidian ]  [ Copy Path ]  [ New ]  │
│                                                 │
└─────────────────────────────────────────────────┘
```

- "New" resets back to input form
- Result card: subtle slide-up + fade-in entrance animation

### 2. Batch View

For processing multiple URLs at once.

```
┌─────────────────────────────────────────────────┐
│  Batch Transcribe                               │
│                                                 │
│  ┌─────────────────────────────────────────┐    │
│  │  Paste URLs (one per line)              │    │  ← Textarea, monospace
│  │  https://youtube.com/watch?v=abc        │    │
│  │  https://youtube.com/watch?v=def        │    │
│  │  /Users/me/recording.mp3               │    │
│  └─────────────────────────────────────────┘    │
│                                                 │
│  Or: [ Upload .txt file ]                       │
│                                                 │
│  3 URLs detected · openai · auto                │
│  [ ▶  Start Batch ]                             │
│                                                 │
│  ── Progress ──────────────────────────────────  │
│  ✓  Ali Abdaal - Second Brain     8,432 words   │
│  ◉  Huberman - Sleep Protocol     transcribing  │
│  ○  Recording.mp3                 queued         │
│                                                 │
│  ━━━━━━━━━━━━━━━━━━░░░░░░░░░░  2/3 complete     │
└─────────────────────────────────────────────────┘
```

### 3. History (sidebar)

Transcription history grouped by date. Each entry shows:
- Title (truncated ~30 chars)
- Platform icon (YouTube / Instagram / file)
- Duration
- Word count (subtle, gray)

**Search/filter input** at the top of the sidebar. Clicking an entry opens a detail panel in the main content area.

**Empty state:** "No transcriptions yet. Paste a URL to get started." with a subtle icon.

### 4. Settings View

Full-page settings (not a modal). Accessible via gear icon.

#### General

| Setting | Control | Options |
|---------|---------|---------|
| Default provider | Dropdown with descriptions | openai — General purpose, multilingual, segment timestamps |
| | | elevenlabs — High accuracy, 99 languages, word-level timestamps |
| | | openrouter — Access various models via unified API |
| | | deepgram — Fast, accurate, native diarization + Hindi Latin support |
| | | sargam — Optimized for Indic languages (Hindi, Tamil, Telugu, etc.) |
| | | local — Offline, free, runs on your machine |
| Default language | Dropdown + custom input | auto, en, es, fr, hi, ar, zh, ja, ko, or custom code |
| Output format | Segmented control | clean \| timestamped \| diarized |
| Keep media | Toggle switch | on / off |
| Local file handling | Segmented control | skip \| copy \| move \| ask |
| Post-transcription download | Segmented control | never \| ask \| always |

#### API Keys

One masked field per provider. Each has:
- Show/hide toggle
- "Get API key →" link to the provider's dashboard
- "Test" button that hits the provider test endpoint
- Green/red dot indicating if key is set

| Provider | Env var | Key URL |
|----------|---------|---------|
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| OpenRouter | `OPENROUTER_API_KEY` | https://openrouter.ai/keys |
| ElevenLabs | `ELEVENLABS_API_KEY` | https://elevenlabs.io/app/settings/api-keys |
| Deepgram | `DEEPGRAM_API_KEY` | https://console.deepgram.com/ |
| Sarvam | `SARGAM_API_KEY` | https://dashboard.sarvam.ai |

#### Instagram

- Username: text input
- Password: password input
- Note: "A secondary/dummy account is recommended"

#### Workspace

- Current path displayed (e.g., `~/anyscribe/`)
- Text input to change (browser can't do native folder picker)
- Show resolved absolute path below

#### About

- Version: displayed from API
- Links: GitHub repo, documentation

All settings auto-save on change (debounced 500ms) with a subtle "Saved" toast.

---

## API Contract

The frontend is built against these endpoints. The backend implements them separately.

### REST

```
GET  /api/config              → { provider, language, keep_media, output_format, diarize,
                                   prompt_download, local_file_media, workspace_path,
                                   instagram: { username } }

PUT  /api/config              ← { ...partial settings } → { ...full updated settings }

GET  /api/providers           → [{ name, description, active, has_key }]
POST /api/providers/test      ← { name } → { success, message }

PUT  /api/keys                ← { provider_name, api_key } → { success }
GET  /api/keys/status         → { openai: true, elevenlabs: false, ... }

POST /api/transcribe          ← { url, provider?, language?, diarize?, keep_media? }
                              → { job_id }

POST /api/batch               ← { urls: [...], provider?, language?, diarize? }
                              → { batch_id }

GET  /api/history             → [{ id, title, platform, duration, language, word_count,
                                    provider, file_path, created_at }]
GET  /api/history/:id         → { ...full detail }

GET  /api/workspace/info      → { path, file_count, total_words }
```

### WebSocket: `/ws/jobs`

Real-time progress updates after starting a job.

```jsonc
// Server → Client messages:
{ "job_id": "abc", "type": "step",     "step": "downloading",  "message": "Downloading audio..." }
{ "job_id": "abc", "type": "step",     "step": "transcribing", "message": "Transcribing with openai..." }
{ "job_id": "abc", "type": "progress", "step": "transcribing", "percent": 68 }
{ "job_id": "abc", "type": "step",     "step": "writing",      "message": "Writing to vault..." }
{ "job_id": "abc", "type": "metadata", "title": "Video Title", "platform": "youtube" }
{ "job_id": "abc", "type": "complete", "result": {
    "file_path": "~/anyscribe/video-title.md",
    "title": "Video Title",
    "platform": "youtube",
    "duration": "45:12",
    "language": "en",
    "word_count": 8432,
    "provider": "openai"
  }
}
{ "job_id": "abc", "type": "error", "message": "API key not set for openai" }
```

---

## Color System

### Dark mode (default)

| Token | Value | Usage |
|-------|-------|-------|
| Background | `#0A0A0B` | Page background (near-black, not pure black) |
| Surface | `#141416` | Cards, sidebar |
| Surface elevated | `#1C1C1F` | Hover states, dropdowns |
| Border | `#27272A` | Dividers, card borders (zinc-800) |
| Text primary | `#FAFAFA` | Headings, body |
| Text secondary | `#A1A1AA` | Labels, captions (zinc-400) |
| Text muted | `#52525B` | Disabled, placeholder (zinc-600) |
| Accent | `#6366F1` | Primary actions, active states (indigo-500) |
| Accent hover | `#818CF8` | Button hover (indigo-400) |
| Success | `#22C55E` | Completed states (green-500) |
| Error | `#EF4444` | Errors (red-500) |
| Warning | `#F59E0B` | Warnings (amber-500) |
| YouTube | `#FF0000` | YouTube badge |
| Instagram | `#E1306C` | Instagram badge |

### Light mode

| Token | Value | Usage |
|-------|-------|-------|
| Background | `#FAFAFA` | Page background |
| Surface | `#FFFFFF` | Cards, sidebar |
| Border | `#E4E4E7` | Dividers (zinc-200) |
| Text primary | `#09090B` | Headings, body |
| Text secondary | `#71717A` | Labels (zinc-500) |
| Accent | `#4F46E5` | Primary actions (indigo-600) |

---

## Interaction Details

### URL input field
- Large hit area (min 48px height)
- Placeholder: "Paste a YouTube or Instagram URL, or drop a file..."
- On focus: subtle glow with accent color
- Drag-and-drop support for local audio/video files
- Auto-detect platform badge on paste:
  - `youtube.com` or `youtu.be` → YouTube (red badge)
  - `instagram.com` → Instagram (pink badge)
  - Starts with `/` or `~` → Local file (gray badge)
- Inline validation warning for malformed URLs (not a toast)

### Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + V` | Paste and auto-start (when input focused) |
| `Cmd/Ctrl + Enter` | Start transcription |
| `Cmd/Ctrl + K` | Focus sidebar search |
| `Cmd/Ctrl + ,` | Open settings |
| `Cmd/Ctrl + N` | New transcription (reset form) |

Show shortcuts in a `?` tooltip in the top bar.

### Toasts

Bottom-right stack, max 3 visible:
- "Settings saved" — success, auto-dismiss 2s
- "API key updated" — success, auto-dismiss 2s
- "Transcription complete: {title}" — success, persists until dismissed
- Error messages — error, persists until dismissed

### Loading states
- Skeleton loaders for history list while fetching
- Pulse animation on the active processing step
- CSS animation for indeterminate progress between percentage updates

---

## Responsive Behavior

| Breakpoint | Behavior |
|-----------|----------|
| ≥1024px | Full layout, sidebar visible |
| 768–1023px | Sidebar collapsed to icons, expandable on click |
| <768px | Sidebar hidden behind hamburger. Main content full-width. Larger touch targets. |

---

## File Structure

```
ui/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── global.css
│   ├── lib/
│   │   ├── api.ts              # REST API client
│   │   ├── ws.ts               # WebSocket connection manager
│   │   └── utils.ts
│   ├── stores/
│   │   ├── config.ts           # Settings state (Zustand)
│   │   ├── jobs.ts             # Active transcription jobs
│   │   └── history.ts          # Transcription history
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── TopBar.tsx
│   │   │   └── StatusBar.tsx
│   │   ├── transcribe/
│   │   │   ├── URLInput.tsx
│   │   │   ├── Options.tsx
│   │   │   ├── Progress.tsx
│   │   │   └── Result.tsx
│   │   ├── batch/
│   │   │   ├── BatchInput.tsx
│   │   │   └── BatchProgress.tsx
│   │   ├── settings/
│   │   │   ├── GeneralSettings.tsx
│   │   │   ├── APIKeys.tsx
│   │   │   ├── InstagramSettings.tsx
│   │   │   └── WorkspaceSettings.tsx
│   │   └── ui/                 # shadcn/ui components
│   └── hooks/
│       ├── useWebSocket.ts
│       ├── useClipboard.ts
│       └── useKeyboardShortcuts.ts
```

---

## Definition of Done

1. `npm run dev` opens a working SPA at localhost:5173
2. All 4 views (transcribe, batch, settings, history detail) functional against mock data (MSW or local mock server)
3. Dark mode default, light mode toggle works
4. Transcribe flow (paste → progress → result) end-to-end with mock WebSocket messages
5. All keyboard shortcuts work
6. Responsive at all 3 breakpoints
7. Realistic mock data — no placeholder lorem ipsum
8. Fast: no layout shift, no FOUC, instant navigation
9. `npm run build` produces a static bundle servable from any directory

---

## Backend Integration Notes

The existing Python codebase has a clean orchestrator at `core/orchestrator.py` with a synchronous `process()` function. To support the web UI:

1. **Async wrapper:** Run `process()` in a background thread, emit progress events via callback
2. **Decouple from Rich:** Replace Rich console writes with an event emitter so the WebSocket can relay progress
3. **History:** Read the Obsidian vault's markdown files + frontmatter to build the history endpoint
4. **Static serving:** FastAPI/Starlette serves the built frontend from `ui/dist/` at the root path
