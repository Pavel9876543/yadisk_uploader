"""
Клиент для работы с Яндекс.Диском.
Создаёт папки при необходимости и загружает файлы.
"""

from pathlib import Path, PurePosixPath
from typing import Callable

import yadisk

from services.env_service import EnvService


class UploadCancelled(RuntimeError):
    """Raised when the user asks to stop the current upload."""


class YadiskClient:
    """
    Клиент Яндекс.Диска.
    Используется в UploadWorker.
    """

    def __init__(self, token: str | None = None) -> None:
        token = (token or EnvService().load_token()).strip()

        if not token:
            raise RuntimeError("Не найден токен Яндекс.Диска (.env)")

        try:
            self.disk = yadisk.YaDisk(token=token)

            if not self.disk.check_token():
                raise RuntimeError("Неверный токен Яндекс.Диска")

        except Exception as exc:
            # ❗ ВАЖНО: всё приводим к RuntimeError
            raise RuntimeError(str(exc)) from exc

    def _normalize_yadisk_path(self, yadisk_path: str) -> str:
        path = yadisk_path.strip().rstrip("/")
        if not path:
            raise RuntimeError("Не указан путь на Яндекс.Диске")
        if not path.startswith("/"):
            path = "/" + path
        return path

    def ensure_path(self, yadisk_path: str) -> str:
        try:
            path = self._normalize_yadisk_path(yadisk_path)

            parts = path.split("/")[1:]
            current_path = ""

            for part in parts:
                current_path += f"/{part}"
                if not self.disk.exists(current_path):
                    self.disk.mkdir(current_path)

            return path

        except Exception as exc:
            raise RuntimeError(
                f"Не удалось создать папку на Яндекс.Диске:\n{yadisk_path}"
            ) from exc

    def upload_file(self, local_file: Path, target_path: str) -> bool:
        """
        Загружает файл, если он не существует на Яндекс.Диске.

        Возвращает:
        - True  — файл загружен
        - False — файл уже существует (пропущен)
        """
        try:
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

    def _target_path(
        self,
        local_folder: Path,
        local_file: Path,
        yadisk_folder: str
    ) -> str:
        relative_path = local_file.relative_to(local_folder).as_posix()
        return f"{yadisk_folder.rstrip('/')}/{relative_path}"

    def upload_folder(
        self,
        local_folder: Path,
        yadisk_folder: str,
        on_progress=None,
        on_skip=None,
        should_cancel: Callable[[], bool] | None = None
    ) -> None:
        """
        Загружает папку целиком.
        Пропускает файлы, которые уже существуют на Яндекс.Диске.
        Сохраняет структуру вложенных подпапок.
        """
        try:
            yadisk_folder = self.ensure_path(yadisk_folder)

            files = [
                f for f in local_folder.rglob("*")
                if f.is_file()
            ]

            total_bytes = sum(f.stat().st_size for f in files)
            uploaded_bytes = 0

            for file in files:
                if should_cancel and should_cancel():
                    raise UploadCancelled("Загрузка прервана пользователем")

                file_size = file.stat().st_size
                target_path = self._target_path(
                    local_folder,
                    file,
                    yadisk_folder
                )
                target_folder = str(PurePosixPath(target_path).parent)
                self.ensure_path(target_folder)

                uploaded = self.upload_file(file, target_path)

                if not uploaded:
                    if on_skip:
                        on_skip(file)

                uploaded_bytes += file_size
                if on_progress:
                    on_progress(uploaded_bytes, total_bytes)

        except Exception:
            raise
