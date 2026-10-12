# Xdrop v2 — Complete Revamp Plan

> **Status:** Planning · **Scope:** whole repository · **Supersedes:** ad-hoc TODOs
> **Owner:** _unassigned_ · **Source audit:** findings verified against `master` on 2026-10-09

This is the single authoritative plan for taking Xdrop from "works on the author's machine"
to a distributable, secure, multi-editor product. It consolidates every confirmed defect,
the architectural changes required to fix whole classes of defects, and the sequencing to
get there without breaking users who are already running it.

Task IDs (`W1.1`, `W2.3`, …) are stable references for issues and PR titles.

ID namespaces: **`D1`–`D14`** = confirmed defects, **`S1`–`S5`** = security
findings, **`AD-1`–`AD-9`** = architecture decisions, **`O-1`–`O-2`** = open questions,
**`W`** = workstream tasks, **`M`** = milestones.

---

## 0. How to read this

| Section | Use it for |
|---|---|
| §1 Scorecard | What is good, what is broken, the verdict |
| §2 Target architecture | The shape we are building toward |
| §3 Decisions | Choices made, with alternatives, so nobody relitigates them |
| §4 Workstreams | The actual work, each item with acceptance criteria |
| §5 Milestones | Sequencing, exit criteria, what "done" means per milestone |
| §6 Verification | How each milestone is proven, not just claimed |
| §7 Migration | Not breaking existing installs |
| §8 Risks | What can go wrong |
| §9 Release checklist | The gate before any public release |

---

## 1. Current-state scorecard

### 1.1 Verified defects (reproduced, not inferred)

| # | Defect | Evidence | Blast radius |
|---|---|---|---|
| D1 | `apps/premiere-plugin/CSXS/manifest.xml` is invalid XML — `<Geometry>` never closed | `xml.dom.minidom` → `mismatched tag: line 56` | **Entire Adobe half of the product never loads** |
| D2 | `xdrop/api/routes_settings.py:87` uses `sys.executable` with no module-level `import sys` | `NameError`, swallowed by local `except` → endpoint returns failure | Every Adobe extension install path |
| D3 | No Library UI exists despite README advertising it | `src/pages/` = Import, Queue, Settings only | Advertised feature missing |
| D4 | Library endpoints cap at `get_library_items(limit=1000)` then linear-scan for id | `routes_library.py` all handlers | Assets #1001+ cannot be deleted/imported/revealed |
| D5 | Docs promise a pytest suite that does not exist | `docs/DEVELOPMENT.md` vs zero test files | Contributor trust; no regression safety net |
| D6 | `docs/SECURITY.md` claims SSRF protection that is not implemented | `routes_analyze.py` `proxy_thumbnail` | False security assurance |

### 1.2 Dead code and dead schema (confirmed by grep)

| # | Item | Status |
|---|---|---|
| D7 | Tables `platform_sources`, `projects`, `download_history` | Created in `schema.py`, **never read or written** |
| D8 | `ProviderManager.set_provider_enabled` / `get_provider_by_id` / `get_providers` | Defined, only referenced by each other, **no API route** |
| D9 | Settings `local_only`, `telemetry_enabled`, `retry_count`, `connection_timeout` | Persisted and shown in UI, **never consumed** (retries hard-coded 10, socket timeout 15) |
| D10 | Setting `preferred_audio_format` | Never consumed by the download pipeline |
| D11 | Protocol messages `PAUSE_JOB`, `RESUME_JOB`; status `paused` | Declared in `packages/protocol`, **no backend handler**; nothing can set `paused` |
| D12 | `POST /api/analyze/batch` | Implemented, never called by the UI |
| D13 | `apps/desktop-service/xdrop/setup.py` lines 1–20 | Whole import block duplicated verbatim |
| D14 | `.pytest_cache/` at repo root and in `apps/desktop-service/` | Untracked leftovers of a test run that has no tests (gitignored, so harmless — but confusing) |

### 1.3 Security findings

| # | Finding | Severity |
|---|---|---|
| S1 | `allow_origins=["*"]` **with** `allow_credentials=True` (spec-invalid); no auth token; no origin check on any mutating route | Critical |
| S2 | `/ws` accepts any connection and immediately sends `INITIAL_STATE` with the full download history. Browsers do **not** apply CORS to WebSockets, and only the server can check `Origin` | Critical |
| S3 | `/api/analyze/thumbnail-proxy` is an unauthenticated SSRF proxy: any URL, `follow_redirects=True`, no private-range check, no content-type allowlist, body returned verbatim | High |
| S4 | SPA catch-all `/{full_path:path}` joins unvalidated input to `dist/` with no `..`/`relative_to` check → file disclosure outside the bundle. Also returns `index.html` HTTP 200 for unknown `/api/*` GETs | High |
| S5 | `POST /api/analyze` runs unbounded yt-dlp extractions on the default executor → local resource exhaustion | Medium |

Because Chrome and Firefox treat `127.0.0.1` as a *potentially trustworthy* origin,
an HTTPS page the editor visits **is** able to reach this local service. There is no
network boundary protecting it. It must protect itself.

### 1.4 Product and UX findings

- Pasting multiple URLs analyses only the first (`urls[0]`); the batch endpoint exists but is unused.
- `getLibrary` in `src/services/api.ts` is typed `{items, count}` while the endpoint returns a bare array.
- Adobe import reports `success: true` purely because a WebSocket broadcast was sent — no ack from the panel — so the queue shows "Imported" when nothing was imported.
- Errors surface as raw exception strings with no next action; no diagnostics surface pointing at `%LOCALAPPDATA%\Xdrop\logs`.
- `retry_count` / `connection_timeout` are exposed as settings but ignored; no resume; no disk-space preflight; cancel leaves partial files on disk.
- Hard-coded port `8484` in ~8 files; no single-instance guard; no conflict handling.
- Not headless by default: the Resolve launcher, `run.bat`, and the CEP fallback all spawn `--gui`, so a pywebview window pops up behind the panel. No daemon mode, no PID/lock file, no service unit for any OS.
- `pywebview` is a hard dependency of the entire service for a window most users never want.
- Dark-only, English-only, no keyboard-shortcut help, no drag-and-drop.
- `apps/resolve-plugin` is actually the shared UI; `apps/premiere-plugin` also contains the AE panel. Names mislead.

### 1.5 Packaging and process findings

