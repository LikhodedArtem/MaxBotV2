"""Классы статуса пользователя и хранения всех статусов"""

from __future__ import annotations

__all__ = ["Status", "Statuses"]

from pydantic import BaseModel

from callback.payload_schemes import Payload
from typing import ClassVar


class Status(BaseModel):
    """Хранит значение статуса пользователя на данный момент

    Attributes:
        value: Само значение статуса
        is_background: если False, то не учитывается при проверке статусов status_check
        send_callback: если True, то отправляется callback от статуса
    """

    value: str | Payload
    is_background: bool = False
    send_callback: bool = True

    def __eq__(self, other: str | Payload | Status) -> bool:
        if isinstance(other, Status):
            return self.value == other.value

        if isinstance(other, str):
            if isinstance(self.value, str):
                return self.value == other
            return False

        if isinstance(other, Payload):
            if isinstance(self.value, Payload):
                return self.value == other
            return False

        return NotImplemented

    @property
    def is_payload(self) -> bool:
        return isinstance(self.value, Payload)

    @property
    def is_str(self) -> bool:
        return isinstance(self.value, str)

class Statuses(BaseModel):
    """Хранит все статусы всех пользователей по их id"""

    statuses: ClassVar[dict[int, Status]] = {}