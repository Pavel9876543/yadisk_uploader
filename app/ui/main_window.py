from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QMessageBox
)
from services.config_service import ConfigService
from services.path_validator import PathValidator


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

    def _upload_clicked(self, key):
        local_path = self.local_inputs[key].text()
        yadisk_path = self.yadisk_inputs[key].text()

        if not self.validator.validate_local_path(local_path):
            QMessageBox.critical(self, "Ошибка", "Локальный путь не существует")
            return

        if not yadisk_path:
            QMessageBox.critical(self, "Ошибка", "Не указан путь на Яндекс.Диске")
            return

        QMessageBox.information(
            self,
            "Загрузка",
            f"Загрузка файлов из:\n{local_path}\n→ {yadisk_path}\n(пока заглушка)"
        )