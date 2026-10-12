# Contributing to Xdrop

Thank you for your interest in contributing to **Xdrop**!

## Code of Conduct & Legal Requirements

Xdrop strictly adheres to platform policies and legal frameworks:
- **NO DRM BYPASS**: Submissions that attempt to defeat DRM or circumvent platform security controls will be rejected immediately.
- **NO AUTH BYPASS**: Xdrop only handles public, permitted media streams or user-authorized API endpoints.
- **NO UNSAFE SHELL CODE**: Shell command construction using string concatenation is strictly prohibited. All process invocations must use safe argument arrays (`subprocess.run([binary, ...], shell=False)`).
- **PATH SAFETY**: Output paths must be validated with directory traversal checks.

## Development Workflow

1. **Clone & Install**:
   ```bash
   git clone https://github.com/Code-Xceed/Xdrop.git
   cd Xdrop
   npm install
   ```

2. **Frontend Development**:
   ```bash
   npm run dev:ui
   ```
   Open `http://localhost:5173`.

3. **Backend Service Development**:
   ```bash
   npm run start:service
   ```

4. **Before Submitting**:
   ```bash
   python -m pytest tests -v   # backend tests
   npm run build:ui            # frontend typecheck + production build
   ```
   Note: `npm test` is an alias for `npm run build:ui` — it does **not** run JavaScript
   unit tests (there is no JS test runner yet). The backend suite is also still small;
   a real one is milestone **M2** in [docs/REVAMP_PLAN.md](docs/REVAMP_PLAN.md). Do not
   assume untested code works.

5. **Submitting a Provider**:
   Follow [docs/PROVIDER_GUIDE.md](docs/PROVIDER_GUIDE.md) to add new platform providers, and include unit tests for URL matching and inspection.
