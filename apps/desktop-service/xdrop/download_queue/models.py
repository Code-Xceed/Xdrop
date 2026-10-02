from typing import Optional
from pydantic import BaseModel, Field

class CreateDownloadRequest(BaseModel):
    source_url: str
    asset_id: str = "best_video"
    format: str = "mp4"
    quality_label: str = "Best"
    media_type: str = "video" # video, audio, image
    title: Optional[str] = None
    author: Optional[str] = None
    target_media_pool_bin: Optional[str] = None
    auto_import_to_resolve: Optional[bool] = None
    target_editor: Optional[str] = None # 'auto', 'resolve', 'premiere', 'aftereffects', 'none'
    auto_import_to_premiere: Optional[bool] = None
    target_premiere_bin: Optional[str] = None
    auto_import_to_aftereffects: Optional[bool] = None
    target_aftereffects_bin: Optional[str] = None
    transcode_video_format: Optional[str] = None # 'mp4', 'mov', None
    transcode_audio_format: Optional[str] = None # 'wav', 'mp3', None
    extract_audio_only: bool = False
    generate_proxy: bool = False