- No releases, no installers, no signing. Onboarding is "clone this repository".
- `xdrop.spec` exists but is frozen-hostile: `ROOT_DIR`/`parents[4]` and relative `bin/` break under `_MEIPASS`; `COLLECT` produces no macOS `.app`; `console=False` hides tracebacks; no icon/version metadata; `upx=True` can break `fusionscript.dll` loading.
- No updater, despite README §6 telling users to re-run setup to update.
- `apps/resolve-plugin/dist/` is committed via a `.gitignore` carve-out → the shipped bundle can drift from source.
- Version `1.0.0` duplicated in `package.json` ×2, `main.py`, `manifest.xml`, `config.json`.
- Two divergent `requirements.txt`; no `pyproject.toml`; `websockets` pinned `<17` while everything else floats → non-reproducible installs.
- Zero CI, zero lint/format config, zero tests.

### 1.6 What is genuinely good — keep it

Do not regress these while refactoring:

1. **Frontend quality.** React 18 + TS in genuine `strict` mode with `noUnusedLocals`; `tsc && vite build` passes clean. Bundled output is small (~228 kB / 65 kB gzip).
2. **Provider abstraction.** `PlatformProvider` ABC with a manager, ordered first-match routing, and a generic fallback — the right seam. Nine platforms share one `YtDlpBaseProvider`.
3. **`MediaOrganizer` path safety.** Windows reserved-name handling, template substitution, `relative_to` containment check, duplicate-suffix logic. This is the security bar the rest of the code should meet.
4. **NLE compatibility transcoding.** `ensure_nle_compatible` measures codecs and stream-copies when possible, honours NVENC/QSV, falls back to libx264 — genuinely valuable domain logic.
5. **Atomic direct downloads.** Temp file + `os.replace`, 1 MB buffered chunks, throttled progress callbacks.
6. **Rotating JSON logs** split by subsystem, plus WAL-mode SQLite with thread-local connections.

### 1.7 Verdict

The **engine** is a competent prototype. The **product shell** around it — packaging, security, lifecycle, distribution, tests, and half the advertised features — is not shippable. The Adobe integration is currently non-functional. Nothing here is architecturally fatal; the seam work was done well and most of this is finishing, hardening, and honesty in documentation.

---

## 2. Target architecture (v2)

```
                    ┌──────────────────────────────────────────┐
                    │          Editor delivery adapters        │
                    │  Resolve │ Adobe CEP │ Adobe UXP* │ Generic│
                    └───────────────┬──────────────────────────┘
                                    │  authenticated loopback IPC
                       (token + Origin check, port from runtime.json)
                                    │
   ┌────────────────────────────────┴────────────────────────────────┐
   │                     xdrop-core (Python)                          │
   │                                                                  │
   │  API layer        Domain services          Infrastructure        │
   │  ─────────        ───────────────          ──────────────        │
   │  REST (OpenAPI)   DownloadEngine           SQLite + migrations    │
   │  WebSocket        DeliveryService          Bounded executor pools │
   │  Auth guard       LibraryService           FFmpeg wrapper          │
   │  Bounded queue    ProviderRegistry         Rotating JSON logs     │
   │                   ConfigService            Thumbnail cache        │
   └────────────────────────────────┬────────────────────────────────┘
                                    │
              ┌─────────────────────┴─────────────────────┐
              ▼                                           ▼
   Local asset library                          Editor project bins
   (Videos/Xdrop Assets)                        / watch folder + FCPXML
```

\* UXP is a spike, not a commitment — see §3 decision AD-4.

**Principles**

1. **The service assumes it is on a hostile origin.** Loopback is not a trust boundary.
2. **One source of truth per fact.** OpenAPI → generated TS client. One version constant. One requirements file. One config schema.
3. **Headless is the default.** Windows exist only when explicitly requested.
4. **Every integration reports truth.** An import is "done" only when the editor confirmed it, or the UI says "queued for import".
5. **Anything advertised exists or is removed from the docs.**

---

## 3. Decisions

Recorded so they are not relitigated. Alternatives are listed for the two open ones.

### Decided

| ID | Decision | Rationale |
|---|---|---|
| AD-1 | **Delete the thumbnail proxy; cache thumbnails server-side at analysis time** and serve them from `/thumbnails/...` | Removes the SSRF surface entirely *and* fixes the CDN referer/CORS problem at the root. Net code deletion. |
| AD-2 | **Bearer token + `Origin` allowlist for all loopback IPC.** Token generated per run, written to `runtime.json` (0600) in the data dir alongside the port; panels read that file | Loopback is reachable from any page the user visits. A shared secret is the minimum viable boundary and costs ~40 lines. |
| AD-3 | **Ship a relocatable embedded CPython + prebuilt wheels**, not PyInstaller, as the primary distribution | The app dynamically imports `DaVinciResolveScript` and spawns subprocesses; PyInstaller's `_MEIPASS` indirection already breaks `ROOT_DIR`/`parents[4]`. Embedded CPython makes the code paths identical to a dev checkout. Keep a PyInstaller "portable single-file" build as a secondary convenience. |
| AD-4 | **Invest in a generic export lane (watch folder + FCPXML + OTIO + EDL), not five more native plugins** | One implementation delivers "works in every NLE" including FCP, CapCut, Avid, Kdenlive, Shotcut. Native adapters remain for Resolve/Adobe where round-trip control matters. |
| AD-5 | **Generate the TypeScript API client from FastAPI's OpenAPI schema** (`openapi-typescript`), deleting hand-written `src/services/api.ts` types | Kills the entire class of bug that produced the `{items, count}` mismatch. FastAPI already emits the schema for free. |
| AD-6 | **Versioned SQL migrations table** replaces the chain of `try: ALTER TABLE ... except: pass` in `connection.py` | Current migrations are unverifiable and will eventually corrupt silently. |
| AD-7 | **One canonical version source** (`VERSION` at repo root) synced into `package.json`, `manifest.xml`, and FastAPI by `scripts/sync_version.py`, enforced in CI | Five copies of `1.0.0` guarantee drift. |
| AD-8 | **Rename** `apps/resolve-plugin` → `apps/panel-ui`, `apps/premiere-plugin` → `apps/adobe-cep` | Names currently misdescribe what the directories contain. Sequenced *after* distribution stabilises (§5, M8) to avoid churn in paths baked into installers. |
| AD-9 | **Drop or wire the dead schema** (§1.2 D7). Wire `platform_sources` to a real provider-enable API; drop `projects` and `download_history` unless a milestone needs them | Dead tables imply features that do not exist. |

### Open — needs an owner decision

