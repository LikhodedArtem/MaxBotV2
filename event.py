import asyncio
import inspect
import logging

from collections import defaultdict

from enum import Enum, auto
from typing import Any, Callable, Awaitable, Optional
from uuid import UUID

from pydantic import BaseModel

from messages.message_schemes import Message, ContactMessage, Callback


class Event(Enum):
    MESSAGE_CREATED = auto()
    MESSAGE_CALLBACK = auto()


class Query(BaseModel):
    event: Event
    message: Optional[Message] = None
    contact_message: Optional[ContactMessage] = None
    callback: Optional[Callback] = None


Handler = Callable[..., Awaitable[None]]


class EventBroker:
    def __init__(self):
        self.subscribers: dict[Event, set[Handler]] = defaultdict(set)

    def subscribe(self, event: Event, handler: Handler) -> None:
        self.subscribers[event].add(handler)

    def unsubscribe(self, event: Event, handler: Handler) -> None:
        self.subscribers[event].discard(handler)

    def check(
        self,
        on_event: Event,
        func: Optional[Callable[[Any], Awaitable[bool]]] = None,
        args: Optional[tuple[Any]] = None,
    ):
        def decorator(handler: Handler) -> Handler:
            async def wrapper(query: Query) -> None:
                if None not in (func, args):
                    kwargs = self._build_handler_kwargs(handler, query)
                    allowed = await func(*args, **kwargs)
                    if not allowed:
                        return

                try:
                    kwargs = self._build_handler_kwargs(handler, query)
                    await handler(**kwargs)
                except Exception as e:
                    logging.exception(
                        "Неизвестная ошибка в handler '%s'",
                        handler.__name__,
                    )

            self.subscribe(on_event, wrapper)

            return wrapper

        return decorator

    @staticmethod
    def _build_handler_kwargs(handler: Handler, query: Query) -> dict[str, Any]:
        sig = inspect.signature(handler)

        available = {
            "query": query,
            "event": query.event,
            "message": query.message,
            "contact_message": query.contact_message,
            "callback": query.callback,
        }

        kwargs = {}

        for name, param in sig.parameters.items():
            if name in available:
                value = available[name]

                if value is None and param.default is inspect.Parameter.empty:
                    raise ValueError(
                        f"Handler '{handler.__name__}' ожидает '{name}', "
                        f"но в query это поле равно None"
                    )

                kwargs[name] = value

        return kwargs

    async def start(self, query: Query) -> None:
        handlers = self.subscribers.get(query.event, set())
        if not handlers:
            return

        await asyncio.gather(*(handler(query) for handler in handlers))
