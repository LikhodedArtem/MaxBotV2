__all__ = ["add_status_query", "create_status"]

from copy import deepcopy
from datetime import datetime
from typing import Optional
from uuid import UUID

from broker.event_broker import Query
from broker.event import Event
from callback.payload_schemes import Payload, PayloadCheck, Inner
from core.config import bot_info
from status.status_shemes import *
from status.status_crud import get_status


def create_status(
    type: Optional[str] = None,
    action: Optional[str] = None,
    uuid: Optional[UUID] = None,
    inner: Optional[str | list[str]] = None,
    name: Optional[str] = None,
    is_background: Optional[bool] = None,
    send_callback: Optional[bool] = None,
) -> Status:
    """Функция для удобного создания Payload статуса"""

    if (type is None or action is None) and not (
            type is None and action is None or type is not None and action is not None):
        raise ValueError("Неправильные аргументы для создания статуса: type и action должны либо оба отсутствовать либо оба быть переданными")

    if type is not None and action is not None:
        payload = Payload(type=type, uuid=uuid, action=action, inner=Inner(value=inner))
    else:
        payload = None


    status_kwargs = {
        "name": name,
        "payload": payload,
        "is_background": is_background,
        "send_callback": send_callback,
    }

    if is_background is None:
        status_kwargs.pop("is_background")
    if send_callback is None:
        status_kwargs.pop("send_callback")

    status = Status(**status_kwargs)

    return status


async def add_status_query(queries: list[Query]) -> list[Query]:
    status = None
    status_query = None

    for query in queries:
        if query.message is not None:
            sender_id = query.message.sender.user_id
            recipient_id = query.message.recipient.user_id

            user_id = sender_id if sender_id != bot_info.my_id else recipient_id

            status = get_status(user_id)

            if sender_id != bot_info.my_id:
                if status is not None and status.send_callback:
                        status_query = deepcopy(query)
                        status_query.event = Event.STATUS_CALLBACK(
                            name=status.name, payload=status.payload
                            )
                        status_query.real_payload = status.payload

            break

    if status is not None and not status.is_background:
        for query in queries:
            query.status = status

    if status_query is not None:
        queries.append(status_query)

    return queries
