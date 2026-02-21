"""
UploadWorker — связка между PyQt и диспетчером загрузки.
Работает в отдельном QThread.
"""

from PyQt5.QtCore import QObject, pyqtSlot
from time import sleep
from .upload_queue import UploadQueue
from .upload_task import UploadTask, TaskStatus
from .upload_signals import UploadSignals


class UploadWorker(QObject):
    """
    Worker для выполнения задач загрузки в отдельном потоке.
    """

    def __init__(self, queue: UploadQueue):
        super().__init__()
        self.queue = queue
        self.signals = UploadSignals()
        self._running = True

    @pyqtSlot()
    def run(self):
        """
        Основной цикл обработки очереди.
        """
        while self._running:
            task = self.queue.get_next_task()

            if task is None:
                self.signals.queue_empty.emit()
                sleep(0.2)
                continue

            self._process_task(task)

    def stop(self):
        """
        Останавливает worker.
        """
        self._running = False

    def _process_task(self, task: UploadTask):
        """
        Обрабатывает одну задачу.
        """
        try:
            task.status = TaskStatus.IN_PROGRESS
            self.signals.task_started.emit(task)

            # 🔧 Заглушка загрузки
            sleep(1)

            task.status = TaskStatus.DONE
            self.signals.task_finished.emit(task)

        except Exception as exc:
            task.status = TaskStatus.ERROR
            task.error_message = str(exc)
            self.signals.task_error.emit(task, task.error_message)