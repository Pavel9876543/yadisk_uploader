"""
Клиент для работы с Яндекс.Диском.
Создаёт папки при необходимости и загружает файлы.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import yadisk


class YadiskClient:
    """
    Клиент Яндекс.Диска.
    Используется в UploadWorker.
    """

    def __init__(self) -> None:
        """
        Инициализация клиента.
        Токен берётся из .env
        """
        load_dotenv()
        token = os.getenv("YANDEX_TOKEN")

        if not token:
            raise RuntimeError("YANDEX_TOKEN не найден в .env")

        self.disk = yadisk.YaDisk(token=token)

        if not self.disk.check_token():
            raise RuntimeError("Неверный YANDEX_TOKEN")

    def ensure_path(self, yadisk_path: str) -> None:
        """
        Гарантирует, что путь на Яндекс.Диске существует.
        Создаёт все отсутствующие папки по цепочке.

        Пример:
        /disk/media/photos/raw
        """
        # Нормализуем путь
        path = yadisk_path.strip().rstrip("/")

        if not path.startswith("/"):
            path = "/" + path

        parts = path.split("/")[1:]  # без первого пустого элемента
        current_path = ""

        for part in parts:
            current_path += f"/{part}"
            if not self.disk.exists(current_path):
                self.disk.mkdir(current_path)

    def upload_file(self, local_file: Path, yadisk_folder: str) -> None:
        """
        Загружает один файл на Яндекс.Диск.
        """
        target_path = f"{yadisk_folder.rstrip('/')}/{local_file.name}"

        self.disk.upload(
            local_file.as_posix(),
            target_path,
            overwrite=True
        )

    def upload_folder(
        self,
        local_folder: Path,
        yadisk_folder: str,
        on_progress=None
    ) -> None:
        """
        Загружает папку целиком.
        Создаёт путь на Яндекс.Диске, если его нет.
        """

        # 1️⃣ Гарантируем, что путь существует
        self.ensure_path(yadisk_folder)

        # 2️⃣ Собираем список файлов
        files = [
            f for f in local_folder.rglob("*")
            if f.is_file()
        ]

        total_bytes = sum(f.stat().st_size for f in files)
        uploaded_bytes = 0

        # 3️⃣ Загружаем файлы
        for file in files:
            self.upload_file(file, yadisk_folder)

            uploaded_bytes += file.stat().st_size
            if on_progress:
                on_progress(uploaded_bytes, total_bytes)