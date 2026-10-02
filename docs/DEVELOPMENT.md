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

Run all unit tests, integration tests, and frontend build verification:
```bash
npm test
```

To run only the backend pytest suite:
```bash
python -m pytest tests -v
```

To run only the frontend build check:
```bash
npm run build:ui
```
