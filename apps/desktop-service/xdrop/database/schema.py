CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS downloads (
    id TEXT PRIMARY KEY,
    source_url TEXT NOT NULL,
    platform TEXT NOT NULL,
    title TEXT NOT NULL,
    author TEXT,
    media_type TEXT NOT NULL,
    format TEXT NOT NULL,
    quality_label TEXT NOT NULL,
    asset_id TEXT,
    status TEXT NOT NULL, -- queued, downloading, processing, importing, completed, failed, cancelled, paused
    progress REAL DEFAULT 0,
    speed TEXT,
    eta TEXT,
    downloaded_bytes INTEGER DEFAULT 0,
    total_bytes INTEGER,
    output_file_path TEXT,
    thumbnail_path TEXT,
    error_message TEXT,
    resolve_imported INTEGER DEFAULT 0,
    resolve_clip_name TEXT,
    premiere_imported INTEGER DEFAULT 0,
    premiere_bin TEXT,
    aftereffects_imported INTEGER DEFAULT 0,
    aftereffects_bin TEXT,
    target_editor TEXT,
    auto_import INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    download_id TEXT,
    source_url TEXT NOT NULL,
    platform TEXT NOT NULL,
    title TEXT NOT NULL,
    author TEXT,
    media_type TEXT NOT NULL,
    format TEXT NOT NULL,
    resolution TEXT,
    duration REAL,
    file_size_bytes INTEGER DEFAULT 0,
    file_path TEXT NOT NULL UNIQUE,
    thumbnail_path TEXT,
    resolve_imported INTEGER DEFAULT 0,
    premiere_imported INTEGER DEFAULT 0,
    aftereffects_imported INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(download_id) REFERENCES downloads(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS platform_sources (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL UNIQUE,
    platform_name TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    rate_limit_rpm INTEGER DEFAULT 60
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    resolve_project_id TEXT,
    custom_assets_dir TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS download_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    download_id TEXT NOT NULL,
    event TEXT NOT NULL,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(download_id) REFERENCES downloads(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status);
CREATE INDEX IF NOT EXISTS idx_assets_platform ON assets(platform);
CREATE INDEX IF NOT EXISTS idx_assets_media_type ON assets(media_type);
CREATE INDEX IF NOT EXISTS idx_assets_created_at ON assets(created_at DESC);
"""
