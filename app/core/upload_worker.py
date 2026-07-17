"""
UploadWorker — связка между PyQt и диспетчером загрузки.
Работает в отдельном QThread.
"""

from PyQt5.QtCore import QObject, pyqtSlot
from time import sleep
from .upload_queue import UploadQueue
from .upload_task import UploadTask, TaskStatus
from .upload_signals import UploadSignals
from integrations.yadisk_client import YadiskClient, UploadCancelled
from utils.logger import logger
from utils.error_translator import translate_exception


class UploadWorker(QObject):
    """
    Worker для выполнения задач загрузки в отдельном потоке.
    """

    def __init__(self, queue: UploadQueue, signals):
        super().__init__()
        self.queue = queue
        self.signals = signals
        self._running = True
        self._cancel_requested = False

    def stop(self):
        """
        Запрашивает остановку worker.
        """
        self._running = False
        self._cancel_requested = True

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

    def _process_task(self, task):
        try:
            self._cancel_requested = False
            task.status = TaskStatus.IN_PROGRESS
            self.signals.task_started.emit(task)

            client = YadiskClient()

            def progress_callback(done, total):
                self.signals.task_progress.emit(task, done, total)

            client.upload_folder(
                local_folder=task.local_path,
                yadisk_folder=task.yadisk_path,
                on_progress=progress_callback,
                should_cancel=lambda: self._cancel_requested
            )

            task.status = TaskStatus.DONE
            self.signals.task_finished.emit(task)

        except UploadCancelled:
            task.status = TaskStatus.CANCELLED
            self.signals.task_cancelled.emit(task)

        except Exception as exc:
            task.status = TaskStatus.ERROR
            task.error_message = translate_exception(exc)

            logger.exception(
                "Ошибка при загрузке категории %s",
                task.category
            )

            self.signals.task_error.emit(task, task.error_message)
