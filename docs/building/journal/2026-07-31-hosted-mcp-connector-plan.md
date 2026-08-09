# Hosted MCP Connector ("Anyscribe Cloud") — Full Plan

```yaml
type: plan
tags: [mcp, hosted, connector, claude-ai, youtube, neon, auth, research]
tldr: >
  Plan (not implemented): turn anyscribe into a remote MCP connector any
  claude.ai user can add once — hosted by us, subscription-gated, team-first.
  Core research finding: don't fight YouTube's bot war. Caption-first pipeline
  (~90% of videos, ~$0.002/video via Supadata), Gemini URL-ingestion or
  Firecrawl→Groq for the rest, self-hosted yt-dlp+residential-proxy only as
  fallback. Stack: FastMCP 3.4.x mounted into the existing FastAPI app,
  WorkOS AuthKit (CIMD+DCR), Neon Postgres ledger, single Hetzner CX33 box.
```

**Status: PLAN.** Decided 2026-07-31 with Rish: build it; billing model (b) — we pay
for transcription, access via subscription, team-only at first; Neon DB as the
per-user transcription ledger. Instagram is **out of scope** for the hosted
product (requires holding user Instagram sessions server-side — refused on
security grounds). The local CLI/vault product continues unchanged; this is a
second deployment surface, not a replacement.

All load-bearing claims below come from three verified research reports
(2026-07-31): YouTube access state-of-the-art, claude.ai connector
requirements, and hosting. Key sources inline.

> **§3's MCP-layer stack decision is superseded — see [§7 Update (2026-08-09)](#7-update--2026-08-09-the-2026-07-28-spec-shipped).**
> The 2026-07-28 spec and official SDK v2 both went stable on 2026-07-28, after
> this plan was written. Everything else below (YouTube lanes, auth
> requirements, database, hosting, costs, phases) stands unchanged. Sections 1–6
> are preserved as written on 2026-07-31 rather than edited, per the
> append-only rule for journal entries.

---

## 1. Product shape

A user on any claude.ai plan (Free included, 1-connector limit there) goes to
Settings → Connectors → Add custom connector → enters our URL → logs in →
done. From then on, in any chat on web/desktop/mobile/Claude Code:

> "transcribe https://youtube.com/watch?v=… and pull out the action items"

Claude calls our server. We fetch/produce the transcript, store it in the
user's cloud library (Neon), and return markdown into the chat. No install,
no Python, no vault, no API keys for the user.

**Not in v1:** Instagram, public directory listing, Stripe self-serve billing
(team access is a manual allowlist), export/sync of the cloud library to a
local vault.

---

## 2. The YouTube problem — research verdict (the load-bearing decision)

Question asked: is there a *proper* solution to YouTube blocking datacenter
IPs, not just workarounds? **Answer: yes — the proper solution is
architectural: stop downloading media for the common case.**

Verified facts that force this:

