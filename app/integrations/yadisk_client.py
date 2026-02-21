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
        load_dotenv()
        token = os.getenv("YANDEX_TOKEN")

        if not token:
            raise RuntimeError("Не найден токен Яндекс.Диска (.env)")

        try:
            self.disk = yadisk.YaDisk(token=token)

            if not self.disk.check_token():
                raise RuntimeError("Неверный токен Яндекс.Диска")

        except Exception as exc:
            # ❗ ВАЖНО: всё приводим к RuntimeError
            raise RuntimeError(str(exc)) from exc

    def ensure_path(self, yadisk_path: str) -> None:
        try:
            path = yadisk_path.strip().rstrip("/")

            if not path.startswith("/"):
                path = "/" + path

            parts = path.split("/")[1:]
            current_path = ""

            for part in parts:
                current_path += f"/{part}"
                if not self.disk.exists(current_path):
                    self.disk.mkdir(current_path)

        except Exception as exc:
            raise RuntimeError(
                f"Не удалось создать папку на Яндекс.Диске:\n{yadisk_path}"
            ) from exc

    def upload_file(self, local_file: Path, yadisk_folder: str) -> None:
        """
        Загружает файл, если он не существует на Яндекс.Диске.

        Возвращает:
        - True  — файл загружен
        - False — файл уже существует (пропущен)
        """
        try:
            target_path = f"{yadisk_folder.rstrip('/')}/{local_file.name}"

            # 🔹 ПРОВЕРКА СУЩЕСТВОВАНИЯ ФАЙЛА
            if self.disk.exists(target_path):
                return False

            self.disk.upload(
                local_file.as_posix(),
                target_path,
                overwrite=False
            )
            return True

        except Exception as exc:
            raise RuntimeError(
                f"Ошибка загрузки файла:\n{local_file.name}"
            ) from exc

    def upload_folder(
        self,
        local_folder: Path,
        yadisk_folder: str,
        on_progress=None,
        on_skip=None
    ) -> None:
        """
        Загружает папку целиком.
        Пропускает файлы, которые уже существуют на Яндекс.Диске.
        """
        try:
            self.ensure_path(yadisk_folder)

            files = [
                f for f in local_folder.rglob("*")
                if f.is_file()
            ]

            total_bytes = sum(f.stat().st_size for f in files)
            uploaded_bytes = 0

            for file in files:
                uploaded = self.upload_file(file, yadisk_folder)

                if uploaded:
                    uploaded_bytes += file.stat().st_size
                    if on_progress:
                        on_progress(uploaded_bytes, total_bytes)
                else:
                    # 🔹 файл пропущен
                    if on_skip:
                        on_skip(file)

        except Exception:
            # ❗ НЕ глотаем — пробрасываем наверх
            raise