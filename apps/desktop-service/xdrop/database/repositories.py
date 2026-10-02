import json
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from xdrop.database.connection import get_db_connection
from xdrop.logger import app_logger, errors_logger

def get_settings_from_db() -> Dict[str, Any]:
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()
        settings: Dict[str, Any] = {}
        for row in rows:
            try:
                settings[row["key"]] = json.loads(row["value"])
            except Exception:
                settings[row["key"]] = row["value"]
        return settings

def save_settings_to_db(settings_dict: Dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        for k, v in settings_dict.items():
            json_val = json.dumps(v)
            conn.execute(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """,
                (k, json_val, now),
            )

def insert_download(job_data: Dict[str, Any]) -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO downloads (
                id, source_url, platform, title, author, media_type, format,
                quality_label, asset_id, status, progress, speed, eta, downloaded_bytes,
                total_bytes, output_file_path, thumbnail_path, error_message,
                resolve_imported, resolve_clip_name, premiere_imported, premiere_bin,
                aftereffects_imported, aftereffects_bin,
                created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_data["id"],
                job_data["source_url"],
                job_data["platform"],
                job_data["title"],
                job_data.get("author"),
                job_data["media_type"],
                job_data["format"],
                job_data["quality_label"],
                job_data.get("asset_id"),
                job_data.get("status", "queued"),
                job_data.get("progress", 0.0),
                job_data.get("speed"),
                job_data.get("eta"),
                job_data.get("downloaded_bytes", 0),
                job_data.get("total_bytes"),
                job_data.get("output_file_path"),
                job_data.get("thumbnail_path"),
                job_data.get("error_message"),
                1 if job_data.get("resolve_imported") else 0,
                job_data.get("resolve_clip_name"),
                1 if job_data.get("premiere_imported") else 0,
                job_data.get("premiere_bin"),
                1 if job_data.get("aftereffects_imported") else 0,
                job_data.get("aftereffects_bin"),
                job_data.get("created_at", datetime.now(timezone.utc).isoformat()),
                job_data.get("completed_at"),
            ),
        )

def update_download_progress(
    job_id: str,
    status: str,
    progress: float,
    downloaded_bytes: int,
    total_bytes: Optional[int] = None,
    speed: Optional[str] = None,
    eta: Optional[str] = None,
    output_file_path: Optional[str] = None,
    thumbnail_path: Optional[str] = None,
    error_message: Optional[str] = None,
    resolve_imported: Optional[bool] = None,
    resolve_clip_name: Optional[str] = None,
    premiere_imported: Optional[bool] = None,
    premiere_bin: Optional[str] = None,
    aftereffects_imported: Optional[bool] = None,
    aftereffects_bin: Optional[str] = None,
) -> None:
    with get_db_connection() as conn:
        updates = ["status = ?", "progress = ?", "downloaded_bytes = ?"]
        params: List[Any] = [status, progress, downloaded_bytes]

        if total_bytes is not None:
            updates.append("total_bytes = ?")
            params.append(total_bytes)
        if speed is not None:
            updates.append("speed = ?")
            params.append(speed)
        if eta is not None:
            updates.append("eta = ?")
            params.append(eta)
        if output_file_path is not None:
            updates.append("output_file_path = ?")
            params.append(output_file_path)
        if thumbnail_path is not None:
            updates.append("thumbnail_path = ?")
            params.append(thumbnail_path)
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        if resolve_imported is not None:
            updates.append("resolve_imported = ?")
            params.append(1 if resolve_imported else 0)
        if resolve_clip_name is not None:
            updates.append("resolve_clip_name = ?")
            params.append(resolve_clip_name)
        if premiere_imported is not None:
            updates.append("premiere_imported = ?")
            params.append(1 if premiere_imported else 0)
        if premiere_bin is not None:
            updates.append("premiere_bin = ?")
            params.append(premiere_bin)
        if aftereffects_imported is not None:
            updates.append("aftereffects_imported = ?")
            params.append(1 if aftereffects_imported else 0)
        if aftereffects_bin is not None:
            updates.append("aftereffects_bin = ?")
            params.append(aftereffects_bin)
        if status in ("completed", "failed", "cancelled"):
            updates.append("completed_at = ?")
            params.append(datetime.now(timezone.utc).isoformat())

        params.append(job_id)
        sql = f"UPDATE downloads SET {', '.join(updates)} WHERE id = ?"
        conn.execute(sql, params)

def update_download_status(job_id: str, status: str, error_message: Optional[str] = None) -> None:
    with get_db_connection() as conn:
        now = datetime.now(timezone.utc).isoformat() if status in ("completed", "failed", "cancelled") else None
        err = error_message if status in ("failed", "cancelled") else None
        conn.execute(
            """
            UPDATE downloads
            SET status = ?, error_message = ?, completed_at = COALESCE(?, completed_at)
            WHERE id = ?
            """,
            (status, err, now, job_id),
        )

def _format_download_row(r: Any) -> Dict[str, Any]:
    if not r:
        return {}
    d = dict(r)
    resolve_imp = bool(d.get("resolve_imported", 0))
    prem_imp = bool(d.get("premiere_imported", 0))
    ae_imp = bool(d.get("aftereffects_imported", 0))
    d["resolve_imported"] = resolve_imp
    d["premiere_imported"] = prem_imp
    d["aftereffects_imported"] = ae_imp
    d["resolveImported"] = resolve_imp
    d["premiereImported"] = prem_imp
    d["aftereffectsImported"] = ae_imp

    d["sourceUrl"] = d.get("source_url") or ""
    d["mediaType"] = d.get("media_type") or "video"
    d["qualityLabel"] = d.get("quality_label") or ""
    d["assetId"] = d.get("asset_id")
    d["downloadedBytes"] = d.get("downloaded_bytes", 0)
    d["totalBytes"] = d.get("total_bytes")
    d["outputFilePath"] = d.get("output_file_path")
    d["thumbnailPath"] = d.get("thumbnail_path")
    d["errorMessage"] = d.get("error_message")
    d["resolveClipName"] = d.get("resolve_clip_name")
    d["premiereBin"] = d.get("premiere_bin")
    d["aftereffectsBin"] = d.get("aftereffects_bin")
    d["targetEditor"] = d.get("target_editor")
    d["createdAt"] = d.get("created_at") or ""
    d["completedAt"] = d.get("completed_at")
    d["progress"] = float(d.get("progress", 0.0) or 0.0)
    return d

def get_download_by_id(job_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM downloads WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return None
        return _format_download_row(row)

def get_all_downloads() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM downloads ORDER BY created_at DESC").fetchall()
        return [_format_download_row(r) for r in rows]

def delete_download(job_id: str) -> None:
    with get_db_connection() as conn:
        conn.execute("DELETE FROM downloads WHERE id = ?", (job_id,))

def insert_library_item(item: Dict[str, Any]) -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO assets (
                id, download_id, source_url, platform, title, author,
                media_type, format, resolution, duration, file_size_bytes,
                file_path, thumbnail_path, resolve_imported, premiere_imported, aftereffects_imported, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                title = excluded.title,
                resolve_imported = excluded.resolve_imported,
                premiere_imported = excluded.premiere_imported,
                aftereffects_imported = excluded.aftereffects_imported
            """,
            (
                item["id"],
                item.get("download_id"),
                item["source_url"],
                item["platform"],
                item["title"],
                item.get("author"),
                item["media_type"],
                item["format"],
                item.get("resolution"),
                item.get("duration"),
                item.get("file_size_bytes", 0),
                item["file_path"],
                item.get("thumbnail_path"),
                1 if item.get("resolve_imported") else 0,
                1 if item.get("premiere_imported") else 0,
                1 if item.get("aftereffects_imported") else 0,
                item.get("created_at", datetime.now(timezone.utc).isoformat()),
            ),
        )

def get_library_items(
    search: Optional[str] = None,
    platform: Optional[str] = None,
    media_type: Optional[str] = None,
    resolve_imported: Optional[bool] = None,
    premiere_imported: Optional[bool] = None,
    aftereffects_imported: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        conditions = []
        params: List[Any] = []

        if search:
            conditions.append("(title LIKE ? OR file_path LIKE ? OR author LIKE ?)")
            q = f"%{search}%"
            params.extend([q, q, q])
        if platform:
            conditions.append("platform = ?")
            params.append(platform)
        if media_type:
            conditions.append("media_type = ?")
            params.append(media_type)
        if resolve_imported is not None:
            conditions.append("resolve_imported = ?")
            params.append(1 if resolve_imported else 0)
        if premiere_imported is not None:
            conditions.append("premiere_imported = ?")
            params.append(1 if premiere_imported else 0)
        if aftereffects_imported is not None:
            conditions.append("aftereffects_imported = ?")
            params.append(1 if aftereffects_imported else 0)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT * FROM assets
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            resolve_imp = bool(d.get("resolve_imported", 0))
            prem_imp = bool(d.get("premiere_imported", 0))
            ae_imp = bool(d.get("aftereffects_imported", 0))
            d["resolve_imported"] = resolve_imp
            d["premiere_imported"] = prem_imp
            d["aftereffects_imported"] = ae_imp
            d["resolveImported"] = resolve_imp
            d["premiereImported"] = prem_imp
            d["aftereffectsImported"] = ae_imp

            d["sourceUrl"] = d.get("source_url") or ""
            d["mediaType"] = d.get("media_type") or "video"
            d["fileSizeBytes"] = d.get("file_size_bytes", 0)
            d["filePath"] = d.get("file_path") or ""
            d["thumbnailPath"] = d.get("thumbnail_path")
            d["createdAt"] = d.get("created_at") or ""
            result.append(d)
        return result

def delete_library_item(item_id: str) -> Optional[str]:
    """Deletes an asset record from DB and returns its file path."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT file_path FROM assets WHERE id = ?", (item_id,)).fetchone()
        if row:
            conn.execute("DELETE FROM assets WHERE id = ?", (item_id,))
            return row["file_path"]
        return None
