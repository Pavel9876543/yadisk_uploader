"""
Модуль описывает сущность задачи загрузки.
Используется для передачи данных между GUI, очередью и загрузчиком.
"""

from dataclasses import dataclass
from pathlib import Path
from enum import Enum


class TaskStatus(Enum):
    """Статусы задачи загрузки."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class UploadTask:
    """
    Модель задачи загрузки одной папки.
    """
    local_path: Path
    yadisk_path: str
    category: str
    status: TaskStatus = TaskStatus.PENDING
    error_message: str | None = None