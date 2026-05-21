__all__ = ["Query"]

from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from status.status_shemes import Status
from .event import AllEvents
from callback.payload_schemes import Payload
from messages.message_schemes import Message, ContactMessage, Callback


class Query(BaseModel):
    event: Optional[AllEvents] = None
    message: Optional[Message | ContactMessage] = None
    contact_message: Optional[ContactMessage] = None
    callback: Optional[Callback] = None
    status: Optional[Status] = None

    @property
    def payload(self) -> Payload | None:
        if self.callback is not None:
            return self.callback.payload
        return None

    @property
    def payload_type(self) -> str | None:
        if self.payload is not None:
            return self.payload.type
        return None

    @property
    def payload_uuid(self) -> UUID | None:
        if self.payload is not None:
            return self.payload.uuid
        return None

    @property
    def payload_action(self) -> str | None:
        if self.payload is not None:
            return self.payload.action
        return None

    @property
    def payload_inner(self) -> list[str] | None:
        if self.payload is not None:
            return self.payload.inner.value
        return None
