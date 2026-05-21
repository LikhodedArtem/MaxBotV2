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
    type: str,
    action: str,
    uuid: Optional[UUID] = None,
    inner: Optional[str | list[str]] = None,
    name: Optional[str] = None,
    is_background: Optional[bool] = None,
    send_callback: Optional[bool] = None,
) -> Status:
    """Функция для удобного создания Payload статуса"""

    payload = Payload(type=type, uuid=uuid, action=action, inner=Inner(value=inner))

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
    for query in queries:
        if query.message is not None:
            sender_id = query.message.sender.user_id
            recipient_id = query.message.recipient.user_id

            status = get_status(
                sender_id if sender_id != bot_info.my_id else recipient_id
            )

            if status is None:
                continue

            query.status = status

            if not status.is_background or status.send_callback:
                if not status.is_background:
                    queries = []

                if status.send_callback:
                    status_query = deepcopy(query)
                    status_query.event = Event.STATUS_CALLBACK(
                        name=status.name, payload=status.payload
                    )
                    queries.append(status_query)

                break

    return queries
