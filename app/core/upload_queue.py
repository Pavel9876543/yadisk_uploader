"""
Модуль реализует очередь задач загрузки.
Отвечает за порядок выполнения и управление задачами.
"""

from collections import deque
from threading import Lock
from .upload_task import UploadTask


class UploadQueue:
    """
    Очередь задач загрузки.
    Потокобезопасна.
    """

    def __init__(self):
        """Инициализация очереди задач."""
        self._queue = deque()
        self._lock = Lock()

    def add_task(self, task: UploadTask) -> None:
        """
        Добавляет задачу в очередь.
        """
        with self._lock:
            self._queue.append(task)

    def get_next_task(self) -> UploadTask | None:
        """
        Возвращает следующую задачу из очереди.
        Если очередь пуста — возвращает None.
        """
        with self._lock:
            if not self._queue:
                return None
            return self._queue.popleft()

    def is_empty(self) -> bool:
        """
        Проверяет, пуста ли очередь.
        """
        with self._lock:
            return len(self._queue) == 0

    def clear(self) -> None:
        """
        Очищает очередь задач.
        """
        with self._lock:
            self._queue.clear()

    def size(self) -> int:
        """
        Возвращает количество задач в очереди.
        """
        with self._lock:
            return len(self._queue)