| ID | Question | Options | Recommendation |
|---|---|---|---|
| O-1 | Do we keep `pywebview` as a supported mode at all? | (a) keep as opt-in `--gui`; (b) remove, always browser/panel; (c) replace with a Tauri shell | **(a)** — keep opt-in for now, but move it to an optional extra so the base install does not require GTK/Qt on Linux. Revisit at M6. |
| O-2 | Is Windows the only launch platform, or must all three be first-class? | (a) Windows-first, macOS best-effort, Linux community; (b) all three equal | **(b) is the honest read of the README's badges.** If it must be (a), say so and the docs must change, because the "Windows &#124; macOS" badge claims both today. |

---

## 4. Workstreams

Each task: **what**, **acceptance criteria** (testable), **files**.

### W1 — Correctness: unblock the product

*Goal: the Adobe integration works and nothing in the product lies.*

- **W1.1** Fix `apps/premiere-plugin/CSXS/manifest.xml` — close `<Geometry>`.
  - ✅ `python -c "import xml.dom.minidom as m; m.parse('apps/premiere-plugin/CSXS/manifest.xml')"` exits 0.
  - ✅ Panel appears under **Window → Extensions → Xdrop** in both Premiere Pro and After Effects on a clean machine.
- **W1.2** Fix `routes_settings.py` — add module-level `import sys`; delete the duplicated local imports.
  - ✅ `POST /api/settings/install-premiere-extension` returns 200 with a real path, not a `NameError` message.
  - ✅ A regression test asserts `install_premiere_extension()` succeeds against a temp `APPDATA`.
- **W1.3** Remove dead code and dead schema per §1.2 D7–D14 (or wire it if a later milestone needs it — D9 is wired in W8).
  - ✅ `grep -rn "platform_sources\|projects\|download_history"` returns only `schema.py`, or the tables are backed by real repositories and routes.
  - ✅ `setup.py` has exactly one import block.
  - ✅ `.pytest_cache/` removed from the tree and from the index.
- **W1.4** Delete `docs/SECURITY.md` claims that are untrue; replace with a **Known Limitations** section listing what is *not* protected yet, linking to the W2 tasks that will fix each.
  - ✅ Every claim in `SECURITY.md` maps to a test in the suite or is labelled a non-goal.
- **W1.5** Fix `getLibrary` response contract (bare array vs `{items, count}`) — superseded by AD-5, but fix immediately if W5 slips.
  - ✅ A test asserts the shape the UI consumes.

### W2 — Security: make loopback a real boundary

*Goal: a hostile web page cannot read or mutate anything.*

- **W2.1 (AD-2, S1, S2)** Auth guard.
  - Generate `XDROP_TOKEN` on startup; write `runtime.json` = `{port, token, pid, version}` to the data dir with `0600`.
  - Middleware rejects any `/api/*` request without `Authorization: Bearer <token>` with **401**.
  - WebSocket: require the token via `Sec-WebSocket-Protocol` or first-message handshake; close with 1008 otherwise.
  - ✅ A test opening `ws://127.0.0.1/ws` with no token gets closed and receives no `INITIAL_STATE`.
  - ✅ A `fetch` with `Origin: https://evil.example` and no token gets 401 and no body.
- **W2.2 (S1)** Correct CORS: replace `["*"]` with an explicit allowlist (`http://127.0.0.1:<port>`, `http://localhost:<port>`, the Adobe CEP origins `file://`-equivalent, and the Vite dev origin in dev mode); set `allow_credentials=False`.
  - ✅ A preflight from an unlisted origin is rejected.
  - ✅ The service works from the panel origin, the browser at `127.0.0.1`, and the Vite dev server.
- **W2.3 (S1)** `isSameOriginRequest` guard on every mutating endpoint (`POST`/`PUT`/`DELETE`), comparing `Origin`/`Referer` against the allowlist; reject with **403**.
  - ✅ A cross-origin `POST /api/downloads` is 403; same-origin succeeds.
- **W2.4 (S3, AD-1)** Delete `/api/analyze/thumbnail-proxy`. During `inspect`, download the thumbnail to `THUMBNAILS_DIR/<hash>.jpg` and return our own `/thumbnails/...` URL.
  - ✅ `grep -rn "thumbnail-proxy"` returns nothing.
  - ✅ Thumbnails render in the UI with no outbound request from the browser.
  - ✅ A URL pointing at `http://169.254.169.254/` cannot be fetched through any endpoint.
- **W2.5 (S4)** SPA catch-all: resolve the candidate path and reject anything not `relative_to(DIST_DIR)`; return **404** for unknown `/api/*` instead of `index.html`.
  - ✅ `curl 'http://127.0.0.1:8484/../../../etc/passwd'` returns 404.
  - ✅ `GET /api/does-not-exist` returns JSON 404, not HTML.
- **W2.6 (S5)** Bound analysis and download concurrency with an explicit `ThreadPoolExecutor` sized from config; add a per-token rate limit on `/api/analyze`.
  - ✅ 50 concurrent `/api/analyze` calls do not spawn 50 yt-dlp processes (measured, asserted in a test).
- **W2.7** Secrets hygiene: ensure `runtime.json`, the SQLite DB, and logs stay inside the data dir, are excluded from assets, and never appear in logs.
  - ✅ A test asserts the token never appears in any log file after a full run.
- **W2.8** Bind host allowlist — refuse `--host 0.0.0.0` unless `--allow-remote` is passed explicitly, and print a loud warning if it is.
  - ✅ `--host 0.0.0.0` without the flag exits with a clear error.

### W3 — Guardrails: tests, CI, typing

*Goal: after this, no later milestone can silently regress.*

- **W3.1** `pyproject.toml` with `[project]` metadata, pinned dependency ranges, and optional extras (`gui` for pywebview, `dev` for tooling). Delete the two divergent `requirements.txt` (keep one generated lock).
  - ✅ `pip install -e .[dev]` succeeds from a clean venv on all three OSes.
  - ✅ Dependency versions are locked (`uv.lock` or `requirements.lock`); CI installs from the lock.
- **W3.2** `pytest` suite under `tests/`, fixtures pointing `XDROP_DATA_DIR` at a tmp dir.
  - ✅ At minimum: organizer path-traversal + reserved names + duplicate suffixing; provider URL routing for all nine platforms + generic fallback; settings round-trip and validation; DB migrations from an empty and from a legacy schema (AD-6); library CRUD + pagination beyond 1000 rows; auth 401/403 matrix; thumbnail caching; NLE-compat decision table (mocked ffmpeg).
  - ✅ `python -m pytest -q` passes in CI; coverage floor enforced (start 60%, raise per milestone).
