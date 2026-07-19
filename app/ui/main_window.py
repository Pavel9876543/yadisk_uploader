from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QMessageBox, QProgressBar,
    QFrame, QGridLayout, QScrollArea, QSizePolicy, QStyle, QApplication
)
from PyQt5.QtCore import QThread, Qt, QSize
from pathlib import Path
from datetime import datetime
from pathlib import PurePosixPath

from services.config_service import ConfigService
from services.env_service import EnvService
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
    "processed_photos": "#14b8a6",
    "raw_photos": "#f59e0b",
    "processed_video": "#3b82f6",
    "raw_video": "#f97316",
}

CATEGORY_DETAILS = {
    "processed_photos": "Фото / готовый материал",
    "raw_photos": "Фото / исходники",
    "processed_video": "Видео / готовый материал",
    "raw_video": "Видео / исходники",
}

CATEGORY_ICONS = {
    "processed_photos": QStyle.SP_FileDialogContentsView,
    "raw_photos": QStyle.SP_FileDialogDetailedView,
    "processed_video": QStyle.SP_MediaPlay,
    "raw_video": QStyle.SP_FileIcon,
}


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yandex Disk Uploader")
        self.resize(1120, 760)
        self.setMinimumSize(940, 660)

        # ─── СЕРВИСЫ ───────────────────────────────────────────────
        self.config_service = ConfigService()
        self.env_service = EnvService()
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
        self.token_input = None
        self.token_status_label = None

        # ─── КОНФИГ (ОДИН РАЗ) ─────────────────────────────────────
        self.config = self.config_service.load()

        # ─── UI ────────────────────────────────────────────────────
        self._init_ui()
        self._init_final_yadisk_paths()
        self._load_paths_from_config()
        self._load_token_from_env()

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
        self.setObjectName("AppRoot")
        self._apply_styles()

        layout = QHBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        workspace = QWidget()
        workspace.setObjectName("Workspace")
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(14)

        workspace_layout.addWidget(self._build_header())
        workspace_layout.addWidget(self._build_token_panel())
        workspace_layout.addWidget(self._build_categories_area(), 1)
        workspace_layout.addWidget(self._build_status_panel())

        layout.addWidget(self._build_sidebar())
        layout.addWidget(workspace, 1)

        self.setLayout(layout)

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(248)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(12)

        brand_icon = QLabel()
        brand_icon.setObjectName("BrandIcon")
        brand_icon.setFixedSize(48, 48)
        brand_icon.setAlignment(Qt.AlignCenter)
        brand_icon.setText("YD")

        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        brand_title = QLabel("Yandex Disk")
        brand_title.setObjectName("SidebarTitle")
        brand_subtitle = QLabel("Uploader")
        brand_subtitle.setObjectName("SidebarSubtitle")
        brand_text.addWidget(brand_title)
        brand_text.addWidget(brand_subtitle)

        brand_row.addWidget(brand_icon)
        brand_row.addLayout(brand_text, 1)
        layout.addLayout(brand_row)

        session_panel = QFrame()
        session_panel.setObjectName("SidebarPanel")
        session_layout = QVBoxLayout(session_panel)
        session_layout.setContentsMargins(14, 12, 14, 12)
        session_layout.setSpacing(10)

        session_label = QLabel("Сессия")
        session_label.setObjectName("SidebarLabel")
        session_date = QLabel(self.app_start_time.strftime("%Y.%m.%d"))
        session_date.setObjectName("SidebarMetric")
        session_layout.addWidget(session_label)
        session_layout.addWidget(session_date)

        layout.addWidget(session_panel)

        counters_panel = QFrame()
        counters_panel.setObjectName("SidebarPanel")
        counters_layout = QGridLayout(counters_panel)
        counters_layout.setContentsMargins(14, 12, 14, 12)
        counters_layout.setHorizontalSpacing(10)
        counters_layout.setVerticalSpacing(8)

        categories_count = QLabel(str(len(CATEGORIES)))
        categories_count.setObjectName("CounterValue")
        categories_label = QLabel("категории")
        categories_label.setObjectName("CounterLabel")
        mode_count = QLabel("1")
        mode_count.setObjectName("CounterValue")
        mode_label = QLabel("поток")
        mode_label.setObjectName("CounterLabel")

        counters_layout.addWidget(categories_count, 0, 0)
        counters_layout.addWidget(categories_label, 1, 0)
        counters_layout.addWidget(mode_count, 0, 1)
        counters_layout.addWidget(mode_label, 1, 1)
        counters_layout.setColumnStretch(0, 1)
        counters_layout.setColumnStretch(1, 1)

        layout.addWidget(counters_panel)

        btn_save = QPushButton("Сохранить")
        btn_save.setObjectName("SidebarButton")
        btn_save.setMinimumHeight(42)
        btn_save.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        btn_save.setIconSize(QSize(18, 18))
        btn_save.clicked.connect(self._save_paths)

        btn_help = QPushButton("Справка")
        btn_help.setObjectName("SidebarButton")
        btn_help.setMinimumHeight(42)
        btn_help.setIcon(self.style().standardIcon(QStyle.SP_DialogHelpButton))
        btn_help.setIconSize(QSize(18, 18))
        btn_help.clicked.connect(self._show_help)

        layout.addWidget(btn_save)
        layout.addWidget(btn_help)
        layout.addStretch(1)

        footer = QLabel("Готов к загрузке")
        footer.setObjectName("SidebarFooter")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

        return sidebar

    def _build_header(self):
        header = QFrame()
        header.setObjectName("Header")

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(5)

        title = QLabel("Загрузка медиатеки")
        title.setObjectName("AppTitle")

        subtitle = QLabel(
            f"Yandex Disk / {self.app_start_time.strftime('%Y.%m.%d')}"
        )
        subtitle.setObjectName("MutedText")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header_layout.addLayout(title_box, 1)

        ready_badge = QLabel("Готово")
        ready_badge.setObjectName("HeaderBadge")
        ready_badge.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(ready_badge)

        return header

    def _build_token_panel(self):
        panel = QFrame()
        panel.setObjectName("TokenPanel")

        grid = QGridLayout(panel)
        grid.setContentsMargins(22, 16, 22, 16)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        title = QLabel("Токен Яндекс.Диска")
        title.setObjectName("CategoryTitle")

        self.token_status_label = QLabel("Токен не задан")
        self.token_status_label.setObjectName("TokenStatusBadge")
        self.token_status_label.setProperty("state", "empty")
        self.token_status_label.setAlignment(Qt.AlignCenter)
        self.token_status_label.setMinimumWidth(118)

        token_label = QLabel("OAuth-токен")
        token_label.setObjectName("FieldLabel")
        token_label.setMinimumWidth(112)

        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("YANDEX_TOKEN")
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setMinimumHeight(40)
        self.token_input.setClearButtonEnabled(True)

        btn_save_token = QPushButton("Сохранить токен")
        btn_save_token.setObjectName("SecondaryButton")
        btn_save_token.setMinimumHeight(40)
        btn_save_token.setMinimumWidth(152)
        btn_save_token.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        btn_save_token.setIconSize(QSize(18, 18))
        btn_save_token.setToolTip("Сохранить токен в .env")
        btn_save_token.clicked.connect(self._save_token)

        btn_check_token = QPushButton("Проверить")
        btn_check_token.setObjectName("SecondaryButton")
        btn_check_token.setMinimumHeight(40)
        btn_check_token.setMinimumWidth(128)
        btn_check_token.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
        btn_check_token.setIconSize(QSize(18, 18))
        btn_check_token.setToolTip("Проверить соединение с Яндекс.Диском")
        btn_check_token.clicked.connect(self._check_yadisk_connection)

        grid.addWidget(title, 0, 0, 1, 3)
        grid.addWidget(self.token_status_label, 0, 3, 1, 1, Qt.AlignRight)
        grid.addWidget(token_label, 1, 0)
        grid.addWidget(self.token_input, 1, 1)
        grid.addWidget(btn_save_token, 1, 2)
        grid.addWidget(btn_check_token, 1, 3)
        grid.setColumnStretch(1, 1)

        return panel

    def _build_categories_area(self):
        scroll = QScrollArea()
        scroll.setObjectName("CategoryScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content.setObjectName("CategoryContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 2, 6, 2)
        content_layout.setSpacing(14)

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
        grid.setContentsMargins(18, 16, 18, 16)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(11)

        heading = QHBoxLayout()
        heading.setSpacing(12)

        icon_label = QLabel()
        icon_label.setObjectName("CategoryIcon")
        icon_label.setProperty("category", key)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedSize(44, 44)
        icon_label.setPixmap(
            self.style().standardIcon(CATEGORY_ICONS[key]).pixmap(QSize(24, 24))
        )

        title_label = QLabel(title)
        title_label.setObjectName("CategoryTitle")

        detail_label = QLabel(CATEGORY_DETAILS[key])
        detail_label.setObjectName("CategoryDetail")

        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title_stack.addWidget(title_label)
        title_stack.addWidget(detail_label)

        heading.addWidget(icon_label)
        heading.addLayout(title_stack, 1)

        status_label = QLabel("Готово")
        status_label.setObjectName("StatusBadge")
        status_label.setProperty("state", "idle")
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setMinimumWidth(96)

        local_label = QLabel("Локальная папка")
        local_label.setObjectName("FieldLabel")
        local_label.setMinimumWidth(112)
        local_input = QLineEdit()
        local_input.setPlaceholderText("Локальная папка")
        local_input.setMinimumHeight(40)
        local_input.setClearButtonEnabled(True)

        btn_select = QPushButton("Выбрать")
        btn_select.setObjectName("SecondaryButton")
        btn_select.setMinimumWidth(112)
        btn_select.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        btn_select.setIconSize(QSize(18, 18))
        btn_select.setToolTip("Выбрать локальную папку")
        btn_select.clicked.connect(lambda _, k=key: self._select_local_path(k))

        yadisk_label = QLabel("Яндекс.Диск")
        yadisk_label.setObjectName("FieldLabel")
        yadisk_input = QLineEdit()
        yadisk_input.setPlaceholderText("Путь на Яндекс.Диске")
        yadisk_input.setMinimumHeight(40)
        yadisk_input.setClearButtonEnabled(True)

        btn_upload = QPushButton("Загрузить")
        btn_upload.setObjectName("PrimaryButton")
        btn_upload.setMinimumHeight(92)
        btn_upload.setMinimumWidth(132)
        btn_upload.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        btn_upload.setIconSize(QSize(18, 18))
        btn_upload.setToolTip("Запустить загрузку этой категории")
        btn_upload.clicked.connect(lambda _, k=key: self._upload_clicked(k))

        grid.addLayout(heading, 0, 0, 1, 3)
        grid.addWidget(status_label, 0, 3, 1, 1, Qt.AlignRight)
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
        layout.setContentsMargins(22, 16, 22, 16)
        layout.setSpacing(12)

        top_line = QHBoxLayout()
        top_line.setSpacing(12)

        status_icon = QLabel()
        status_icon.setObjectName("StatusIcon")
        status_icon.setFixedSize(34, 34)
        status_icon.setAlignment(Qt.AlignCenter)
        status_icon.setPixmap(
            self.style().standardIcon(QStyle.SP_BrowserReload).pixmap(QSize(19, 19))
        )

        self.current_state_label = QLabel("Ожидание")
        self.current_state_label.setObjectName("CurrentState")

        self.current_detail_label = QLabel("Готов к загрузке")
        self.current_detail_label.setObjectName("MutedText")
        self.current_detail_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        state_stack = QVBoxLayout()
        state_stack.setSpacing(1)
        state_stack.addWidget(self.current_state_label)
        state_stack.addWidget(self.current_detail_label)

        top_line.addWidget(status_icon)
        top_line.addLayout(state_stack, 1)

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
                color: #20242a;
                font-family: "Segoe UI", "Arial", sans-serif;
                font-size: 14px;
                letter-spacing: 0;
            }

            QWidget#AppRoot {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #111317,
                    stop: 0.52 #191b20,
                    stop: 1 #202025
                );
            }

            QWidget#Workspace {
                background: transparent;
            }

            QLabel {
                background: transparent;
            }

            QFrame#Sidebar {
                background: #15181d;
                border: 1px solid #2a3038;
                border-radius: 8px;
            }

            QLabel#BrandIcon {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #1fb7a6,
                    stop: 1 #2f6fed
                );
                color: #ffffff;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 900;
            }

            QLabel#SidebarTitle {
                color: #f7fafc;
                font-size: 18px;
                font-weight: 800;
            }

            QLabel#SidebarSubtitle,
            QLabel#SidebarFooter {
                color: #9ea8b5;
                font-size: 13px;
                font-weight: 600;
            }

            QLabel#SidebarFooter {
                background: #101216;
                border: 1px solid #2a3038;
                border-radius: 8px;
                padding: 10px;
            }

            QFrame#SidebarPanel {
                background: #101216;
                border: 1px solid #2a3038;
                border-radius: 8px;
            }

            QLabel#SidebarLabel,
            QLabel#CounterLabel {
                color: #8994a2;
                font-size: 12px;
                font-weight: 700;
            }

            QLabel#SidebarMetric,
            QLabel#CounterValue {
                color: #f7fafc;
                font-size: 22px;
                font-weight: 800;
            }

            QFrame#Header,
            QFrame#StatusPanel,
            QFrame#TokenPanel,
            QFrame#CategoryPanel {
                background: #fbfcfe;
                border: 1px solid #dce2ea;
                border-radius: 8px;
            }

            QFrame#Header {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #f7fbff,
                    stop: 0.52 #ffffff,
                    stop: 1 #fff7ed
                );
            }

            QFrame#StatusPanel {
                background: #f7f9fc;
            }

            QFrame#TokenPanel {
                background: #fbfcfe;
            }

            QFrame#CategoryPanel[state="active"] {
                border-color: #14b8a6;
                background: #f3fffd;
            }

            QFrame#CategoryPanel[state="waiting"] {
                border-color: #f59e0b;
                background: #fffaf0;
            }

            QFrame#CategoryPanel[state="success"] {
                border-color: #22c55e;
                background: #f4fff8;
            }

            QFrame#CategoryPanel[state="error"] {
                border-color: #ef4444;
                background: #fff7f7;
            }

            QFrame#CategoryPanel[state="cancelled"] {
                border-color: #64748b;
                background: #f8fafc;
            }

            QScrollArea#CategoryScroll,
            QWidget#CategoryContent {
                background: transparent;
                border: none;
            }

            QLabel#AppTitle {
                color: #141820;
                font-size: 28px;
                font-weight: 800;
            }

            QLabel#HeaderBadge {
                background: #111827;
                color: #ffffff;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 13px;
                font-weight: 800;
            }

            QLabel#CategoryTitle {
                color: #171b22;
                font-size: 16px;
                font-weight: 800;
            }

            QLabel#CategoryDetail {
                color: #6b7280;
                font-size: 12px;
                font-weight: 600;
            }

            QLabel#CategoryIcon {
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.55);
            }

            QLabel#CategoryIcon[category="processed_photos"] {
                background: #ccfbf1;
            }

            QLabel#CategoryIcon[category="raw_photos"] {
                background: #fef3c7;
            }

            QLabel#CategoryIcon[category="processed_video"] {
                background: #dbeafe;
            }

            QLabel#CategoryIcon[category="raw_video"] {
                background: #ffedd5;
            }

            QLabel#CurrentState {
                color: #141820;
                font-size: 16px;
                font-weight: 800;
            }

            QLabel#MutedText {
                color: #697381;
            }

            QLabel#FieldLabel {
                color: #4b5563;
                font-size: 13px;
                font-weight: 800;
            }

            QLabel#StatusBadge {
                background: #eef2f7;
                color: #4b5563;
                border: 1px solid #d8dee8;
                border-radius: 8px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: 800;
            }

            QLabel#TokenStatusBadge {
                background: #eef2f7;
                color: #4b5563;
                border: 1px solid #d8dee8;
                border-radius: 8px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: 800;
            }

            QLabel#TokenStatusBadge[state="saved"],
            QLabel#TokenStatusBadge[state="valid"] {
                background: #dcfce7;
                color: #166534;
                border-color: #9ee6b7;
            }

            QLabel#TokenStatusBadge[state="checking"] {
                background: #e0f2fe;
                color: #075985;
                border-color: #bae6fd;
            }

            QLabel#TokenStatusBadge[state="error"] {
                background: #fee2e2;
                color: #991b1b;
                border-color: #fecaca;
            }

            QLabel#StatusBadge[state="active"] {
                background: #ccfbf1;
                color: #0f766e;
                border-color: #8be3d6;
            }

            QLabel#StatusBadge[state="success"] {
                background: #dcfce7;
                color: #166534;
                border-color: #9ee6b7;
            }

            QLabel#StatusBadge[state="error"] {
                background: #fee2e2;
                color: #991b1b;
                border-color: #fecaca;
            }

            QLabel#StatusBadge[state="waiting"] {
                background: #fef3c7;
                color: #92400e;
                border-color: #fde68a;
            }

            QLabel#StatusBadge[state="cancelled"] {
                background: #e2e8f0;
                color: #334155;
                border-color: #cbd5e1;
            }

            QLabel#StatusIcon {
                background: #e0f2fe;
                border: 1px solid #bae6fd;
                border-radius: 8px;
            }

            QLineEdit {
                background: #ffffff;
                border: 1px solid #cfd8e3;
                border-radius: 6px;
                padding: 8px 11px;
                color: #111827;
                selection-background-color: #14b8a6;
            }

            QLineEdit:focus {
                border-color: #14b8a6;
                background: #fcfffe;
            }

            QPushButton {
                background: #ffffff;
                border: 1px solid #cfd8e3;
                border-radius: 6px;
                padding: 9px 13px;
                font-weight: 800;
                color: #1f2937;
            }

            QPushButton:hover {
                background: #f3f7fb;
                border-color: #aab7c7;
            }

            QPushButton:pressed {
                background: #e8eef6;
            }

            QPushButton:disabled {
                background: #edf1f5;
                color: #9aa5b1;
                border-color: #dce2ea;
            }

            QPushButton#SidebarButton {
                background: #20252d;
                border: 1px solid #343c48;
                color: #f7fafc;
                text-align: left;
                padding-left: 12px;
            }

            QPushButton#SidebarButton:hover {
                background: #2a3140;
                border-color: #425066;
            }

            QPushButton#SidebarButton:pressed {
                background: #171b22;
            }

            QPushButton#PrimaryButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #14b8a6,
                    stop: 1 #2563eb
                );
                color: #ffffff;
                border: none;
            }

            QPushButton#PrimaryButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #0d9488,
                    stop: 1 #1d4ed8
                );
            }

            QPushButton#PrimaryButton:pressed {
                background: #0f766e;
            }

            QPushButton#PrimaryButton:disabled {
                background: #a9b8c9;
                color: #eef4fb;
            }

            QProgressBar#MainProgress {
                background: #e2e8f0;
                border: none;
                border-radius: 8px;
                color: #111827;
                height: 18px;
                text-align: center;
                font-size: 12px;
                font-weight: 800;
            }

            QProgressBar#MainProgress::chunk {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #14b8a6,
                    stop: 0.55 #22c55e,
                    stop: 1 #3b82f6
                );
                border-radius: 8px;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 2px 0 2px 0;
            }

            QScrollBar::handle:vertical {
                background: #8d99a8;
                border-radius: 5px;
                min-height: 36px;
            }

            QScrollBar::handle:vertical:hover {
                background: #6f7c8d;
            }

            QToolTip {
                background: #111827;
                color: #ffffff;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 6px;
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
    # Токен
    # ==================================================================

    def _load_token_from_env(self):
        token = self.env_service.load_token()
        if not self.token_input:
            return

        self.token_input.setText(token)
        self.token_input.setCursorPosition(0)

        if token:
            self._set_token_status("saved", "Токен загружен")
        else:
            self._set_token_status("empty", "Токен не задан")

    def _save_token(self):
        token = self.token_input.text().strip()
        if not token:
            self._set_token_status("error", "Токен не задан")
            QMessageBox.warning(
                self,
                "Токен не задан",
                "Введите OAuth-токен Яндекс.Диска."
            )
            return

        try:
            env_path = self.env_service.save_token(token)
        except Exception as exc:
            self._set_token_status("error", "Ошибка")
            QMessageBox.critical(
                self,
                "Ошибка сохранения",
                f"Не удалось сохранить токен в .env:\n{exc}"
            )
            return

        self._set_token_status("saved", "Токен сохранён")
        self.current_state_label.setText("Токен сохранён")
        self.current_detail_label.setText(env_path.as_posix())
        QMessageBox.information(
            self,
            "Успех",
            "Токен Яндекс.Диска сохранён в файл .env."
        )

    def _check_yadisk_connection(self):
        token = self.token_input.text().strip()
        if not token:
            self._set_token_status("error", "Токен не задан")
            QMessageBox.warning(
                self,
                "Токен не задан",
                "Введите OAuth-токен Яндекс.Диска."
            )
            return

        self._set_token_status("checking", "Проверка")
        self.current_state_label.setText("Проверка соединения")
        self.current_detail_label.setText("Яндекс.Диск")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:
            is_valid = self.env_service.check_token(token)
        except Exception as exc:
            error_message = str(exc) or exc.__class__.__name__
            self._set_token_status("error", "Ошибка")
            self.current_state_label.setText("Ошибка соединения")
            self.current_detail_label.setText(error_message.splitlines()[0])
            QMessageBox.critical(
                self,
                "Ошибка соединения",
                f"Не удалось проверить соединение с Яндекс.Диском:\n{error_message}"
            )
            return
        finally:
            QApplication.restoreOverrideCursor()

        if is_valid:
            self._set_token_status("valid", "Соединение есть")
            self.current_state_label.setText("Соединение есть")
            self.current_detail_label.setText("Токен Яндекс.Диска действителен")
            QMessageBox.information(
                self,
                "Соединение есть",
                "Токен Яндекс.Диска действителен."
            )
            return

        self._set_token_status("error", "Неверный токен")
        self.current_state_label.setText("Неверный токен")
        self.current_detail_label.setText("Яндекс.Диск отклонил токен")
        QMessageBox.warning(
            self,
            "Неверный токен",
            "Яндекс.Диск отклонил указанный токен."
        )

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
                line_edit = self.local_inputs[category]
                line_edit.setText(path or "")
                line_edit.setCursorPosition(0)

        # Пути Яндекс.Диска — УЖЕ С ДАТОЙ
        for category, final_path in self.final_yadisk_paths.items():
            if category in self.yadisk_inputs:
                line_edit = self.yadisk_inputs[category]
                line_edit.setText(final_path)
                line_edit.setCursorPosition(0)

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
            self.local_inputs[key].setCursorPosition(0)
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

    def _set_token_status(self, state: str, text: str):
        if not self.token_status_label:
            return

        self.token_status_label.setText(text)
        self.token_status_label.setProperty("state", state)
        self._refresh_widget_style(self.token_status_label)

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