- Cloud IPs (AWS/GCP/Azure and broadly all datacenter ASNs) are blocked by
  default; blocking is **ASN/range-level**, so hopping providers buys weeks,
  not a fix (yt-dlp maintainer bashonly: "PO tokens are **not** a solution if
  your IP is already blocked", yt-dlp#16773).
- PO tokens are now **per-video** attestations; yt-dlp needs a JS runtime
  (Deno) + bgutil sidecar; 15 releases in 10 months incl. 3 emergency
  releases in one week (Jan 2026). Running this as the primary pipeline is a
  permanent pager subscription.
- Media URLs are **IP-signed** (verified: `ip=` inside `sparams`), so
  extract-and-download must exit the same sticky proxy IP.
- **Caption URLs are NOT IP-bound** (verified: signed over `ip=0.0.0.0`;
  plain `curl` fetch succeeded, ~7h lifetime). An `srt` is ~90 KB/hour vs
  22–58 MB/hour for audio.
- ~90% of talk-content videos have (auto-)captions (12-video sample: 11/12).
- Account/cookie fleets are the highest-risk path: Google permanently bans
  accounts it believes were created for automation; OAuth login is dead.
- Legal: no configuration of scraping/downloading is ToS-compliant, incl.
  buying scraped data (Developer Policies §III.E). But observed enforcement
  against transcription services is **zero** to date; Google's real
  enforcement is technical (blocks), and its active lawsuits target
  scraping-**API resellers** (SerpApi), music, and training-data harvesting.
  A consumer transcription product consuming existing captions sits at the
  bottom of the risk stack. *Yout v. RIAA* is still undecided on appeal.
  EU precedent (OLG Hamburg 2024) is settled *against* media downloaders —
  another reason to prefer the caption/Gemini lanes over media download.

### The three-lane pipeline

```
YouTube URL
  ├─ Lane A (~90%): captions exist → buy them (Supadata: 1 credit ≈ $0.002/video,
  │                 any length) → format into anyscribe markdown
  ├─ Lane B (~10%): no captions →
  │     B1: Gemini API YouTube-URL ingestion (~$0.11/hr; Google reading Google,
  │         structurally unblockable, cleanest ToS posture; PREVIEW — must pass
  │         the verbatim-quality spike test first)
  │     B2: Firecrawl `audio` format (returns real MP3, 5 credits/page)
  │         → Groq whisper-large-v3-turbo ($0.04/hr) through existing provider code
  └─ Lane C (fallback only, phase 2+): self-hosted yt-dlp + bgutil PO-token
        sidecar + Deno + rotating residential proxy (Webshare ~$2.75/GB,
        sticky sessions; ~$0.03–0.16/hr bandwidth). Built because vendors go
        down, never as primary.
```

Direct file/audio URLs and user uploads skip all lanes → existing
orchestrator ASR path with our keys (Groq primary).

Supadata's own pricing (1 credit for existing captions vs 2 credits/**minute**
for generated) proves caption-first is the production pattern the whole
market runs on.

**Spike tests before building (Phase 0):**
1. Gemini YouTube-URL verbatim test — 5 videos, diff against Whisper. Decides
   whether B1 or B2 is the no-caption lane.
2. Supadata free tier (100 credits) against ~20 real team URLs — reliability
   + caption formatting quality.
3. Check auto-caption quality bar on our real content (Hinglish!). If
   auto-captions are too rough for Hindi/Hinglish content, default those
   languages to Lane B ASR (Sarvam/Deepgram already in the codebase).

**Watch item:** the `exp=xpe` experiment (PO tokens for subtitles,
youtube-transcript-api#592) could close the *self-built* caption path; vendor
APIs absorb that risk for us — one more reason to buy Lane A.

---

## 3. Architecture

```
claude.ai / Desktop / mobile / Claude Code
        │  Streamable HTTP + OAuth (WorkOS AuthKit)
        ▼
FastAPI app (existing src/anyscribe/web/app.py)
  ├─ /.well-known/oauth-protected-resource[…]   ← BEFORE the SPA catch-all!
  ├─ /mcp  ← FastMCP 3.4.x app, mounted, stateless_http=True, spec 2025-11-25
  ├─ existing Web UI + REST (unchanged, localhost use)
  ▼
JobManager (existing web/jobs.py, extended: persist to Neon, user-scoped)
  ▼
orchestrator → lane router (captions / gemini / firecrawl+groq / yt-dlp)
  ▼
Neon Postgres (users, jobs, transcripts, usage) — replaces vault writer on
the hosted path; markdown template logic reused from vault/writer.py
```

### MCP layer (reuses `src/anyscribe/mcp/server.py` tool vocabulary)

- **FastMCP 3.4.x pinned** (not 4.0 beta; not official SDK 2.0 — FastMCP is
  the only path with a real auth layer: `AuthKitProvider`, `OAuthProxy`).
  Port from the current stdio server is decorator-compatible.
- Mount with `combine_lifespans` (the mounted-lifespan footgun is the #1
  documented failure). `stateless_http=True` + single instance → no session
  affinity, and the 2026-07-28 sessionless spec migration becomes free.
- **Tools (hosted set):** `transcribe` (start job → returns job_id +
  "call check_job next" text), `check_job`, `get_transcript` (paginated —
  claude.ai caps results at ~150k chars), `list_transcripts`,
  `delete_transcript`, `get_usage`. All with `title` +
  `readOnlyHint`/`destructiveHint` (drives auto-permissions; required if we
  ever list in the directory).
- Job states modeled exactly on MCP Tasks' five states (`working` /
  `input_required` / `completed` / `failed` / `cancelled`) so when claude.ai
  ships the Tasks extension we swap transport, not state machine.
