"""
Формирование итоговых путей на Яндекс.Диске
на основе config.json и текущей даты.
"""

from datetime import datetime
from pathlib import PurePosixPath


CATEGORY_SUBFOLDERS = {
    "processed_photos": ["Фото"],
    "raw_photos": ["Исходники", "Фото"],
    "processed_video": ["Видео"],
    "raw_video": ["Исходники", "Видео"],
}


def build_yadisk_path(base_path: str, category: str, now: datetime) -> str:
    if not isinstance(base_path, str):
        raise TypeError(
            f"base_path должен быть строкой, получено: {type(base_path)}"
        )

    year = str(now.year)
    date = now.strftime("%Y.%m.%d")

    parts = [base_path, year, date]
    parts.extend(CATEGORY_SUBFOLDERS.get(category, []))

    return str(PurePosixPath(*parts))