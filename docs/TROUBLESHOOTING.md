# Troubleshooting Guide

### 1. DaVinci Resolve Status Shows "Offline"

**Symptom**: The badge in Xdrop header displays "DaVinci Resolve Offline" in amber.

**Possible Causes & Fixes**:
1. **DaVinci Resolve is not open**: Launch DaVinci Resolve and open any project. Xdrop will automatically detect it within seconds, or click the refresh button next to the status badge.
2. **No project is open**: Resolve needs an active project to access the Media Pool. Open an existing project or create an "Untitled Project".
3. **External Scripting Disabled in Resolve**:
   - Go to **DaVinci Resolve → Preferences → General**.
   - Check that **External scripting using** is set to **Local** or **All Users**.
   - Restart DaVinci Resolve.
4. **Environment Variables**:
   Ensure `RESOLVE_SCRIPT_API` points to:
   `%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting`

---

### 2. "FFmpeg Not Detected" Error

**Symptom**: Settings page shows a red warning "FFmpeg Not Detected" and audio extraction or proxy generation fails.

**Fix**:
1. If you have FFmpeg installed (e.g. at `C:\ffmpeg\bin\ffmpeg.exe`), paste that path into **Settings → FFmpeg Executable Path**.
2. Or install FFmpeg quickly via PowerShell:
   ```powershell
   winget install Gyan.FFmpeg
   ```
3. Restart Xdrop.

---

### 3. Media Imported into Media Pool Has "Media Offline" or Codec Error

**Symptom**: Clip appears in Resolve Media Pool with a red "Media Offline" badge or won't play audio.

**Fix**:
- Some video formats (like raw WebM with Opus audio) are not natively decoded by the free version of DaVinci Resolve.
- In Xdrop **Settings**, set **Preferred Video Editing Format** to **Universal MP4 (H.264 / AAC)** or **Apple ProRes MOV**.
- Xdrop will automatically remux and convert the stream into standard ProRes or H.264 with PCM/AAC audio before importing.

---

### 4. "This platform or URL type is not currently supported"

**Symptom**: The URL cannot be analyzed.

**Fix**:
- Check that the URL is public and accessible without logging in.
- For private videos or stories that require authentication, Xdrop will decline to download in compliance with security guidelines.
- Try copying the direct canonical share link from your browser address bar.
