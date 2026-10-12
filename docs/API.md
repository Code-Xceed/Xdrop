# Xdrop API Reference

The Xdrop Local Service runs on `http://127.0.0.1:8484` by default.

> **Status and accuracy.** The authoritative, always-current reference is the OpenAPI
> schema the running service generates at `/docs` (Swagger UI) and `/openapi.json`.
> This page is a hand-maintained summary and is **not exhaustive** — the Adobe-specific
> import routes (`/api/downloads/{id}/import-premiere`, `…/import-aftereffects`,
> `/api/library/{id}/import-premiere`, `…/import-aftereffects`) and
> `POST /api/settings/install-aftereffects-extension` are omitted below.
>
> **Authentication:** as of this revision the local API has **no authentication** and
> permits any origin. Read [SECURITY.md](SECURITY.md) §2 before relying on it.
>
> `GET /api/analyze/thumbnail-proxy` still exists but is scheduled for removal
> ([REVAMP_PLAN.md](REVAMP_PLAN.md) AD-1 / W2.4) because it is an SSRF risk.

---

## 1. Analysis Endpoints

### `POST /api/analyze`
Inspects a media URL and returns available stream assets.

**Request Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=..."
}
```

**Response (200 OK):**
```json
{
  "url": "https://www.youtube.com/watch?v=...",
  "platform": "youtube",
  "platform_name": "YouTube",
  "title": "Sample Video Title",
  "author": "Creator Name",
  "duration": 184.2,
  "thumbnail_url": "https://...",
  "assets": [
    {
      "id": "video_1080p_137",
      "media_type": "video",
      "format": "mp4",
      "quality_label": "Video (1080p)",
      "resolution": "1920x1080",
      "fps": 60,
      "filesize_approx": 45000000,
      "is_default": true
    },
    {
      "id": "audio_best",
      "media_type": "audio",
      "format": "wav",
      "quality_label": "Audio Only (High Quality WAV)",
      "is_default": false
    }
  ]
}
```

### `POST /api/analyze/batch`
Detects platform support for an array of URLs quickly without querying streams.

**Request Body:**
```json
{
  "urls": [
    "https://www.youtube.com/watch?v=123",
    "https://www.instagram.com/reel/abc/"
  ]
}
```

---

## 2. Download Queue Endpoints

### `POST /api/downloads`
Enqueues a new media download.

**Request Body:**
```json
{
  "source_url": "https://www.youtube.com/watch?v=...",
  "asset_id": "video_1080p_137",
  "format": "mp4",
  "quality_label": "1080p",
  "media_type": "video",
  "title": "Sample Clip",
  "target_media_pool_bin": "Xdrop",
  "auto_import_to_resolve": true,
  "extract_audio_only": false,
  "generate_proxy": false
}
```

### `GET /api/downloads`
Lists all active, completed, or failed download jobs.

### `POST /api/downloads/{id}/cancel`
Cancels an active or queued job.

### `POST /api/downloads/{id}/retry`
Retries a failed or cancelled job.

### `DELETE /api/downloads/{id}`
Removes a job from the queue.

### `POST /api/downloads/{id}/import`
Triggers manual import into DaVinci Resolve for a completed download.

---

## 3. Library Endpoints

### `GET /api/library`
Queries previous downloaded assets.
- `search`: string
- `platform`: string
- `media_type`: 'video' | 'audio' | 'image'
- `resolve_imported`: boolean
- `limit`: number
- `offset`: number

### `DELETE /api/library/{id}?delete_file={boolean}`
Removes asset from database, optionally deleting the physical file on disk.

### `POST /api/library/{id}/import`
Imports the existing local asset file into DaVinci Resolve.

### `POST /api/library/{id}/reveal`
Reveals the asset file in Windows File Explorer (`explorer.exe /select,...`).

---

## 4. Cross-NLE Bridge Endpoints

### `GET /api/editors/status`
Returns live status of all video editors and indicates which editor is currently active:
```json
{
  "activeEditor": "resolve",
  "resolve": {
    "isAvailable": true,
    "productName": "DaVinci Resolve Studio",
    "version": "19.0.0",
    "currentProject": "Commercial_Cut_v2"
  },
  "premiere": {
    "isAvailable": false,
    "productName": "Adobe Premiere Pro"
  },
  "aftereffects": {
    "isAvailable": false,
    "productName": "Adobe After Effects"
  }
}
```

### `GET /api/resolve/status`
Returns live status of DaVinci Resolve connection.

### `POST /api/resolve/import`
Directly imports specified paths into a target Media Pool bin.

### `GET /api/premiere/status` & `POST /api/premiere/heartbeat`
Returns live status and receives CEP panel heartbeats from Adobe Premiere Pro.

### `POST /api/premiere/import`
Broadcasts an import command to the Adobe Premiere Pro CEP panel. Refused with
`success: false` and an explanation when the panel is not open, because nothing would
receive the command.

### `POST /api/premiere/import-result`
Receives the real ExtendScript outcome of an import from the CEP panel, which is what
marks a job (and its library asset) as imported.
```json
{ "requestId": "imp_1a2b3c4d5e", "success": true, "clipName": "clip.mp4", "binName": "Xdrop", "error": null }
```

### `GET /api/aftereffects/status` & `POST /api/aftereffects/heartbeat`
Returns live status and receives CEP panel heartbeats from Adobe After Effects.

### `POST /api/aftereffects/import`
Broadcasts an import command to the Adobe After Effects CEP panel. Refused the same way
as the Premiere endpoint when the panel is not open.

### `POST /api/aftereffects/import-result`
Receives the real ExtendScript outcome of an import from the After Effects CEP panel.
Same body as the Premiere endpoint.

### `GET /api/editors/pending-imports`
Lists downloads whose import is still waiting on an editor, grouped by editor
(`resolve`, `premiere`, `aftereffects`).

### `POST /api/editors/flush-imports?force={boolean}`
Attempts every outstanding import against the editors that are currently available. The
service also does this automatically every few seconds, so this endpoint is for forcing
a retry (pass `force=true` to ignore the once-per-run retry guard).

---

## 5. Settings & Diagnostics Endpoints

### `GET /api/settings`
Returns current application configuration.

### `PUT /api/settings`
Updates and persists application configuration.

### `GET /api/settings/tools-status`
Returns operational status of FFmpeg and editor script/extension installations.

### `GET /api/settings/system-info`
Returns full machine diagnostics:
```json
{
  "python": { "version": "3.11.9", "executable": "...", "is64bit": true },
  "ytdlp": { "version": "2024.08.01" },
  "ffmpeg": { "isAvailable": true, "path": "...", "info": "..." },
  "os": { "system": "Windows", "release": "11", "machine": "AMD64" },
  "editors": { "resolveInstalled": true, "adobeInstalled": true }
}
```

### `POST /api/settings/update-ytdlp`
Updates the `yt-dlp` social media extractor engine directly via pip.

### `POST /api/settings/install-resolve-script`
Installs `Xdrop.py` into DaVinci Resolve Utility Scripts.

### `POST /api/settings/install-premiere-extension`
Installs the CEP dockable panel for Adobe Premiere Pro and After Effects.

---

## 6. WebSocket Protocol (`/ws`)

Connect to `ws://127.0.0.1:8484/ws`.