- **W3.3** `vitest` for `packages/utilities` (formatting, URL extraction, sanitize parity with the Python implementation).
  - ✅ Python and TS sanitizers are asserted against the **same fixture table** so they cannot drift.
- **W3.4** Lint and format: `ruff` (lint + format) for Python, `eslint` + `prettier` for TS, `pre-commit` hooks.
  - ✅ `ruff check`, `ruff format --check`, `eslint`, `prettier --check`, `tsc --noEmit` all pass in CI with zero suppressions.
- **W3.5** `mypy` on `xdrop/` at a pragmatic level (start `--ignore-missing-imports`, no `disable_error_code` escapes).
  - ✅ Clean run; any `# type: ignore` carries an explanatory comment and is reviewed.
- **W3.6** GitHub Actions matrix: `windows-latest`, `macos-latest`, `ubuntu-latest`; Python 3.11/3.12/3.13; Node 20.
  - ✅ CI runs tests, lint, typecheck, UI build, and a **frozen-build smoke test**.
  - ✅ Branch protection requires the matrix green.
- **W3.7** Contract test: fail CI if the committed `dist/` differs from a fresh build, or remove `dist/` from the repo entirely (preferred once distribution does not depend on it).
  - ✅ `git diff --exit-code` after a build, or `dist/` is gone and untracked.
- **W3.8 (AD-7)** `scripts/sync_version.py` + CI check that `VERSION`, `package.json`, `manifest.xml`, and the FastAPI app agree.
  - ✅ Changing `VERSION` without syncing fails CI with a clear message.

### W4 — Lifecycle: headless, single-instance, real ports

*Goal: the service behaves like a service.*

- **W4.1** Make headless the default. Remove `--gui` from the generated Resolve launcher, `run.bat`/`run.sh`, and the CEP auto-start fallback. Add `--gui` as explicit opt-in; move pywebview to the `gui` extra (O-1).
  - ✅ Launching from Resolve opens no window; the panel is the UI.
  - ✅ A base install without the `gui` extra starts fine and `--gui` gives an actionable error telling the user which extra to install.
- **W4.2** `--port 0` support + `runtime.json` handshake (shared with W2.1). All hard-coded `8484` references (CEP `index.html`, CEP `config.json`, Vite proxy, both launchers) read the port from the runtime file or a configurable default.
  - ✅ With the default port occupied, the service starts on a free port and the panel still connects.
- **W4.3** Single-instance guard: lock file with PID + liveness check; a second launch focuses/reuses the running instance instead of failing on `EADDRINUSE`.
  - ✅ Double-clicking `run.bat` twice gives one service and one UI.
- **W4.4** OS service units: Windows (service or scheduled task), macOS `launchd` agent, Linux `systemd --user`. `--install-service` / `--uninstall-service` flags.
  - ✅ Service starts on login and survives reboot on all three OSes.
  - ✅ Logs land in the data dir and rotate.
- **W4.5** Graceful shutdown: cancel in-flight jobs, mark them `interrupted` (new status) so they can be resumed, flush SQLite, close the executor.
  - ✅ `SIGTERM` mid-download leaves no orphaned partial file and the job is resumable.

### W5 — Engine reliability

*Goal: downloads are resumable, cancelable, honest, and bounded.*

- **W5.1** Resume support: yt-dlp `continuedl` with `.part` retention; the Direct provider uses HTTP `Range` and keeps its partial across attempts.
  - ✅ Kill the service at 60% of a 500 MB direct download; restart; the job completes having downloaded materially less than the full file (measured byte counts).
- **W5.2** Cooperative cancellation: replace "raise `CancelledError` inside the yt-dlp progress hook thread" with a cancellation token checked in the hook, plus guaranteed cleanup of `.part`/temp files.
  - ✅ Cancelling 10 jobs in a row leaves zero files in the download dir that are not referenced by a library row.
- **W5.3** Duplicate detection: unique index on `(source_url, asset_id, quality_label)`; on collision the UI offers "Already in library — re-import" instead of silently writing `Title_1.mp4`.
  - ✅ Downloading the same URL twice produces one library row and no second file.
- **W5.4** Disk-space preflight plus an optional max-file-size guard; refuse with an actionable message before consuming bandwidth.
  - ✅ A job on a filesystem with insufficient free space fails fast with "needs 4.2 GB, 900 MB free".
- **W5.5** Wire the dead settings (D9/D10): `retry_count` → yt-dlp `retries`/`fragment_retries`; `connection_timeout` → `socket_timeout` and httpx timeouts; `preferred_audio_format` → the audio path. Remove `local_only`/`telemetry_enabled` or implement them (recommend: remove `telemetry_enabled`, keep `local_only` as a documented no-op only if it gates something real).
  - ✅ Changing each setting in the UI observably changes engine behaviour (asserted by test).
- **W5.6** Per-job timeouts derived from config instead of the fixed 600 s transcode cap; long jobs report progress and are interruptible.
  - ✅ A 30-minute 4K ProRes transcode completes on CI hardware (or is interrupted cleanly) rather than failing at a hard cap.
- **W5.7** Real import acknowledgement (fix the "success: true because we broadcast" lie). Introduce `pending` → `confirmed`/`failed` import states; the panel acks over the WebSocket; the UI shows "Queued for import" until confirmed.
  - ✅ With the editor closed, the UI never claims "Imported".
- **W5.8** Implement `PAUSE_JOB`/`RESUME_JOB` end-to-end, or delete them from the protocol and the `paused` status (D11).
  - ✅ Every message type in `packages/protocol` has a backend handler and a test, or does not exist.

### W6 — Library and UX

*Goal: every advertised feature exists and is pleasant.*

- **W6.1 (D3, D4)** Build the Library page: search, platform/type filters, pagination, thumbnail, "Import Again" (per editor), "Reveal", "Delete record" / "Delete file" with confirmation.
  - ✅ A 5,000-row library is fully navigable; asset #4,999 can be imported, revealed, and deleted.
  - ✅ Add a `get_library_item_by_id` repository function so no handler scans a capped list.
- **W6.2 (AD-5)** Adopt the generated OpenAPI TypeScript client; delete hand-rolled types in `src/services/api.ts`.
  - ✅ A backend response-shape change breaks `tsc`, not the runtime.
- **W6.3** Batch import: paste many URLs → analyse all (bounded) → queue the selected ones. The `/analyze/batch` endpoint becomes used (D12) or is removed.
  - ✅ Pasting 10 links produces 10 analysed entries; the user can queue all with one click.
