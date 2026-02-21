from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QMessageBox
)
from services.config_service import ConfigService
from services.path_validator import PathValidator
from PyQt5.QtCore import QThread
from core.upload_queue import UploadQueue
from core.upload_worker import UploadWorker
from pathlib import Path
from core.upload_task import UploadTask
from PyQt5.QtWidgets import QProgressBar
from utils.category_labels import get_category_label


CATEGORIES = [
    ("processed_photos", "Обработанные фото"),
    ("raw_photos", "Исходные фото"),
    ("processed_video", "Обработанные видео"),
    ("raw_video", "Исходные видео"),
]


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yandex Disk Uploader")
        self.resize(800, 400)

        self.config_service = ConfigService()
        self.validator = PathValidator()

        self.local_inputs = {}
        self.yadisk_inputs = {}

        self._init_ui()
        self._load_config()

        self.upload_queue = UploadQueue()

        self.upload_thread = QThread(self)
        self.upload_worker = UploadWorker(self.upload_queue)
        self.upload_worker.moveToThread(self.upload_thread)

        # прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Ожидание загрузки…")
        self.layout().addWidget(self.progress_bar)

        self.upload_in_progress = False

        # сигналы
        self._init_upload_system()

        self.upload_thread.start()

    def _init_upload_system(self):
        # 1️⃣ Очередь
        self.upload_queue = UploadQueue()

        # 2️⃣ Поток
        self.upload_thread = QThread(self)

        # 3️⃣ Worker
        self.upload_worker = UploadWorker(self.upload_queue)
        self.upload_worker.moveToThread(self.upload_thread)

        # 4️⃣ Запуск worker
        self.upload_thread.started.connect(self.upload_worker.run)

        # 5️⃣ ПОДКЛЮЧЕНИЕ СИГНАЛОВ (ВОТ ЗДЕСЬ)
        signals = self.upload_worker.signals

        signals.task_started.connect(self.on_task_started)
        signals.task_progress.connect(self.on_task_progress)
        signals.task_finished.connect(self.on_task_finished)
        signals.task_error.connect(self.on_task_error)

        # (опционально)
        # signals.queue_empty.connect(self.on_queue_empty)

        # 6️⃣ Запуск потока
        self.upload_thread.start()

    def _init_ui(self):
        layout = QVBoxLayout()

        for key, title in CATEGORIES:
            layout.addWidget(QLabel(title))

            # Локальный путь
            local_layout = QHBoxLayout()
            local_input = QLineEdit()
            btn_select = QPushButton("Выбрать")
            btn_upload = QPushButton("Отправить")

            btn_select.clicked.connect(
                lambda _, k=key: self._select_local_path(k)
            )
            btn_upload.clicked.connect(
                lambda _, k=key: self._upload_clicked(k)
            )

            local_layout.addWidget(QLabel("Локальный путь:"))
            local_layout.addWidget(local_input)
            local_layout.addWidget(btn_select)
            local_layout.addWidget(btn_upload)

            # Путь Яндекс.Диска
            yadisk_layout = QHBoxLayout()
            yadisk_input = QLineEdit()
            yadisk_layout.addWidget(QLabel("Путь на Яндекс.Диске:"))
            yadisk_layout.addWidget(yadisk_input)

            self.local_inputs[key] = local_input
            self.yadisk_inputs[key] = yadisk_input

            layout.addLayout(local_layout)
            layout.addLayout(yadisk_layout)

        btn_save = QPushButton("Сохранить пути")
        btn_save.clicked.connect(self._save_paths)
        layout.addWidget(btn_save)

        self.setLayout(layout)

    def closeEvent(self, event):
        """
        Корректное завершение приложения.
        """
        if self.upload_in_progress:
            reply = QMessageBox.question(
                self,
                "Загрузка выполняется",
                "Загрузка файлов ещё не завершена.\n"
                "Прервать загрузку и выйти?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.No:
                event.ignore()
                return

            # Пользователь согласился — останавливаем загрузку
            self._shutdown_upload_system()

        else:
            self._shutdown_upload_system()

        event.accept()

    def _select_local_path(self, key):
        path = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if path:
            self.local_inputs[key].setText(path)

    def _load_config(self):
        data = self.config_service.load()
        for key in self.local_inputs:
            self.local_inputs[key].setText(data["local_paths"].get(key, ""))
            self.yadisk_inputs[key].setText(data["yadisk_paths"].get(key, ""))

    def _save_paths(self):
        data = {
            "local_paths": {k: self.local_inputs[k].text() for k in self.local_inputs},
            "yadisk_paths": {k: self.yadisk_inputs[k].text() for k in self.yadisk_inputs},
        }
        self.config_service.save(data)
        QMessageBox.information(self, "Успех", "Пути сохранены")

    def _upload_clicked(self, category: str):
        """
        Обработчик кнопки «Отправить».

        Локальный путь:
        - берётся ТОЛЬКО из поля GUI
        - из config.json НЕ используется НИКОГДА
        """

        # 🔹 1. ЛОКАЛЬНЫЙ ПУТЬ — ТОЛЬКО ИЗ ПОЛЯ
        local_path = self.local_inputs[category].text()

        ok, error_message = PathValidator.validate_local_directory(local_path)
        if not ok:
            QMessageBox.critical(
                self,
                "Ошибка",
                error_message
            )
            return

        # 🔹 2. ПУТЬ НА ЯНДЕКС.ДИСКЕ (поле → config)
        yadisk_path_ui = self.yadisk_inputs[category].text().strip()

        config = self.config_service.load()
        yadisk_path_config = config["yadisk_paths"].get(category, "").strip()

        yadisk_path = yadisk_path_ui or yadisk_path_config

        if not yadisk_path:
            QMessageBox.critical(
                self,
                "Ошибка",
                "Не указан путь для загрузки на Яндекс.Диск."
            )
            return

        # 🔹 3. СОЗДАЁМ ЗАДАЧУ
        task = UploadTask(
            local_path=Path(local_path),
            yadisk_path=yadisk_path,
            category=category
        )

        upload_already_running = self.upload_in_progress

        self.upload_queue.add_task(task)
        self.upload_signals.task_added.emit(task)

        if upload_already_running:
            QMessageBox.information(
                self,
                "Задача добавлена в очередь",
                "Загрузка выполняется.\n"
                "Выбранная папка добавлена в очередь."
            )

    def on_task_started(self, task):
        self.upload_in_progress = True
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(
            f"Загрузка: {get_category_label(task.category)} (%p%)"
        )

    def on_task_progress(self, task, uploaded, total):
        if total == 0:
            return

        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(uploaded)

        percent = int(uploaded / total * 100)
        self.progress_bar.setFormat(
            f"{get_category_label(task.category)}: {percent}% ({uploaded // 1024} / {total // 1024} KB)"
        )

    def on_task_finished(self, task):
        self.upload_in_progress = False
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_bar.setFormat("Загрузка завершена")

        QMessageBox.information(
            self,
            "Готово",
            f"Загрузка категории «{get_category_label(task.category)}» успешно завершена."
        )

    def on_task_error(self, task, message):
        self.upload_in_progress = False
        self.progress_bar.setFormat("Ошибка загрузки")

        QMessageBox.critical(
            self,
            "Ошибка загрузки",
            f"Категория: {get_category_label(task.category)}\n\n{message}"
        )

    def on_task_cancelled(self, task):
        self.upload_in_progress = False

    def _shutdown_upload_system(self):
        """
        Быстрое завершение приложения без блокировки UI.
        """
        if self.upload_worker:
            self.upload_worker.stop()

        if self.upload_thread:
            self.upload_thread.quit()
            # ❗ НЕ wait()