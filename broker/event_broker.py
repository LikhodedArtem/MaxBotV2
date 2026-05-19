import asyncio
import inspect
import logging
from collections import defaultdict
from functools import wraps
from typing import Any, Awaitable, Callable, Optional
from uuid import UUID

from pydantic import BaseModel

from broker.event import Event, CommandEvent
from messages.message_schemes import Message, ContactMessage, Callback
from callback.payload_schemes import Payload
from status.status_shemes import Status


class Query(BaseModel):
    event: Optional[Event | CommandEvent] = None
    status: Optional[Status] = None
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
        self.subscribers: dict[Event | str, set[Handler] | dict] = {}

    def subscribe_on_event(self, event: Event, handler: Handler) -> None:
        if event not in self.subscribers:
            self.subscribers[event] = set()
        self.subscribers[event].add(handler)

    def subscribe_on_status(self, status: Status, handler: Handler) -> None:
        current_node = self.subscribers

        if isinstance(status.value, str):
            path = [status.value]
        else:
            payload = status.value
            path = [payload.type, payload.action] + payload.inner.value

        for i, key in enumerate(path):
            if key not in current_node:
                current_node[key] = {}
            current_node = current_node[key]

            if i > 0 and "__handlers__" not in current_node:
                current_node["__handlers__"] = set()

        current_node["__handlers__"].add(handler)

    def unsubscribe_on_event(self, event: Event | CommandEvent, handler: Handler) -> None:
        self.subscribers[event].discard(handler)

    def unsubscribe_on_status(self, status: Status, handler: Handler) -> None:
        current_node = self.subscribers

        if isinstance(status.value, str):
            path = [status.value]
        else:
            payload = status.value
            path = [payload.type, payload.action] + payload.inner.value

        for key in path:
            if key not in current_node:
                return
            current_node = current_node[key]

        current_node["__handlers__"].discard(handler)

    def check(
        self,
        on_event: Optional[Event | CommandEvent | list[Event | CommandEvent]] = None,
        on_status: Optional[str | dict[str, str] | list[str | dict[str, str]]] = None,
        func: Optional[list[Predicate] | Predicate] = None,
        args: Optional[list[tuple[Any, ...] | tuple[Any, ...]]] = None,
    ) -> Callable[[Handler], Handler]:
        def decorator(handler: Handler) -> Handler:
            @wraps(handler)
            async def wrapper(query: Query) -> None:
                try:
                    if func is not None:
                        if not isinstance(func, list):
                            function_list = [func]
                        else:
                            function_list = func

                        if not isinstance(args, list):
                            args_list = [args]
                        else:
                            args_list = args

                        for i, function in enumerate(function_list):
                            predicate_kwargs = self._build_handler_kwargs(function, query)
                            allowed = await function(*(args_list[i] or ()), **predicate_kwargs)
                            if not allowed:
                                return


                    handler_kwargs = self._build_handler_kwargs(handler, query)
                    await handler(**handler_kwargs)

                except Exception:
                    logging.exception(
                        "Неизвестная ошибка в handler '%s'",
                        handler.__name__,
                    )

            if on_event is not None:
                if isinstance(on_event, list):
                    events = on_event
                else:
                    events = [on_event]

                for event in events:
                    self.subscribe_on_event(event, wrapper)

            if on_status is not None:
                if isinstance(on_status, list):
                    statuses = on_status
                else:
                    statuses = [on_status]

                for status in statuses:
                    self.subscribe_on_status(Status(value=status), wrapper)

            return wrapper

        return decorator

    def get_handlers_on_status(self, status: Optional[Status]) -> set[Handler]:
        if status is None:
            return set()

        current_node = self.subscribers

        if isinstance(status.value, str):
            return current_node[status.value]["__handlers__"]
        else:
            handlers = set()

            payload = status.value

            current_node = current_node[payload.type][payload.action]

            for inner_item in payload.inner.value:
                handlers |= current_node["__handlers__"]
                if inner_item in current_node:
                    current_node = current_node[inner_item]
                else:
                    return handlers

            handlers |= self.get_all_handlers(current_node)

            print("===get_all_handlers", self.get_all_handlers(current_node))

            return handlers


    def get_all_handlers(self, subscribers: dict):
        handlers = set()
        for key in subscribers:
            if key == "__handlers__":
                handlers |= subscribers[key]
            else:
                handlers |= self.get_all_handlers(subscribers[key])
        return handlers


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
            "status": query.status,
        }

        kwargs = {}

        for name, param in sig.parameters.items():
            if name in available:
                value = available[name]

                if value is None and name != "status" and param.default is inspect.Parameter.empty:
                    raise ValueError(
                        f"Handler '{func.__name__}' ожидает '{name}', "
                        f"но в query это поле равно None"
                    )

                kwargs[name] = value

        return kwargs

    async def publish(self, query: Query) -> None:
        status = query.status
        event = query.event
        if status is None or status.is_background:
            event_handlers = self.subscribers.get(event, set())
        else:
            event_handlers = set()

        if status is not None and status.send_callback:
            status_handlers = self.get_handlers_on_status(status)
        else:
            status_handlers = set()

        all_handlers = event_handlers | status_handlers

        print("===publish", status)
        print("===publish", self.subscribers)

        if not all_handlers:
            return

        await asyncio.gather(*(handler(query) for handler in all_handlers))


broker = EventBroker()