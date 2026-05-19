__all__ = ["Event"]

from enum import Enum, auto

class Event(Enum):
    MESSAGE_CREATED = auto()
    MESSAGE_CALLBACK = auto()