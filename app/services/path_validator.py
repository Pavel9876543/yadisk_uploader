"""
Валидация локальных путей файловой системы.
"""

from pathlib import Path


class PathValidator:
    @staticmethod
    def validate_local_directory(path: str) -> tuple[bool, str]:
        """
        Проверяет, что путь:
        - не пустой
        - существует
        - является директорией

        Возвращает (ok, error_message)
        """
        if not path or not path.strip():
            return False, "Локальный путь не указан."

        p = Path(path)

        if not p.exists():
            return False, "Указанный локальный путь не существует."

        if not p.is_dir():
            return False, "Указанный путь не является папкой."

        return True, ""