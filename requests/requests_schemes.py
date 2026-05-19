from __future__ import annotations

__all__ = ["NewMessageData"]

from abc import ABC, abstractmethod
from typing import Optional, Literal, Any, Union

from pydantic import BaseModel, Field, field_validator

from buttons.keyboards import Keyboard


class MixinMyRequest(BaseModel, ABC):
    url: str
    params: dict[str, Any]
    headers: dict[str, str]

    @abstractmethod
    async def json_data(self) -> dict[str, Any]:
        pass


class MyRequest(MixinMyRequest):
    data: NewMessageData = Field(alias="json")

    async def json_data(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "params": self.params,
            "headers": self.headers,
            "json": (
                self.data
                if not isinstance(self.data, NewMessageData)
                else self.data.model_dump()
            ),
        }

    @field_validator("data", mode="before")
    @classmethod
    def data_to_form(cls, v: dict[str, Any] | NewMessageData) -> NewMessageData:
        if isinstance(v, dict):
            return NewMessageData(**v)
        return v


class MyDeleteRequest(MixinMyRequest):
    async def json_data(self) -> dict[str, Any]:
        return {"url": self.url, "params": self.params, "headers": self.headers}


class NewMessageData(BaseModel):
    text: str
    attachments: Optional[list[Attachments]]
    # link: Optional[str] = None # Не доделано
    notify: Optional[bool] = True
    format: Literal["html", "markdown"] = "html"


class FilePayload(BaseModel):
    token: Optional[str]


class ImagePayload(BaseModel):
    token: Optional[str]
    url: Optional[str] = Field(..., min_length=1)
    photos: str  # Не доделано


class VideoPayload(BaseModel):
    token: Optional[str]


class AudioPayload(BaseModel):
    token: Optional[str]


class StickerPayload(BaseModel):
    code: str
    token: Optional[str]


class ContactPayload(BaseModel):
    name: str | None
    contact_id: Optional[int]
    vcf_info: Optional[str]
    vcf_phone: Optional[str]


class InlineKeyboardPayload(BaseModel):
    buttons: Keyboard = None


class Attachments(BaseModel):
    type: str

    payload: Optional[
        Union[
            FilePayload,
            ImagePayload,
            VideoPayload,
            AudioPayload,
            StickerPayload,
            ContactPayload,
            InlineKeyboardPayload,
        ]
    ] = None

    @classmethod
    def create(
            cls,
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
            data: Optional[dict[str, Any]] = None
    ) -> list[Attachments] | None:

        if type == "base_text":
            return None

        if data is None:
            raise ValueError(f"Для типа Attachments: {type} не был указан payload")

        payloads = {
            "file": FilePayload,
            "image": ImagePayload,
            "video": VideoPayload,
            "audio": AudioPayload,
            "sticker": StickerPayload,
            "contact": ContactPayload,
            "inline_keyboard": InlineKeyboardPayload,
        }
        payload = payloads[type](**data)

        return [cls(type=type, payload=payload)]