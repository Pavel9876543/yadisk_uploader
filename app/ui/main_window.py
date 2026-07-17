from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QMessageBox, QProgressBar
)
from PyQt5.QtCore import QThread
from pathlib import Path
from datetime import datetime
from pathlib import PurePosixPath

from services.config_service import ConfigService
from services.path_validator import PathValidator
from services.yadisk_path_builder import build_yadisk_path

from core.upload_queue import UploadQueue
from core.upload_worker import UploadWorker
from core.upload_task import UploadTask
from core.upload_signals import UploadSignals

from utils.category_labels import get_category_label

from .help_dialog import HelpDialog


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
        self.resize(800, 450)

        # ─── СЕРВИСЫ ───────────────────────────────────────────────
        self.config_service = ConfigService()
        self.validator = PathValidator()

        # ─── СОСТОЯНИЕ ─────────────────────────────────────────────
        self.upload_in_progress = False
        self.app_start_time = datetime.now()

        # ─── ДАННЫЕ ────────────────────────────────────────────────
        self.local_inputs = {}
        self.yadisk_inputs = {}
        self.final_yadisk_paths = {}

        # ─── КОНФИГ (ОДИН РАЗ) ─────────────────────────────────────
        self.config = self.config_service.load()

        # ─── UI ────────────────────────────────────────────────────
        self._init_ui()
        self._init_final_yadisk_paths()
        self._load_paths_from_config()

        # ─── ЗАГРУЗКА ──────────────────────────────────────────────
        self.upload_queue = UploadQueue()
        self.upload_signals = UploadSignals()

        self.upload_thread = QThread(self)
        self.upload_worker = UploadWorker(
            queue=self.upload_queue,
            signals=self.upload_signals
        )
        self.upload_worker.moveToThread(self.upload_thread)

        self.upload_thread.started.connect(self.upload_worker.run)

        self.upload_signals.task_started.connect(self.on_task_started)
        self.upload_signals.task_progress.connect(self.on_task_progress)
        self.upload_signals.task_finished.connect(self.on_task_finished)
        self.upload_signals.task_error.connect(self.on_task_error)
        self.upload_signals.task_cancelled.connect(self.on_task_cancelled)
        self.upload_signals.queue_empty.connect(self.on_queue_empty)

        self.upload_thread.start()

    # ==================================================================
    # UI
    # ==================================================================

    def _init_ui(self):
        layout = QVBoxLayout()

        for key, title in CATEGORIES:
            layout.addWidget(QLabel(f"<b>{title}</b>"))

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

        # Кнопка сохранения
        btn_save = QPushButton("Сохранить пути")
        btn_save.clicked.connect(self._save_paths)
        layout.addWidget(btn_save)

        btn_save = QPushButton("Справка")
        btn_save.clicked.connect(self._show_help)
        layout.addWidget(btn_save)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Ожидание загрузки…")
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    # ==================================================================
    # Пути
    # ==================================================================

    def _init_final_yadisk_paths(self):
        """
        Формирует итоговые пути Яндекс.Диска (с датой)
        ОДИН РАЗ при запуске приложения.
        """
        yadisk_paths = self.config.get("yadisk_paths", {})

        for category, base_path in yadisk_paths.items():
            if not base_path or not isinstance(base_path, str):
                continue

            self.final_yadisk_paths[category] = build_yadisk_path(
                base_path=base_path,
                category=category,
                now=self.app_start_time
            )

    def _load_paths_from_config(self):
        """
        Заполняет поля при запуске.
        """
        # Локальные пути
        for category, path in self.config.get("local_paths", {}).items():
            if category in self.local_inputs:
                self.local_inputs[category].setText(path or "")

        # Пути Яндекс.Диска — УЖЕ С ДАТОЙ
        for category, final_path in self.final_yadisk_paths.items():
            if category in self.yadisk_inputs:
                self.yadisk_inputs[category].setText(final_path)

    def _save_paths(self):
        """
        Сохраняет пути в config.json.

        - локальные пути — полностью
        - пути Яндекс.Диска — ТОЛЬКО базовые (2 папки)
        """

        local_paths = {
            k: self.local_inputs[k].text().strip()
            for k in self.local_inputs
        }

        yadisk_paths = {}
        for k in self.yadisk_inputs:
            full_path = self.yadisk_inputs[k].text().strip()
            base_path = self._extract_base_yadisk_path(full_path)
            yadisk_paths[k] = base_path

        data = {
            "local_paths": local_paths,
            "yadisk_paths": yadisk_paths,
        }

        self.config_service.save(data)

        QMessageBox.information(
            self,
            "Успех",
            "Локальные пути сохранены.\n"
            "Базовые пути Яндекс.Диска обновлены."
        )

    def _show_help(self):
        """
        Показывает окно со справкой.
        """
        dialog = HelpDialog(self)
        dialog.exec_()

    def _extract_base_yadisk_path(self, full_path: str) -> str:
        """
        Из полного пути Яндекс.Диска оставляет
        только первые две папки после корня.

        /a/b/c/d -> /a/b
        """
        if not full_path:
            return ""

        # Нормализуем как POSIX
        path = PurePosixPath(full_path)

        parts = path.parts  # ('/', 'Медиатека', 'Богослужения', ...)

        # Нужно минимум: / + 2 папки
        if len(parts) < 3:
            return full_path

        return str(PurePosixPath(parts[0], parts[1], parts[2]))

    # ==================================================================
    # Загрузка
    # ==================================================================

    def _upload_clicked(self, category: str):
        """
        Обработчик кнопки «Отправить».

        Локальный путь:
        - берётся ТОЛЬКО из поля GUI
        - из config.json НЕ используется НИКОГДА
        """

        # 🔹 1. ЛОКАЛЬНЫЙ ПУТЬ — ТОЛЬКО ИЗ ПОЛЯ
        local_path = self.local_inputs[category].text().strip()

        ok, error_message = PathValidator.validate_local_directory(local_path)
        if not ok:
            QMessageBox.critical(
                self,
                "Ошибка",
                error_message
            )
            return

        # 🔹 2. ПУТЬ НА ЯНДЕКС.ДИСКЕ (поле)
        yadisk_path = self.yadisk_inputs[category].text().strip()

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

    # ==================================================================
    # Сигналы
    # ==================================================================

    def on_task_started(self, task):
        self.upload_in_progress = True
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(100)
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
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_bar.setFormat("Загрузка завершена")

        QMessageBox.information(
            self,
            "Готово",
            f"Загрузка категории «{get_category_label(task.category)}» успешно завершена."
        )

    def on_task_error(self, task, message):
        self.progress_bar.setFormat("Ошибка загрузки")

        QMessageBox.critical(
            self,
            "Ошибка загрузки",
            f"Категория: {get_category_label(task.category)}\n\n{message}"
        )

    def on_task_cancelled(self, task):
        self.progress_bar.setFormat("Загрузка прервана")

    def on_queue_empty(self):
        self.upload_in_progress = False

    # ==================================================================
    # Закрытие
    # ==================================================================

    def closeEvent(self, event):
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

        self._shutdown_upload_system()
        event.accept()

    def _shutdown_upload_system(self):
        if self.upload_worker:
            self.upload_worker.stop()
        self.upload_queue.clear()
        if self.upload_thread:
            self.upload_thread.quit()
            self.upload_thread.wait(3000)

    # ==================================================================
    # Вспомогательные
    # ==================================================================

    def _select_local_path(self, key):
        path = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if path:
            self.local_inputs[key].setText(path)
