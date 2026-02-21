"""
Человекочитаемые названия категорий для UI.
Используются во всех сообщениях пользователю.
"""

CATEGORY_LABELS = {
    "raw_photos": "Исходные фото",
    "processed_photos": "Обработанные фото",
    "raw_videos": "Исходные видео",
    "processed_videos": "Обработанные видео",
}

def get_category_label(category_key: str) -> str:
    """
    Возвращает человекочитаемое название категории.
    Если ключ неизвестен — возвращает сам ключ.
    """
    return CATEGORY_LABELS.get(category_key, category_key)