- **W6.4** Drag-and-drop URLs onto the panel; keep clipboard paste.
  - ✅ Dropping a link from a browser populates and analyses the URL.
- **W6.5** Diagnostics surface: a "Diagnostics" panel showing Python/yt-dlp/FFmpeg/editor versions, resolved paths, the log directory, and the last 20 errors, with **Copy diagnostics** and **Open log folder**.
  - ✅ A user can produce a complete bug report without leaving the app.
- **W6.6** Actionable error copy: map known failure classes (private video, DRM, geo-block, unsupported URL, FFmpeg missing, no editor open) to human sentences with a next step.
  - ✅ No raw exception string is shown to the user for any class we can recognise.
- **W6.7** Pre-download preview: resolution, codec, duration, estimated size, and the exact destination path.
  - ✅ The user can see where a file will land before starting.
- **W6.8** Optional: light theme, i18n scaffolding, keyboard-shortcut help overlay. (Track as nice-to-have; do not block the milestone.)

### W7 — Distribution, updates, onboarding

*Goal: a working install in one download, no terminal, no Python knowledge.*

- **W7.1 (AD-3)** Embedded-CPython bundle: `scripts/build_runtime.py` produces a per-OS runtime directory (relocatable CPython + wheels + `xdrop` + prebuilt `panel-ui/dist`) and a tiny native launcher. Verify the dynamic `DaVinciResolveScript` import and subprocess spawning work from the bundled runtime.
  - ✅ On a clean VM with no Python, Node, or FFmpeg, the installer produces a working service reachable from the Resolve script menu, the Adobe panel, and a browser.
- **W7.2** Installers: Inno Setup (`.exe`) for Windows, signed `.dmg`/`.pkg` for macOS, AppImage + `.deb` for Linux.
  - ✅ Install/uninstall on clean VMs of each OS leaves no orphaned data outside the data dir.
- **W7.3** Code signing: Authenticode for Windows (EV ideally, to clear SmartScreen) and Developer ID + notarization for macOS.
  - ✅ No SmartScreen or Gatekeeper warning on a clean machine.
- **W7.4** Browser-download-friendly onboarding: GitHub Releases with artifacts, a checksum file, and a README that starts with "Download Xdrop for Windows/macOS/Linux" rather than "clone this repository".
  - ✅ A non-developer can go from zero to a working panel in under three minutes.
- **W7.5** Auto-update: check a signed release manifest on launch (opt-out), verify signature/checksum, download in the background, apply on restart.
  - ✅ An older build detects a new one, verifies it, and updates without losing the DB or settings.
- **W7.6** Re-evaluate `xdrop.spec`: either make it correct (absolute-path-free, `BUNDLE` for macOS, version/icon metadata, **no `upx`**) or delete it in favour of the embedded runtime.
  - ✅ The frozen build passes the same smoke test as the embedded runtime, or the file is gone.
- **W7.7** FFmpeg strategy: ship a known-good FFmpeg during install (per-OS) instead of relying on `winget`/`PATH` at runtime; keep the current discovery as an override.
  - ✅ A clean VM without FFmpeg has working transcoding immediately after setup.

### W8 — Editor breadth

*Goal: "works in every editor", delivered as one generic lane plus real native adapters.*

- **W8.1 (AD-4)** Introduce an `EditorTarget` abstraction (`probe()`, `import(files, bin) -> ImportResult`, `capabilities()`) with adapters: `ResolveAdapter`, `AdobeCepAdapter`, and `GenericExportAdapter`.
  - ✅ `DownloadQueueManager` no longer knows about specific editors; adding an editor touches one new file.
- **W8.2** `GenericExportAdapter`: write the asset to a configurable watch folder plus a sidecar bundle — **FCPXML 1.11**, **OTIO** (`.otio`), and a plain **EDL** — with a per-project folder structure.
  - ✅ A user with no supported native editor can drag the generated FCPXML into Final Cut Pro / Resolve / Premiere and get the clip on a timeline.
  - ✅ CapCut/Shotcut/Kdenlive users can point at the watch folder.
- **W8.3** Avid path: MXF OP-Atom transcode + ALE sidecar. AAF is **not** in scope (no reliable writer in our stack) — document this honestly rather than half-shipping it.
  - ✅ `ffmpeg` produces OP-Atom MXF and an ALE that Avid Media Composer indexes.
- **W8.4** Adobe UXP spike (time-boxed): assess whether a UXP panel can reach the local service and whether the plugin surface we need (project items, bins, imports) is available for the target Premiere/AE versions.
  - ✅ Written finding: adopt / defer / reject, with evidence. **Not** a commitment to ship.
- **W8.5** Provider lifecycle: expose `/api/providers` (GET list with enabled state, PATCH toggle) wired to the existing `set_provider_enabled`, replacing the dead `platform_sources` table with a settings-backed implementation, and persist it.
  - ✅ A user can disable a platform and the analyser rejects its URLs with a clear message.
- **W8.6** Per-provider health: surface "extractor may be stale" when analysis fails repeatedly for one platform, with a one-click "Update yt-dlp" (the endpoint already exists).
  - ✅ A stale extractor is detectable from the UI without reading logs.

### W9 — Docs, naming, and honesty

- **W9.1 (AD-8)** Directory renames: `apps/resolve-plugin` → `apps/panel-ui`, `apps/premiere-plugin` → `apps/adobe-cep`. Update `vite.config.ts`, `setup.py`, `xdrop.spec`, `main.py`'s `DIST_DIR`, `.gitignore`, Docker/installer paths, and every doc. Sequence **after** M7 so installer paths are stable.
  - ✅ No reference to the old names remains; CI is green.
- **W9.2** Rewrite `docs/ARCHITECTURE.md` for the multi-editor reality (it currently describes Resolve only) and align it with §2 of this plan.
  - ✅ An architecture diagram that matches `apps/desktop-service/xdrop/` as it actually is.
- **W9.3** Rewrite `docs/INSTALLATION.md` for real installers, and correct the "no admin rights required" claim for the Resolve script path (`C:\ProgramData` typically needs elevation).
  - ✅ Documented elevation requirement, or the install path changed to a per-user location.
- **W9.4** Rewrite `docs/DEVELOPMENT.md` with commands that exist (`ruff`, `pytest`, `vitest`, `npm run build:ui`), and delete the phantom `tests/` instructions.
  - ✅ Every command in the doc is executed by CI.
