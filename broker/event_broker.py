import asyncio
import inspect
import logging
from functools import wraps
from typing import Any, Awaitable, Callable, Optional, Literal

from fastapi.routing import get_request_handler

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
    def go_to_payload_inner(
            event: Status | AllEvents, action: Literal["create", "go"], current_node: dict
    ) -> None | dict:
        if hasattr(event, "name"):
            if hasattr(event, "name") and event.name is not None:
                if "__names__" not in current_node:
                    if action == "go":
                        return
                    current_node["__names__"] = {}
                current_node = current_node["__names__"]
                if event.name not in current_node:
                    if action == "go":
                        return
                    current_node[event.name] = {}
                current_node = current_node[event.name]

        payload = event.payload

        if payload is not None:
            if payload.type not in current_node:
                if action == "go":
                    return
                current_node[payload.type] = {"__handlers__": set()}

            current_node = current_node[payload.type]

            if payload.action not in current_node:
                if action == "go":
                    return
                current_node[payload.action] = {"__handlers__": set()}

            current_node = current_node[payload.action]
        return current_node

    def go_to_payload_event(
        self, event: Status | AllEvents, action: Literal["create", "go"], current_node: dict
    ) -> None | dict:
        current_node = self.go_to_payload_inner(event, action, current_node)

        payload = event.payload

        if payload is not None:
            if current_node is not None:
                for inner_item in event.payload.inner:
                    if inner_item not in current_node:
                        if action == "go":
                            return
                        current_node[inner_item] = {"__handlers__": set()}
                    current_node = current_node[inner_item]

        return current_node

    def subscribe_on_event_with_status(
        self, event: AllEvents, handler: Handler, status: Optional[Status]
    ) -> None:
        if status is None:
            self.subscribe_on_event(event, handler)
        else:
            if SubPayloadEvent.STATUS_CALLBACK not in self.subscribers:
                self.subscribers[SubPayloadEvent.STATUS_CALLBACK] = {}
            current_node = self.subscribers[SubPayloadEvent.STATUS_CALLBACK]

            current_node = self.go_to_payload_event(status, "create", current_node)

            self.subscribe_on_event(event, handler, current_node)

    def unsubscribe_on_event_with_status(
        self, event: AllEvents, handler: Handler, status: Optional[Status]
    ) -> None:
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

    def get_handlers_from_event_with_status(
        self, event: AllEvents, status: Optional[Status]
    ) -> set[Handler]:
        if status is None:
            return self.get_handlers_from_event(event)
        else:
            if SubPayloadEvent.STATUS_CALLBACK not in self.subscribers:
                return set()
            current_node = self.subscribers[SubPayloadEvent.STATUS_CALLBACK]
            current_node = self.go_to_payload_inner(status, "go", current_node)

            handlers = set()

            if current_node is None:
                return handlers

            if status.payload is not None:
                for inner_item in status.payload.inner:
                    handlers |= self.get_handlers_from_event(event, current_node)

                    if inner_item not in current_node:
                        return handlers
                    current_node = current_node[inner_item]

            return self.get_remain_status_handlers(event, current_node)

    def get_remain_status_handlers(self, event: AllEvents, current_node: dict) -> set[Handler]:
        handlers = self.get_handlers_from_event(event, current_node)
        for key in current_node:
            if isinstance(current_node[key], dict):
                handlers |= self.get_remain_status_handlers(event, current_node[key])
        return handlers

    def subscribe_on_event(
        self, event: AllEvents, handler: Handler, current: Optional[dict] = None
    ) -> None:
        current_node = self.current_to_node(current)

        if not isinstance(event, PayloadEvent):
            if event not in current_node:
                current_node[event] = set()
            current_node[event].add(handler)
        else:
            self.subscribe_on_payload_event(event, handler, current_node)

    def subscribe_on_payload_event(
        self, event: PayloadEvent, handler: Handler, current: Optional[dict] = None
    ) -> None:
        current_node = self.current_to_node(current)

        if event.sub_event not in current_node:
            current_node[event.sub_event] = {"__handlers__": set()}

        current_node = current_node[event.sub_event]

        current_node = self.go_to_payload_event(event, "create", current_node)

        current_node["__handlers__"].add(handler)

    def unsubscribe_from_event(
        self, event: AllEvents, handler: Handler, current: Optional[dict] = None
    ) -> None:
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
        """Используется для получения всех handler'ов для всех видов событий.
        Для подписчиков на статус подразумевает получение положения уже в этом статусе,
        что реализуется через get_handlers_from_event_with_status

        Args:
            event: Любое событие, из которого мы хоти получить подписчиков
            current: Текущее положение для поисков подписчиков

        Returns:
            Множество найденных handler'ов

        """

        current_node = self.current_to_node(current)

        if not isinstance(event, PayloadEvent):
            return current_node.get(event, set())
        else:
            smth = self.get_handlers_from_payload_event(event, current_node)
            return smth

    def get_handlers_from_payload_event(
        self, event: PayloadEvent, current: Optional[dict] = None
    ) -> set[Handler]:
        """Используется для получения всех handler'ов через подписку на payload.
        Для подписчиков на статус подразумевает получение положения уже в этом статусе,
        что реализуется через get_handlers_from_event_with_status

        Args:
            event: Payload событие, из которого мы хоти получить подписчиков
            current: Текущее положение для поисков подписчиков

        Returns:
            Множество найденных handler'ов
        """

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

    def get_remain_handlers(self, current_node: dict) -> set[Handler]:
        """По системе получения подписчиков через Inner: когда
        мы нашли нужного подписчика через объекты Inner, необходимо "добрать"
        все оставшиеся handler'ы нашего события, что и делает данная функция

        Args:
            current_node: текущая позиция в подписчиках брокера

        Returns:
            Множество всех найденных handler'ов
        """

        handlers = set()
        for key in current_node:
            if isinstance(key, SubPayloadEvent):
                return handlers
            if key == "__handlers__":
                handlers |= current_node[key]
            elif isinstance(current_node[key], dict):
                handlers |= self.get_remain_handlers(current_node[key])
        return handlers

    def current_to_node(self, current: Optional[dict]) -> dict:
        """Вспомогательная функция. Позволяет определиться с
        выбором текущей позиции (current_node)в подписчиках брокера

        current:
            None -> self.subscribers\n
            dict -> dict

        Args:
            current: текущая позиция в подписчиках брокера

        Returns:
            Выбранное положение в подписчиках брокера
        """

        if current is None:
            return self.subscribers
        return current

    def check(
        self,
        on_events: Optional[AllEvents | list[AllEvents]] = None,
        allowed: Optional[
            Status
            | list[Status]
            | dict[str, str]
            | list[dict[str, str] | str | list[str]]
        ] = None,
        without_allowed: bool = True,
        checkers: Optional[list[Predicate] | Predicate] = None,
        checkers_kwargs: Optional[dict | list[dict]] = None,
        can_be_none: bool = False,
        compare_uuids: bool = False,
    ) -> Callable[[Handler], Handler]:
        """Многофункциональный декоратор, который является главной возможностью взаимодействовать
        с брокером событий.

        Args:
            on_events: Событие или список событий, на которые будет подписана функция
            allowed: Статус или список статусов
            without_allowed: Подписывать ли handler на те же события без статусов, что и со статусами
            checkers: Функция или список функций. Если не все функции вернули True, то функция подписчик выполняться не будет
            checkers_kwargs: kwargs передаваемые в checkers
            can_be_none: Из query в handler передаются различные ключи. Этот атрибут определяет, вызывать ли ошибку, если атрибут пуст
            compare_uuids: Если у статуса и у callback есть uuid, и они разные, handler просто не выполниться
        """

        def decorator(handler: Handler) -> Handler:
            if checkers is None:
                function_list = []
            if not isinstance(checkers, list):
                function_list = [checkers]
            else:
                function_list = checkers

            if checkers_kwargs is None:
                kwargs_list = []
            elif not isinstance(checkers, list):
                kwargs_list = [checkers_kwargs]
            else:
                kwargs_list = checkers_kwargs

            if checkers_kwargs is not None:
                if len(function_list) != len(kwargs_list):
                    raise ValueError("Неправильно переданы checkers или checkers_kwargs в check")

            @wraps(handler)
            async def wrapper(query: Optional[Query] = None, **kwargs) -> None:
                try:
                    if query is not None:
                        if checkers is not None:
                            for i, function in enumerate(function_list):
                                predicate_kwargs = self._build_handler_kwargs(
                                    function, query, True
                                )
                                if checkers_kwargs is not None:
                                    predicate_kwargs |= kwargs_list[i]
                                if not await function(**predicate_kwargs):
                                    return

                        if compare_uuids:
                            su = query.status_uuid
                            cu = query.callback_uuid
                            if su is not None and cu is not None and su != cu:
                                return

                        handler_kwargs = self._build_handler_kwargs(handler, query, can_be_none)
                        await handler(**handler_kwargs)

                    else:
                        if checkers is not None:
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

                if isinstance(allowed_statuses[0], Status):
                    allowed_statuses = set(allowed_statuses)
                elif isinstance(allowed_statuses[0], dict):
                    allowed_statuses = set(
                        map(lambda x: Status(payload=Payload(**x)), allowed_statuses)
                    )
                elif isinstance(allowed_statuses[0], str):
                    allowed_statuses = set(
                        map(lambda x: Status(name=x), allowed_statuses)
                    )
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
                if allowed_statuses is not None and without_allowed:
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
            "status_payload": query.status_payload,
            "status_type": query.status_type,
            "status_uuid": query.status_uuid,
            "status_action": query.status_action,
            "status_inner": query.status_inner,
            "callback_payload": query.callback_payload,
            "callback_type": query.callback_type,
            "callback_uuid": query.callback_uuid,
            "callback_action": query.callback_action,
            "callback_inner": query.callback_inner,
            "status": query.status,
            "sender": query.sender,
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
