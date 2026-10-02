# Platform Provider Guide

This guide explains how to create, test, and register a new media provider in **Xdrop**.

---

## 1. Provider Contract

Every platform provider inherits from `PlatformProvider` defined in `apps/desktop-service/xdrop/providers/base.py`:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from xdrop.providers.base import PlatformProvider, MediaInfoModel, MediaAssetModel, DownloadResult

class MyNewPlatformProvider(PlatformProvider):
    platform_id = "myplatform"
    platform_name = "My Platform"
    enabled = True

    def can_handle(self, url: str) -> bool:
        """Return True if this provider can process the given URL."""
        return "myplatform.com" in url.lower()

    def inspect(self, url: str) -> MediaInfoModel:
        """Extract metadata and available streams from public content."""
        # 1. Fetch metadata via official public API or compliant extractor
        # 2. Return a validated MediaInfoModel
        pass

    def download(
        self,
        url: str,
        asset_id: str,
        output_template: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> DownloadResult:
        """Download stream to output_template with real progress updates."""
        pass
```

---

## 2. Best Practices & Compliance Rules

1. **Strictly No DRM/Auth Bypassing**:
   Only access public content or officially authenticated user tokens. Never implement DRM circumvention.
2. **Safe Arguments**:
   Never use `shell=True` or format strings into shell commands. Pass argument arrays to `subprocess.run([...], shell=False)`.
3. **Real Progress Hooking**:
   Emit real progress percentage, downloaded bytes, total bytes, speed string (e.g. `12.4 MB/s`), and ETA (e.g. `00:15`) to `progress_callback`.

---

## 3. Registering the Provider

Open `apps/desktop-service/xdrop/providers/manager.py` and register the provider in `_register_default_providers()`:

```python
from xdrop.providers.myplatform import MyNewPlatformProvider

def _register_default_providers(self) -> None:
    # ...
    self._providers.append(MyNewPlatformProvider())
```

---

## 4. Writing Automated Tests

Add test cases in `tests/test_providers.py`:

```python
def test_my_platform_urls():
    p = MyNewPlatformProvider()
    assert p.can_handle("https://myplatform.com/post/12345")
    assert not p.can_handle("https://youtube.com/watch?v=123")
```

Run tests to verify:
```bash
python -m pytest tests/test_providers.py -v
```