- **claude.ai hard limits:** 300s per tool call (progress notifications do
  NOT extend it) → async jobs from day one. 10s OAuth endpoint timeout.
  IPv4 required; no cross-host redirects on the MCP URL; Anthropic egress
  `160.79.104.0/21`.

### Auth + subscription gating

- **WorkOS AuthKit** (free to 1M MAU) via FastMCP's `AuthKitProvider`.
  Enable **CIMD** in the dashboard (off by default) *and* keep DCR — Claude
  falls back to DCR when CIMD metadata is incomplete; Anthropic recommends
  CIMD for high-traffic connectors.
- Requirements checklist (from Anthropic docs, all non-negotiable): 401 +
  `WWW-Authenticate: Bearer … resource_metadata=…` at the HTTP layer (never
  200 + isError); RFC 9728 PRM with `resource` matching the typed URL
  exactly; first entry only in `authorization_servers`; PKCE S256; refresh
  rotation; `/token` accepts form-encoded.
- **Subscription = allowlist in Neon for v1.** `users.status ∈ {invited,
  active, disabled}`; login succeeds via AuthKit but tools return a polite
  "ask Rish for access" unless status=active. Stripe comes in Phase 2 when
  access opens beyond the team.
- ⚠️ **Landmine already in our code:** the SPA catch-all
  `@app.get("/{full_path:path}")` in `web/app.py` will swallow
  `/.well-known/*` and return index.html. Well-known + MCP mount must
  register before it.

### Database (Neon)

Serverless Postgres, scale-to-zero (fits: idle most of the day, pennies).
Long-running Python server → plain SQLAlchemy/psycopg pool against the
pooled (`-pooler`) endpoint. Branching gives us a free staging DB.

```sql
users        (id, workos_user_id, email, name, status, created_at)
jobs         (id, user_id, url, source_kind, status, lane, progress_step,
              error, created_at, updated_at, ttl_expires_at)
transcripts  (id, user_id, job_id, source_url, title, channel, duration_s,
              lane, provider, language, markdown, created_at)
usage_events (id, user_id, job_id, lane, media_minutes,
              est_cost_usd, created_at)
```

`usage_events` is the ledger Rish asked for: every transcription, per user,
with estimated cost — later the input to billing.

### Hosting

**Hetzner CX33 (4 vCPU / 8 GB / 80 GB, €8.49/mo + IPv4) + Coolify + Caddy
(buffering off), single instance. ~€12/mo all-in.** Chosen because: ffmpeg
CPU is the real constraint and this is the best CPU/$ by 3–5×; no
platform-imposed request timeouts or buffering proxies; full egress control
for the (fallback) proxy lane; 20 TB egress included. Post-June-2026
repricing rule: **buy CX or CAX lines only, never CPX/CCX** (+144–169%).
Managed alternative if ops burden ever bites: Fly.io ≈ $30–50/mo
(`min_machines_running=1`, autostop off). Avoid Railway (15-min request cap,
volumes unshareable), Cloud Run/App Runner (scale-to-zero hostile).

### Guidance layer

Tool descriptions are the only lever that works on claude.ai web/mobile —
invest there first. Phase 2: a plugin (public GitHub repo) bundling a hosted
variant of the existing skill + connector reference for Claude Code/Cowork.
Watch: MCP spec 2026-07-28 "Skills over MCP" extension would let the server
ship its own skill; not on claude.ai yet.

---

## 4. Cost model (team scale)

| Item | Monthly |
|---|---|
| Hetzner CX33 + IPv4 | ~€12 |
| Neon | $0 (free tier) at team scale |
| WorkOS AuthKit | $0 (free to 1M MAU) |
| Supadata Basic/Pro | $5–17 |
| Gemini URL ingest | preview-free today; ~$0.11/hr later |
| Groq ASR (Lane B2/uploads) | $0.04/hr of audio |
| Webshare proxy (only when Lane C is built) | ~$28 for 10 GB, lasts months |

