import asyncio
import logging

from .status_shemes import Statuses

from core.config import bot_info

async def cleanup_statuses_loop() -> None:
    while True:
        try:
            await Statuses.delete_expired_statuses(lifetime_seconds=bot_info.statuses_life_time_seconds)
        except Exception:
            logging.exception("Ошибка при очистке устаревших статусов")
        await asyncio.sleep(bot_info.statuses_life_time_check_seconds)