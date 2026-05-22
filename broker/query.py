__all__ = ["Query"]

from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from status.status_shemes import Status
from .event import AllEvents
from callback.payload_schemes import Payload
from messages.message_schemes import Message, ContactMessage, Callback, Sender


class Query(BaseModel):
    event: Optional[AllEvents] = None
    message: Optional[Message | ContactMessage] = None
    contact_message: Optional[ContactMessage] = None
    callback: Optional[Callback] = None
    real_payload: Optional[Payload] = None
    user: Optional[Sender] = None
    status: Optional[Status] = None

    @property
    def payload(self) -> Payload | None:
        if self.real_payload is not None:
            return self.real_payload
        if self.callback is not None:
            return self.callback.payload
        if self.status is not None:
            return self.status.payload
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
    def payload_inner(self) -> tuple[str, ...] | None:
        if self.payload is not None:
            return self.payload.inner.value
        return None

    @property
    def sender(self) -> Sender | None:
        if self.user is not None:
            return self.user
        if self.message is not None:
            return self.message.sender
        return None
