from __future__ import annotations

__all__ = ["Message", "ContactMessage", "Callback", "Sender"]

from typing import Optional, Literal, Any

from pydantic import BaseModel, field_validator

from callback.payload_schemes import Payload
from callback.payload_functions import restore_payload
from requests.requests_schemes import NewMessageData, Attachments


class MessageMixin:
    @staticmethod
    def create_message(
        text: str,
        type: Literal[
            "base_text",
            "video",
            "audio",
            "file",
            "sticker",
            "contact",
            "inline_keyboard",
            "location",
        ] = "base_text",
        link: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        notify: Optional[bool] = True,
        format: Literal["html", "markdown"] = "html",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> NewMessageData:
        # cords = (latitude, longitude)
        # attachments_data = {"type": type, "payload": payload} if await is_use_first(payload, cords) \
        #     else {"type": type, "latitude": latitude, "longitude": longitude}

        attachments = Attachments.create(type, payload)

        message_data = NewMessageData(
            text=text, attachments=attachments, notify=notify, format=format
        )

        return message_data


class Message(BaseModel):
    pass


class Callback(BaseModel):
    timestamp: int
    callback_id: str
    payload: Optional[Payload]
    user: Sender
    type: Literal["button", "status"] = "button"

    @field_validator("payload", mode="before")
    @classmethod
    def payload(cls, v: str | Payload) -> Payload:
        if isinstance(v, str):
            return restore_payload(v)
        return v

    async def answer(
        self,
        notification: str = "",
        text: Optional[str] = None,
        type: Literal[
            "base_text",
            "video",
            "audio",
            "file",
            "sticker",
            "contact",
            "inline_keyboard",
            "location",
        ] = "base_text",
        link: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        notify: Optional[bool] = True,
        format: str = "html",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> None:
        if text != None:
            message_data = await MessageMixin.create_message(
                text, type, link, payload, notify, format, latitude, longitude
            )
        else:
            message_data = None

        await callback_answer(self.callback_id, message_data, notification)


class ContactMessage(BaseModel):
    pass


class Sender(BaseModel):
    user_id: int
    first_name: str
    last_name: Optional[str] = None
    is_bot: bool
    last_activity_time: int
    username: Optional[str] = None
    name: Optional[str] = None

    # status: Optional[Status] = None