Fixed ≈ **$25–35/mo**; marginal cost ≈ **$0.002/video** captioned, ≈
**$0.05–0.20/hr** uncaptioned. Subscription pricing is unconstrained by cost.

---

## 5. Phases

**Phase 0 — spikes (2–3 days).** The three tests in §2. Output: a journal
entry with lane decision (B1 vs B2) and caption-quality verdict for
Hinglish content.

**Phase 1 — build + team launch (~2–3 weeks).**
1. Neon schema + SQLAlchemy models; job persistence replacing in-memory-only
   JobManager state on the hosted path.
2. Lane A + Lane B behind a `lane_router` in core; markdown via existing
   template logic; store to Neon instead of vault when running hosted.
3. FastMCP mount + the 6 tools; well-known routes before SPA catch-all.
4. AuthKit integration (CIMD + DCR), allowlist gating.
5. Deploy on Hetzner/Coolify; verify with MCP Inspector, then as a REAL
   custom connector (Inspector misses redirect/DNS/WAF failures); team
   onboarding.
6. Docs: user doc for "add the connector", building docs, skill files
   untouched (local product unchanged).

**Phase 2 — hardening + opening up.** Stripe subscriptions; Lane C fallback
(yt-dlp + bgutil + Deno + Webshare sticky sessions); plugin + skill for
Claude Code/Cowork; usage dashboard in the Web UI; consider directory
submission (needs split read/write tools — already true — public docs, test
creds).

**Explicitly deferred:** Instagram; vault export/sync; MCP Tasks + spec
2026-07-28 migration (watch claude.ai support announcements); Prefect
Horizon/managed MCP hosting.

---

## 6. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Gemini URL feature is preview; pricing/limits "likely to change" | It's Lane B1, not the backbone; B2 (Firecrawl→Groq) is the drop-in |
| Supadata outage/price change | Lane B works for captioned videos too (just costlier); Lane C in Phase 2 |
| `exp=xpe` closes DIY caption fetch | We buy Lane A; vendor absorbs it |
| ToS exposure | No enforcement history vs transcription products; team-only, no API resale, no music focus, caption-first; Gemini lane is the cleanest posture. Revisit before any public launch |
| claude.ai ships 2026-07-28 spec / Tasks | Stateless + Tasks-shaped job states make both migrations cheap by design |
| Residential proxy supply chain (NetNut/FBI seizure 2026-07) | Only affects Lane C; diligence provider provenance, keep a second warm |

---

## 7. Update — 2026-08-09: the 2026-07-28 spec shipped

Written 2026-07-31; nine days later the ground under §3 moved. This section
records what is now verified fact and what it changes. Sections 1–6 stay as
written.

### What actually happened

MCP specification revision **`2026-07-28` is now the current spec**, published
2026-07-28. The official Python SDK shipped **`2.0.0` the same day**. anyscribe's
own local stdio server migrated to it in v0.16.3 — see
[[2026-08-09-mcp-sdk-v2-migration.md]] — so we are already running the new
protocol in production on the local product.

The headline change is the one this plan was betting on: **the protocol core is
now stateless**. The `initialize`/`initialized` handshake and the
`Mcp-Session-Id` header are retired. Every request is self-describing, carrying
protocol version and client identity in `_meta`.

### What it changes for the hosted connector

**Session affinity is gone as a design constraint.** §3 chose
`stateless_http=True` on a single instance to dodge it, and called the future
migration "free". That bet paid: any request can now land on any instance behind
plain round-robin, no shared session store. The single Hetzner box stays the
right *starting* size for cost reasons, but it is no longer a correctness
requirement — horizontal scale is now a pure capacity decision.

**`input_required` is a protocol result type, not just our job state.** Multi
Round-Trip Requests (MRTR) replace server-initiated requests over held-open
streams: a tool returns `resultType: "input_required"`, the client retries with
`inputResponses`. §3 modelled job states on the MCP Tasks five-state machine
including `input_required` — that shape is now vindicated and partly native. The
300s claude.ai per-call ceiling still stands, so async jobs from day one remains
correct.