### Server-to-Client Messages
- `INITIAL_STATE`: Sent upon connection with active jobs and Resolve status.
- `JOB_CREATED`: Emitted when a new download job is created.
- `JOB_PROGRESS`: Real-time download progress updates (progress, speed, eta, bytes).
- `JOB_COMPLETED`: Emitted when download and processing finish. The payload also carries
  an `imports` array describing, per editor, whether the import was confirmed, deferred,
  or failed with a reason.
- `JOB_FAILED`: Emitted when download or import encounters an error.
- `JOB_IMPORT_STATE`: Emitted when an import is confirmed, rejected, or completed later by
  the deferred-import flush. Payload includes the refreshed `job` so panels show the
  current per-editor state.
- `RESOLVE_STATUS_CHANGED`: Emitted when Resolve connection state changes.

### Import state on a job

Each job tracks its import state per editor:

| Field | Meaning |
| --- | --- |
| `resolveImported` / `premiereImported` / `aftereffectsImported` | Confirmed present in that editor's project. |
| `resolveImportPending` / `premiereImportPending` / `aftereffectsImportPending` | Import is outstanding: the editor was closed, or the Adobe panel has not confirmed the ExtendScript result yet. |
| `resolveImportError` / `premiereImportError` / `aftereffectsImportError` | Why the most recent attempt for that editor did not land; cleared on success. |

A successful import response carries `confirmed`: `true` means the clip is in the project
(always the case for Resolve, which imports synchronously). `false` means the request was
delivered to the Adobe panel and is awaiting its confirmation.

### Client-to-Server Commands
```json
{ "type": "PING" }
{ "type": "CHECK_RESOLVE" }
{ "type": "CANCEL_JOB", "jobId": "dl_..." }
{ "type": "RETRY_JOB", "jobId": "dl_..." }
{ "type": "REMOVE_JOB", "jobId": "dl_..." }
{ "type": "TRIGGER_RESOLVE_IMPORT", "jobId": "dl_..." }
```