- **W9.5** `docs/TROUBLESHOOTING.md`: the top 15 real failure modes with the actual error text and the fix. `docs/SECURITY.md`: real guarantees plus explicit non-goals (W1.4).
  - ✅ Each entry reproduces from a real failure or a test.
- **W9.6** ADRs under `docs/adr/` capturing §3 decisions.
  - ✅ Every decision in §3 has an ADR.
- **W9.7** `CONTRIBUTING.md`: real workflow, PR checklist, how to add a provider, how to add an editor adapter.
  - ✅ A new contributor can add a provider following only the doc.

---

## 5. Milestones

Sequencing is chosen so that (a) the product works, then (b) it is safe, then (c) it is
guarded by tests before any large refactor, then (d) it becomes distributable.

| Milestone | Workstreams | Exit criteria (all must hold) | Size |
|---|---|---|---|
| **M0 — Stop the bleeding** | W1 | Adobe panel loads; extension install endpoint returns 200; docs make no false claims; dead code/schema removed; `git status` clean and build reproducible | S |
| **M1 — Trust boundary** | W2 | 401 without token; 403 cross-origin; no SSRF surface remains; SPA traversal yields 404; concurrency bounded; secret never logged | M |
| **M2 — Guardrails** | W3 | pytest + vitest + ruff + eslint + tsc + mypy green in a 3-OS CI matrix; version drift fails CI; coverage floor enforced | M |
| **M3 — Lifecycle** | W4 | Headless by default; single instance; dynamic port; service units on 3 OSes; graceful shutdown with resumable jobs | M |
| **M4 — Engine truth** | W5 | Resume measured; cancel leaves no orphans; duplicate downloaded twice → one file; every setting does something; no fake "Imported" | L |
| **M5 — Library & UX** | W6 | Library page works past 1,000 rows; batch paste; generated TS client in use; diagnostics panel | L |
| **M6 — Distribution** | W7 | Clean-VM install on Windows/macOS/Linux with no Python/Node/FFmpeg; signed; auto-update verified; releases published | L |
| **M7 — Editor breadth** | W8 | Generic export lane produces FCPXML/OTIO/EDL accepted by at least FCP, Resolve, and Premiere; provider toggles work; UXP verdict written | L |
| **M8 — Docs & naming** | W9 | Renames landed; all docs match reality; ADRs recorded | S |

**Critical path:** M0 → M1 → M2 → M3 → M4 → M6. M5 and M7 can run in parallel with M4/M6
if there are two contributors.

**Suggested first increment:** M0 (hours, not days) so the Adobe path stops being dead,
followed immediately by M1, because the security finding is the only one with a realistic
abuse scenario today.

---

## 6. Verification plan

The plan is only credible if each milestone is *proven*. Rules:

1. **Reproduce before fixing.** Every task's defect is reproduced first and the reproduction becomes a test.
2. **Test through the interface the user uses.** Auth is verified with a raw WebSocket client and a browser, not by calling the handler. Resume is verified by killing the process, not by mocking.
3. **Measure, do not assert.** "Faster", "resumable", "bounded" require numbers (bytes, process counts, wall time).
4. **Clean-VM acceptance.** M6 is verified on a fresh VM per OS with no dev tooling.
5. **Two-account/negative paths.** Every auth check is tested with (a) no token, (b) wrong token, (c) foreign origin, (d) valid token + same origin.
6. **No weakened checks.** Failures are fixed at the cause; `# type: ignore`, `--no-verify`, and skipped tests are not acceptable outcomes. If a check must change, the plan documents why and the new behaviour is verified.

---

## 7. Migration and backward compatibility

- **Data:** `%LOCALAPPDATA%\Xdrop` (and the `~/.xdrop` fallback) stay the data location. The legacy `resolvefetch.db` copy logic and the `RESOLVEFETCH_DATA_DIR` env var are preserved.
- **DB:** W3.2 includes migrations tested from both an empty DB and a legacy `resolvefetch.db` snapshot, so the new migrations table can adopt existing installs without data loss.
- **Settings:** stored under the same keys; snake_case and camelCase both keep working during a deprecation window (the current dual-key response already does this — make it explicit and tested, then remove camelCase from the *server* once AD-5 lands and the generated client is snake_case-clean).
- **Editors:** the Resolve script installs `Xdrop.py` **and** keeps `ResolveFetch.py` updated, as today. The Adobe CEP bundle keeps installing under both `com.xdrop.panel` and the legacy `com.resolvefetch.premiere` ids, as today. Deprecate only after a release cycle.
- **Ports:** default stays `8484`; dynamic allocation is opt-in via `--port 0`, so existing pinned configs keep working.
- **Directory renames (W9.1)** happen last, so installer paths and the `dist/` bundle location are frozen before the churn.

---

## 8. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Platform extractors break continuously (yt-dlp churn) | High | High | Auto-update path (W8.6); provider health signals; `--update-ytdlp` already exists |
| Platform ToS / legal action against the project | Medium | High | Keep `local_only` honest; public-content-only messaging; no DRM; per-provider toggles (W8.5); a written policy in `docs/SECURITY.md` |
| Code-signing cost and process friction | Medium | High | Budget for an EV cert + Apple Developer account; ship unsigned previews meanwhile with documented workaround |
| Embedded-CPython bundle behaves differently from a dev checkout | Medium | Medium | Same smoke test runs against both; CI builds the bundle on every merge (W3.6) |
| `fusionscript.dll` cannot load from inside a frozen bundle | Medium | High | AD-3 avoids freezing; smoke test explicitly exercises the Resolve path |
| Renames break installer or `dist/` paths | Medium | Medium | Sequenced last (M8); CI asserts no stale references |
| Scope creep — five more native plugins | High | Medium | AD-4: generic lane first; native adapters only for Resolve/Adobe |
| Security fix breaks panel auto-start (token handshake) | Medium | Medium | Token distributed via `runtime.json` next to `config.json`; explicit test for the panel→service handshake on a clean install |
| No dedicated maintainer | Medium | High | Milestones are independently shippable; M0–M2 alone materially improve the product |

---

## 9. Release checklist (gate for any public release)

