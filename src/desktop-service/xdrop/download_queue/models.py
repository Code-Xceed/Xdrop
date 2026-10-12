from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, model_validator


class CreateDownloadRequest(BaseModel):
    source_url: str = ""
    url: Optional[str] = None
    asset_id: str = "best_video"
    format: str = "mp4"
    quality_label: str = "Best"
    quality: Optional[str] = None
    media_type: str = "video"  # video, audio, image
    title: Optional[str] = None
    author: Optional[str] = None
    target_media_pool_bin: Optional[str] = None
    auto_import_to_resolve: Optional[bool] = None
    target_editor: Optional[str] = None  # 'auto', 'resolve', 'premiere', 'aftereffects', 'none'
    editorTarget: Optional[str] = None
    auto_import_to_premiere: Optional[bool] = None
    target_premiere_bin: Optional[str] = None
    auto_import_to_aftereffects: Optional[bool] = None
    target_aftereffects_bin: Optional[str] = None
    auto_import_to_audition: Optional[bool] = None
    target_audition_bin: Optional[str] = None
    transcode_video_format: Optional[str] = None  # 'mp4', 'mov', None
    transcode_audio_format: Optional[str] = None  # 'wav', 'mp3', None
    extract_audio_only: bool = False
    generate_proxy: bool = False

    insert_timeline: Optional[bool] = False

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Fallback for 'url' -> 'source_url'
            if not data.get("source_url") and data.get("url"):
                data["source_url"] = data["url"]
            # Fallback for 'editorTarget' -> 'target_editor'
            if not data.get("target_editor") and data.get("editorTarget"):
                data["target_editor"] = data["editorTarget"]

            # Fallback for target_bin (from Lua / NLE scripts) -> target_media_pool_bin
            if data.get("target_bin"):
                tb = data["target_bin"]
                if not data.get("target_media_pool_bin"):
                    data["target_media_pool_bin"] = tb
                if not data.get("target_premiere_bin"):
                    data["target_premiere_bin"] = tb
                if not data.get("target_aftereffects_bin"):
                    data["target_aftereffects_bin"] = tb
                if not data.get("target_audition_bin"):
                    data["target_audition_bin"] = tb

            # Fallback for audio_only / target_format == 'audio'
            if data.get("audio_only") or data.get("target_format") == "audio":
                data["extract_audio_only"] = True
                data["media_type"] = "audio"

            # Fallback for 'max_resolution' / 'quality' -> 'quality_label' & 'asset_id'
            res_val = data.get("max_resolution") or data.get("quality") or data.get("quality_label")
            if res_val:
                q = str(res_val).lower().strip()
                if "wav" in q:
                    data["quality_label"] = "Broadcast WAV (48kHz)"
                    data["format"] = "wav"
                    data["media_type"] = "audio"
                    data["asset_id"] = "audio_wav"
                    data["extract_audio_only"] = True
                    data["transcode_audio_format"] = "wav"
                elif "mp3" in q:
                    data["quality_label"] = "MP3 (320kbps)"
                    data["format"] = "mp3"
                    data["media_type"] = "audio"
                    data["asset_id"] = "audio_mp3"
                    data["extract_audio_only"] = True
                    data["transcode_audio_format"] = "mp3"
                elif "aac" in q or "m4a" in q:
                    data["quality_label"] = "AAC / M4A (320kbps)"
                    data["format"] = "m4a"
                    data["media_type"] = "audio"
                    data["asset_id"] = "audio_aac"
                    data["extract_audio_only"] = True
                elif "prores" in q:
                    data["quality_label"] = "ProRes 422 (MOV Master)"
                    data["format"] = "mov"
                    data["asset_id"] = "video_prores_mov"
                    data["transcode_video_format"] = "mov"
                elif "1080" in q:
                    data["quality_label"] = "1080p Full HD"
                    data["asset_id"] = "video_1080p"
                    data["format"] = data.get("format") or "mp4"
                elif "720" in q:
                    data["quality_label"] = "720p HD"
                    data["asset_id"] = "video_720p"
                    data["format"] = data.get("format") or "mp4"
                elif "4k" in q or "2160" in q:
                    data["quality_label"] = "4K Ultra HD"
                    data["asset_id"] = "video_2160p"
                    data["format"] = data.get("format") or "mp4"
                elif "480" in q:
                    data["quality_label"] = "480p SD"
                    data["asset_id"] = "video_480p"
                    data["format"] = data.get("format") or "mp4"
                elif "best" in q:
                    data["quality_label"] = "Best Available Video (MP4)"
                    data["asset_id"] = "best_video"
                    data["format"] = data.get("format") or "mp4"
        return data