**Two new obligations at the HTTP layer**, both of which touch the Caddy config
in §3's hosting section:

- Requests must carry `Mcp-Method` and `Mcp-Name` headers, so gateways can route
  and meter without parsing the JSON body. Useful to us directly: per-tool
  metering can happen at the proxy, feeding `usage_events` without app code.
- List responses (`tools/list` et al.) carry `ttlMs` and `cacheScope`, letting
  clients cache the tool catalog and hold stable upstream prompt caches across
  reconnects.

**Auth requirements tightened**, and §3's checklist needs three additions: RFC
9207 issuer validation (prevents authorization-server mix-up), `application_type`
support (fixes localhost redirect rejection for CLI/desktop clients), and
credentials bound to their issuing server. Note the emphasis flip: **DCR is now
formally deprecated in favour of CIMD**. §3 said "enable CIMD *and* keep DCR" —
still right operationally, but CIMD is now the primary path and DCR the legacy
fallback, not co-equals.

**Legacy HTTP+SSE is officially deprecated** with a year-long offramp. §3 already
specified Streamable HTTP, so nothing to change — just don't let anything
reintroduce SSE.

### The stack decision in §3 is now wrong — and this is the important part

§3 pinned **FastMCP 3.4.x**, reasoning it was "the only path with a real auth
layer" and explicitly rejecting "official SDK 2.0". Both halves of that
reasoning have expired. Verified by installing them, not by reading changelogs:

| | Speaks `2026-07-28`? | Stability | Auth |
|---|---|---|---|
| **Official SDK `2.0.0`** | **Yes** (`LATEST_PROTOCOL_VERSION == 2026-07-28`) | Stable, 2026-07-28 | Ships `mcp.server.auth` — `provider`, `routes`, `middleware`, `handlers`, `settings`. A real OAuth resource-server layer, but a generic provider interface, not a prebuilt WorkOS integration |
| **FastMCP `3.4.6`** (current stable, 2026-08-05) | **No** — installs official `mcp 1.29.0`, protocol `2025-11-25` | Stable | `AuthKitProvider` / `OAuthProxy` — prebuilt WorkOS, still its main advantage |
| **FastMCP `4.0.0b2`** (2026-08-07) | Announced (stateless interactivity, enterprise auth, background tasks) | **Beta** — b1 landed on spec-release day, b2 two days ago | Announced "enterprise auth" |

So: **picking FastMCP 3.4.x today would ship the hosted connector on the
previous protocol revision** — precisely the position v0.16.3 just dug the local
server out of. That is a materially different tradeoff than the one §3 weighed.

A third argument appeared that did not exist on 2026-07-31: the local stdio
server is now on official SDK 2.0. Choosing (a) means **one SDK across both
deployment surfaces**, and the tool vocabulary ports decorator-for-decorator
because v2 kept `@tool()` / `@resource()` signatures intact.

**Not deciding this now** — it wants its own spike, and nothing is blocked on it
until Phase 1 step 3. The decision test is narrow and cheap:

> Wire WorkOS AuthKit against official SDK 2.0's `mcp.server.auth` provider
> interface and time it. If it is under roughly a day, take the official SDK for
> protocol currency plus a single shared SDK. If AuthKit integration proves
> genuinely painful, re-evaluate FastMCP 4.0 once it reaches stable — but do not
> ship the connector on FastMCP 3.4.x and its `2025-11-25` protocol.

### Deferral list, revised

§5 deferred "MCP Tasks + spec 2026-07-28 migration (watch claude.ai support
announcements)". Split that: the **spec migration is no longer a deferral**, it
is the baseline any new hosted work should be built on. **MCP Tasks stays
deferred**, still gated on claude.ai support. Likewise §3's watch item on
"Skills over MCP" — the extension exists in the shipped spec; the open question
is purely claude.ai support, not whether it is specified.

### Carried forward unchanged

The YouTube three-lane verdict (§2), the Phase 0 spikes, WorkOS/Neon/Hetzner
choices, the cost model, and the SPA catch-all landmine in `web/app.py` are all
untouched by this and remain the plan of record.
