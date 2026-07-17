"""
Перевод технических исключений в понятные пользователю сообщения.
"""

import socket
import ssl

import yadisk
from requests.exceptions import ProxyError, ConnectionError, Timeout


def _exception_chain(exc: Exception):
    current = exc
    seen = set()

    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def _has_message(exc: Exception, text: str) -> bool:
    return any(text in str(item) for item in _exception_chain(exc))


def _has_type(exc: Exception, types) -> bool:
    return any(isinstance(item, types) for item in _exception_chain(exc))


def translate_exception(exc: Exception) -> str:
    """
    Преобразует исключение в человеко-читаемое сообщение.
    Учитывает исходную причину, даже если ошибка была обёрнута выше.
    """
    if _has_message(exc, "Загрузка прервана пользователем"):
        return "Загрузка была прервана пользователем."

    # Авторизация / токен
    if _has_type(exc, yadisk.exceptions.UnauthorizedError):
        return "Ошибка авторизации. Проверьте токен Яндекс.Диска."

    if _has_message(exc, "Не найден токен"):
        return "Не найден токен Яндекс.Диска. Проверьте переменную YANDEX_TOKEN в файле .env."

    if _has_message(exc, "Неверный токен"):
        return "Неверный токен Яндекс.Диска. Проверьте значение YANDEX_TOKEN."

    # Права и лимиты Яндекс.Диска
    if _has_type(exc, yadisk.exceptions.ForbiddenError):
        return (
            "Недостаточно прав для записи в указанную папку "
            "на Яндекс.Диске."
        )

    if _has_type(exc, yadisk.exceptions.InsufficientStorageError):
        return "На Яндекс.Диске недостаточно свободного места."

    if _has_type(exc, yadisk.exceptions.UploadTrafficLimitExceededError):
        return (
            "Превышен лимит загрузки на Яндекс.Диск.\n"
            "Попробуйте повторить загрузку позже."
        )

    if _has_type(exc, yadisk.exceptions.TooManyRequestsError):
        return (
            "Яндекс.Диск временно ограничил частоту запросов.\n"
            "Подождите немного и повторите загрузку."
        )

    # Сеть / прокси / SSL
    if _has_type(exc, ProxyError):
        return (
            "Ошибка подключения через прокси.\n"
            "Проверьте настройки прокси или отключите его."
        )

    if _has_type(exc, (
        ConnectionError,
        Timeout,
        socket.timeout,
        yadisk.exceptions.YaDiskConnectionError,
        yadisk.exceptions.RequestTimeoutError,
    )):
        return (
            "Не удалось подключиться к Яндекс.Диску.\n"
            "Проверьте интернет-соединение."
        )

    if _has_type(exc, ssl.SSLError):
        return (
            "Ошибка SSL-соединения.\n"
            "Возможно, используется корпоративный прокси "
            "или антивирус с перехватом трафика."
        )

    if _has_type(exc, yadisk.exceptions.RetriableYaDiskError):
        return (
            "Яндекс.Диск временно недоступен.\n"
            "Повторите загрузку позже."
        )

    # Пути и файлы
    if _has_type(exc, (
        yadisk.exceptions.PathNotFoundError,
        yadisk.exceptions.ParentNotFoundError,
        yadisk.exceptions.NotFoundError,
    )):
        return (
            "Путь на Яндекс.Диске не найден.\n"
            "Проверьте папку назначения."
        )

    if _has_message(exc, "Не указан путь на Яндекс.Диске"):
        return "Не указан путь для загрузки на Яндекс.Диск."

    if _has_message(exc, "Не удалось создать папку"):
        return (
            "Не удалось создать папку на Яндекс.Диске.\n"
            "Проверьте путь и права доступа."
        )

    if _has_type(exc, FileNotFoundError):
        return (
            "Файл или папка не найдены.\n"
            "Возможно, они были удалены во время загрузки."
        )

    if _has_type(exc, PermissionError):
        return (
            "Нет доступа к файлу или папке.\n"
            "Проверьте права доступа."
        )

    # Конфликты ресурсов
    if _has_type(exc, (
        yadisk.exceptions.ResourceIsLockedError,
        yadisk.exceptions.LockedError,
    )):
        return (
            "Файл или папка на Яндекс.Диске временно заблокированы.\n"
            "Повторите загрузку позже."
        )

    if _has_type(exc, yadisk.exceptions.ConflictError):
        return (
            "Конфликт при загрузке файла.\n"
            "Проверьте, не изменяется ли эта папка одновременно в другом месте."
        )

    if _has_type(exc, yadisk.exceptions.PayloadTooLargeError):
        return (
            "Файл слишком большой для загрузки этим способом.\n"
            "Попробуйте загрузить его отдельно."
        )

    if _has_message(exc, "Ошибка загрузки файла"):
        return (
            "Не удалось загрузить один из файлов.\n"
            "Проверьте доступ к файлу и повторите загрузку."
        )

    return (
        "Произошла непредвиденная ошибка.\n\n"
        f"Техническая информация:\n{str(exc)}"
    )
