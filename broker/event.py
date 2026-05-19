from __future__ import annotations

__all__ = ["Event", "CommandEvent"]

from enum import Enum, auto
from dataclasses import dataclass

@dataclass(frozen=True)
class CommandEvent:
    command: str

class Event(Enum):
    MESSAGE_CREATED = auto()
    MESSAGE_CALLBACK = auto()
    MESSAGE_COMMAND = auto()

    def __call__(self, command: str) -> CommandEvent:
        if self == Event.MESSAGE_COMMAND:
            return CommandEvent(command)
        raise TypeError(f"Событие {self.name} нельзя вызвать с аргументом")