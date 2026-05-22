"""Классы статуса пользователя и хранения всех статусов"""

from __future__ import annotations

__all__ = ["Status", "Statuses"]

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
    """

    model_config = ConfigDict(frozen=True)

    name: Optional[str] = None
    payload: Optional[Payload] = None
    is_background: bool = False
    send_callback: bool = True

    def __eq__(self, other: str | Payload | Status) -> bool:
        if isinstance(other, Status):
            return self.value == other.value and self.payload == self.payload
        return NotImplemented


class Statuses(BaseModel):
    """Хранит все статусы всех пользователей по их id"""

    statuses: ClassVar[dict[int, Status]] = {}