- [ ] CI green on Windows, macOS, Linux × Python 3.11–3.13 × Node 20
- [ ] `ruff`, `eslint`, `prettier`, `tsc --noEmit`, `mypy` clean, zero suppressions
- [ ] Test suite green; coverage floor met
- [ ] Auth matrix verified: 401 / 403 / valid
- [ ] No SSRF-capable endpoint exists (`grep -ri "thumbnail-proxy"` empty)
- [ ] SPA traversal returns 404
- [ ] Clean-VM install verified on all three OSes with no Python/Node/FFmpeg present
- [ ] Installers signed; no SmartScreen/Gatekeeper warning
- [ ] Version synced across all manifests (CI-enforced)
- [ ] Upgrade from the previous release preserves DB, settings, and library
- [ ] Every README/docs claim true, or removed
- [ ] `SECURITY.md` matches implemented behaviour and lists non-goals
- [ ] `REVAMP_PLAN.md` milestone table reflects what actually shipped

---

## 10. Explicitly out of scope

Stated so nobody assumes they are coming:

- **DRM circumvention** — never. Public content only.
- **AAF export for Avid** — no reliable writer in this stack (W8.3 ships MXF OP-Atom + ALE instead).
- **Private/authenticated media** via logged-in cookies or account credentials.
- **Cloud sync, accounts, or a hosted service** — this stays a local-first tool.
- **Blender VSE and other niche NLEs as native adapters** — covered by the generic lane (W8.2) rather than bespoke integrations.
- **Mobile or web-hosted versions.**
- **Full i18n** — tracked as W6.8 nice-to-have, not a milestone exit criterion.

---

## 11. Effort estimate

Relative sizing only; convert to dates with your actual capacity. Assumes one focused
engineer unless noted.

| Milestone | Estimate |
|---|---|
| M0 Stop the bleeding | ~1 day |
| M1 Trust boundary | ~4–6 days |
| M2 Guardrails | ~5–8 days |
| M3 Lifecycle | ~4–6 days |
| M4 Engine truth | ~7–10 days |
| M5 Library & UX | ~6–9 days |
| M6 Distribution | ~8–12 days (+ signing procurement lead time) |
| M7 Editor breadth | ~8–12 days |
| M8 Docs & naming | ~2–3 days |

**Total:** roughly 45–67 focused engineer-days, excluding signing-account procurement.
M0–M2 (the difference between "dangerous prototype" and "safe tool with guardrails") is
about two weeks and is the highest-value slice.

---

## 12. Progress log

### M0 — Stop the bleeding — **COMPLETE** (2026-10-09)

**Shipped**

| Task | Change |
| --- | --- |
| W1.1 | `apps/premiere-plugin/CSXS/manifest.xml` — added the missing `</Geometry>`; the file now parses and `<Icons>` is a sibling of `<Geometry>`, not nested inside it |
| W1.2 | `xdrop/api/routes_settings.py` — hoisted `sys`, `json`, `shutil`, `subprocess` to module scope and deleted the duplicated local imports; `install_premiere_extension()` no longer raises `NameError` |
| W1.3 | Dropped the dead `projects` and `download_history` tables; **kept `platform_sources`** with an explanatory comment because AD-9 assigns it to W8.5. Removed the duplicated import block at the top of `xdrop/setup.py`. Deleted the stray `.pytest_cache/` directories |
| W1.4 | **All shipped docs audited for false claims.** `docs/SECURITY.md` rewritten to separate what is *enforced* from six *known gaps*; `docs/DEVELOPMENT.md` testing section corrected; `docs/INSTALLATION.md` admin-rights claim corrected; `docs/TROUBLESHOOTING.md` repeated the false "re-running setup upgrades yt-dlp" claim and was corrected; `docs/API.md` gained an accuracy note (no auth, non-exhaustive, `thumbnail-proxy` pending removal); `docs/PROVIDER_GUIDE.md` no longer points at a non-existent test file; `docs/ARCHITECTURE.md` gained a staleness banner; `CONTRIBUTING.md` no longer claims `npm test` runs tests. `README.md` gained an Implementation-status table and its Library + "keeping up-to-date" claims were corrected |
| W3.2 (early) | First tests in the repository: `tests/conftest.py` + `tests/test_cep_extension_install.py` (4 tests). `conftest.py` redirects `XDROP_DATA_DIR` so the suite never touches real user data |

**Verified** — not assumed

- `python -m pytest tests -v` → **4 passed** (exit 0), including the real HTTP interface:
  `POST /api/settings/install-premiere-extension` → **200** with `success: true`
- `xml.dom.minidom.parse` on the shipped manifest → parses (it previously failed at line 56)
- `python -m compileall apps/desktop-service/xdrop` → exit 0
- `npm run build:ui` → exit 0

**Deferred from W1.3, with reasons** (deliberate, not missed)

| Item | Deferred to | Why |
| --- | --- | --- |
| D8 — provider enable/disable methods | W8.5 (M7) | AD-9 assigns them to the provider-toggle API; deleting and re-adding would be churn |
| D9 / D10 — dead settings | W5.5 (M4) | M4 wires or removes them; removing them now would just move the work |
| D11 — `PAUSE_JOB` / `RESUME_JOB` | W5.8 (M4) | Needs the engine work from M4 |
| D12 — unused `/api/analyze/batch` | W6.3 (M5) | M5 builds the batch-import UI that consumes it |
| W1.5 — `getLibrary` response contract | AD-5, W6.2 (M5) | The generated OpenAPI client replaces the hand-written type entirely |

**Notes and cautions**

- Running pytest recreates `.pytest_cache/` every time. It is gitignored, so this is
  expected; D14 was about the confusing untracked leftovers, which are gone.
- `docs/ARCHITECTURE.md` is still Resolve-only and stale. It now carries an explicit
  staleness banner rather than silently misleading readers; the full rewrite remains
  W9.2 (M8).
- Several files in this repository mix LF and CRLF on disk. The M0 edits normalised the
  touched files to LF (what `HEAD` stores) so the review diff is honest — without that,
  `docs/DEVELOPMENT.md` showed a 76/71 whole-file rewrite instead of its real 13/8.
  Consider adding a `.gitattributes` to make this deterministic (see W3).
- **All of S1–S5 remain unfixed.** M0 deliberately did not touch the security posture;
  M1 is the next milestone. `docs/SECURITY.md` §2 now states this plainly.
- No changes were committed. The user's working tree holds the M0 diff for review.

---

### Editor import trust — **COMPLETE** (2026-10-09)

Not a numbered milestone: this is the cross-NLE correctness slice the user asked for ahead
of M1 ("make it a perfect extension for the editors"). It is a prerequisite for the
editor-facing work in the plan, because the editor integration could report success
without importing anything.

**The defect**

