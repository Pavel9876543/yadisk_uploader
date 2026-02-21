"""
Сигналы загрузки для связи core-логики с GUI.
"""

from PyQt5.QtCore import QObject, pyqtSignal


class UploadSignals(QObject):
    """
    Набор сигналов, используемых диспетчером загрузки.
    """
    task_started = pyqtSignal(object)
    task_finished = pyqtSignal(object)
    task_error = pyqtSignal(object, str)
    queue_empty = pyqtSignal()