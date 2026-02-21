"""
Перевод технических исключений в понятные пользователю сообщения.
"""

import socket
import ssl
import requests
import yadisk
from requests.exceptions import ProxyError, ConnectionError, Timeout


def translate_exception(exc: Exception) -> str:
    """
    Преобразует исключение в человеко-читаемое сообщение.
    """
    # 🔹 Яндекс.Диск
    if isinstance(exc, yadisk.exceptions.UnauthorizedError):
        return "Ошибка авторизации. Проверьте токен Яндекс.Диска."

    if isinstance(exc, RuntimeError):
        return (
            "Указанный путь на Яндекс.Диске не существует.\n"
            "Проверьте правильность пути в настройках."
        )

    if isinstance(exc, yadisk.exceptions.ForbiddenError):
        return (
            "Недостаточно прав для записи в указанную папку "
            "на Яндекс.Диске."
        )

    if isinstance(exc, yadisk.exceptions.ConflictError):
        return (
            "Конфликт при загрузке файла.\n"
            "Возможно, файл уже используется или заблокирован."
        )

    # 🔹 Сеть / прокси / SSL
    if isinstance(exc, ProxyError):
        return (
            "Ошибка подключения через прокси.\n"
            "Проверьте настройки прокси или отключите его."
        )

    if isinstance(exc, (ConnectionError, Timeout, socket.timeout)):
        return (
            "Не удалось подключиться к Яндекс.Диску.\n"
            "Проверьте интернет-соединение."
        )

    if isinstance(exc, ssl.SSLError):
        return (
            "Ошибка SSL-соединения.\n"
            "Возможно, используется корпоративный прокси "
            "или антивирус с перехватом трафика."
        )

    # 🔹 Файловая система
    if isinstance(exc, FileNotFoundError):
        return (
            "Файл или папка не найдены.\n"
            "Возможно, они были удалены во время загрузки."
        )

    if isinstance(exc, PermissionError):
        return (
            "Нет доступа к файлу или папке.\n"
            "Проверьте права доступа."
        )

    # 🔹 Отмена пользователем
    if str(exc) == "Загрузка прервана пользователем":
        return "Загрузка была прервана пользователем."

    # 🔹 Фолбэк
    return (
        "Произошла непредвиденная ошибка.\n\n"
        f"Техническая информация:\n{str(exc)}"
    )