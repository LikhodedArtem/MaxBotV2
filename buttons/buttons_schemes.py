from __future__ import annotations

__all__ = [
    "Button",
    "CallbackButton",
    "LinkButton",
    "RequestGeoLocationButton",
    "RequestContactButton",
    "OpenAppButton",
    "MessageButton",
    "ClipboardButton",
]

from pydantic import BaseModel, Field
from typing import Optional, Union


class BaseButton(BaseModel):
    text: str = Field(..., min_length=1, max_length=128)


class CallbackButton(BaseButton):
    type: str = "callback"
    payload: str = Field(..., max_length=1024)

    @classmethod
    def create(cls, text: str, payload: str) -> CallbackButton:
        return cls(text=text, payload=payload)


class LinkButton(BaseButton):
    type: str = "link"
    url: str = Field(..., max_length=2048)

    @classmethod
    def create(cls, text: str, url: str) -> LinkButton:
        return cls(text=text, url=url)


class RequestGeoLocationButton(BaseButton):
    type: str = "request_geo_location"
    quick: Optional[bool]

    @classmethod
    def create(
        cls, text: str, quick: Optional[bool] = None
    ) -> RequestGeoLocationButton:
        return cls(text=text, quick=quick)


class RequestContactButton(BaseButton):
    type: str = "request_contact"

    @classmethod
    def create(cls, text: str) -> RequestContactButton:
        return cls(text=text)


class OpenAppButton(BaseButton):
    type: str = "open_app"
    wep_app: Optional[str]
    contact_id: Optional[int]
    payload: Optional[str]

    @classmethod
    def create(
        cls,
        text: str,
        wep_app: Optional[str] = None,
        contact_id: Optional[int] = None,
        payload: Optional[str] = None,
    ) -> OpenAppButton:
        return cls(text=text, wep_app=wep_app, contact_id=contact_id, payload=payload)


class MessageButton(BaseButton):
    type: str = "message"

    @classmethod
    def create(cls, text: str) -> MessageButton:
        return cls(text=text)


class ClipboardButton(BaseButton):
    payload: str = Field(..., max_length=1024)

    @classmethod
    def create(cls, text: str, payload: str) -> ClipboardButton:
        return cls(text=text, payload=payload)


Button = Union[
    CallbackButton,
    LinkButton,
    RequestGeoLocationButton,
    RequestContactButton,
    OpenAppButton,
    MessageButton,
    ClipboardButton,
]
