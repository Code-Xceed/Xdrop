from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel

class MediaAssetModel(BaseModel):
    id: str
    media_type: str # 'video', 'audio', 'image'
    format: str     # 'mp4', 'mov', 'wav', 'mp3', 'png', etc.
    quality_label: str
    resolution: Optional[str] = None
    fps: Optional[int] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    filesize_approx: Optional[int] = None
    url: Optional[str] = None
    is_default: bool = False

class MediaInfoModel(BaseModel):
    url: str
    platform: str
    platform_name: str
    title: str
    author: Optional[str] = None
    author_url: Optional[str] = None
    source_id: str
    duration: Optional[float] = None
    thumbnail_url: Optional[str] = None
    description: Optional[str] = None
    assets: List[MediaAssetModel] = []

class DownloadResult(BaseModel):
    success: bool
    output_file_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    downloaded_bytes: int = 0
    error_message: Optional[str] = None

class PlatformProvider(ABC):
    """Abstract base class for all platform media providers."""

    platform_id: str = "generic"
    platform_name: str = "Generic Platform"
    enabled: bool = True

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Determines if this provider can handle the supplied URL."""
        pass

    @abstractmethod
    def inspect(self, url: str) -> MediaInfoModel:
        """Inspects the URL for public metadata and available asset formats."""
        pass

    @abstractmethod
    def download(
        self,
        url: str,
        asset_id: str,
        output_template: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> DownloadResult:
        """Downloads the requested asset stream to disk with real progress reporting."""
        pass
