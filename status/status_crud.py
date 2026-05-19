__all__ = [
    "get_status",
    "set_status",
    "clear_status",
    "has_status",
]


from core.config import bot_info
from .status_shemes import Statuses, Status


async def get_status(user_id: int) -> Status | None:
    """Получить статус пользователя по id

    Args:
        user_id: id пользователя"""

    assert user_id != bot_info.my_id, ValueError("Попытка получить статус бота!")

    if user_id in Statuses.statuses:
        return Statuses.statuses[user_id]
    return None


async def set_status(user_id: int, status: Status) -> None:
    """Установить статус пользователя по id

    Args:
        user_id: id пользователя
        status: status пользователя
    """

    assert user_id != bot_info.my_id, ValueError("Попытка поставить статус боту!")

    if status is not None:
        Statuses.statuses[user_id] = status


async def clear_status(user_id: int) -> None:
    """Очистить статус пользователя по id

    Args:
        user_id: id пользователя
    """

    assert user_id != bot_info.my_id, ValueError("Попытка очистить статус бота!")

    if user_id in Statuses.statuses:
        Statuses.statuses.pop(user_id)


async def has_status(user_id: int) -> bool:
    """Есть ли у пользователя по id статус

    Args:
        user_id: id пользователя"""

    assert user_id != bot_info.my_id, ValueError("Попытка обратиться к статусу бота!")

    return user_id in Statuses.statuses