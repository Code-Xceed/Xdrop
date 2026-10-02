import logging
import os
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Log directory resolution: local project directory or %LOCALAPPDATA%/Xdrop/logs
def get_log_dir() -> Path:
    if os.getenv("XDROP_DATA_DIR"):
        base_dir = Path(os.getenv("XDROP_DATA_DIR"))
    elif os.getenv("RESOLVEFETCH_DATA_DIR"):
        base_dir = Path(os.getenv("RESOLVEFETCH_DATA_DIR"))
    else:
        appdata = os.getenv("LOCALAPPDATA")
        if appdata:
            base_dir = Path(appdata) / "Xdrop"
        else:
            base_dir = Path.home() / ".xdrop"
    
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir

LOG_DIR = get_log_dir()

def setup_logger(name: str, log_file: str, level=logging.INFO) -> logging.Logger:
    """Creates a configured rotating file logger and stdout handler."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers if already configured
    if logger.handlers:
        return logger

    file_path = LOG_DIR / log_file
    formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
    )

    # Rotating file handler (5 MB each, up to 5 backups)
    file_handler = RotatingFileHandler(
        file_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger

# Pre-configured loggers for different subsystems
app_logger = setup_logger("app", "app.log")
downloads_logger = setup_logger("downloads", "downloads.log")
errors_logger = setup_logger("errors", "errors.log", level=logging.ERROR)
resolve_logger = setup_logger("resolve", "resolve.log")
