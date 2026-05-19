from __future__ import annotations

from pydantic import BaseModel

from typing import Optional


class Message(BaseModel):
    pass


class Callback(BaseModel):
    timestamp: int
    callback_id: str


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