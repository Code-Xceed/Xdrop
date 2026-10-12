# Development Guide

This document details the development environment setup, workflow, and testing for **Xdrop**.

---

## 1. Prerequisites

- **OS**: Windows 10/11 or macOS
- **Node.js**: v18.0.0 or later (v20+ recommended)
- **Python**: 3.10 or later
- **FFmpeg**: Executable available in PATH or common directories
- **DaVinci Resolve**: Free or Studio 18+

---

## 2. Monorepo Setup

1. **Install JavaScript/TypeScript packages**:
   ```bash
   npm install
   ```

2. **Install Python backend requirements**:
   ```bash
   pip install -r apps/desktop-service/requirements.txt
   pip install pytest
   ```

---

## 3. Running in Development Mode

Run the backend and frontend concurrently:

### Terminal 1: Backend Service
```bash
python apps/desktop-service/xdrop/main.py
```
Backend runs on `http://127.0.0.1:8484`.

### Terminal 2: React Frontend with Vite HMR
```bash
npm run dev:ui
```
Vite runs on `http://localhost:5173` and proxies `/api`, `/thumbnails`, and `/ws` to the backend on `:8484`.

### Companion Desktop Window Mode
To run the full app in a desktop window:
```bash
npm run start:gui
```

---

## 4. Testing

The backend test suite lives in `tests/` and runs with pytest:
```bash
python -m pytest tests -v
```

`tests/conftest.py` redirects all runtime state (SQLite DB, logs, thumbnails) to athrowaway directory via `XDROP_DATA_DIR`, so running the suite never touches yourreal `%LOCALAPPDATA%\Xdrop` data.

> **Coverage is currently minimal.** The suite so far contains regression tests for
> the CEP manifest and the Adobe extension installer. A real suite — organizer path
> safety, provider URL routing, database migrations, API contracts, the auth matrix —
> is tracked as milestone M2 in [REVAMP_PLAN.md](REVAMP_PLAN.md) (W3.2). Do not
> assume untested code works.

`npm test` is an alias for the frontend production build, **not** a test run:
```bash
npm test        # same as: npm run build:ui  (tsc + vite build)
```

There is no frontend unit-test runner yet (W3.3).
