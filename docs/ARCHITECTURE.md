# Xdrop: System Architecture

## 1. Architectural Philosophy

Xdrop is architected as an **offline-first, desktop-native companion application** designed to integrate with DaVinci Resolve with minimum system overhead and zero cloud account dependencies.

The architecture decouples the user interface from media processing and platform extraction:
- **UI Layer (Frontend)**: React 18, TypeScript, and Vite. Statically compiled and served either directly by the local Python service or embedded in a lightweight desktop window (via `pywebview` / Edge WebView2) and DaVinci Resolve panels.
- **Service Layer (Backend)**: Python FastAPI running locally on `http://127.0.0.1:8484`. Manages the SQLite database, platform providers, FFmpeg subprocesses, and the official DaVinci Resolve Scripting API bridge.
- **DaVinci Resolve Integration Layer**: Communicates with DaVinci Resolve via the official `DaVinciResolveScript` library (`fusionscript.dll`) and script menus.

```text
┌────────────────────────────────────────────────────────┐
│                   DaVinci Resolve                      │
│                                                        │
│   Workspace Menu:                                      │
│   Scripts → Utility → Xdrop.py                  │
│                                                        │
│   ┌─────────────────────────────────────────────────┐  │
│   │               Xdrop UI                   │  │
│   │            (React + TypeScript)                 │  │
│   └───────────────────────┬─────────────────────────┘  │
└───────────────────────────┼────────────────────────────┘
                            │ Local HTTP / WebSocket (:8484)
                            ▼
┌────────────────────────────────────────────────────────┐
│              Xdrop Local Service                │
│                                                        │
│   ┌────────────────────────────────────────────────┐   │
│   │                 API Router                     │   │
│   │   /analyze   /downloads   /library   /resolve  │   │
│   └──────┬────────────────────┬──────────────┬─────┘   │
│          │                    │              │         │
│          ▼                    ▼              ▼         │
│   ┌──────────────┐    ┌──────────────┐ ┌─────────────┐ │
│   │   Provider   │    │    Queue     │ │   DaVinci   │ │
│   │   Manager    │    │   Manager    │ │   Bridge    │ │
│   └──────┬───────┘    └──────┬───────┘ └──────┬──────┘ │
│          │                   │                │        │
│          │                   ▼                │        │
│          │            ┌──────────────┐        │        │
│          │            │    FFmpeg    │        │        │
│          │            │  Processor   │        │        │
│          │            └──────┬───────┘        │        │
│          │                   │                │        │
│          ▼                   ▼                ▼        │
│   ┌────────────────────────────────────────────────┐   │
│   │           Local SQLite Database                │   │
│   │  (downloads, assets, settings, history)        │   │
│   └────────────────────────────────────────────────┘   │
└───────────────────────────┬────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
     Local Asset Library          DaVinci Media Pool
  (C:/.../Xdrop Assets)     (Active Project Bin)
```

---

## 2. DaVinci Resolve Integration

DaVinci Resolve provides a Python scripting interface powered by `fusionscript`. Xdrop uses the official connection protocol:

1. **Environment Setup**:
   On Windows, the scripting module is located in:
   `%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules\DaVinciResolveScript.py`
   With DLL at:
   `C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll`
2. **Connection Protocol**:
   `bmd.scriptapp("Resolve")` connects to the running Resolve instance.
   - If Resolve is not running, `bmd.scriptapp("Resolve")` returns `None`. The backend safely marks Resolve status as `isAvailable: False` and informs the user. Downloaded files are saved locally in the Library, and can be imported later with a single click.
   - If Resolve is open, Xdrop queries:
     - `resolve.GetProductName()`
     - `resolve.GetVersionString()`
     - `projectManager.GetCurrentProject()`
     - `project.GetMediaPool()`
     - `mediaPool.GetRootFolder()`
3. **Media Pool Automation**:
   When importing an asset:
   - Target bin (default: `Xdrop`) is located or created under the root folder via `mediaPool.AddSubFolder(rootFolder, binName)`.
   - Current folder is switched: `mediaPool.SetCurrentFolder(targetFolder)`.
   - `mediaPool.ImportMedia([file_path])` imports the file directly into the bin.
   - Returned `MediaPoolItem` objects verify success, and clip names are registered in the database.

---

## 3. Provider Architecture

Platform-specific extraction logic is decoupled from downloader routines via the `PlatformProvider` interface:

```python
class PlatformProvider(ABC):
    platform_id: str
    platform_name: str
    enabled: bool

    @abstractmethod
    def can_handle(self, url: str) -> bool: ...

    @abstractmethod
    def inspect(self, url: str) -> MediaInfoModel: ...

    @abstractmethod
    def download(self, url: str, asset_id: str, output_template: str, progress_callback: Callable) -> DownloadResult: ...
```

Registered Providers:
1. `DirectMediaProvider`: For direct public files (`.mp4`, `.mov`, `.wav`, `.mp3`, `.png`, `.jpg`).
2. `YouTubeProvider`: YouTube videos, shorts, audio.
3. `InstagramProvider`: Public reels and posts.
4. `XTwitterProvider`: X (Twitter) public videos.
5. `TikTokProvider`: Public TikTok videos.
6. `RedditProvider`: Reddit videos with audio muxing.
7. `FacebookProvider`: Public video posts and reels.
8. `PinterestProvider`: Video pins.
9. `VimeoProvider`: Public Vimeo videos.
10. `GenericWebMediaProvider`: Web media fallback.

---

## 4. Download Queue & State Machine

Every download job moves through a deterministic state machine:

```text
[QUEUED] ──► [DOWNLOADING] ──► [PROCESSING] ──► [IMPORTING] ──► [COMPLETED]
   │               │                 │               │
   ▼               ▼                 ▼               ▼
[CANCELLED]    [FAILED]          [FAILED]         [FAILED]
```

- **Queued**: Enqueued into `asyncio.Queue`, persisted in SQLite.
- **Downloading**: Stream downloaded via Provider with thread-safe progress hook emitting `speed`, `progress`, `eta`, and `downloaded_bytes` via WebSocket.
- **Processing**: FFmpeg transcode (H.264/AAC MP4 or ProRes MOV), audio extraction (WAV/MP3), frame thumbnail capture, and proxy generation.
- **Importing**: Communicates with DaVinci Resolve Media Pool.
- **Completed**: Catalogued into `assets` table.
- **Failed / Cancelled**: Error recorded, allows one-click retry.

---

## 5. Storage & Naming Templates

Templates support dynamic variables:
- `{project}`: Current DaVinci Resolve project name
- `{platform}`: e.g. `YouTube`, `Instagram`
- `{mediaType}`: `Video`, `Audio`, `Images`
- `{date}`: Current date (`YYYY-MM-DD`)
- `{title}`: Sanitized media title
- `{quality}`: Quality label (`1080p`, `WAV`, etc.)

Security: All path components are strictly sanitized and checked with `Path.is_relative_to(base_dir)` to prevent path traversal.
