"""Классы статуса пользователя и хранения всех статусов"""

from __future__ import annotations

__all__ = ["Status", "Statuses"]

import asyncio
from dataclasses import Field
from datetime import datetime, timedelta
from typing import ClassVar, Optional

from pydantic import BaseModel, ConfigDict

from callback.payload_schemes import Payload


class Status(BaseModel):
    """Хранит значение статуса пользователя на данный момент

    Attributes:
        name: Название статуса
        payload: Payload статуса
        is_background: если False, то не учитывается при проверке статусов status_check
        send_callback: если True, то отправляется callback от статуса
        create_time: Время создания статуса
    """

    model_config = ConfigDict(frozen=True)

    name: Optional[str] = None
    payload: Optional[Payload] = None
    is_background: bool = False
    send_callback: bool = True
    create_time: datetime = datetime.now()

    def __eq__(self, other: str | Payload | Status) -> bool:
        if isinstance(other, Status):
            return self.value == other.value and self.payload == self.payload
        return NotImplemented


class Statuses(BaseModel):
    """Хранит все статусы всех пользователей по их id"""

    statuses: ClassVar[dict[int, Status]] = {}
    lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    @classmethod
    async def delete_expired_statuses(cls, lifetime_seconds: int = 600) -> None:
        async with cls.lock:
            now = datetime.now()
            expired_ids = [
                user_id
                for user_id, status in cls.statuses.items()
                if now - status.create_time > timedelta(seconds=lifetime_seconds)
            ]

            from requests.requests_functions import send_message
            from core.global_names import GN
            from requests.requests_schemes import NewMessageData
            from buttons.keyboards import Keyboards
            from requests.requests_schemes import Attachments

            for user_id in expired_ids:
                del cls.statuses[user_id]
                await send_message(NewMessageData(text="⏱️Время ожидания действия истекло"), user_id=user_id)
                await send_message(NewMessageData(text=GN.help_text, attachments=[Attachments(type="inline_keyboard", payload=Keyboards.help())]), user_id=user_id)
