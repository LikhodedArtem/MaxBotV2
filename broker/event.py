from __future__ import annotations

__all__ = ["Event", "AllEvents", "PayloadEvent", "SubPayloadEvent"]

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional

from click import command
from pydantic import BaseModel, ConfigDict

from callback.payload_schemes import Payload


class Event(Enum):
    BOT_STARTED = auto()

    BOT_STOPPED = auto()
    DIALOG_REMOVED = auto()

    MESSAGE_CREATED = auto()
    MESSAGE_CALLBACK = auto()
    MESSAGE_COMMAND = auto()

    STATUS_CALLBACK = auto()

    def __call__(self, *args, **kwargs) -> AllEvents:
        if self == Event.MESSAGE_CREATED:
            if len(args) > 0 and isinstance(args[0], str):
                return MessageEvent(text=args[0])
            if "text" in kwargs and isinstance(kwargs["text"], str):
                return MessageEvent(text=kwargs["text"])

            raise ValueError("Не правильный формат данных для MESSAGE_CREATED")

        if self == Event.MESSAGE_COMMAND:
            if len(args) > 0 and isinstance(args[0], str):
                return CommandEvent(command=args[0])
            if "command" in kwargs and isinstance(kwargs["command"], str):
                return CommandEvent(command=kwargs["command"])

            raise ValueError("Не правильный формат данных для MESSAGE_COMMAND")

        if self == Event.MESSAGE_CALLBACK:
            payload = kwargs["payload"] if "payload" in kwargs else None

            if payload is None:
                return MessageCallback(payload=None)
            if isinstance(payload, Payload):
                return MessageCallback(payload=payload)
            if isinstance(kwargs["payload"], dict):
                payload: dict
                return MessageCallback(payload=Payload(**payload))

            raise ValueError("Не правильный формат данных для MESSAGE_CALLBACK")

        if self == Event.STATUS_CALLBACK:
            name = kwargs["name"] if "name" in kwargs else None
            payload = kwargs["payload"] if "payload" in kwargs else None

            if payload is None:
                return StatusCallback(name=name, payload=None)
            if isinstance(payload, Payload):
                return StatusCallback(name=name, payload=payload)
            if isinstance(kwargs["payload"], dict):
                payload: dict
                return StatusCallback(name=name, payload=Payload(**payload))

            raise ValueError("Не правильный формат данных для STATUS_CALLBACK")

        raise TypeError(f"Событие {self.name} нельзя вызвать с аргументом")


class MessageEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str


class CommandEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    command: str


class PayloadEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    sub_event: Event
    payload: Optional[Payload] = None


class SubPayloadEvent(Enum):
    STATUS_CALLBACK = auto()
    MESSAGE_CALLBACK = auto()


class StatusCallback(PayloadEvent):
    sub_event: Event = SubPayloadEvent.STATUS_CALLBACK
    name: Optional[str] = None


class MessageCallback(PayloadEvent):
    sub_event: Event = SubPayloadEvent.MESSAGE_CALLBACK


AllEvents = MessageEvent | CommandEvent | StatusCallback | MessageCallback | Event
