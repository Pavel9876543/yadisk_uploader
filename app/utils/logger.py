"""
Централизованный логгер приложения.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger("yadisk_uploader")
logger.setLevel(logging.DEBUG)
logger.propagate = False

formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s | %(name)s | %(message)s"
)

if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    try:
        log_dir = Path.home() / ".local" / "state" / "yadisk_uploader"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / "app.log",
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        logger.exception("Не удалось настроить файловый лог")
