import asyncio
import inspect
import logging
from functools import wraps
from typing import Any, Awaitable, Callable, Optional, Literal

from broker.event import *
from broker.query import Query
from callback.payload_schemes import Payload
from status.status_shemes import Status

Handler = Callable[..., Awaitable[None]]
Predicate = Callable[..., Awaitable[bool]]
Checker = Callable[[list[Query]], Awaitable[bool]]


class EventBroker:
    def __init__(self, checkers: Optional[Predicate | list[Predicate]] = None) -> None:
        self.subscribers: dict[AllEvents, dict[str, set | dict] | set[Handler]] = {}
        self.checkers = checkers if isinstance(checkers, list) else [checkers]

    @staticmethod
    def go_to_payload_event(event: Status | AllEvents, action: Literal["create", "go"], current_node: dict) -> None | dict:
        if hasattr(event, "name"):
            if hasattr(event, "name") and event.name is not None:
                if "__names__" not in current_node:
                    if action == "go": return
                    current_node["__names__"] = {}
                current_node = current_node["__names__"]
                if event.name not in current_node:
                    if action == "go": return
                    current_node[event.name] = {}
                current_node = current_node[event.name]

        payload = event.payload

        if payload is not None:
            if payload.type not in current_node:
                if action == "go": return
                current_node[payload.type] = {"__handlers__": set()}

            current_node = current_node[payload.type]

            if payload.action not in current_node:
                if action == "go": return
                current_node[payload.action] = {"__handlers__": set()}

            current_node = current_node[payload.action]

            for inner_item in payload.inner:
                if inner_item not in current_node:
                    if action == "go": return
                    current_node[inner_item] = {"__handlers__": set()}
                current_node = current_node[inner_item]

        return current_node


    def subscribe_on_event_with_status(self, event: AllEvents, handler: Handler, status: Optional[Status]) -> None:
        if status is None:
            self.subscribe_on_event(event, handler)
        else:
            if SubPayloadEvent.STATUS_CALLBACK not in self.subscribers:
                self.subscribers[SubPayloadEvent.STATUS_CALLBACK] = {}
            current_node = self.subscribers[SubPayloadEvent.STATUS_CALLBACK]

            current_node = self.go_to_payload_event(status, "create", current_node)

            self.subscribe_on_event(event, handler, current_node)

    def unsubscribe_on_event_with_status(self, event: AllEvents, handler: Handler, status: Optional[Status]) -> None:
        if status is None:
            self.unsubscribe_from_event(event, handler)
        else:
            if SubPayloadEvent.STATUS_CALLBACK not in self.subscribers:
                return
            current_node = self.subscribers[SubPayloadEvent.STATUS_CALLBACK]

            current_node = self.go_to_payload_event(status, "go", current_node)

            if current_node is None:
                return

            self.unsubscribe_from_event(event, handler, current_node)

    def get_handlers_from_event_with_status(self, event: AllEvents, status: Optional[Status]) -> set[Handler]:
        if status is None:
            return self.get_handlers_from_event(event)
        else:
            if SubPayloadEvent.STATUS_CALLBACK not in self.subscribers:
                return set()
            current_node = self.subscribers[SubPayloadEvent.STATUS_CALLBACK]

            current_node = self.go_to_payload_event(status, "go", current_node)

            if current_node is None:
                return set()

            return self.get_handlers_from_event(event, current_node)

    def subscribe_on_event(self, event: AllEvents, handler: Handler, current: Optional[dict] = None) -> None:
        current_node = self.current_to_node(current)

        if not isinstance(event, PayloadEvent):
            if event not in current_node:
                current_node[event] = set()
            current_node[event].add(handler)
        else:
            self.subscribe_on_payload_event(event, handler, current_node)

    def subscribe_on_payload_event(self, event: PayloadEvent, handler: Handler, current: Optional[dict] = None) -> None:
        current_node = self.current_to_node(current)

        if event.sub_event not in current_node:
            current_node[event.sub_event] = {"__handlers__": set()}

        current_node = current_node[event.sub_event]

        print(handler, event.payload)

        current_node = self.go_to_payload_event(event, "create", current_node)

        current_node["__handlers__"].add(handler)

    def unsubscribe_from_event(self, event: AllEvents, handler: Handler, current: Optional[dict] = None) -> None:
        current_node = self.current_to_node(current)

        if not isinstance(event, PayloadEvent):
            current_node[event].discard(handler)
        else:
            self.unsubscribe_from_payload_event(event, handler, current_node)

    def unsubscribe_from_payload_event(
        self, event: PayloadEvent, handler: Handler, current: Optional[dict] = None
    ) -> None:
        current_node = self.current_to_node(current)

        if event.sub_event not in current_node:
            return
        current_node = current_node[event.sub_event]

        current_node = self.go_to_payload_event(event, "go", current_node)

        current_node["__handlers__"].discard(handler)

    def get_handlers_from_event(self, event: AllEvents, current: Optional[dict] = None):
        current_node = self.current_to_node(current)

        if not isinstance(event, PayloadEvent):
            return current_node.get(event, set())
        else:
            return self.get_handlers_from_payload_event(event, current_node)

    def get_handlers_from_payload_event(self, event: PayloadEvent, current: Optional[dict] = None) -> set[Handler]:
        current_node = self.current_to_node(current)

        if event.sub_event not in current_node:
            return set()
        current_node = current_node[event.sub_event]

        handlers = set()

        if hasattr(event, "name") and event.name is not None:
            current_node = current_node["__names__"][event.name]

        if event.payload is None:
            pass
        else:
            payload = event.payload

            if payload.type not in current_node:
                return handlers

            current_node = current_node[payload.type]

            if payload.action not in current_node:
                return handlers

            current_node = current_node[payload.action]

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
            if isinstance(key, AllEvents):
                pass
            if key == "__handlers__":
                handlers |= subscribers[key]
            else:
                handlers |= self.get_remain_handlers(subscribers[key])
        return handlers

    def current_to_node(self, current: dict):
        if current is None:
            return self.subscribers
        return current

    def check(
        self,
        on_events: Optional[AllEvents | list[AllEvents]] = None,
        allowed: Optional[Status | list[Status] | dict[str, str] | list[dict[str, str] | str | list[str]]] = None,
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
                                predicate_kwargs = self._build_handler_kwargs(
                                    function, query
                                )
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
            if allowed is not None:
                if not isinstance(allowed, list):
                    allowed_statuses = [allowed]
                else:
                    allowed_statuses = allowed

                if isinstance(allowed[0], Status):
                     pass
                elif isinstance(allowed[0], dict):
                    allowed_statuses = list(map(lambda x: Status(payload=Payload(**x)), allowed_statuses))
                elif isinstance(allowed[0], str):
                    allowed_statuses = list(map(lambda x: Status(name=x), allowed_statuses))
                else:
                    raise ValueError(f"Передан не верный формат allowed: {allowed}")
            else:
                allowed_statuses = None

            if on_events is not None:
                if isinstance(on_events, list):
                    events = on_events
                else:
                    events = [on_events]

                if allowed_statuses is not None:
                    for status in allowed_statuses:
                        for event in events:
                            self.subscribe_on_event_with_status(event, wrapper, status)
                else:
                    for event in events:
                        self.subscribe_on_event(event, wrapper)

            return wrapper

        return decorator

    @staticmethod
    def _build_handler_kwargs(
        func: Callable[..., Any], query: Query, can_be_none: bool = False
    ) -> dict[str, Any]:
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
                    if (
                        value is None
                        and name != "status"
                        and param.default is inspect.Parameter.empty
                    ):
                        raise ValueError(
                            f"Handler '{func.__name__}' ожидает '{name}', "
                            f"но в query это поле равно None"
                        )

                kwargs[name] = value

        return kwargs

    async def publish_queries(self, queries: list[Query]):
        for checker in self.checkers:
            if not await checker(queries):
                return

        await asyncio.gather(*(broker.publish(query) for query in queries))

    async def publish(self, query: Query) -> None:
        event = query.event
        status = query.status

        all_handlers = self.get_handlers_from_event_with_status(event, status)


        if not all_handlers:
            return

        await asyncio.gather(*(handler(query) for handler in all_handlers))


from .broker_checkers import reg_checker

broker = EventBroker(checkers=reg_checker)
