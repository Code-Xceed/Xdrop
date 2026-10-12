# Security & Compliance Model

> **Read this first.** This document describes what Xdrop **actually enforces today**.
> Anything not listed in §1 is a known gap, listed in §2. Do not repeat the older
> marketing version of these claims — several of them were not true.

---

## 1. Enforced today

### Untrusted URL inputs

- Only `http://` and `https://` URLs are accepted. `file://`, `ftp://`,
  `javascript:`, `data:`, and anything else never reach a provider: provider
  matching is pattern-based on http/https, and an unmatched URL is rejected with
  HTTP 400 before any network work happens.
- Analysis and download run against the matched provider only, never against a
  user-supplied path.

### Safe subprocess execution (command injection prevention)

- Subprocesses (FFmpeg, `tasklist` / `pgrep`, `pip`) are **always** invoked with an
  argument array and `shell=False`. No shell string is ever assembled.
- Filenames, titles, and URLs are never interpolated into a shell command.
- The only command built from stored data is `explorer.exe /select,<path>` for
  "Reveal in Explorer", and it is passed as an argument array, not a shell string.

### Arbitrary file write & path traversal prevention

- Naming-pattern tokens and asset titles are sanitized by `sanitize_filename_py`:
  invalid and control characters, trailing dots/spaces, Windows reserved device
  names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`), and a 120-character cap.
- `..` and `.` segments are stripped before a destination is assembled.
- The resolved destination is verified to sit inside the configured download root
  via `relative_to`. If it escapes, the write is forced into the root instead.
- Implemented in `xdrop/processor/organizer.py`. A behaviour test for this is
  tracked in the revamp plan (W3.2); it does not exist yet.

### Data locality

- All state — SQLite database, logs, thumbnails, proxies — lives under
  `%LOCALAPPDATA%\Xdrop` (Windows) or `~/.xdrop` (elsewhere), overridable with the
  `XDROP_DATA_DIR` environment variable.
- No telemetry, no account, no phone-home. The only outbound requests are to the
  media hosts whose URLs you paste.
- If a legacy `resolvefetch.db` is found it is copied forward; that copy stays local.

---

## 2. Known gaps — NOT yet protected

These are real and unfixed. They are tracked in `docs/REVAMP_PLAN.md` milestone M1.
Until the listed task lands, do not describe them as protections.

| Gap | Why it matters | Task |
| --- | --- | --- |
| The local HTTP API has **no authentication**, and CORS allows **any origin** (`allow_origins=["*"]` together with `allow_credentials=True`, which is also spec-invalid) | Any web page the user visits can read the asset library and download history, and can trigger downloads or editor imports. Browsers treat `127.0.0.1` as a *trustworthy* origin, so HTTPS pages can reach this service — mixed-content blocking does not help | W2.1, W2.2 |
| No origin/CSRF check on state-changing requests | Cross-origin drive-by commands against the local service | W2.3 |
| `GET /api/analyze/thumbnail-proxy` fetches **any** user-supplied URL, follows redirects, and checks neither private address ranges nor content type | Server-side request forgery: internal and cloud-metadata endpoints are reachable through the local service. The thumbnail body is returned verbatim | W2.4 |
| The SPA catch-all serves files joined from unvalidated path input | File disclosure outside the web bundle | W2.5 |
| `POST /api/analyze` has no concurrency or rate limit | Local resource exhaustion from repeated requests | W2.6 |
| The service binds loopback by default but nothing stops `--host 0.0.0.0` | Exposes an unauthenticated service to the local network | W2.8 |

**If you run Xdrop on a shared or untrusted machine, treat the local service as
unauthenticated: keep it on `127.0.0.1`, and do not run it while browsing untrusted
sites until M1 has shipped.**

---

## 3. Legal & platform compliance

Xdrop is built for importing legitimate public assets, reference reels, open-source
footage, and permitted social media content.

- **No DRM circumvention.** There is no code to decrypt DRM-protected media or to
  defeat Widevine, PlayReady, or FairPlay.
- **No authentication bypass.** The app does not log in as you, use your cookies, or
  reach private media.
- **Public content only.** Private, followers-only, and paywalled media are expected
  to fail; that is intended behaviour, not a bug.
- **Independent providers.** Platform integrations can be enabled, disabled, or
  updated independently as platform policies change. A per-provider toggle API is
  planned (W8.5); today providers are always on.
- **You are responsible** for complying with each platform's terms of service and
  with the copyright of anything you import.

---

## 4. Privacy

- **100% local execution.** Databases, downloaded assets, and transcoded files stay
  on your machine.
- **No external telemetry.** Xdrop does not track editing activity, imported assets,
  or project filenames. The `telemetry_enabled` setting exists but nothing reads it;
  there is no telemetry implementation to disable.
- **No mandatory account.** No sign-in and no subscription server.

---

## 5. Reporting a vulnerability

Until a security contact is published, open a minimal private report describing the
class of issue and the affected endpoint, without including exploit payloads for
anything that could be weaponised against other users.
