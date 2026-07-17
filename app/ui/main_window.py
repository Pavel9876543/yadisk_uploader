from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QMessageBox, QProgressBar,
    QFrame, QGridLayout, QScrollArea, QSizePolicy, QStyle
)
from PyQt5.QtCore import QThread, Qt, QSize
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

CATEGORY_ACCENTS = {
    "processed_photos": "#2f8f83",
    "raw_photos": "#b28d2d",
    "processed_video": "#3662a3",
    "raw_video": "#c75c38",
}


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yandex Disk Uploader")
        self.resize(1040, 720)
        self.setMinimumSize(880, 620)

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
        self.upload_buttons = {}
        self.category_panels = {}
        self.category_status_labels = {}

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

        self.upload_thread.start()

    # ==================================================================
    # UI
    # ==================================================================

    def _init_ui(self):
        self._apply_styles()

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_categories_area(), 1)
        layout.addWidget(self._build_status_panel())

        self.setLayout(layout)

    def _build_header(self):
        header = QFrame()
        header.setObjectName("Header")

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 18, 20, 18)
        header_layout.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        title = QLabel("Yandex Disk Uploader")
        title.setObjectName("AppTitle")

        subtitle = QLabel(
            f"Дата загрузки: {self.app_start_time.strftime('%Y.%m.%d')}"
        )
        subtitle.setObjectName("MutedText")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header_layout.addLayout(title_box, 1)

        btn_save = QPushButton("Сохранить")
        btn_save.setObjectName("SecondaryButton")
        btn_save.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        btn_save.setIconSize(QSize(18, 18))
        btn_save.clicked.connect(self._save_paths)

        btn_help = QPushButton("Справка")
        btn_help.setObjectName("SecondaryButton")
        btn_help.setIcon(self.style().standardIcon(QStyle.SP_DialogHelpButton))
        btn_help.setIconSize(QSize(18, 18))
        btn_help.clicked.connect(self._show_help)

        header_layout.addWidget(btn_save)
        header_layout.addWidget(btn_help)

        return header

    def _build_categories_area(self):
        scroll = QScrollArea()
        scroll.setObjectName("CategoryScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content.setObjectName("CategoryContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        for key, title in CATEGORIES:
            content_layout.addWidget(self._build_category_panel(key, title))

        content_layout.addStretch(1)
        scroll.setWidget(content)

        return scroll

    def _build_category_panel(self, key: str, title: str):
        panel = QFrame()
        panel.setObjectName("CategoryPanel")
        panel.setProperty("state", "idle")
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        panel_layout = QHBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        accent = QFrame()
        accent.setObjectName("CategoryAccent")
        accent.setFixedWidth(5)
        accent.setStyleSheet(
            f"QFrame#CategoryAccent {{ background: {CATEGORY_ACCENTS[key]}; }}"
        )
        panel_layout.addWidget(accent)

        grid = QGridLayout()
        grid.setContentsMargins(18, 14, 18, 14)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("CategoryTitle")

        status_label = QLabel("Готово")
        status_label.setObjectName("StatusBadge")
        status_label.setProperty("state", "idle")
        status_label.setAlignment(Qt.AlignCenter)

        local_label = QLabel("Локальная папка")
        local_label.setObjectName("FieldLabel")
        local_input = QLineEdit()
        local_input.setPlaceholderText("Локальная папка")
        local_input.setMinimumHeight(38)

        btn_select = QPushButton("Выбрать")
        btn_select.setObjectName("SecondaryButton")
        btn_select.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        btn_select.setIconSize(QSize(18, 18))
        btn_select.clicked.connect(lambda _, k=key: self._select_local_path(k))

        yadisk_label = QLabel("Яндекс.Диск")
        yadisk_label.setObjectName("FieldLabel")
        yadisk_input = QLineEdit()
        yadisk_input.setPlaceholderText("Путь на Яндекс.Диске")
        yadisk_input.setMinimumHeight(38)

        btn_upload = QPushButton("Отправить")
        btn_upload.setObjectName("PrimaryButton")
        btn_upload.setMinimumHeight(86)
        btn_upload.setMinimumWidth(132)
        btn_upload.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        btn_upload.setIconSize(QSize(18, 18))
        btn_upload.clicked.connect(lambda _, k=key: self._upload_clicked(k))

        grid.addWidget(title_label, 0, 0, 1, 2)
        grid.addWidget(status_label, 0, 2, 1, 2, Qt.AlignRight)
        grid.addWidget(local_label, 1, 0)
        grid.addWidget(local_input, 1, 1, 1, 2)
        grid.addWidget(btn_select, 1, 3)
        grid.addWidget(yadisk_label, 2, 0)
        grid.addWidget(yadisk_input, 2, 1, 1, 3)
        grid.addWidget(btn_upload, 1, 4, 2, 1)
        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(2, 2)

        panel_layout.addLayout(grid, 1)

        self.local_inputs[key] = local_input
        self.yadisk_inputs[key] = yadisk_input
        self.upload_buttons[key] = btn_upload
        self.category_panels[key] = panel
        self.category_status_labels[key] = status_label

        return panel

    def _build_status_panel(self):
        status = QFrame()
        status.setObjectName("StatusPanel")

        layout = QVBoxLayout(status)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        top_line = QHBoxLayout()
        top_line.setSpacing(12)

        self.current_state_label = QLabel("Ожидание")
        self.current_state_label.setObjectName("CurrentState")

        self.current_detail_label = QLabel("Готов к загрузке")
        self.current_detail_label.setObjectName("MutedText")
        self.current_detail_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        top_line.addWidget(self.current_state_label)
        top_line.addWidget(self.current_detail_label, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("MainProgress")
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Ожидание загрузки…")

        layout.addLayout(top_line)
        layout.addWidget(self.progress_bar)

        return status

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background: #f5f6f3;
                color: #222831;
                font-family: "Segoe UI", "Arial", sans-serif;
                font-size: 14px;
                letter-spacing: 0;
            }

            QLabel {
                background: transparent;
            }

            QFrame#Header,
            QFrame#StatusPanel,
            QFrame#CategoryPanel {
                background: #ffffff;
                border: 1px solid #d9ddd4;
                border-radius: 8px;
            }

            QFrame#CategoryPanel[state="active"] {
                border-color: #2f8f83;
                background: #fbfefd;
            }

            QFrame#CategoryPanel[state="waiting"] {
                border-color: #b28d2d;
                background: #fffdf6;
            }

            QFrame#CategoryPanel[state="success"] {
                border-color: #7aa850;
                background: #fbfef8;
            }

            QFrame#CategoryPanel[state="error"] {
                border-color: #c75c38;
                background: #fffaf8;
            }

            QFrame#CategoryPanel[state="cancelled"] {
                border-color: #8b7b61;
                background: #fbfaf7;
            }

            QScrollArea#CategoryScroll,
            QWidget#CategoryContent {
                background: transparent;
                border: none;
            }

            QLabel#AppTitle {
                color: #1d252f;
                font-size: 24px;
                font-weight: 700;
            }

            QLabel#CategoryTitle {
                color: #1d252f;
                font-size: 16px;
                font-weight: 700;
            }

            QLabel#CurrentState {
                color: #1d252f;
                font-size: 16px;
                font-weight: 700;
            }

            QLabel#MutedText {
                color: #667065;
            }

            QLabel#FieldLabel {
                color: #56605a;
                font-size: 13px;
                font-weight: 600;
            }

            QLabel#StatusBadge {
                background: #eef1eb;
                color: #56605a;
                border: 1px solid #d9ddd4;
                border-radius: 8px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: 700;
            }

            QLabel#StatusBadge[state="active"] {
                background: #e6f3f1;
                color: #1f7168;
                border-color: #a8d7d1;
            }

            QLabel#StatusBadge[state="success"] {
                background: #edf6e7;
                color: #4f7f29;
                border-color: #c7dfb7;
            }

            QLabel#StatusBadge[state="error"] {
                background: #fff0e9;
                color: #a74726;
                border-color: #ecc0ad;
            }

            QLabel#StatusBadge[state="waiting"] {
                background: #f8f0d8;
                color: #85691d;
                border-color: #e6d29b;
            }

            QLabel#StatusBadge[state="cancelled"] {
                background: #eee9df;
                color: #675943;
                border-color: #d7cbb8;
            }

            QLineEdit {
                background: #fbfcfa;
                border: 1px solid #cfd5cc;
                border-radius: 6px;
                padding: 8px 10px;
                selection-background-color: #2f8f83;
            }

            QLineEdit:focus {
                border-color: #2f8f83;
                background: #ffffff;
            }

            QPushButton {
                background: #ffffff;
                border: 1px solid #cfd5cc;
                border-radius: 6px;
                padding: 9px 13px;
                font-weight: 600;
            }

            QPushButton:hover {
                background: #f1f4ef;
                border-color: #aeb8ad;
            }

            QPushButton:pressed {
                background: #e7ece5;
            }

            QPushButton:disabled {
                background: #ecefeb;
                color: #9aa39a;
                border-color: #d9ddd4;
            }

            QPushButton#PrimaryButton {
                background: #2f8f83;
                color: #ffffff;
                border: none;
            }

            QPushButton#PrimaryButton:hover {
                background: #287c72;
            }

            QPushButton#PrimaryButton:pressed {
                background: #226b63;
            }

            QPushButton#PrimaryButton:disabled {
                background: #b9d2ce;
                color: #eef6f4;
            }

            QProgressBar#MainProgress {
                background: #e8ece5;
                border: none;
                border-radius: 7px;
                color: #1d252f;
                height: 16px;
                text-align: center;
                font-size: 12px;
                font-weight: 700;
            }

            QProgressBar#MainProgress::chunk {
                background: #2f8f83;
                border-radius: 7px;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 2px 0 2px 0;
            }

            QScrollBar::handle:vertical {
                background: #c7cec4;
                border-radius: 5px;
                min-height: 36px;
            }

            QScrollBar::handle:vertical:hover {
                background: #aeb8ad;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

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
        if self.upload_in_progress:
            QMessageBox.warning(
                self,
                "Загрузка уже выполняется",
                "Дождитесь завершения текущей загрузки.\n"
                "Новые папки в очередь не добавляются."
            )
            return

        # 🔹 1. ЛОКАЛЬНЫЙ ПУТЬ — ТОЛЬКО ИЗ ПОЛЯ
        local_path = self.local_inputs[category].text().strip()

        ok, error_message = PathValidator.validate_local_directory(local_path)
        if not ok:
            self._set_category_state(category, "error", "Ошибка")
            self.current_state_label.setText("Ошибка ввода")
            self.current_detail_label.setText(error_message)
            QMessageBox.critical(
                self,
                "Ошибка",
                error_message
            )
            return

        # 🔹 2. ПУТЬ НА ЯНДЕКС.ДИСКЕ (поле)
        yadisk_path = self.yadisk_inputs[category].text().strip()

        if not yadisk_path:
            self._set_category_state(category, "error", "Ошибка")
            self.current_state_label.setText("Ошибка ввода")
            self.current_detail_label.setText("Не указан путь на Яндекс.Диске")
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

        self.upload_in_progress = True
        self._set_upload_controls_enabled(False)
        self._set_category_state(category, "waiting", "Подготовка")
        self.current_state_label.setText("Подготовка")
        self.current_detail_label.setText(get_category_label(category))
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Подготовка загрузки…")

        self.upload_queue.add_task(task)
        self.upload_signals.task_added.emit(task)

    # ==================================================================
    # Сигналы
    # ==================================================================

    def on_task_started(self, task):
        self.upload_in_progress = True
        self._set_upload_controls_enabled(False)
        self._set_category_state(task.category, "active", "Загрузка")
        self.current_state_label.setText("Загрузка")
        self.current_detail_label.setText(get_category_label(task.category))
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
        self.current_state_label.setText(f"Загрузка {percent}%")
        self.current_detail_label.setText(
            f"{get_category_label(task.category)} · "
            f"{self._format_size(uploaded)} / {self._format_size(total)}"
        )
        self.progress_bar.setFormat(
            f"{get_category_label(task.category)}: {percent}% "
            f"({self._format_size(uploaded)} / {self._format_size(total)})"
        )

    def on_task_finished(self, task):
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_bar.setFormat("Загрузка завершена")
        self._set_category_state(task.category, "success", "Завершено")
        self.current_state_label.setText("Готово")
        self.current_detail_label.setText(get_category_label(task.category))
        self._finish_current_upload()

        QMessageBox.information(
            self,
            "Готово",
            f"Загрузка категории «{get_category_label(task.category)}» успешно завершена."
        )

    def on_task_error(self, task, message):
        self.progress_bar.setFormat("Ошибка загрузки")
        self._set_category_state(task.category, "error", "Ошибка")
        self.current_state_label.setText("Ошибка")
        self.current_detail_label.setText(message.splitlines()[0])
        self._finish_current_upload()

        QMessageBox.critical(
            self,
            "Ошибка загрузки",
            f"Категория: {get_category_label(task.category)}\n\n{message}"
        )

    def on_task_cancelled(self, task):
        self.progress_bar.setFormat("Загрузка прервана")
        self._set_category_state(task.category, "cancelled", "Прервано")
        self.current_state_label.setText("Прервано")
        self.current_detail_label.setText(get_category_label(task.category))
        self._finish_current_upload()

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
        self._finish_current_upload()
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
            self._set_category_state(key, "idle", "Готово")
            self.current_state_label.setText("Папка выбрана")
            self.current_detail_label.setText(get_category_label(key))

    def _set_upload_controls_enabled(self, enabled: bool):
        for button in self.upload_buttons.values():
            button.setEnabled(enabled)

    def _finish_current_upload(self):
        self.upload_in_progress = False
        self._set_upload_controls_enabled(True)

    def _set_category_state(self, category: str, state: str, text: str):
        panel = self.category_panels.get(category)
        badge = self.category_status_labels.get(category)

        if panel:
            panel.setProperty("state", state)
            self._refresh_widget_style(panel)

        if badge:
            badge.setText(text)
            badge.setProperty("state", state)
            self._refresh_widget_style(badge)

    def _refresh_widget_style(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def _format_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} Б"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} КБ"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} МБ"
        return f"{size / (1024 * 1024 * 1024):.1f} ГБ"
