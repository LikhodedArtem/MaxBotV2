import asyncio
import inspect
import logging
from functools import wraps
from typing import Any, Awaitable, Callable, Optional

from broker.event import *
from broker.query import Query


Handler = Callable[..., Awaitable[None]]
Predicate = Callable[..., Awaitable[bool]]
Checker = Callable[[list[Query]], Awaitable[bool]]


class EventBroker:
    def __init__(self, checkers: Optional[Predicate | list[Predicate]] = None) -> None:
        self.subscribers: dict[AllEvents, dict[str, set | dict] | set[Handler]] = {}
        self.checkers = checkers if isinstance(checkers, list) else [checkers]

    def subscribe_on_event(self, event: AllEvents, handler: Handler) -> None:
        if not isinstance(event, PayloadEvent):
            if event not in self.subscribers:
                self.subscribers[event] = set()
            self.subscribers[event].add(handler)

        else:
            self.subscribe_on_payload_event(event, handler)

    def subscribe_on_payload_event(self, event: PayloadEvent, handler: Handler) -> None:
        if event.my_event not in self.subscribers:
            self.subscribers[event.my_event] = {"__handlers__": set()}

        current_node = self.subscribers[event.my_event]

        if hasattr(event, "name") and event.name is not None:
           if event.name not in current_node:
               current_node[event.name] = {"__handlers__": set()}
           current_node = current_node[event.name]

        if event.payload is None:
            pass
        else:
            payload = event.payload
            path = [payload.type, payload.action] + payload.inner.value

            for i, key in enumerate(path):
                if key not in current_node:
                    current_node[key] = {"__handlers__": set()}
                current_node = current_node[key]

        current_node["__handlers__"].add(handler)

    def unsubscribe_from_event(self, event: AllEvents, handler: Handler) -> None:
        if not isinstance(event, PayloadEvent):
            self.subscribers[event].discard(handler)
        else:
            self.unsubscribe_from_payload_event(event, handler)

    def unsubscribe_from_payload_event(self, event: PayloadEvent, handler: Handler) -> None:
        if event.my_event not in self.subscribers:
            return

        current_node = self.subscribers[event.my_event]

        if hasattr(event, "name") and event.name is not None:
            current_node = self.subscribers[event.name]

        if event.payload is None:
            pass
        else:
            payload = event.payload
            path = [payload.type, payload.action] + payload.inner.value

            for key in path:
                if key not in current_node:
                    return
                current_node = current_node[key]

        current_node["__handlers__"].discard(handler)

    def check(
        self,
        on_events: Optional[AllEvents | list[AllEvents]] = None,
        func: Optional[list[Predicate] | Predicate] = None,
    ) -> Callable[[Handler], Handler]:
        def decorator(handler: Handler) -> Handler:
            if func is None:
                function_list = []
            elif not isinstance(func, list):
                function_list = [func]
            else:
                function_list = func

            @wraps(handler)
            async def wrapper(query: Optional[Query] = None, **kwargs) -> None:
                try:
                    if query is not None:
                        if func is not None:
                            for function in function_list:
                                predicate_kwargs = self._build_handler_kwargs(function, query)
                                allowed = await function(**predicate_kwargs)
                                if not allowed:
                                    return

                        handler_kwargs = self._build_handler_kwargs(handler, query)
                        await handler(**handler_kwargs)

                    else:
                        if func is not None:
                            for function in function_list:
                                if not await function(**kwargs):
                                    return
                        await handler(**kwargs)

                except Exception:
                    logging.exception(
                        "Ошибка в handler '%s'",
                        handler.__name__,
                    )

            if on_events is not None:
                if isinstance(on_events, list):
                    events = on_events
                else:
                    events = [on_events]

                for event in events:
                    self.subscribe_on_event(event, wrapper)

            return wrapper

        return decorator

    def get_handlers_from_event(self, event: AllEvents):
        if not isinstance(event, PayloadEvent):
            return self.subscribers.get(event, set())
        else:
            return self.get_handlers_from_payload_event(event)

    def get_handlers_from_payload_event(self, event: PayloadEvent) -> set[Handler]:
        if event.my_event not in self.subscribers:
            return set()

        current_node = self.subscribers[event.my_event]

        handlers = current_node["__handlers__"]

        if hasattr(event, "name") and event.name is not None:
            current_node = current_node[event.name]

        if event.payload is None:
            pass
        else:
            payload = event.payload

            current_node = current_node[payload.type][payload.action]

            for inner_item in payload.inner.value:
                handlers |= current_node["__handlers__"]
                if inner_item in current_node:
                    current_node = current_node[inner_item]
                else:
                    return handlers

            handlers |= self.get_remain_handlers(current_node)

        return handlers


    def get_remain_handlers(self, subscribers: dict):
        handlers = set()
        for key in subscribers:
            if key == "__handlers__":
                handlers |= subscribers[key]
            else:
                handlers |= self.get_remain_handlers(subscribers[key])
        return handlers


    @staticmethod
    def _build_handler_kwargs(func: Callable[..., Any], query: Query, can_be_none: bool = True) -> dict[str, Any]:
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

                if not can_be_none:
                    if value is None and name != "status" and param.default is inspect.Parameter.empty:
                        raise ValueError(
                            f"Handler '{func.__name__}' ожидает '{name}', "
                            f"но в query это поле равно None"
                        )

                kwargs[name] = value

        return kwargs


    async def publish_queries(self, queries: list[Query]):
        for checker in self.checkers:
            if not await checker(queries): return

        await asyncio.gather(*(broker.publish(query) for query in queries))

    async def publish(self, query: Query) -> None:
        event = query.event

        all_handlers = self.get_handlers_from_event(event)

        if not all_handlers:
            return

        await asyncio.gather(*(handler(query) for handler in all_handlers))


from .broker_checkers import reg_checker

broker = EventBroker(checkers=reg_checker)