"""
Сигналы для взаимодействия core-логики загрузки с GUI (PyQt).

Используются UploadWorker и MainWindow для обмена событиями
о состоянии очереди, задач и прогрессе загрузки.
"""

from PyQt5.QtCore import QObject, pyqtSignal


class UploadSignals(QObject):
    """
    Набор сигналов загрузки.
    Все сигналы испускаются из worker-потока
    и принимаются в GUI-потоке.
    """

    # 🔹 Очередь
    queue_started = pyqtSignal()
    queue_finished = pyqtSignal()
    queue_empty = pyqtSignal()

    # 🔹 Задача
    task_added = pyqtSignal(object)              # UploadTask
    task_started = pyqtSignal(object)            # UploadTask
    task_finished = pyqtSignal(object)           # UploadTask
    task_cancelled = pyqtSignal(object)          # UploadTask
    task_error = pyqtSignal(object, str)         # UploadTask, error message

    # 🔹 Прогресс
    task_progress = pyqtSignal(
        object,     # UploadTask
        int,        # bytes_uploaded
        int         # total_bytes
    )

    # 🔹 Служебные / лог
    log_message = pyqtSignal(str)