An import was treated as successful as soon as Xdrop had *broadcast* the request.
`ConnectionManager.broadcast()` returns silently when no client is connected, and
`PremiereBridge.import_media()` returned `success: True` regardless, so:

- Premiere Pro open with the Xdrop panel closed → job flagged `premiere_imported`, green
  "Imported to Premiere" badge, empty project. This is the common case, not an edge case:
  the panel only receives imports while it is docked.
- `is_running()` (a process-list check) was used as the gate, so the host process standing
  in for "the panel is listening" was the root cause.
- A download finishing while the editor was closed was skipped entirely, even though the
  service and the docs promise the import happens once the editor is opened.

**Shipped**

| Area | Change |
| --- | --- |
| Panel liveness | New `has_live_panel()`: a heartbeat within 30s is the only proof the Adobe panel is open. `get_status()` now reports `panelAttached` and explains the `Window > Extensions > Xdrop` step when the host runs without the panel |
| Honest results | `import_media()` refuses with an actionable error when no panel is open, and returns `confirmed: false` for a delivered request. Only the panel's real ExtendScript result marks a clip as imported. New `POST /api/{premiere,aftereffects}/import-result` carries that result |
| Deferred imports | A finished download with no editor open is recorded as pending against the preferred editor (`resolve` → `premiere` → `aftereffects`) instead of being dropped, and is imported automatically once that editor appears (10s background flush). `GET /api/editors/pending-imports`, `POST /api/editors/flush-imports` |
| Bounded retries | Each `(job, editor)` pair is retried at most once per service run, so a permanently failing import cannot loop; `force=true` or a user-initiated import overrides it |
| Per-editor state | `downloads` gained `*_import_pending`, `*_import_error` and `resolve_bin`. `update_download_import_state()` writes only the fields it is given, so a confirmation clears the pending flag and the stale reason together |
| Deduplication | `xdrop/adobe/base.py` now holds the panel logic shared by Premiere and After Effects (the two bridges were ~95% duplicated); both are thin subclasses. `import_media`/`import_media_async` keep their signatures |
| Panel | Batch import with backslash **and quote** escaping (a quote in a path previously broke out of the ExtendScript call), aggregating the per-file results into one report back to the service |
| UI | Queue cards show `WAITING FOR <EDITOR>` plus the reason instead of a false "Available in Bin"; `JOB_IMPORT_STATE` keeps it live. Library import routes no longer mark assets imported on delivery |

**Verified** — not assumed

- `python -m pytest tests` → **18 passed** (exit 0): the 4 M0 tests plus 14 new ones in
  `tests/test_editor_imports.py`, driven through the real HTTP API and the queue's event
  stream (`heartbeat → import → import-result`, deferral, flush, retry guard, target
  selection).
- **The new tests were shown to have teeth.** Re-introducing the original behaviour
  (`has_live_panel()` forced to `True`) failed exactly the 6 honesty tests and nothing
  else; the file was restored byte-identical afterwards (`diff` clean, no `TEMPORARY`
  markers left).
- Legacy upgrade path: a database created with the pre-change `downloads` table migrated
  in place — all 9 new columns added, existing rows preserved, new columns writable.
- `python -m compileall apps/desktop-service/xdrop` → exit 0; app imports; new endpoints
  present in the generated OpenAPI schema (38 paths total).
- `npm run build:ui` → exit 0 (strict `tsc`, `noUnusedLocals`).
- The rebuilt bundle actually contains the new UI logic (`WAITING FOR`, `JOB_IMPORT_STATE`,
  `premiereImportPending`), and `dist/index.html` points at the new hash — the service
  serves `dist/`, so the change reaches users running from source.
- Panel JavaScript parses under `node --check`.
- Docs updated to match: `README.md` (a "How imports actually behave" section),
  `docs/API.md` (new endpoints, `confirmed` semantics, per-editor state table),
  `apps/premiere-plugin/README.md` (the panel must be open).

**Limitations — stated plainly**

- **No Adobe application or DaVinci Resolve was available here**, so nothing was verified
  against a real host. What is proven is the service-side protocol, the state machine and
  the panel's own logic (including its escaping and result parsing); a real
  `Window → Extensions → Xdrop` import on a machine with Premiere/AE is still untested.
- The flush loop polls every 10s and only retries on editor availability, so an import can
  land up to ~10s after the editor opens. Immediate triggering (a panel-connected event)
  is a small follow-up.
- `docs/ARCHITECTURE.md` remains stale in substance (banner only).
- **All of S1–S5 remain unfixed**: the local API is still unauthenticated and reachable
  from any web page. This slice deliberately did not touch that; M1 does.
- `apps/resolve-plugin/dist/` is tracked in this repository, so the rebuild is part of the
  diff (one asset replaced, `index.html` hash updated).
- No changes were committed.

---

### Packaging research — **COMPLETE** (2026-10-09)

The user asked how Adobe and Blackmagic extensions are packaged so users can install them
and have them work. Written up in [PACKAGING.md](PACKAGING.md). Findings that change the
plan:

- **CEP has a published end date.** Removed from the flagship apps from **December 2029**;
  Premiere Pro CEP-disabled-by-default **December 2028**, no new Marketplace CEP
  submissions after **December 2027**. After Effects gets UXP public beta around
  **November 2026**. The CEP panel is safe for now but is on a clock, and a UXP
  implementation needs two `.ccx` packages (one host each) and a Marketplace-distinct
  plugin ID. ExtendScript is explicitly unaffected.
- **Premiere Pro 2026 may already be stricter than the published timeline.** Two
  independent 2026 reports show CEP panels not loading even with the correct folder and
  `PlayerDebugMode`. Cause not confirmed; treat "CEP works on 26.x" as unverified and test
  it on a real install.
- **Resolve does not need admin rights if the script is installed per-user.** The current
  installer only targets the all-users `Fusion/Scripts/Utility`, which needs elevation on
  Windows. Per-user paths for all three OSes are documented and are the cheapest
  reliability win available.
- **Workflow Integration plugins are Studio-only** and Windows/macOS-only, so they cannot
  replace the script, which works on the free version everywhere.
- **`.drfx` is irrelevant** to Xdrop — it packages Fusion templates, not panels or apps.
- A `.zxp` must be signed **with a timestamp**; without one, an expired certificate stops
  the extension loading for every user with no warning. Signed `.zxp` installs also do not
  need `PlayerDebugMode`, unlike the folder copy used today.

Nothing in this section was implemented — it is research. The per-user Resolve install path
(§5.1 of PACKAGING.md) is the recommended first follow-up.
