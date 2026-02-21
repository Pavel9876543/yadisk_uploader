"""
Диспетчер загрузки.
Управляет выполнением задач из очереди строго по одной.
"""

import threading
from time import sleep
from .upload_queue import UploadQueue
from .upload_task import UploadTask, TaskStatus


class UploadDispatcher:
    """
    Диспетчер задач загрузки.
    Выполняет задачи последовательно в отдельном потоке.
    """

    def __init__(self, queue: UploadQueue):
        """
        Инициализация диспетчера.
        """
        self.queue = queue
        self._worker_thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        """
        Запускает диспетчер, если он ещё не запущен.
        """
        if self._running:
            return

        self._running = True
        self._worker_thread = threading.Thread(
            target=self._run,
            daemon=True
        )
        self._worker_thread.start()

    def stop(self) -> None:
        """
        Останавливает диспетчер после текущей задачи.
        """
        self._running = False

    def _run(self) -> None:
        """
        Основной цикл обработки очереди.
        """
        while self._running:
            task = self.queue.get_next_task()

            if task is None:
                sleep(0.2)
                continue

            self._process_task(task)

    def _process_task(self, task: UploadTask) -> None:
        """
        Обрабатывает одну задачу загрузки.
        Пока используется заглушка.
        """
        try:
            task.status = TaskStatus.IN_PROGRESS
            print(f"[START] {task.category}: {task.local_path}")

            # ⏳ Заглушка вместо реальной загрузки
            sleep(1)

            task.status = TaskStatus.DONE
            print(f"[DONE] {task.category}")

        except Exception as exc:
            task.status = TaskStatus.ERROR
            task.error_message = str(exc)
            print(f"[ERROR] {task.error_message}")