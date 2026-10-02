# Security & Compliance Model

Security and legal compliance are fundamental architectural pillars of **Xdrop**.

---

## 1. Threat Model & Protections

### Untrusted URL Inputs
All URLs supplied by the user or clipboard are treated as untrusted input:
- URLs are strictly validated to require standard HTTP/HTTPS schemes.
- Disallowed protocols (such as `file://`, `ftp://`, `javascript:`, `data:`) are rejected.
- Private network ranges and loopback requests are checked to prevent Server-Side Request Forgery (SSRF).

### Safe Subprocess Execution (Command Injection Prevention)
- **Zero Raw Shell Commands**: Subprocesses (FFmpeg, FFprobe, Python workers) are **never** executed using shell strings or `shell=True`.
- **Safe Argv Arrays**: All executable calls pass clean string argument lists (`subprocess.run([binary_path, arg1, arg2], shell=False)`).
- Arguments containing filenames or titles are never interpolated into shell strings.

### Arbitrary File Write & Path Traversal Prevention
- All user-defined naming patterns and asset titles are sanitized via `sanitize_filename_py`.
- Path traversal sequences (`..`, `/`, `\`) are stripped from dynamic template tokens.
- Final destination paths are explicitly verified with `Path(dest).is_relative_to(base_dir)`. If a path escapes the configured base directory, Xdrop overrides it and forces it safely into the root asset folder.
- Windows reserved file names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`) are automatically renamed with safe suffixes to prevent file system locking bugs.

---

## 2. Legal & Platform Compliance

Xdrop strictly adheres to platform policies:
- **No DRM Circumvention**: Xdrop contains no code to decrypt DRM-protected media or circumvent Widevine, PlayReady, or FairPlay technologies.
- **No Authentication Bypass**: The application does not bypass authentication or access private media without permission.
- **Support for Public Media**: Designed for editors importing legitimate public assets, reference reels, open-source footage, and permitted social media content.
- **Independent Providers**: Platform integrations can be toggled or updated independently as platform API policies evolve.

---

## 3. Privacy & Offline-First Design

- **100% Local Execution**: All database records, downloaded assets, and transcoded files remain strictly on the user's local machine (`%LOCALAPPDATA%\Xdrop`).
- **No External Telemetry**: Xdrop does not track or phone home user editing activity, imported assets, or project filenames.
- **No Mandatory Account**: Users do not need an account or subscription server connection to run the application.
