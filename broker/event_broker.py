import asyncio
import inspect
import logging
from collections import defaultdict
from functools import wraps
from typing import Any, Awaitable, Callable, Optional
from uuid import UUID

from pydantic import BaseModel

from broker.event import Event
from messages.message_schemes import Message, ContactMessage, Callback
from callback.payload_schemes import Payload


class Query(BaseModel):
    event: Event
    message: Optional[Message] = None
    contact_message: Optional[ContactMessage] = None
    callback: Optional[Callback] = None

    @property
    def payload(self) -> Payload | None:
        if self.callback is not None:
            return self.callback.payload
        return None

    @property
    def payload_type(self) -> str | None:
        if self.payload is not None:
            return self.payload.type
        return None

    @property
    def payload_uuid(self) -> UUID | None:
        if self.payload is not None:
            return self.payload.uuid
        return None

    @property
    def payload_action(self) -> str | None:
        if self.payload is not None:
            return self.payload.action
        return None

    @property
    def payload_inner(self) -> list[str] | None:
        if self.payload is not None:
            return self.payload.inner.value
        return None


Handler = Callable[..., Awaitable[None]]
Predicate = Callable[..., Awaitable[bool]]


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
        func: Optional[Predicate] = None,
        args: Optional[tuple[Any, ...]] = None,
    ) -> Callable[[Handler], Handler]:
        def decorator(handler: Handler) -> Handler:
            @wraps(handler)
            async def wrapper(query: Query) -> None:
                try:
                    if func is not None:
                        predicate_kwargs = self._build_handler_kwargs(func, query)
                        allowed = await func(*(args or ()), **predicate_kwargs)
                        if not allowed:
                            return

                    handler_kwargs = self._build_handler_kwargs(handler, query)
                    await handler(**handler_kwargs)

                except Exception:
                    logging.exception(
                        "Неизвестная ошибка в handler '%s'",
                        handler.__name__,
                    )

            self.subscribe(on_event, wrapper)
            return wrapper

        return decorator

    @staticmethod
    def _build_handler_kwargs(func: Callable[..., Any], query: Query) -> dict[str, Any]:
        sig = inspect.signature(func)

        available = {
            "query": query,
            "event": query.event,
            "message": query.message,
            "contact_message": query.contact_message,
            "callback": query.callback,
            "payload": query.payload,
            "payload_type": query.payload_type,
            "payload_uuid": query.payload_uuid,
            "payload_action": query.payload_action,
            "payload_inner": query.payload_inner,
        }

        kwargs = {}

        for name, param in sig.parameters.items():
            if name in available:
                value = available[name]

                if value is None and param.default is inspect.Parameter.empty:
                    raise ValueError(
                        f"Handler '{func.__name__}' ожидает '{name}', "
                        f"но в query это поле равно None"
                    )

                kwargs[name] = value

        return kwargs

    async def publish(self, query: Query) -> None:
        handlers = self.subscribers.get(query.event, set())
        if not handlers:
            return

        await asyncio.gather(*(handler(query) for handler in handlers))


broker = EventBroker()