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


class LinkButton(BaseButton):
    type: str = "link"
    url: str = Field(..., max_length=2048)


class RequestGeoLocationButton(BaseButton):
    type: str = "request_geo_location"
    quick: Optional[bool]


class RequestContactButton(BaseButton):
    type: str = "request_contact"


class OpenAppButton(BaseButton):
    type: str = "open_app"
    wep_app: Optional[str]
    contact_id: Optional[int]
    payload: Optional[str]


class MessageButton(BaseButton):
    type: str = "message"


class ClipboardButton(BaseButton):
    payload: str = Field(..., max_length=1024)


Button = Union[
    CallbackButton,
    LinkButton,
    RequestGeoLocationButton,
    RequestContactButton,
    OpenAppButton,
    MessageButton,
    ClipboardButton,
]