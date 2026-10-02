# Xdrop API Reference

The Xdrop Local Service runs on `http://127.0.0.1:8484` by default.

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

## 4. DaVinci Resolve Bridge Endpoints

### `GET /api/resolve/status`
Returns live status of DaVinci Resolve connection:
```json
{
  "isAvailable": true,
  "version": "21.0.4.5",
  "productName": "DaVinci Resolve Studio",
  "currentProject": "Commercial_Cut_v2",
  "currentTimeline": "Timeline 1",
  "mediaPoolFolder": "Master",
  "error": null,
  "lastChecked": "2026-10-01T03:00:00Z"
}
```

### `POST /api/resolve/import`
Directly imports specified paths into a target Media Pool bin.

---

## 5. Settings Endpoints

### `GET /api/settings`
Returns current application configuration.

### `PUT /api/settings`
Updates and persists application configuration.

### `GET /api/settings/tools-status`
Returns operational status of FFmpeg and DaVinci Resolve script installation.

### `POST /api/settings/install-resolve-script`
Installs `Xdrop.py` into DaVinci Resolve Utility Scripts.

---

## 6. WebSocket Protocol (`/ws`)

Connect to `ws://127.0.0.1:8484/ws`.

### Server-to-Client Messages
- `INITIAL_STATE`: Sent upon connection with active jobs and Resolve status.
- `JOB_CREATED`: Emitted when a new download job is created.
- `JOB_PROGRESS`: Real-time download progress updates (progress, speed, eta, bytes).
- `JOB_COMPLETED`: Emitted when download, processing, and Resolve import succeed.
- `JOB_FAILED`: Emitted when download or import encounters an error.
- `RESOLVE_STATUS_CHANGED`: Emitted when Resolve connection state changes.

### Client-to-Server Commands
```json
{ "type": "PING" }
{ "type": "CHECK_RESOLVE" }
{ "type": "CANCEL_JOB", "jobId": "dl_..." }
{ "type": "RETRY_JOB", "jobId": "dl_..." }
{ "type": "REMOVE_JOB", "jobId": "dl_..." }
{ "type": "TRIGGER_RESOLVE_IMPORT", "jobId": "dl_..." }
```
