from __future__ import annotations

__all__ = ["Message", "ContactMessage", "Callback", "Sender"]

from typing import Optional, Literal, Any

from pydantic import BaseModel, field_validator

from callback.payload_schemes import Payload
from callback.payload_functions import restore_payload
from core.config import bot_info
from requests.requests_schemes import NewMessageData, Attachments
from requests.requests_functions import *
from status.status_shemes import *
from status.status_crud import *


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


class MessageMixin(BaseModel):
    recipient: Recipient
    timestamp: int
    sender: Sender

    @property
    def my_status(self) -> Status | None:
        return get_status(self.sender.user_id)

    async def answer(
        self,
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
    ) -> Message:
        message_data = create_message(
            text, type, link, payload, notify, format, latitude, longitude
        )

        response = await send_message(message_data, chat_id=self.recipient.chat_id)
        message = response.json()["message"]
        message = Message(**message)
        return message

    async def edit(
        self,
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
    ) -> None:
        message_data = create_message(
            text, type, link, payload, notify, format, latitude, longitude
        )

        await edit_message(message_data, self.body.mid)

    async def delete(self):
        await delete_message(self.body.mid)

    async def status(
            self, status: Status | str, is_background: bool = False, send_callback: bool = True
    ) -> None:
        user_id = (
            self.sender.user_id
            if self.sender.user_id != bot_info.my_id
            else self.recipient.user_id
        )

        if isinstance(status, str):
            status = Status(value=status, is_background=is_background, send_callback=send_callback)
        else:
            status = Status(value=status.value, is_background=is_background, send_callback=send_callback)

        from status.status_crud import set_status

        await set_status(user_id, status)

    async def clear_status(self):
        user_id = (
            self.sender.user_id
            if self.sender.user_id != bot_info.my_id
            else self.recipient.user_id
        )

        from status.status_crud import clear_status

        await clear_status(user_id)


class Message(MessageMixin):
    body: Body


class ContactMessage(MessageMixin):
    body: ContactBody



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
        format: Literal["html", "markdown"] = "html",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> None:
        if text != None:
            message_data = create_message(
                text, type, link, payload, notify, format, latitude, longitude
            )
        else:
            message_data = None

        await callback_answer(self.callback_id, message_data, notification)


class Sender(BaseModel):
    user_id: int
    first_name: str
    last_name: Optional[str] = None
    is_bot: bool
    last_activity_time: int
    username: Optional[str] = None
    name: Optional[str] = None

    # status: Optional[Status] = None


class Recipient(BaseModel):
    chat_id: int
    chat_type: str
    user_id: int


class Body(BaseModel):
    mid: str
    seq: int
    text: str


class ContactBody(Body):
    attachments: list[ContactAttachment]


class ContactAttachment(BaseModel):
    payload: ContactPayload
    type: str


class ContactPayload(BaseModel):
    vcf_info: str
    max_info: Sender
    hash: str